#!/usr/bin/env python3
"""Extract deterministic execution metrics from `codex exec --json` output."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


NON_TOOL_ITEM_TYPES = {"agent_message", "reasoning"}


def load_jsonl(trace_path: Path) -> list[dict]:
    """Load a Codex JSONL trace and fail with a useful line-number error."""
    events = []
    for line_number, line in enumerate(
        trace_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid JSONL in {trace_path} at line {line_number}: {error}"
            ) from error
        if not isinstance(event, dict):
            raise ValueError(
                f"Expected a JSON object in {trace_path} at line {line_number}"
            )
        events.append(event)
    return events


def collect_metrics(
    events: list[dict],
    exit_code: int | None = None,
) -> dict:
    """Summarize tool usage, failures, messages, and token usage."""
    tool_calls: Counter[str] = Counter()
    total_steps = 0
    errors_encountered = 0
    transcript_chars = 0
    usage: Counter[str] = Counter()
    turns_completed = 0
    turns_failed = 0

    for event in events:
        event_type = event.get("type", "")

        if event_type == "item.completed":
            item = event.get("item", {})
            item_type = item.get("type", "unknown")
            total_steps += 1

            if item_type not in NON_TOOL_ITEM_TYPES:
                tool_calls[item_type] += 1

            if item.get("status") in {"failed", "error"}:
                errors_encountered += 1

            if item_type == "agent_message":
                transcript_chars += len(item.get("text", ""))

        elif event_type == "turn.failed":
            turns_failed += 1
            errors_encountered += 1

        elif event_type == "error":
            errors_encountered += 1

        elif event_type == "turn.completed":
            turns_completed += 1
            for key, value in event.get("usage", {}).items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    usage[key] += value

    if exit_code not in (None, 0) or turns_failed:
        run_status = "failed"
    elif turns_completed:
        run_status = "completed"
    else:
        run_status = "incomplete"

    # A missing terminal event or nonzero exit is itself a failure signal.
    # Without this increment, an empty or CLI-failed trace could look clean.
    if run_status != "completed" and errors_encountered == 0:
        errors_encountered = 1

    total_tokens = usage.get("total_tokens", 0)
    if not total_tokens:
        total_tokens = usage.get("input_tokens", 0) + usage.get(
            "output_tokens",
            0,
        )

    result = {
        "tool_calls": dict(sorted(tool_calls.items())),
        "total_tool_calls": sum(tool_calls.values()),
        "total_steps": total_steps,
        "errors_encountered": errors_encountered,
        "transcript_chars": transcript_chars,
        "run_status": run_status,
        "turns_completed": turns_completed,
        "turns_failed": turns_failed,
        "usage": dict(sorted(usage.items())),
        "total_tokens": total_tokens,
    }
    if exit_code is not None:
        result["exit_code"] = exit_code
    return result


def write_run_metrics(
    trace_path: Path,
    run_dir: Path,
    duration_seconds: float | None = None,
    exit_code: int | None = None,
) -> tuple[Path, Path]:
    """Write metrics.json and timing.json for one Codex eval run."""
    metrics = collect_metrics(load_jsonl(trace_path), exit_code=exit_code)

    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = outputs_dir / "metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2) + "\n",
        encoding="utf-8",
    )

    timing = {
        "total_tokens": metrics["total_tokens"],
        "source": "codex-exec-jsonl",
        "run_status": metrics["run_status"],
    }
    if exit_code is not None:
        timing["exit_code"] = exit_code
    if duration_seconds is not None:
        timing["duration_ms"] = round(duration_seconds * 1000)
        timing["total_duration_seconds"] = duration_seconds

    timing_path = run_dir / "timing.json"
    timing_path.write_text(
        json.dumps(timing, indent=2) + "\n",
        encoding="utf-8",
    )

    return metrics_path, timing_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect metrics from a codex exec --json trace",
    )
    parser.add_argument("trace", help="Path to the Codex JSONL trace")
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Run directory that will receive outputs/metrics.json and timing.json",
    )
    parser.add_argument(
        "--duration-seconds",
        type=float,
        default=None,
        help="Measured wall-clock duration for the Codex run",
    )
    parser.add_argument(
        "--exit-code",
        type=int,
        default=None,
        help="Exit code returned by codex exec",
    )
    args = parser.parse_args()

    try:
        metrics_path, timing_path = write_run_metrics(
            Path(args.trace),
            Path(args.run_dir),
            args.duration_seconds,
            args.exit_code,
        )
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print(metrics_path)
    print(timing_path)


if __name__ == "__main__":
    main()
