#!/usr/bin/env python3
"""Run one full skill test case through an isolated medium-reasoning Codex."""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts.codex_exec import (
    build_codex_exec_command,
    discover_global_skill_files,
    reasoning_config,
    require_codex_cli,
)
from scripts.collect_codex_metrics import load_jsonl, write_run_metrics
from scripts.eval_manifest import load_run_context
from scripts.utils import parse_skill_md, validate_skill_name


TEST_REASONING_CONFIG = reasoning_config("medium")
ISOLATION_VIOLATION_EXIT_CODE = 2
EVALUATION_ISOLATION_INSTRUCTION = (
    "Evaluation isolation: work only with files under the current run "
    "directory. Do not inspect, search, or use skills or source checkouts "
    "outside it, even if they are discoverable. If a skill is available for "
    "this run, use only its copy under .agents/skills/."
)
DELIVERABLE_INSTRUCTION = "Save requested deliverables under outputs/."


def build_test_command(
    run_dir: Path,
    output_path: Path,
    model: str | None = None,
) -> list[str]:
    """Build the Codex command for one full skill test run."""
    run_dir = run_dir.resolve()
    output_path = output_path.resolve()
    command = build_codex_exec_command(
        reasoning_effort="medium",
        sandbox="workspace-write",
        model=model,
    )
    command.extend([
        "--json",
        "-C",
        str(run_dir),
        "-o",
        str(output_path),
        "-",
    ])
    return command


def build_test_prompt(prompt: str) -> str:
    """Add stable isolation and output-location instructions to a prompt."""
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Test prompt must not be empty")
    return (
        f"{prompt}\n\n{EVALUATION_ISOLATION_INSTRUCTION}\n\n"
        f"{DELIVERABLE_INSTRUCTION}"
    )


def collect_protected_skill_roots(
    run_dir: Path,
    skill_paths: list[Path],
) -> list[Path]:
    """Resolve source copies whose use would contaminate an eval run."""
    run_dir = run_dir.resolve()
    roots: dict[str, Path] = {}
    skill_names = set()

    for raw_path in skill_paths:
        lexical_path = raw_path.expanduser().absolute()
        resolved_path = lexical_path.resolve()
        skill_file = resolved_path / "SKILL.md"
        if not skill_file.is_file():
            raise ValueError(f"No SKILL.md found at {raw_path}")
        if (
            resolved_path == run_dir
            or run_dir in resolved_path.parents
            or resolved_path in run_dir.parents
        ):
            raise ValueError(
                "Protected skill sources and run directories must be separate"
            )
        skill_name, _, _ = parse_skill_md(resolved_path)
        skill_names.add(validate_skill_name(skill_name))
        for path in (lexical_path, resolved_path):
            roots[str(path)] = path

    if skill_names:
        for skill_file in discover_global_skill_files():
            try:
                global_name, _, _ = parse_skill_md(skill_file.parent)
                global_name = validate_skill_name(global_name)
            except (OSError, ValueError):
                continue
            if global_name not in skill_names:
                continue
            for path in (skill_file.parent.absolute(), skill_file.parent.resolve()):
                roots[str(path)] = path

    return sorted(roots.values(), key=str)


def _path_needles(path: Path) -> set[str]:
    """Return common textual forms a tool trace may use for one path."""
    needles = {str(path)}
    home = Path.home().resolve()
    try:
        relative = path.resolve().relative_to(home).as_posix()
    except ValueError:
        return needles
    needles.update({
        f"~/{relative}",
        f"$HOME/{relative}",
        f"${{HOME}}/{relative}",
    })
    return needles


def audit_trace_for_protected_sources(
    trace_path: Path,
    protected_roots: list[Path],
) -> list[dict]:
    """Find tool activity that disclosed or used protected skill sources."""
    if not protected_roots:
        return []

    roots_and_needles = [
        (root, _path_needles(root))
        for root in protected_roots
    ]
    violations = []
    seen = set()
    for line_number, event in enumerate(load_jsonl(trace_path), start=1):
        if event.get("type") not in {"item.started", "item.completed"}:
            continue
        item = event.get("item", {})
        item_type = item.get("type", "unknown")
        if item_type in {"agent_message", "reasoning"}:
            continue
        payload = json.dumps(item, ensure_ascii=False, sort_keys=True)
        item_id = str(item.get("id", line_number))
        for root, needles in roots_and_needles:
            if not any(needle and needle in payload for needle in needles):
                continue
            key = (item_id, str(root))
            if key in seen:
                continue
            seen.add(key)
            violations.append({
                "event_line": line_number,
                "item_type": item_type,
                "protected_root": str(root),
            })
    return violations


