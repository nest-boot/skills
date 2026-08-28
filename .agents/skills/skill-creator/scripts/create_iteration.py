#!/usr/bin/env python3
"""Snapshot skill versions and prepare one manifest-driven iteration."""

import argparse
import json
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts.create_eval_workspace import (
    load_workspace_metadata,
    validate_workspace_location,
)
from scripts.eval_manifest import (
    CONFIG_NEW,
    CONFIG_OLD,
    CONFIG_WITHOUT,
    EVAL_METADATA,
    ITERATION_MANIFEST,
    ITERATION_SCHEMA_VERSION,
    load_iteration_manifest,
    manifest_path_value,
    read_json_object,
)
from scripts.utils import parse_skill_md, validate_skill_name


def _eval_name(item: dict) -> str:
    explicit = item.get("name")
    if explicit is not None:
        return validate_skill_name(explicit)
    prompt = item.get("prompt", "")
    words = re.findall(r"[a-z0-9]+", prompt.lower())[:6]
    candidate = "-".join(words).strip("-")[:64].rstrip("-")
    if candidate:
        return validate_skill_name(candidate)
    return f"case-{item['id']}"


def _load_source_evals(source_skill: Path, skill_name: str) -> list[dict]:
    path = source_skill / "evals" / "evals.json"
    data = read_json_object(path, "source evals")
    if data.get("skill_name") != skill_name:
        raise ValueError(f"Eval skill name does not match {skill_name}: {path}")
    evals = data.get("evals")
    if not isinstance(evals, list) or not evals:
        raise ValueError(f"No evals found in {path}")

    normalized = []
    seen_ids: set[int] = set()
    seen_names: set[str] = set()
    for item in evals:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid eval in {path}")
        eval_id = item.get("id")
        prompt = item.get("prompt")
        expectations = item.get("expectations", [])
        files = item.get("files", [])
        if not isinstance(eval_id, int) or isinstance(eval_id, bool) or eval_id < 0:
            raise ValueError(f"Invalid eval ID in {path}")
        if eval_id in seen_ids:
            raise ValueError(f"Duplicate eval ID {eval_id} in {path}")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Eval {eval_id} has no prompt in {path}")
        if not isinstance(expectations, list) or not all(
            isinstance(value, str) and value.strip() for value in expectations
        ):
            raise ValueError(f"Eval {eval_id} has invalid expectations in {path}")
        if not isinstance(files, list) or not all(
            isinstance(value, str) and value for value in files
        ):
            raise ValueError(f"Eval {eval_id} has invalid files in {path}")
        name = _eval_name(item)
        if name in seen_names:
            raise ValueError(f"Duplicate eval name {name} in {path}")
        seen_ids.add(eval_id)
        seen_names.add(name)
        normalized.append({
            "id": eval_id,
            "name": name,
            "prompt": prompt,
            "expectations": expectations,
            "files": files,
        })
    return normalized


