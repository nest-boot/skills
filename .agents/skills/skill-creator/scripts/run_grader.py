#!/usr/bin/env python3
"""Grade one completed skill evaluation run with a high-reasoning Codex call."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts.codex_exec import (
    build_codex_exec_command,
    reasoning_config,
    require_codex_cli,
)
from scripts.eval_manifest import load_run_context


GRADER_INSTRUCTIONS = SKILL_ROOT / "agents" / "grader.md"
GRADING_SCHEMA = SKILL_ROOT / "references" / "grading.schema.json"
GRADER_REASONING_CONFIG = reasoning_config("high")


def require_completed_run(run_dir: Path) -> None:
    """Reject grading when the executor did not finish successfully."""
    for path in (run_dir / "outputs" / "metrics.json", run_dir / "timing.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Invalid grader input: {path}") from error
        if (
            data.get("run_status") != "completed"
            or data.get("exit_code", 0) != 0
            or data.get("isolation_violations")
        ):
            raise ValueError(f"Run is not completed successfully: {path}")


def build_grader_command(
    run_dir: Path,
    eval_metadata_path: Path,
    output_path: Path,
    model: str | None = None,
) -> list[str]:
    """Build the isolated Codex command for grading a single run."""
    run_dir = run_dir.resolve()
    eval_metadata_path = eval_metadata_path.resolve()
    output_path = output_path.resolve()
    trace_path = run_dir / "trace.jsonl"
    final_response_path = run_dir / "outputs" / "final.md"
    outputs_dir = run_dir / "outputs"

    prompt = (
        f"Read {GRADER_INSTRUCTIONS}. Grade only this run using expectations "
        f"from {eval_metadata_path}, the Codex trace at {trace_path}, the final "
        f"response at {final_response_path}, and deliverables under "
        f"{outputs_dir}. Return the rubric result."
    )

    command = build_codex_exec_command(
        reasoning_effort="high",
        sandbox="read-only",
        model=model,
    )
    command.extend([
        "-C",
        str(run_dir),
        "--output-schema",
        str(GRADING_SCHEMA),
        "-o",
        str(output_path),
        prompt,
    ])
    return command


def run_grader(
    run_dir: Path,
) -> int:
    """Grade one prepared run using only its enclosing manifests."""
    context = load_run_context(run_dir)
    run_dir = context.run_dir
    eval_metadata_path = context.eval_metadata_path
    output_path = run_dir / "grading.json"

    required_paths = [
        run_dir,
        eval_metadata_path,
        run_dir / "trace.jsonl",
        run_dir / "outputs",
        run_dir / "outputs" / "final.md",
        run_dir / "outputs" / "metrics.json",
        run_dir / "timing.json",
        GRADER_INSTRUCTIONS,
        GRADING_SCHEMA,
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise ValueError("Missing grader input(s): " + ", ".join(missing))
    require_completed_run(run_dir)
    require_codex_cli()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        build_grader_command(
            run_dir,
            eval_metadata_path,
            output_path,
            context.model,
        ),
        text=True,
    )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grade one completed skill evaluation run",
    )
    parser.add_argument(
        "run_dir",
        type=Path,
        help="Completed run directory below an iteration manifest",
    )
    args = parser.parse_args()

    try:
        return run_grader(args.run_dir)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