def mark_run_contaminated(
    metrics_path: Path,
    timing_path: Path,
    violations: list[dict],
) -> None:
    """Persist isolation evidence and make completed runs ungradable."""
    for path in (metrics_path, timing_path):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["isolation_violations"] = violations
        if data.get("run_status") == "completed":
            data["run_status"] = "contaminated"
            if path == metrics_path:
                data["errors_encountered"] = (
                    data.get("errors_encountered", 0) + 1
                )
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def prepare_run_directory(
    run_dir: Path,
    skill_path: Path | None = None,
) -> tuple[Path, Path]:
    """Prepare an empty result layout and optionally install one skill copy."""
    run_dir = run_dir.resolve()
    trace_path = run_dir / "trace.jsonl"
    output_path = run_dir / "outputs" / "final.md"
    reserved_paths = [
        trace_path,
        output_path,
        run_dir / "outputs" / "metrics.json",
        run_dir / "timing.json",
    ]
    conflicts = [str(path) for path in reserved_paths if path.exists()]
    if conflicts:
        raise ValueError(
            "Run directory already contains result artifacts: "
            + ", ".join(conflicts)
        )

    skill_name = None
    if skill_path is not None:
        skill_path = skill_path.resolve()
        skill_file = skill_path / "SKILL.md"
        if not skill_file.is_file():
            raise ValueError(f"No SKILL.md found at {skill_path}")
        if skill_path == run_dir or skill_path in run_dir.parents:
            raise ValueError("Run directory must not be inside the source skill")

        skill_name, _, _ = parse_skill_md(skill_path)
        skill_name = validate_skill_name(skill_name)

    skills_dir = run_dir / ".agents" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if skill_path is not None:
        assert skill_name is not None
        target_path = skills_dir / skill_name
        if target_path.resolve().parent != skills_dir.resolve():
            raise ValueError(f"Skill fixture path escapes its root: {target_path}")
        if target_path.exists() or target_path.is_symlink():
            raise ValueError(f"Skill fixture already exists: {target_path}")
        shutil.copytree(skill_path, target_path)

    return trace_path, output_path


def run_test_case(run_dir: Path) -> int:
    """Execute one prepared run using only its enclosing manifests."""
    context = load_run_context(run_dir)
    run_dir = context.run_dir
    require_codex_cli()
    protected_roots = collect_protected_skill_roots(
        run_dir,
        list(context.protected_skill_paths),
    )
    trace_path, output_path = prepare_run_directory(
        run_dir,
        context.skill_path,
    )
    command = build_test_command(run_dir, output_path, context.model)
    test_prompt = build_test_prompt(context.eval_metadata["prompt"])

    started_at = time.monotonic()
    with trace_path.open("x", encoding="utf-8") as trace_file:
        result = subprocess.run(
            command,
            input=test_prompt,
            stdout=trace_file,
            text=True,
        )
    duration_seconds = time.monotonic() - started_at

    exit_code = result.returncode
    missing_final = exit_code == 0 and not output_path.is_file()
    if missing_final:
        exit_code = 1
    metrics_path, timing_path = write_run_metrics(
        trace_path,
        run_dir,
        duration_seconds=duration_seconds,
        exit_code=exit_code,
    )
    violations = audit_trace_for_protected_sources(
        trace_path,
        protected_roots,
    )
    if violations:
        mark_run_contaminated(metrics_path, timing_path, violations)
        if exit_code == 0:
            exit_code = ISOLATION_VIOLATION_EXIT_CODE
    if missing_final:
        raise RuntimeError(
            "codex exec exited successfully but did not write "
            f"{output_path}"
        )
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one isolated full skill test case",
    )
    parser.add_argument(
        "run_dir",
        type=Path,
        help="Prepared run directory below an iteration manifest",
    )
    args = parser.parse_args()

    try:
        return run_test_case(args.run_dir)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