def _copy_path(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def _resolve_eval_input(source_skill: Path, relative: str) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError(f"Eval input path is unsafe: {relative}")
    source = (source_skill / raw).resolve()
    try:
        source.relative_to(source_skill.resolve())
    except ValueError as error:
        raise ValueError(f"Eval input escapes the source skill: {relative}") from error
    if not source.exists():
        raise ValueError(f"Eval input does not exist: {source}")
    return source


def _copy_skill(source: Path, destination: Path) -> None:
    name, _, _ = parse_skill_md(source)
    validate_skill_name(name)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def _existing_iterations(workspace: Path) -> list[tuple[int, Path, dict]]:
    iterations = []
    for path in workspace.glob("iteration-*"):
        match = re.fullmatch(r"iteration-(\d+)", path.name)
        if not match or not (path / ITERATION_MANIFEST).is_file():
            continue
        manifest = load_iteration_manifest(path)
        iterations.append((int(match.group(1)), path.resolve(), manifest))
    return sorted(iterations)


def create_iteration(
    workspace: Path,
    *,
    baseline: str,
    runs: int,
    model: str,
) -> Path:
    """Snapshot versions and deterministically prepare one complete iteration."""
    workspace = workspace.resolve()
    workspace_metadata = load_workspace_metadata(workspace)
    source_skill = Path(workspace_metadata["source_skill"]).resolve()
    validate_workspace_location(workspace, source_skill)
    if not isinstance(runs, int) or isinstance(runs, bool) or runs < 1:
        raise ValueError("Run count must be a positive integer")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Model must not be empty")

    skill_name = validate_skill_name(workspace_metadata["skill_name"])
    source_name, _, _ = parse_skill_md(source_skill)
    if validate_skill_name(source_name) != skill_name:
        raise ValueError("Workspace source skill identity has changed")
    evals = _load_source_evals(source_skill, skill_name)
    for item in evals:
        for relative in item["files"]:
            _resolve_eval_input(source_skill, relative)

    existing = _existing_iterations(workspace)
    iteration_number = existing[-1][0] + 1 if existing else 1
    previous = existing[-1] if existing else None
    iteration_name = f"iteration-{iteration_number}"
    destination = workspace / iteration_name
    if destination.exists():
        raise ValueError(f"Iteration already exists: {destination}")

    baseline_kind = baseline
    baseline_source = None
    source_iteration = None
    if baseline == "none":
        baseline_configuration = CONFIG_WITHOUT
    elif baseline == "previous":
        if previous is None:
            raise ValueError("A previous baseline requires an existing iteration")
        baseline_configuration = CONFIG_OLD
        source_iteration = previous[1].name
        baseline_source = manifest_path_value(
            previous[1],
            previous[2]["candidate"]["snapshot"],
        )
    else:
        baseline_kind = "path"
        baseline_configuration = CONFIG_OLD
        baseline_source = Path(baseline).expanduser().resolve()
        if not (baseline_source / "SKILL.md").is_file():
            raise ValueError(f"No baseline SKILL.md found at {baseline_source}")
        baseline_name, _, _ = parse_skill_md(baseline_source)
        if validate_skill_name(baseline_name) != skill_name:
            raise ValueError("Baseline skill name does not match workspace skill")

    staging = Path(tempfile.mkdtemp(prefix=f".{iteration_name}-", dir=workspace))
    try:
        candidate_relative = Path("snapshots") / CONFIG_NEW / skill_name
        _copy_skill(source_skill, staging / candidate_relative)

        baseline_relative = None
        if baseline_source is not None:
            baseline_relative = Path("snapshots") / CONFIG_OLD / skill_name
            _copy_skill(baseline_source, staging / baseline_relative)

        configurations = [CONFIG_NEW, baseline_configuration]
        eval_entries = []
        for item in evals:
            eval_directory = f"eval-{item['id']}-{item['name']}"
            eval_dir = staging / eval_directory
            eval_dir.mkdir(parents=True)
            metadata = {
                "eval_id": item["id"],
                "eval_name": item["name"],
                "prompt": item["prompt"],
                "expectations": item["expectations"],
            }
            (eval_dir / EVAL_METADATA).write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            for configuration in configurations:
                for run_number in range(1, runs + 1):
                    run_dir = eval_dir / configuration / f"run-{run_number}"
                    run_dir.mkdir(parents=True)
                    for relative in item["files"]:
                        source = _resolve_eval_input(source_skill, relative)
                        _copy_path(source, run_dir / relative)
            eval_entries.append({
                "id": item["id"],
                "name": item["name"],
                "directory": eval_directory,
            })

        baseline_manifest = {
            "kind": baseline_kind,
            "configuration": baseline_configuration,
            "snapshot": str(baseline_relative) if baseline_relative else None,
        }
        if source_iteration is not None:
            baseline_manifest["source_iteration"] = source_iteration
        if baseline_kind == "path":
            assert baseline_source is not None
            baseline_manifest["source"] = str(baseline_source)

        manifest = {
            "schema_version": ITERATION_SCHEMA_VERSION,
            "iteration": iteration_number,
            "skill_name": skill_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": model.strip(),
            "runs": runs,
            "candidate": {
                "configuration": CONFIG_NEW,
                "snapshot": str(candidate_relative),
            },
            "baseline": baseline_manifest,
            "configurations": configurations,
            "previous_iteration": previous[1].name if previous else None,
            "evals": eval_entries,
        }
        (staging / ITERATION_MANIFEST).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        staging.rename(destination)
        load_iteration_manifest(destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        elif destination.exists():
            shutil.rmtree(destination)
        raise

    return destination.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Snapshot skill versions and prepare one evaluation iteration",
    )
    parser.add_argument("workspace", type=Path, help="Marked evaluation workspace")
    parser.add_argument(
        "--baseline",
        required=True,
        help="Baseline: none, previous, or a path to an existing skill",
    )
    parser.add_argument("--runs", required=True, type=int, help="Runs per configuration")
    parser.add_argument("--model", required=True, help="Codex model for execution and grading")
    args = parser.parse_args()

    try:
        iteration_dir = create_iteration(
            args.workspace,
            baseline=args.baseline,
            runs=args.runs,
            model=args.model,
        )
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(iteration_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
