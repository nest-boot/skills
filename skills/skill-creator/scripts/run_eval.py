#!/usr/bin/env python3
"""Run Codex trigger evaluation for a skill description.

Tests whether a skill's description causes Codex to load the skill for a set
of queries. Outputs results as JSON.
"""

import argparse
import json
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from scripts.utils import parse_skill_md


def build_skill_fixture(
    skill_name: str,
    skill_description: str,
    marker: str,
) -> str:
    """Build a minimal SKILL.md that exposes a deterministic load marker."""
    indented_description = "\n  ".join(skill_description.splitlines())
    return (
        "---\n"
        f"name: {json.dumps(skill_name)}\n"
        "description: |\n"
        f"  {indented_description}\n"
        "---\n\n"
        "# Trigger evaluation fixture\n\n"
        "This temporary skill exists only for trigger evaluation. If you load "
        "this skill, include the following exact marker somewhere in your final "
        f"response: `{marker}`. Then handle the user's request normally.\n"
    )


def output_shows_skill_load(
    jsonl_output: str,
    marker: str,
    skill_file: Path,
    working_dir: Path,
) -> bool:
    """Detect a skill load from Codex JSONL command or agent-message events."""
    absolute_path = str(skill_file)
    relative_path = str(skill_file.relative_to(working_dir))

    for line in jsonl_output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        item = event.get("item", {})
        item_type = item.get("type")

        if item_type == "agent_message" and marker in item.get("text", ""):
            return True

        if item_type == "command_execution":
            serialized_item = json.dumps(item, ensure_ascii=False)
            if (
                marker in serialized_item
                or absolute_path in serialized_item
                or relative_path in serialized_item
            ):
                return True

    return False


def run_codex_until_skill_load(
    cmd: list[str],
    query: str,
    timeout: int,
    working_dir: Path,
    marker: str,
    skill_file: Path,
) -> bool:
    """Stream Codex JSONL and stop as soon as the skill load is observable."""
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=working_dir,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    line_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()

    def pump_stream(channel: str, stream) -> None:
        try:
            for line in iter(stream.readline, ""):
                line_queue.put((channel, line))
        finally:
            line_queue.put((channel, None))

    reader_threads = [
        threading.Thread(
            target=pump_stream,
            args=("stdout", process.stdout),
            daemon=True,
        ),
        threading.Thread(
            target=pump_stream,
            args=("stderr", process.stderr),
            daemon=True,
        ),
    ]
    for reader_thread in reader_threads:
        reader_thread.start()

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    open_streams = {"stdout", "stderr"}
    deadline = time.monotonic() + timeout

    try:
        process.stdin.write(query)
        process.stdin.close()

        while open_streams:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(
                    cmd,
                    timeout,
                    output="".join(stdout_lines),
                    stderr="".join(stderr_lines),
                )

            try:
                channel, line = line_queue.get(timeout=min(0.5, remaining))
            except queue.Empty:
                continue

            if line is None:
                open_streams.discard(channel)
                continue

            if channel == "stdout":
                stdout_lines.append(line)
                if output_shows_skill_load(
                    line,
                    marker,
                    skill_file,
                    working_dir,
                ):
                    return True
            else:
                stderr_lines.append(line)

        returncode = process.wait(timeout=max(0.1, deadline - time.monotonic()))
        if returncode != 0:
            raise RuntimeError(
                f"codex exec exited {returncode}\n"
                f"stderr: {''.join(stderr_lines)}"
            )

        return output_shows_skill_load(
            "".join(stdout_lines),
            marker,
            skill_file,
            working_dir,
        )
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()
        process.stderr.close()
        for reader_thread in reader_threads:
            reader_thread.join(timeout=1)


def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    model: str | None = None,
) -> bool:
    """Run a single query and return whether the skill was triggered.

    Creates an isolated .agents/skills fixture, runs `codex exec --json`, and
    detects either Codex reading the fixture's SKILL.md or emitting its marker.
    Isolation prevents concurrent eval workers from seeing one another's
    temporary skills.
    """
    marker = f"SKILL_TRIGGERED_{uuid.uuid4().hex}"

    with tempfile.TemporaryDirectory(prefix="skill-trigger-eval-") as temp_dir:
        working_dir = Path(temp_dir)
        skill_dir = working_dir / ".agents" / "skills" / skill_name
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            build_skill_fixture(skill_name, skill_description, marker),
            encoding="utf-8",
        )

        cmd = [
            "codex",
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--json",
        ]
        if model:
            cmd.extend(["--model", model])
        cmd.append("-")

        return run_codex_until_skill_load(
            cmd,
            query,
            timeout,
            working_dir,
            marker,
            skill_file,
        )


