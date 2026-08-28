"""Shared Codex CLI primitives for skill-creator workflow scripts."""

import json
import os
import shutil
import stat
from collections.abc import Iterator
from pathlib import Path


def _iter_skill_files(
    root: Path,
    ancestor_directories: frozenset[tuple[int, int]] = frozenset(),
) -> Iterator[Path]:
    """Yield lexical SKILL.md paths without re-entering symlink cycles."""
    try:
        metadata = root.stat()
    except OSError:
        return
    if not stat.S_ISDIR(metadata.st_mode):
        return

    identity = (metadata.st_dev, metadata.st_ino)
    if identity in ancestor_directories:
        return
    descendants = ancestor_directories | {identity}

    try:
        with os.scandir(root) as scanner:
            entries = list(scanner)
    except OSError:
        return

    for entry in entries:
        entry_path = Path(entry.path)
        try:
            if (
                entry.name == "SKILL.md"
                and entry.is_file(follow_symlinks=True)
            ):
                yield entry_path.absolute()
            if entry.is_dir(follow_symlinks=True):
                yield from _iter_skill_files(entry_path, descendants)
        except OSError:
            continue


def reasoning_config(effort: str) -> str:
    """Return the Codex config override for one reasoning effort."""
    return f'model_reasoning_effort="{effort}"'


def discover_global_skill_files(
    *,
    home: Path | None = None,
    codex_home: Path | None = None,
) -> list[Path]:
    """Find user and Codex-global skills without changing either home."""
    home = (home or Path.home()).expanduser().absolute()
    codex_home = (
        codex_home
        or Path(os.environ.get("CODEX_HOME", home / ".codex"))
    ).expanduser().absolute()

    candidates = {
        path
        for root in (home / ".agents" / "skills", codex_home / "skills")
        for path in _iter_skill_files(root)
    }
    return sorted(candidates)


def disabled_skills_config(skill_files: list[Path]) -> str:
    """Build one process-local TOML override disabling exact skill paths."""
    entries = ", ".join(
        "{path=" + json.dumps(str(path)) + ",enabled=false}"
        for path in skill_files
    )
    return f"skills.config=[{entries}]"


def build_codex_exec_command(
    *,
    reasoning_effort: str,
    sandbox: str,
    model: str | None = None,
) -> list[str]:
    """Build the common, ephemeral prefix for a Codex exec command."""
    command = [
        "codex",
        "exec",
        "-c",
        reasoning_config(reasoning_effort),
    ]
    global_skills = discover_global_skill_files()
    if global_skills:
        command.extend(["-c", disabled_skills_config(global_skills)])
    command.extend([
        "--ephemeral",
        "--sandbox",
        sandbox,
        "--skip-git-repo-check",
    ])
    if model:
        command.extend(["--model", model])
    return command


def require_codex_cli() -> None:
    """Fail with a consistent message when the Codex CLI is unavailable."""
    if shutil.which("codex") is None:
        raise RuntimeError("codex CLI was not found on PATH")
