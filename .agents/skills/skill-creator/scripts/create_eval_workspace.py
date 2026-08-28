#!/usr/bin/env python3
"""Create and validate an isolated temporary skill-evaluation workspace."""

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts.utils import parse_skill_md, validate_skill_name


WORKSPACE_MARKER = ".skill-creator-workspace.json"
WORKSPACE_SCHEMA_VERSION = 1


def path_is_within(path: Path, parent: Path) -> bool:
    """Return whether path is parent or one of its descendants."""
    path = path.resolve()
    parent = parent.resolve()
    return path == parent or parent in path.parents


def find_repository_root(path: Path) -> Path | None:
    """Return the nearest Git repository root discoverable from path."""
    path = path.resolve()
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def find_ancestor_skill_roots(path: Path) -> list[Path]:
    """Return .agents/skills directories above path, excluding path itself."""
    path = path.resolve()
    roots = []
    for ancestor in path.parents:
        skill_root = ancestor / ".agents" / "skills"
        if skill_root.is_dir():
            roots.append(skill_root)
    return roots


def validate_workspace_location(
    workspace: Path,
    source_skill: Path,
) -> None:
    """Reject workspace locations that can inherit repository context."""
    workspace = workspace.resolve()
    source_skill = source_skill.resolve()

    if path_is_within(workspace, source_skill):
        raise ValueError("Evaluation workspace must be outside the source skill")

    repository_root = find_repository_root(workspace)
    if repository_root is not None:
        raise ValueError(
            "Evaluation workspace must be outside a Git repository: "
            f"{repository_root}"
        )

    skill_roots = find_ancestor_skill_roots(workspace)
    if skill_roots:
        raise ValueError(
            "Evaluation workspace inherits ancestor skill root(s): "
            + ", ".join(str(path) for path in skill_roots)
        )


def workspace_metadata(
    skill_name: str,
    source_skill: Path,
    source_skill_lexical: Path | None = None,
) -> dict:
    """Build the marker payload for a new evaluation workspace."""
    return {
        "schema_version": WORKSPACE_SCHEMA_VERSION,
        "skill_name": skill_name,
        "source_skill": str(source_skill.resolve()),
        "source_skill_lexical": str(
            (source_skill_lexical or source_skill).expanduser().absolute()
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def create_eval_workspace(
    source_skill: Path,
    *,
    temp_parent: Path | None = None,
) -> Path:
    """Create, validate, and mark a persistent temporary eval workspace."""
    source_skill_lexical = source_skill.expanduser().absolute()
    source_skill = source_skill_lexical.resolve()
    skill_file = source_skill / "SKILL.md"
    if not skill_file.is_file():
        raise ValueError(f"No SKILL.md found at {source_skill}")

    skill_name, _, _ = parse_skill_md(source_skill)
    skill_name = validate_skill_name(skill_name)

    parent = temp_parent.resolve() if temp_parent is not None else None
    if parent is not None and not parent.is_dir():
        raise ValueError(f"Temporary parent is not a directory: {parent}")

    workspace = Path(tempfile.mkdtemp(
        prefix=f"{skill_name}-workspace-",
        dir=str(parent) if parent is not None else None,
    )).resolve()
    marker_path = workspace / WORKSPACE_MARKER
    try:
        validate_workspace_location(workspace, source_skill)
        with marker_path.open("x", encoding="utf-8") as marker_file:
            json.dump(
                workspace_metadata(
                    skill_name,
                    source_skill,
                    source_skill_lexical,
                ),
                marker_file,
                indent=2,
                sort_keys=True,
            )
            marker_file.write("\n")
    except (OSError, ValueError):
        if marker_path.exists():
            marker_path.unlink()
        workspace.rmdir()
        raise

    return workspace


def find_workspace_root(run_dir: Path) -> Path | None:
    """Find the marked evaluation workspace containing a run directory."""
    run_dir = run_dir.resolve()
    for candidate in (run_dir, *run_dir.parents):
        if (candidate / WORKSPACE_MARKER).is_file():
            return candidate
    return None


def load_workspace_metadata(workspace: Path) -> dict:
    """Load and validate one workspace marker."""
    marker_path = workspace.resolve() / WORKSPACE_MARKER
    try:
        metadata = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Invalid evaluation workspace marker: {marker_path}"
        ) from error

    if not isinstance(metadata, dict):
        raise ValueError(f"Invalid evaluation workspace marker: {marker_path}")
    if metadata.get("schema_version") != WORKSPACE_SCHEMA_VERSION:
        raise ValueError(f"Unsupported evaluation workspace marker: {marker_path}")
    for field in ("skill_name", "source_skill", "created_at"):
        if not isinstance(metadata.get(field), str) or not metadata[field]:
            raise ValueError(
                f"Evaluation workspace marker is missing {field}: {marker_path}"
            )
    source_skill_lexical = metadata.get("source_skill_lexical")
    if source_skill_lexical is not None and (
        not isinstance(source_skill_lexical, str) or not source_skill_lexical
    ):
        raise ValueError(
            "Evaluation workspace marker has invalid source_skill_lexical: "
            f"{marker_path}"
        )
    return metadata


def validate_run_directory(run_dir: Path) -> Path:
    """Require a run directory inside a still-isolated marked workspace."""
    run_dir = run_dir.resolve()
    workspace = find_workspace_root(run_dir)
    if workspace is None:
        raise ValueError(
            "Run directory must be inside a workspace created by "
            "create_eval_workspace.py"
        )
    if run_dir == workspace:
        raise ValueError("Run directory must be below the evaluation workspace")

    metadata = load_workspace_metadata(workspace)
    validate_workspace_location(workspace, Path(metadata["source_skill"]))

    repository_root = find_repository_root(run_dir)
    if repository_root is not None and repository_root != run_dir:
        raise ValueError(
            "Run directory must not inherit a Git repository: "
            f"{repository_root}"
        )
    skill_roots = find_ancestor_skill_roots(run_dir)
    if skill_roots:
        raise ValueError(
            "Run directory inherits ancestor skill root(s): "
            + ", ".join(str(path) for path in skill_roots)
        )
    return workspace


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create an isolated temporary skill-evaluation workspace",
    )
    parser.add_argument(
        "--skill-path",
        required=True,
        help="Source skill whose evaluations will use this workspace",
    )
    args = parser.parse_args()

    try:
        workspace = create_eval_workspace(Path(args.skill_path))
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(workspace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