def summarize_query_result(
    item: dict,
    triggers: list[bool],
    errors: list[str],
    expected_runs: int,
    trigger_threshold: float,
) -> dict:
    """Summarize one eval item without treating missing runs as evidence."""
    completed_runs = len(triggers)
    trigger_rate = (
        sum(triggers) / completed_runs
        if completed_runs
        else None
    )

    if completed_runs == expected_runs and not errors:
        status = "completed"
        if item["should_trigger"]:
            did_pass = trigger_rate >= trigger_threshold
        else:
            did_pass = trigger_rate < trigger_threshold
    elif completed_runs:
        status = "incomplete"
        did_pass = False
    else:
        status = "error"
        did_pass = False

    return {
        "query": item["query"],
        "should_trigger": item["should_trigger"],
        "trigger_rate": trigger_rate,
        "triggers": sum(triggers),
        "runs": completed_runs,
        "expected_runs": expected_runs,
        "error_count": len(errors),
        "errors": errors,
        "status": status,
        "pass": did_pass,
    }


def run_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: str | None = None,
) -> dict:
    """Run the full eval set and return results."""
    if shutil.which("codex") is None:
        raise RuntimeError("codex CLI was not found on PATH")
    if num_workers < 1:
        raise ValueError("num_workers must be at least 1")
    if runs_per_query < 1:
        raise ValueError("runs_per_query must be at least 1")
    if not 0 <= trigger_threshold <= 1:
        raise ValueError("trigger_threshold must be between 0 and 1")

    results = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        query_triggers: dict[int, list[bool]] = {
            item_index: [] for item_index in range(len(eval_set))
        }
        query_errors: dict[int, list[str]] = {
            item_index: [] for item_index in range(len(eval_set))
        }

        for item_index, item in enumerate(eval_set):
            for run_idx in range(runs_per_query):
                future = executor.submit(
                    run_single_query,
                    item["query"],
                    skill_name,
                    description,
                    timeout,
                    model,
                )
                future_to_info[future] = (item_index, run_idx)

        for future in as_completed(future_to_info):
            item_index, _ = future_to_info[future]
            try:
                query_triggers[item_index].append(future.result())
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                query_errors[item_index].append(str(e))

    for item_index, item in enumerate(eval_set):
        results.append(summarize_query_result(
            item,
            query_triggers[item_index],
            query_errors[item_index],
            runs_per_query,
            trigger_threshold,
        ))

    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    error_count = sum(r["error_count"] for r in results)

    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "error_runs": error_count,
            "queries_with_errors": sum(
                1 for result in results if result["error_count"] > 0
            ),
            "incomplete_queries": sum(
                1 for result in results if result["status"] == "incomplete"
            ),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Run trigger evaluation for a skill description")
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override description to test")
    parser.add_argument("--num-workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per query in seconds")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Number of runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")
    parser.add_argument("--model", default=None, help="Model to use for codex exec (default: user's configured model)")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    eval_set = json.loads(Path(args.eval_set).read_text())
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, _ = parse_skill_md(skill_path)
    description = args.description or original_description
    if args.verbose:
        print(f"Evaluating: {description}", file=sys.stderr)

    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
    )

    if args.verbose:
        summary = output["summary"]
        print(f"Results: {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for r in output["results"]:
            if r["status"] == "error":
                status = "ERROR"
            elif r["status"] == "incomplete":
                status = "INCOMPLETE"
            else:
                status = "PASS" if r["pass"] else "FAIL"
            rate_str = (
                f"{r['triggers']}/{r['runs']} valid, "
                f"{r['runs']}/{r['expected_runs']} completed"
            )
            error_str = f" errors={r['error_count']}" if r["error_count"] else ""
            print(f"  [{status}] rate={rate_str}{error_str} expected={r['should_trigger']}: {r['query'][:70]}", file=sys.stderr)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
