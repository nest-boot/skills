"""Shared manifest validation and run-context resolution for skill evals."""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts.create_eval_workspace import (
    load_workspace_metadata,
    validate_run_directory,
    validate_workspace_location,
)
from scripts.utils import parse_skill_md, validate_skill_name


ITERATION_MANIFEST = "iteration.json"
ITERATION_SCHEMA_VERSION = 1
EVAL_METADATA = "eval_metadata.json"
CONFIG_NEW = "new_skill"
CONFIG_OLD = "old_skill"
CONFIG_WITHOUT = "without_skill"


@dataclass(frozen=True)
class RunContext:
    """Resolved immutable inputs for one prepared run directory."""

    workspace: Path
    iteration_dir: Path
    run_dir: Path
    eval_dir: Path
    eval_metadata_path: Path
    eval_metadata: dict
    manifest: dict
    configuration: str
    run_number: int
    model: str
    skill_path: Path | None
    protected_skill_paths: tuple[Path, ...]


def read_json_object(path: Path, label: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid {label}: {path}") from error
    if not isinstance(data, dict):
        raise ValueError(f"Invalid {label}: {path}")
    return data


def resolve_manifest_path(root: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Iteration manifest is missing {field}")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Iteration manifest has unsafe {field}: {value}")
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(
            f"Iteration manifest path escapes its iteration: {value}"
        ) from error
    return resolved


def _validate_skill_snapshot(path: Path, expected_name: str, field: str) -> None:
    if not (path / "SKILL.md").is_file():
        raise ValueError(f"Missing {field}: {path}")
    name, _, _ = parse_skill_md(path)
    if validate_skill_name(name) != expected_name:
        raise ValueError(f"{field} skill name does not match {expected_name}")


def load_eval_metadata(path: Path, expected_id: int, expected_name: str) -> dict:
    metadata = read_json_object(path, "eval metadata")
    if metadata.get("eval_id") != expected_id:
        raise ValueError(f"Eval metadata ID mismatch: {path}")
    if metadata.get("eval_name") != expected_name:
        raise ValueError(f"Eval metadata name mismatch: {path}")
    if not isinstance(metadata.get("prompt"), str) or not metadata["prompt"].strip():
        raise ValueError(f"Eval metadata has no prompt: {path}")
    expectations = metadata.get("expectations")
    if not isinstance(expectations, list) or not all(
        isinstance(item, str) and item.strip() for item in expectations
    ):
        raise ValueError(f"Eval metadata has invalid expectations: {path}")
    return metadata


def load_iteration_manifest(iteration_dir: Path) -> dict:
    """Load and validate an iteration manifest and its prepared layout."""
    iteration_dir = iteration_dir.resolve()
    manifest_path = iteration_dir / ITERATION_MANIFEST
    manifest = read_json_object(manifest_path, "iteration manifest")
    if manifest.get("schema_version") != ITERATION_SCHEMA_VERSION:
        raise ValueError(f"Unsupported iteration manifest: {manifest_path}")

    match = re.fullmatch(r"iteration-(\d+)", iteration_dir.name)
    if not match or manifest.get("iteration") != int(match.group(1)):
        raise ValueError(f"Iteration directory and manifest disagree: {iteration_dir}")

    skill_name = validate_skill_name(manifest.get("skill_name", ""))
    model = manifest.get("model")
    runs = manifest.get("runs")
    if not isinstance(model, str) or not model.strip():
        raise ValueError(f"Iteration manifest has no model: {manifest_path}")
    if not isinstance(runs, int) or isinstance(runs, bool) or runs < 1:
        raise ValueError(f"Iteration manifest has invalid run count: {manifest_path}")

    workspace_metadata = load_workspace_metadata(iteration_dir.parent)
    if workspace_metadata["skill_name"] != skill_name:
        raise ValueError("Iteration skill name does not match its workspace")
    validate_workspace_location(
        iteration_dir.parent,
        Path(workspace_metadata["source_skill"]),
    )

    candidate = manifest.get("candidate")
    if not isinstance(candidate, dict) or candidate.get("configuration") != CONFIG_NEW:
        raise ValueError(f"Iteration manifest has invalid candidate: {manifest_path}")
    candidate_path = manifest_path_value(
        iteration_dir,
        candidate.get("snapshot"),
    )
    _validate_skill_snapshot(candidate_path, skill_name, "candidate snapshot")

    baseline = manifest.get("baseline")
    if not isinstance(baseline, dict):
        raise ValueError(f"Iteration manifest has invalid baseline: {manifest_path}")
    baseline_kind = baseline.get("kind")
    baseline_configuration = baseline.get("configuration")
    if baseline_kind == "none":
        if baseline_configuration != CONFIG_WITHOUT or baseline.get("snapshot") is not None:
            raise ValueError(f"Iteration manifest has invalid no-skill baseline: {manifest_path}")
    elif baseline_kind in {"previous", "path"}:
        if baseline_configuration != CONFIG_OLD:
            raise ValueError(f"Iteration manifest has invalid old-skill baseline: {manifest_path}")
        baseline_path = manifest_path_value(iteration_dir, baseline.get("snapshot"))
        _validate_skill_snapshot(baseline_path, skill_name, "baseline snapshot")
        if baseline_kind == "previous":
            source_iteration = baseline.get("source_iteration")
            if not isinstance(source_iteration, str) or not re.fullmatch(
                r"iteration-\d+", source_iteration
            ):
                raise ValueError(
                    f"Iteration manifest has invalid previous baseline: {manifest_path}"
                )
        elif not isinstance(baseline.get("source"), str) or not baseline["source"]:
            raise ValueError(f"Iteration manifest has invalid path baseline: {manifest_path}")
    else:
        raise ValueError(f"Iteration manifest has unknown baseline: {manifest_path}")

    expected_configurations = [CONFIG_NEW, baseline_configuration]
    if manifest.get("configurations") != expected_configurations:
        raise ValueError(f"Iteration configurations are invalid: {manifest_path}")

    evals = manifest.get("evals")
    if not isinstance(evals, list) or not evals:
        raise ValueError(f"Iteration manifest has no evals: {manifest_path}")
    seen_ids: set[int] = set()
    seen_directories: set[str] = set()
    for entry in evals:
        if not isinstance(entry, dict):
            raise ValueError(f"Iteration manifest has invalid eval entry: {manifest_path}")
        eval_id = entry.get("id")
        eval_name = entry.get("name")
        directory = entry.get("directory")
        if not isinstance(eval_id, int) or isinstance(eval_id, bool) or eval_id < 0:
            raise ValueError(f"Iteration manifest has invalid eval ID: {manifest_path}")
        eval_name = validate_skill_name(eval_name)
        if not isinstance(directory, str) or not directory:
            raise ValueError(f"Iteration manifest has invalid eval directory: {manifest_path}")
        if eval_id in seen_ids or directory in seen_directories:
            raise ValueError(f"Iteration manifest has duplicate evals: {manifest_path}")
        seen_ids.add(eval_id)
        seen_directories.add(directory)
        eval_dir = resolve_manifest_path(iteration_dir, directory, "eval.directory")
        if eval_dir.parent != iteration_dir:
            raise ValueError(f"Eval directory must be directly under {iteration_dir}")
        load_eval_metadata(eval_dir / EVAL_METADATA, eval_id, eval_name)
        actual_configurations = {
            child.name for child in eval_dir.iterdir() if child.is_dir()
        }
        if actual_configurations != set(expected_configurations):
            raise ValueError(
                f"Eval configurations do not match iteration.json: {eval_dir}"
            )
        for configuration in expected_configurations:
            config_dir = eval_dir / configuration
            expected_runs = {
                f"run-{run_number}" for run_number in range(1, runs + 1)
            }
            actual_runs = {
                child.name for child in config_dir.iterdir() if child.is_dir()
            }
            if actual_runs != expected_runs:
                raise ValueError(
                    f"Run directories do not match iteration.json: {config_dir}"
                )
            for run_number in range(1, runs + 1):
                run_dir = eval_dir / configuration / f"run-{run_number}"
                if not run_dir.is_dir():
                    raise ValueError(f"Missing prepared run directory: {run_dir}")

    unexpected_evals = {
        child.name
        for child in iteration_dir.glob("eval-*")
        if child.is_dir() and child.name not in seen_directories
    }
    if unexpected_evals:
        raise ValueError(
            "Iteration contains undeclared eval directories: "
            + ", ".join(sorted(unexpected_evals))
        )

    previous_iteration = manifest.get("previous_iteration")
    if previous_iteration is not None and (
        not isinstance(previous_iteration, str)
        or not re.fullmatch(r"iteration-\d+", previous_iteration)
    ):
        raise ValueError(f"Iteration manifest has invalid previous_iteration: {manifest_path}")

    return manifest


def manifest_path_value(iteration_dir: Path, value: str) -> Path:
    return resolve_manifest_path(iteration_dir, value, "snapshot")


def load_run_context(run_dir: Path) -> RunContext:
    """Resolve one prepared run exclusively from its enclosing manifests."""
    run_dir = run_dir.resolve()
    workspace = validate_run_directory(run_dir)
    if not re.fullmatch(r"run-(\d+)", run_dir.name):
        raise ValueError(f"Invalid run directory name: {run_dir}")
    run_number = int(run_dir.name.removeprefix("run-"))
    configuration = run_dir.parent.name
    eval_dir = run_dir.parent.parent
    iteration_dir = eval_dir.parent
    manifest = load_iteration_manifest(iteration_dir)

    if iteration_dir.parent != workspace:
        raise ValueError(f"Run is not directly below an iteration: {run_dir}")
    if configuration not in manifest["configurations"]:
        raise ValueError(f"Run configuration is not in iteration.json: {run_dir}")
    if run_number < 1 or run_number > manifest["runs"]:
        raise ValueError(f"Run number is not in iteration.json: {run_dir}")

    eval_entry = next(
        (entry for entry in manifest["evals"] if entry["directory"] == eval_dir.name),
        None,
    )
    if eval_entry is None:
        raise ValueError(f"Eval directory is not in iteration.json: {eval_dir}")
    eval_metadata_path = eval_dir / EVAL_METADATA
    eval_metadata = load_eval_metadata(
        eval_metadata_path,
        eval_entry["id"],
        eval_entry["name"],
    )

    candidate_path = manifest_path_value(
        iteration_dir,
        manifest["candidate"]["snapshot"],
    )
    baseline = manifest["baseline"]
    if configuration == CONFIG_NEW:
        skill_path = candidate_path
    elif configuration == CONFIG_OLD:
        skill_path = manifest_path_value(iteration_dir, baseline["snapshot"])
    else:
        skill_path = None

    workspace_metadata = load_workspace_metadata(workspace)
    protected = {candidate_path.resolve()}
    original_sources = [Path(workspace_metadata["source_skill"])]
    if workspace_metadata.get("source_skill_lexical"):
        original_sources.append(Path(workspace_metadata["source_skill_lexical"]))
    for source in original_sources:
        source = source.expanduser().absolute()
        if (source / "SKILL.md").is_file():
            protected.add(source)
    if baseline.get("snapshot"):
        protected.add(
            manifest_path_value(iteration_dir, baseline["snapshot"]).resolve()
        )
    if baseline.get("kind") == "path":
        baseline_source = Path(baseline["source"]).expanduser().absolute()
        if (baseline_source / "SKILL.md").is_file():
            protected.add(baseline_source)

    return RunContext(
        workspace=workspace,
        iteration_dir=iteration_dir,
        run_dir=run_dir,
        eval_dir=eval_dir,
        eval_metadata_path=eval_metadata_path,
        eval_metadata=eval_metadata,
        manifest=manifest,
        configuration=configuration,
        run_number=run_number,
        model=manifest["model"],
        skill_path=skill_path,
        protected_skill_paths=tuple(sorted(protected, key=str)),
    )
