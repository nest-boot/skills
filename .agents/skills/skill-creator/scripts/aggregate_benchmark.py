#!/usr/bin/env python3
"""
Aggregate individual run results into benchmark summary statistics.

Reads grading.json files from run directories and produces:
- run_summary with mean, stddev, min, max for each metric
- delta between the candidate and declared baseline configurations

Usage:
    python aggregate_benchmark.py <iteration-dir>

The iteration manifest is the source of truth for evals, configurations,
model, and run count. Missing, extra, incomplete, or ungraded expected runs
are rejected instead of being silently omitted from the benchmark.
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts.eval_manifest import load_iteration_manifest


def calculate_stats(values: list[float]) -> dict:
    """Calculate mean, stddev, min, max for a list of values."""
    if not values:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}

    n = len(values)
    mean = sum(values) / n

    if n > 1:
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        stddev = math.sqrt(variance)
    else:
        stddev = 0.0

    return {
        "mean": round(mean, 4),
        "stddev": round(stddev, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4)
    }


def _load_json(path: Path, label: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid {label}: {path}") from error
    if not isinstance(data, dict):
        raise ValueError(f"Invalid {label}: {path}")
    return data


def load_completed_execution(run_dir: Path) -> tuple[dict, dict]:
    """Require matching completed metrics and timing for one run."""
    metrics_path = run_dir / "outputs" / "metrics.json"
    timing_path = run_dir / "timing.json"
    metrics = _load_json(metrics_path, "execution metrics")
    timing = _load_json(timing_path, "execution timing")
    for path, data in ((metrics_path, metrics), (timing_path, timing)):
        status = data.get("run_status")
        if status != "completed":
            raise RuntimeError(
                f"Cannot aggregate {run_dir}: execution status is {status} in {path}"
            )
        if data.get("exit_code", 0) != 0:
            raise RuntimeError(
                f"Cannot aggregate {run_dir}: nonzero exit code in {path}"
            )
        if data.get("isolation_violations"):
            raise RuntimeError(
                f"Cannot aggregate {run_dir}: isolation violations in {path}"
            )
    return metrics, timing


def load_run_results(iteration_dir: Path) -> dict:
    """Load exactly the runs declared by one iteration manifest."""
    iteration_dir = iteration_dir.resolve()
    manifest = load_iteration_manifest(iteration_dir)
    results: dict[str, list] = {
        configuration: [] for configuration in manifest["configurations"]
    }

    for eval_entry in manifest["evals"]:
        eval_dir = iteration_dir / eval_entry["directory"]
        for configuration in manifest["configurations"]:
            for run_number in range(1, manifest["runs"] + 1):
                run_dir = eval_dir / configuration / f"run-{run_number}"
                metrics, timing = load_completed_execution(run_dir)
                grading_file = run_dir / "grading.json"
                grading = _load_json(grading_file, "grading result")
                summary = grading.get("summary")
                if not isinstance(summary, dict):
                    raise ValueError(f"Invalid grading summary: {grading_file}")

                raw_expectations = grading.get("expectations")
                if not isinstance(raw_expectations, list):
                    raise ValueError(f"Invalid grading expectations: {grading_file}")
                for expectation in raw_expectations:
                    if not isinstance(expectation, dict) or not all(
                        field in expectation for field in ("text", "passed", "evidence")
                    ):
                        raise ValueError(
                            f"Invalid grading expectation in {grading_file}"
                        )

                notes_summary = grading.get("user_notes_summary", {})
                if not isinstance(notes_summary, dict):
                    raise ValueError(f"Invalid grader notes: {grading_file}")
                notes = []
                for key in ("uncertainties", "needs_review", "workarounds"):
                    values = notes_summary.get(key, [])
                    if isinstance(values, list):
                        notes.extend(values)

                results[configuration].append({
                    "eval_id": eval_entry["id"],
                    "eval_name": eval_entry["name"],
                    "run_number": run_number,
                    "pass_rate": summary.get("pass_rate", 0.0),
                    "passed": summary.get("passed", 0),
                    "failed": summary.get("failed", 0),
                    "total": summary.get("total", 0),
                    "time_seconds": timing.get("total_duration_seconds", 0.0),
                    "tokens": timing.get("total_tokens", metrics.get("total_tokens", 0)),
                    "tool_calls": metrics.get("total_tool_calls", 0),
                    "errors": metrics.get("errors_encountered", 0),
                    "expectations": raw_expectations,
                    "notes": notes,
                })

    return results


def aggregate_results(results: dict) -> dict:
    """
    Aggregate run results into summary statistics.

    Returns run_summary with stats for each configuration and delta.
    """
    run_summary = {}
    configs = list(results.keys())

    for config in configs:
        runs = results.get(config, [])

        if not runs:
            run_summary[config] = {
                "pass_rate": {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0},
                "time_seconds": {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0},
                "tokens": {"mean": 0, "stddev": 0, "min": 0, "max": 0}
            }
            continue

        pass_rates = [r["pass_rate"] for r in runs]
        times = [r["time_seconds"] for r in runs]
        tokens = [r.get("tokens", 0) for r in runs]

        run_summary[config] = {
            "pass_rate": calculate_stats(pass_rates),
            "time_seconds": calculate_stats(times),
            "tokens": calculate_stats(tokens)
        }

    # Calculate delta between the first two configs (if two exist)
    if len(configs) >= 2:
        primary = run_summary.get(configs[0], {})
        baseline = run_summary.get(configs[1], {})
    else:
        primary = run_summary.get(configs[0], {}) if configs else {}
        baseline = {}

    delta_pass_rate = primary.get("pass_rate", {}).get("mean", 0) - baseline.get("pass_rate", {}).get("mean", 0)
    delta_time = primary.get("time_seconds", {}).get("mean", 0) - baseline.get("time_seconds", {}).get("mean", 0)
    delta_tokens = primary.get("tokens", {}).get("mean", 0) - baseline.get("tokens", {}).get("mean", 0)

    run_summary["delta"] = {
        "pass_rate": f"{delta_pass_rate:+.2f}",
        "time_seconds": f"{delta_time:+.1f}",
        "tokens": f"{delta_tokens:+.0f}"
    }

    return run_summary


def generate_benchmark(iteration_dir: Path) -> dict:
    """
    Generate complete benchmark.json from one declared iteration.
    """
    iteration_dir = iteration_dir.resolve()
    manifest = load_iteration_manifest(iteration_dir)
    results = load_run_results(iteration_dir)
    run_summary = aggregate_results(results)

    # Build runs array for benchmark.json
    runs = []
    for config in results:
        for result in results[config]:
            runs.append({
                "eval_id": result["eval_id"],
                "eval_name": result["eval_name"],
                "configuration": config,
                "run_number": result["run_number"],
                "result": {
                    "pass_rate": result["pass_rate"],
                    "passed": result["passed"],
                    "failed": result["failed"],
                    "total": result["total"],
                    "time_seconds": result["time_seconds"],
                    "tokens": result.get("tokens", 0),
                    "tool_calls": result.get("tool_calls", 0),
                    "errors": result.get("errors", 0)
                },
                "expectations": result["expectations"],
                "notes": result["notes"]
            })

    # Determine eval IDs from results
    eval_ids = sorted(set(
        r["eval_id"]
        for config in results.values()
        for r in config
    ))

    run_counts_by_configuration = {
        config: {
            str(eval_entry["id"]): manifest["runs"]
            for eval_entry in manifest["evals"]
        }
        for config in manifest["configurations"]
    }
    candidate_path = (
        iteration_dir / manifest["candidate"]["snapshot"]
    ).resolve()

    benchmark = {
        "metadata": {
            "skill_name": manifest["skill_name"],
            "skill_path": str(candidate_path),
            "executor_model": manifest["model"],
            "analyzer_model": manifest["model"],
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "evals_run": eval_ids,
            "runs_per_configuration": manifest["runs"],
            "run_counts_by_configuration": run_counts_by_configuration,
        },
        "runs": runs,
        "run_summary": run_summary,
        "notes": []  # To be filled by analyzer
    }

    return benchmark


def generate_markdown(benchmark: dict) -> str:
    """Generate human-readable benchmark.md from benchmark data."""
    metadata = benchmark["metadata"]
    run_summary = benchmark["run_summary"]

    # Determine config names (excluding "delta")
    configs = [k for k in run_summary if k != "delta"]
    config_a = configs[0] if len(configs) >= 1 else "config_a"
    config_b = configs[1] if len(configs) >= 2 else "config_b"
    label_a = config_a.replace("_", " ").title()
    label_b = config_b.replace("_", " ").title()

    lines = [
        f"# Skill Benchmark: {metadata['skill_name']}",
        "",
        f"**Model**: {metadata['executor_model']}",
        f"**Date**: {metadata['timestamp']}",
        f"**Evals**: {', '.join(map(str, metadata['evals_run']))} ({metadata['runs_per_configuration']} runs each per configuration)",
        "",
        "## Summary",
        "",
        f"| Metric | {label_a} | {label_b} | Delta |",
        "|--------|------------|---------------|-------|",
    ]

    a_summary = run_summary.get(config_a, {})
    b_summary = run_summary.get(config_b, {})
    delta = run_summary.get("delta", {})

    # Format pass rate
    a_pr = a_summary.get("pass_rate", {})
    b_pr = b_summary.get("pass_rate", {})
    lines.append(f"| Pass Rate | {a_pr.get('mean', 0)*100:.0f}% ± {a_pr.get('stddev', 0)*100:.0f}% | {b_pr.get('mean', 0)*100:.0f}% ± {b_pr.get('stddev', 0)*100:.0f}% | {delta.get('pass_rate', '—')} |")

    # Format time
    a_time = a_summary.get("time_seconds", {})
    b_time = b_summary.get("time_seconds", {})
    lines.append(f"| Time | {a_time.get('mean', 0):.1f}s ± {a_time.get('stddev', 0):.1f}s | {b_time.get('mean', 0):.1f}s ± {b_time.get('stddev', 0):.1f}s | {delta.get('time_seconds', '—')}s |")

    # Format tokens
    a_tokens = a_summary.get("tokens", {})
    b_tokens = b_summary.get("tokens", {})
    lines.append(f"| Tokens | {a_tokens.get('mean', 0):.0f} ± {a_tokens.get('stddev', 0):.0f} | {b_tokens.get('mean', 0):.0f} ± {b_tokens.get('stddev', 0):.0f} | {delta.get('tokens', '—')} |")

    # Notes section
    if benchmark.get("notes"):
        lines.extend([
            "",
            "## Notes",
            ""
        ])
        for note in benchmark["notes"]:
            lines.append(f"- {note}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate benchmark run results into summary statistics"
    )
    parser.add_argument(
        "iteration_dir",
        type=Path,
        help="Prepared iteration directory"
    )

    args = parser.parse_args()

    if not args.iteration_dir.exists():
        print(f"Directory not found: {args.iteration_dir}")
        sys.exit(1)

    # Generate benchmark
    try:
        benchmark = generate_benchmark(args.iteration_dir)
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    # Determine output paths
    output_json = args.iteration_dir / "benchmark.json"
    output_md = args.iteration_dir / "benchmark.md"

    # Write benchmark.json
    with open(output_json, "w") as f:
        json.dump(benchmark, f, indent=2)
    print(f"Generated: {output_json}")

    # Write benchmark.md
    markdown = generate_markdown(benchmark)
    with open(output_md, "w") as f:
        f.write(markdown)
    print(f"Generated: {output_md}")

    # Print summary
    run_summary = benchmark["run_summary"]
    configs = [k for k in run_summary if k != "delta"]
    delta = run_summary.get("delta", {})

    print(f"\nSummary:")
    for config in configs:
        pr = run_summary[config]["pass_rate"]["mean"]
        label = config.replace("_", " ").title()
        print(f"  {label}: {pr*100:.1f}% pass rate")
    print(f"  Delta:         {delta.get('pass_rate', '—')}")


if __name__ == "__main__":
    main()
