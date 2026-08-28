import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from scripts.improve_description import DESCRIPTION_SCHEMA, _call_codex
from scripts.codex_exec import (
    disabled_skills_config,
    discover_global_skill_files,
)
from scripts.run_grader import (
    GRADER_INSTRUCTIONS,
    GRADER_REASONING_CONFIG,
    GRADING_SCHEMA,
    build_grader_command,
    run_grader,
)
from scripts.aggregate_benchmark import generate_benchmark, load_run_results
from scripts.collect_codex_metrics import collect_metrics, write_run_metrics
from scripts.create_eval_workspace import (
    WORKSPACE_MARKER,
    create_eval_workspace,
    validate_run_directory,
)
from scripts.create_iteration import create_iteration
from scripts.eval_manifest import (
    CONFIG_NEW,
    CONFIG_OLD,
    CONFIG_WITHOUT,
    ITERATION_MANIFEST,
    load_iteration_manifest,
    load_run_context,
)
from scripts.run_eval import (
    build_skill_fixture,
    output_shows_skill_load,
    run_single_query,
    summarize_query_result,
)
from scripts.run_loop import run_loop, split_eval_set
from scripts.run_test_case import (
    DELIVERABLE_INSTRUCTION,
    EVALUATION_ISOLATION_INSTRUCTION,
    ISOLATION_VIOLATION_EXIT_CODE,
    TEST_REASONING_CONFIG,
    audit_trace_for_protected_sources,
    build_test_command,
    build_test_prompt,
    collect_protected_skill_roots,
    prepare_run_directory,
    run_test_case,
)
from scripts.utils import validate_skill_name


VIEWER_MODULE_PATH = SKILL_ROOT / "eval-viewer" / "generate_review.py"
VIEWER_SPEC = importlib.util.spec_from_file_location(
    "skill_creator_generate_review",
    VIEWER_MODULE_PATH,
)
VIEWER_MODULE = importlib.util.module_from_spec(VIEWER_SPEC)
assert VIEWER_SPEC.loader is not None
VIEWER_SPEC.loader.exec_module(VIEWER_MODULE)


def create_eval_skill(parent: Path, body: str = "# Example\n") -> Path:
    """Create a minimal skill with one manifest-ready eval."""
    skill_path = parent / "example-skill"
    skill_path.mkdir(parents=True)
    (skill_path / "SKILL.md").write_text(
        "---\n"
        "name: example-skill\n"
        "description: Use for example tasks.\n"
        "---\n\n"
        f"{body}",
        encoding="utf-8",
    )
    evals_dir = skill_path / "evals"
    evals_dir.mkdir()
    (evals_dir / "evals.json").write_text(
        json.dumps({
            "skill_name": "example-skill",
            "evals": [{
                "id": 7,
                "name": "complete-example-task",
                "prompt": "Complete the example task",
                "expected_output": "A complete result",
                "files": [],
                "expectations": ["The output is complete"],
            }],
        }),
        encoding="utf-8",
    )
    return skill_path


def prepare_iteration(
    root: Path,
    *,
    baseline: str = "none",
    runs: int = 1,
    model: str = "test-model",
) -> tuple[Path, Path, Path]:
    source_skill = create_eval_skill(root / "source")
    temp_parent = root / "system-temp"
    temp_parent.mkdir()
    workspace = create_eval_workspace(source_skill, temp_parent=temp_parent)
    iteration = create_iteration(
        workspace,
        baseline=baseline,
        runs=runs,
        model=model,
    )
    return source_skill, workspace, iteration


def write_completed_result(
    run_dir: Path,
    *,
    status: str = "completed",
    pass_rate: float = 1.0,
) -> None:
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "trace.jsonl").write_text("", encoding="utf-8")
    (outputs_dir / "final.md").write_text("Done", encoding="utf-8")
    (outputs_dir / "metrics.json").write_text(
        json.dumps({
            "run_status": status,
            "exit_code": 0,
            "total_tool_calls": 4,
            "errors_encountered": 0 if status == "completed" else 1,
            "total_tokens": 4321,
        }),
        encoding="utf-8",
    )
    (run_dir / "timing.json").write_text(
        json.dumps({
            "run_status": status,
            "exit_code": 0,
            "total_duration_seconds": 12.5,
            "total_tokens": 4321,
        }),
        encoding="utf-8",
    )
    (run_dir / "grading.json").write_text(
        json.dumps({
            "expectations": [{
                "text": "The output is complete",
                "passed": pass_rate == 1.0,
                "evidence": "Observed output",
            }],
            "summary": {
                "passed": 1 if pass_rate == 1.0 else 0,
                "failed": 0 if pass_rate == 1.0 else 1,
                "total": 1,
                "pass_rate": pass_rate,
            },
            "claims": [],
            "user_notes_summary": {
                "uncertainties": [],
                "needs_review": [],
                "workarounds": [],
            },
            "eval_feedback": {"suggestions": [], "overall": ""},
        }),
        encoding="utf-8",
    )


def iteration_run_dirs(iteration: Path) -> list[Path]:
    manifest = load_iteration_manifest(iteration)
    return [
        iteration
        / eval_entry["directory"]
        / configuration
        / f"run-{run_number}"
        for eval_entry in manifest["evals"]
        for configuration in manifest["configurations"]
        for run_number in range(1, manifest["runs"] + 1)
    ]


class TriggerDetectionTests(unittest.TestCase):
    def setUp(self):
        self.working_dir = Path("/tmp/skill-trigger-eval-test")
        self.skill_file = (
            self.working_dir
            / ".agents"
            / "skills"
            / "example-skill"
            / "SKILL.md"
        )

    def test_fixture_uses_agents_skill_layout_and_marker(self):
        content = build_skill_fixture(
            "example-skill",
            "Use for example tasks.",
            "SKILL_TRIGGERED_test",
        )

        self.assertIn('name: "example-skill"', content)
        self.assertIn("description: |", content)
        self.assertIn("SKILL_TRIGGERED_test", content)

    def test_detects_marker_in_agent_message(self):
        output = json.dumps({
            "type": "item.completed",
            "item": {
                "type": "agent_message",
                "text": "Done. SKILL_TRIGGERED_test",
            },
        })

        self.assertTrue(output_shows_skill_load(
            output,
            "SKILL_TRIGGERED_test",
            self.skill_file,
            self.working_dir,
        ))

    def test_detects_skill_read_command(self):
        output = json.dumps({
            "type": "item.started",
            "item": {
                "type": "command_execution",
                "command": "sed -n '1,200p' .agents/skills/example-skill/SKILL.md",
            },
        })

        self.assertTrue(output_shows_skill_load(
            output,
            "SKILL_TRIGGERED_test",
            self.skill_file,
            self.working_dir,
        ))

    def test_ignores_unrelated_events(self):
        output = json.dumps({
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "No skill needed."},
        })

        self.assertFalse(output_shows_skill_load(
            output,
            "SKILL_TRIGGERED_test",
            self.skill_file,
            self.working_dir,
        ))

    def test_partial_run_failures_are_never_scored_as_passes(self):
        result = summarize_query_result(
            {"query": "Do the example task", "should_trigger": True},
            [True],
            ["timeout", "transport failed"],
            expected_runs=3,
            trigger_threshold=0.5,
        )

        self.assertEqual(result["trigger_rate"], 1.0)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["expected_runs"], 3)
        self.assertFalse(result["pass"])

    @patch("scripts.run_eval.run_codex_until_skill_load", return_value=True)
    def test_trigger_eval_uses_medium_reasoning(self, run_mock):
        self.assertTrue(run_single_query(
            "Do the example task",
            "example-skill",
            "Use for example tasks.",
            timeout=10,
            model="test-model",
        ))

        command = run_mock.call_args.args[0]
        config_index = command.index("-c")
        self.assertEqual(
            command[config_index + 1],
            'model_reasoning_effort="medium"',
        )
        self.assertNotIn("env", run_mock.call_args.kwargs)

    @patch("scripts.run_eval.run_codex_until_skill_load")
    def test_trigger_eval_rejects_unsafe_skill_name(self, run_mock):
        with self.assertRaisesRegex(ValueError, "not safe"):
            run_single_query(
                "Do the example task",
                "../../escaped-skill",
                "Use for example tasks.",
                timeout=10,
            )

        run_mock.assert_not_called()


class DescriptionOptimizerTests(unittest.TestCase):
    @patch("scripts.improve_description.subprocess.run")
    def test_uses_output_schema_and_parses_description(self, run_mock):
        run_mock.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='{"new_description":"Use for focused example tasks."}',
            stderr="",
        )

        raw, description = _call_codex(
            "Improve this description",
            "test-model",
        )

        self.assertEqual(
            json.loads(raw),
            {"new_description": "Use for focused example tasks."},
        )
        self.assertEqual(description, "Use for focused example tasks.")
        command = run_mock.call_args.args[0]
        self.assertIn("--output-schema", command)
        self.assertIn(str(DESCRIPTION_SCHEMA), command)
        self.assertIn("--model", command)
        config_index = command.index("-c")
        self.assertEqual(
            command[config_index + 1],
            'model_reasoning_effort="high"',
        )
        self.assertEqual(command[-1], "-")
        self.assertNotIn("env", run_mock.call_args.kwargs)


class GlobalSkillConfigTests(unittest.TestCase):
    def test_discovers_user_codex_and_system_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home = root / "home"
            codex_home = root / "codex"
            paths = [
                home / ".agents/skills/user-skill/SKILL.md",
                codex_home / "skills/codex-skill/SKILL.md",
                codex_home / "skills/.system/system-skill/SKILL.md",
                codex_home / "skills/vendor/nested/deep-skill/SKILL.md",
            ]
            for path in paths:
                path.parent.mkdir(parents=True)
                path.write_text("---\nname: example\n---\n", encoding="utf-8")
            symlink_target = root / "linked-skill-target"
            symlink_target.mkdir()
            (symlink_target / "SKILL.md").write_text(
                "---\nname: linked\n---\n",
                encoding="utf-8",
            )
            symlink_path = home / ".agents/skills/linked-skill"
            symlink_path.symlink_to(symlink_target, target_is_directory=True)
            paths.append(symlink_path / "SKILL.md")
            second_symlink = codex_home / "skills/second-linked-skill"
            second_symlink.parent.mkdir(parents=True, exist_ok=True)
            second_symlink.symlink_to(
                symlink_target,
                target_is_directory=True,
            )
            paths.append(second_symlink / "SKILL.md")

            discovered = discover_global_skill_files(
                home=home,
                codex_home=codex_home,
            )

        self.assertEqual(discovered, sorted(path.absolute() for path in paths))

    def test_does_not_reenter_directory_symlink_cycle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home = root / "home"
            skill_dir = home / ".agents/skills/cyclic-skill"
            skill_dir.mkdir(parents=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(
                "---\nname: cyclic-skill\n---\n",
                encoding="utf-8",
            )
            (skill_dir / "back").symlink_to(
                skill_dir,
                target_is_directory=True,
            )

            discovered = discover_global_skill_files(
                home=home,
                codex_home=root / "codex",
            )

        self.assertEqual(discovered, [skill_file.absolute()])

    def test_builds_one_exact_path_override(self):
        skill_files = [
            Path("/tmp/global one/SKILL.md"),
            Path("/tmp/global-two/SKILL.md"),
        ]

        config = disabled_skills_config(skill_files)

        self.assertEqual(
            config,
            'skills.config=[{path="/tmp/global one/SKILL.md",enabled=false}, '
            '{path="/tmp/global-two/SKILL.md",enabled=false}]',
        )


class EvalWorkspaceTests(unittest.TestCase):
    @staticmethod
    def create_skill(root: Path) -> Path:
        skill_path = root / "example-skill"
        skill_path.mkdir(parents=True)
        (skill_path / "SKILL.md").write_text(
            "---\n"
            "name: example-skill\n"
            "description: Use for example tasks.\n"
            "---\n",
            encoding="utf-8",
        )
        return skill_path

    def test_creates_marked_workspace_and_validates_nested_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_path = self.create_skill(root / "source")
            temp_parent = root / "system-temp"
            temp_parent.mkdir()

            workspace = create_eval_workspace(
                skill_path,
                temp_parent=temp_parent,
            )
            metadata = json.loads(
                (workspace / WORKSPACE_MARKER).read_text(encoding="utf-8")
            )
            run_dir = workspace / "iteration-1" / "eval-0" / "run-1"

            self.assertTrue(workspace.is_absolute())
            self.assertEqual(workspace.parent, temp_parent.resolve())
            self.assertEqual(metadata["schema_version"], 1)
            self.assertEqual(metadata["skill_name"], "example-skill")
            self.assertEqual(metadata["source_skill"], str(skill_path.resolve()))
            self.assertEqual(
                metadata["source_skill_lexical"],
                str(skill_path.absolute()),
            )
            self.assertEqual(validate_run_directory(run_dir), workspace)

    def test_rejects_workspace_inside_git_repository(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = Path(temp_dir) / "repository"
            (repository / ".git").mkdir(parents=True)
            skill_path = self.create_skill(repository / "skills")
            temp_parent = repository / "temporary"
            temp_parent.mkdir()

            with self.assertRaisesRegex(ValueError, "outside a Git repository"):
                create_eval_workspace(skill_path, temp_parent=temp_parent)

            self.assertEqual(list(temp_parent.iterdir()), [])

    def test_rejects_workspace_below_ancestor_skill_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_path = self.create_skill(root / "source")
            contaminated = root / "contaminated"
            (contaminated / ".agents" / "skills").mkdir(parents=True)
            temp_parent = contaminated / "temporary"
            temp_parent.mkdir()

            with self.assertRaisesRegex(ValueError, "ancestor skill root"):
                create_eval_workspace(skill_path, temp_parent=temp_parent)

            self.assertEqual(list(temp_parent.iterdir()), [])

    def test_run_directory_requires_workspace_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "iteration-1" / "eval-0" / "run-1"

            with self.assertRaisesRegex(ValueError, "create_eval_workspace.py"):
                validate_run_directory(run_dir)

    def test_run_validation_rechecks_ancestor_skill_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_path = self.create_skill(root / "source")
            temp_parent = root / "system-temp"
            temp_parent.mkdir()
            workspace = create_eval_workspace(
                skill_path,
                temp_parent=temp_parent,
            )

            contaminated = root / "contaminated"
            (contaminated / ".agents" / "skills").mkdir(parents=True)
            destination_parent = contaminated / "temporary"
            destination_parent.mkdir()
            moved_workspace = workspace.rename(
                destination_parent / workspace.name
            )
            run_dir = moved_workspace / "iteration-1" / "eval-0" / "run-1"

            with self.assertRaisesRegex(ValueError, "ancestor skill root"):
                validate_run_directory(run_dir)

    def test_run_directory_may_be_its_own_git_repository(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_path = self.create_skill(root / "source")
            temp_parent = root / "system-temp"
            temp_parent.mkdir()
            workspace = create_eval_workspace(
                skill_path,
                temp_parent=temp_parent,
            )
            run_dir = workspace / "iteration-1" / "eval-0" / "run-1"
            (run_dir / ".git").mkdir(parents=True)

            self.assertEqual(validate_run_directory(run_dir), workspace)


class IterationManifestTests(unittest.TestCase):
    def test_prepares_snapshots_metadata_and_all_declared_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source, workspace, iteration = prepare_iteration(root, runs=3)
            manifest = load_iteration_manifest(iteration)

            self.assertEqual(iteration.parent, workspace)
            self.assertTrue((iteration / ITERATION_MANIFEST).is_file())
            self.assertEqual(manifest["runs"], 3)
            self.assertEqual(
                manifest["configurations"],
                [CONFIG_NEW, CONFIG_WITHOUT],
            )
            self.assertEqual(manifest["baseline"]["kind"], "none")
            self.assertTrue(
                (iteration / manifest["candidate"]["snapshot"] / "SKILL.md").is_file()
            )
            self.assertEqual(len(iteration_run_dirs(iteration)), 6)
            self.assertTrue(all(path.is_dir() for path in iteration_run_dirs(iteration)))
            self.assertEqual(
                json.loads(
                    (iteration / manifest["evals"][0]["directory"] / "eval_metadata.json")
                    .read_text(encoding="utf-8")
                )["prompt"],
                "Complete the example task",
            )
            self.assertEqual(
                (source / "SKILL.md").read_text(encoding="utf-8"),
                (
                    iteration
                    / manifest["candidate"]["snapshot"]
                    / "SKILL.md"
                ).read_text(encoding="utf-8"),
            )

    def test_previous_baseline_snapshots_prior_candidate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source, workspace, first = prepare_iteration(root)
            first_manifest = load_iteration_manifest(first)
            previous_content = (
                first / first_manifest["candidate"]["snapshot"] / "SKILL.md"
            ).read_text(encoding="utf-8")
            (source / "SKILL.md").write_text(
                "---\nname: example-skill\n"
                "description: Use for example tasks.\n---\n\n# Revised\n",
                encoding="utf-8",
            )

            second = create_iteration(
                workspace,
                baseline="previous",
                runs=1,
                model="test-model",
            )
            manifest = load_iteration_manifest(second)
            eval_dir = second / manifest["evals"][0]["directory"]
            old_context = load_run_context(eval_dir / CONFIG_OLD / "run-1")

            self.assertEqual(manifest["baseline"]["kind"], "previous")
            self.assertEqual(manifest["baseline"]["source_iteration"], "iteration-1")
            self.assertEqual(manifest["previous_iteration"], "iteration-1")
            self.assertEqual(
                (old_context.skill_path / "SKILL.md").read_text(encoding="utf-8"),
                previous_content,
            )
            self.assertNotEqual(
                (old_context.skill_path / "SKILL.md").read_text(encoding="utf-8"),
                (
                    second
                    / manifest["candidate"]["snapshot"]
                    / "SKILL.md"
                ).read_text(encoding="utf-8"),
            )

    def test_path_baseline_is_snapshotted_and_recorded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = create_eval_skill(root / "source", "# Candidate\n")
            baseline = create_eval_skill(root / "baseline", "# Baseline\n")
            temp_parent = root / "system-temp"
            temp_parent.mkdir()
            workspace = create_eval_workspace(source, temp_parent=temp_parent)

            iteration = create_iteration(
                workspace,
                baseline=str(baseline),
                runs=1,
                model="test-model",
            )
            manifest = load_iteration_manifest(iteration)
            old_snapshot = iteration / manifest["baseline"]["snapshot"]

            self.assertEqual(manifest["baseline"]["kind"], "path")
            self.assertEqual(manifest["baseline"]["configuration"], CONFIG_OLD)
            self.assertEqual(manifest["baseline"]["source"], str(baseline.resolve()))
            self.assertIn("# Baseline", (old_snapshot / "SKILL.md").read_text())
            self.assertEqual(
                manifest["configurations"],
                [CONFIG_NEW, CONFIG_OLD],
            )

    def test_run_context_derives_inputs_without_cli_configuration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source, _, iteration = prepare_iteration(root, model="gpt-5.6-sol")
            manifest = load_iteration_manifest(iteration)
            run_dir = (
                iteration
                / manifest["evals"][0]["directory"]
                / CONFIG_WITHOUT
                / "run-1"
            )

            context = load_run_context(run_dir)

            self.assertIsNone(context.skill_path)
            self.assertEqual(context.model, "gpt-5.6-sol")
            self.assertEqual(context.eval_metadata["expectations"], [
                "The output is complete"
            ])
            self.assertIn(source.resolve(), context.protected_skill_paths)
            self.assertIn(
                (iteration / manifest["candidate"]["snapshot"]).resolve(),
                context.protected_skill_paths,
            )

    def test_rejects_previous_baseline_without_an_iteration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = create_eval_skill(root / "source")
            temp_parent = root / "system-temp"
            temp_parent.mkdir()
            workspace = create_eval_workspace(source, temp_parent=temp_parent)

            with self.assertRaisesRegex(ValueError, "requires an existing iteration"):
                create_iteration(
                    workspace,
                    baseline="previous",
                    runs=1,
                    model="test-model",
                )

            self.assertFalse(list(workspace.glob("iteration-*")))

    def test_manifest_rejects_undeclared_run_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, iteration = prepare_iteration(Path(temp_dir))
            manifest = load_iteration_manifest(iteration)
            extra = (
                iteration
                / manifest["evals"][0]["directory"]
                / CONFIG_NEW
                / "run-2"
            )
            extra.mkdir()

            with self.assertRaisesRegex(ValueError, "do not match iteration.json"):
                load_iteration_manifest(iteration)


class ManifestCliTests(unittest.TestCase):
    def test_runtime_scripts_expose_only_one_position_argument(self):
        scripts = [
            SKILL_ROOT / "scripts" / "run_test_case.py",
            SKILL_ROOT / "scripts" / "run_grader.py",
            SKILL_ROOT / "scripts" / "aggregate_benchmark.py",
            SKILL_ROOT / "eval-viewer" / "generate_review.py",
        ]
        removed_options = [
            "--run-dir",
            "--skill-path",
            "--protected-skill-path",
            "--model",
            "--prompt",
            "--prompt-file",
            "--eval-metadata",
            "--output",
            "--benchmark",
            "--previous-workspace",
            "--static",
        ]

        for script in scripts:
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [sys.executable, str(script), "--help"],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                for option in removed_options:
                    self.assertNotIn(option, result.stdout)


class TestCaseRunnerTests(unittest.TestCase):
    def test_prompt_applies_same_read_isolation_contract(self):
        prompt = build_test_prompt("Complete the example task")

        self.assertIn(EVALUATION_ISOLATION_INSTRUCTION, prompt)
        self.assertTrue(prompt.endswith(DELIVERABLE_INSTRUCTION))

    def test_builds_medium_workspace_command(self):
        run_dir = Path("/tmp/skill-creator/eval/with_skill/run-1")
        output_path = run_dir / "outputs" / "final.md"

        command = build_test_command(
            run_dir,
            output_path,
            model="test-model",
        )

        self.assertEqual(
            command[command.index("-c") + 1],
            TEST_REASONING_CONFIG,
        )
        self.assertEqual(
            TEST_REASONING_CONFIG,
            'model_reasoning_effort="medium"',
        )
        self.assertEqual(
            command[command.index("--sandbox") + 1],
            "workspace-write",
        )
        self.assertIn("--ephemeral", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("--json", command)
        self.assertEqual(command[command.index("-C") + 1], str(run_dir.resolve()))
        self.assertEqual(
            command[command.index("-o") + 1],
            str(output_path.resolve()),
        )
        self.assertEqual(command[command.index("--model") + 1], "test-model")
        self.assertEqual(command[-1], "-")

    def test_prepares_empty_no_skill_baseline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "without_skill" / "run-1"
            trace_path, output_path = prepare_run_directory(run_dir)

            resolved_run_dir = run_dir.resolve()
            self.assertEqual(trace_path, resolved_run_dir / "trace.jsonl")
            self.assertEqual(
                output_path,
                resolved_run_dir / "outputs" / "final.md",
            )
            self.assertEqual(
                list((resolved_run_dir / ".agents" / "skills").iterdir()),
                [],
            )

    def test_trace_audit_detects_external_skill_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected = root / "source" / "example-skill"
            protected.mkdir(parents=True)
            (protected / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Example.\n---\n",
                encoding="utf-8",
            )
            run_dir = root / "workspace" / "run-1"
            run_dir.mkdir(parents=True)
            trace_path = run_dir / "trace.jsonl"
            trace_path.write_text(
                json.dumps({
                    "type": "item.completed",
                    "item": {
                        "id": "item-1",
                        "type": "command_execution",
                        "command": f"sed -n 1,200p {protected}/SKILL.md",
                        "status": "completed",
                    },
                }) + "\n",
                encoding="utf-8",
            )

            roots = collect_protected_skill_roots(run_dir, [protected])
            violations = audit_trace_for_protected_sources(trace_path, roots)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["item_type"], "command_execution")
        self.assertIn(
            violations[0]["protected_root"],
            {str(protected.absolute()), str(protected.resolve())},
        )

    @patch("scripts.run_test_case.discover_global_skill_files")
    def test_protects_global_alias_by_frontmatter_name(self, discover_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source" / "example-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Example.\n---\n",
                encoding="utf-8",
            )
            global_alias = root / "global" / "renamed-directory"
            global_alias.mkdir(parents=True)
            global_file = global_alias / "SKILL.md"
            global_file.write_text(
                "---\nname: example-skill\ndescription: Global.\n---\n",
                encoding="utf-8",
            )
            discover_mock.return_value = [global_file]
            run_dir = root / "workspace" / "run-1"

            protected = collect_protected_skill_roots(run_dir, [source])

        self.assertIn(global_alias.absolute(), protected)

    def test_trace_audit_allows_installed_run_copy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected = root / "source" / "example-skill"
            protected.mkdir(parents=True)
            (protected / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Example.\n---\n",
                encoding="utf-8",
            )
            run_dir = root / "workspace" / "run-1"
            local_skill = run_dir / ".agents/skills/example-skill/SKILL.md"
            local_skill.parent.mkdir(parents=True)
            local_skill.write_text("local copy", encoding="utf-8")
            trace_path = run_dir / "trace.jsonl"
            trace_path.write_text(
                json.dumps({
                    "type": "item.completed",
                    "item": {
                        "id": "item-1",
                        "type": "command_execution",
                        "command": (
                            "sed -n 1,200p "
                            ".agents/skills/example-skill/SKILL.md"
                        ),
                        "status": "completed",
                    },
                }) + "\n",
                encoding="utf-8",
            )

            roots = collect_protected_skill_roots(run_dir, [protected])
            violations = audit_trace_for_protected_sources(trace_path, roots)

        self.assertEqual(violations, [])

    def test_trace_audit_does_not_confuse_local_copy_with_global_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            trace_path = Path(temp_dir) / "trace.jsonl"
            trace_path.write_text(
                json.dumps({
                    "type": "item.completed",
                    "item": {
                        "id": "item-1",
                        "type": "command_execution",
                        "command": (
                            "sed -n 1,200p "
                            ".agents/skills/skill-creator/SKILL.md"
                        ),
                        "status": "completed",
                    },
                }) + "\n",
                encoding="utf-8",
            )
            global_copy = Path.home() / ".agents/skills/skill-creator"

            violations = audit_trace_for_protected_sources(
                trace_path,
                [global_copy],
            )

        self.assertEqual(violations, [])

    def test_rejects_skill_name_that_escapes_fixture_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = root / "workspace" / "run-1"
            escaped_path = root / "escaped-skill"
            skill_path = root / "unsafe-skill"
            skill_path.mkdir()
            (skill_path / "SKILL.md").write_text(
                "---\n"
                f"name: {escaped_path}\n"
                "description: Unsafe fixture.\n"
                "---\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "not safe"):
                prepare_run_directory(run_dir, skill_path)

            self.assertFalse(escaped_path.exists())
            self.assertFalse(run_dir.exists())

    @patch("scripts.run_test_case.subprocess.run")
    @patch("scripts.run_test_case.require_codex_cli")
    def test_runs_and_writes_artifacts_with_current_environment(
        self,
        _require_mock,
        run_mock,
    ):
        def fake_codex(command, **kwargs):
            kwargs["stdout"].write(json.dumps({
                "type": "turn.completed",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }) + "\n")
            output_path = Path(command[command.index("-o") + 1])
            output_path.write_text("Done", encoding="utf-8")
            return subprocess.CompletedProcess(command, returncode=0)

        run_mock.side_effect = fake_codex

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, iteration = prepare_iteration(root)
            manifest = load_iteration_manifest(iteration)
            run_dir = (
                iteration
                / manifest["evals"][0]["directory"]
                / CONFIG_NEW
                / "run-1"
            )

            self.assertEqual(
                run_test_case(run_dir),
                0,
            )

            metrics = json.loads(
                (run_dir / "outputs" / "metrics.json").read_text()
            )
            timing = json.loads((run_dir / "timing.json").read_text())
            copied_skill = (
                run_dir
                / ".agents"
                / "skills"
                / "example-skill"
                / "SKILL.md"
            )

            self.assertTrue((run_dir / "trace.jsonl").is_file())
            self.assertEqual(
                (run_dir / "outputs" / "final.md").read_text(),
                "Done",
            )
            self.assertTrue(copied_skill.is_file())
            self.assertEqual(metrics["run_status"], "completed")
            self.assertEqual(metrics["total_tokens"], 15)
            self.assertEqual(metrics["exit_code"], 0)
            self.assertEqual(timing["run_status"], "completed")
            self.assertIn("duration_ms", timing)

        command = run_mock.call_args.args[0]
        self.assertEqual(command[command.index("-c") + 1], TEST_REASONING_CONFIG)
        self.assertTrue(
            run_mock.call_args.kwargs["input"].endswith(DELIVERABLE_INSTRUCTION)
        )
        self.assertNotIn("env", run_mock.call_args.kwargs)

    @patch("scripts.run_test_case.subprocess.run")
    @patch("scripts.run_test_case.require_codex_cli")
    def test_source_read_marks_run_contaminated(
        self,
        _require_mock,
        run_mock,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_path, _, iteration = prepare_iteration(root)
            manifest = load_iteration_manifest(iteration)
            run_dir = (
                iteration
                / manifest["evals"][0]["directory"]
                / CONFIG_WITHOUT
                / "run-1"
            )

            def fake_codex(command, **kwargs):
                kwargs["stdout"].write(json.dumps({
                    "type": "item.completed",
                    "item": {
                        "id": "item-1",
                        "type": "command_execution",
                        "command": f"cat {skill_path}/SKILL.md",
                        "status": "completed",
                    },
                }) + "\n")
                kwargs["stdout"].write(json.dumps({
                    "type": "turn.completed",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                }) + "\n")
                output_path = Path(command[command.index("-o") + 1])
                output_path.write_text("Done", encoding="utf-8")
                return subprocess.CompletedProcess(command, returncode=0)

            run_mock.side_effect = fake_codex
            exit_code = run_test_case(run_dir)
            metrics = json.loads(
                (run_dir / "outputs/metrics.json").read_text(encoding="utf-8")
            )
            timing = json.loads(
                (run_dir / "timing.json").read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, ISOLATION_VIOLATION_EXIT_CODE)
        self.assertEqual(metrics["run_status"], "contaminated")
        self.assertEqual(timing["run_status"], "contaminated")
        self.assertEqual(len(metrics["isolation_violations"]), 1)


class SkillNameValidationTests(unittest.TestCase):
    def test_accepts_canonical_skill_name(self):
        self.assertEqual(
            validate_skill_name("release-readiness-2"),
            "release-readiness-2",
        )

    def test_rejects_empty_traversal_and_overlong_names(self):
        invalid_names = [
            "",
            "../escaped",
            "/tmp/escaped",
            "two--hyphens",
            "a" * 65,
        ]

        for skill_name in invalid_names:
            with self.subTest(skill_name=skill_name):
                with self.assertRaises(ValueError):
                    validate_skill_name(skill_name)


class GraderWrapperTests(unittest.TestCase):
    def test_builds_schema_constrained_high_reasoning_command(self):
        run_dir = Path(
            "/tmp/skill-creator/eval-0/with_skill/run-1"
        ).resolve()
        metadata_path = Path(
            "/tmp/skill-creator/eval-0/eval_metadata.json"
        ).resolve()
        output_path = run_dir / "grading.json"

        command = build_grader_command(
            run_dir,
            metadata_path,
            output_path,
            model="test-model",
        )

        config_index = command.index("-c")
        self.assertEqual(command[config_index + 1], GRADER_REASONING_CONFIG)
        self.assertEqual(GRADER_REASONING_CONFIG, 'model_reasoning_effort="high"')
        self.assertIn("--output-schema", command)
        self.assertIn(str(GRADING_SCHEMA), command)
        self.assertIn("--model", command)
        self.assertIn(str(GRADER_INSTRUCTIONS), command[-1])
        self.assertIn(str(metadata_path), command[-1])
        self.assertIn(str(run_dir / "trace.jsonl"), command[-1])
        self.assertIn(str(run_dir / "outputs" / "final.md"), command[-1])
        self.assertEqual(
            command[command.index("-o") + 1],
            str(output_path),
        )

    @patch("scripts.run_grader.subprocess.run")
    @patch("scripts.run_grader.require_codex_cli")
    def test_grader_inherits_current_environment(self, _require_mock, run_mock):
        run_mock.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, iteration = prepare_iteration(root)
            manifest = load_iteration_manifest(iteration)
            run_dir = (
                iteration
                / manifest["evals"][0]["directory"]
                / CONFIG_NEW
                / "run-1"
            )
            outputs_dir = run_dir / "outputs"
            outputs_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "trace.jsonl").write_text("", encoding="utf-8")
            (outputs_dir / "final.md").write_text("Done", encoding="utf-8")
            (outputs_dir / "metrics.json").write_text(
                json.dumps({"run_status": "completed", "exit_code": 0}),
                encoding="utf-8",
            )
            (run_dir / "timing.json").write_text(
                json.dumps({"run_status": "completed", "exit_code": 0}),
                encoding="utf-8",
            )
            self.assertEqual(run_grader(run_dir), 0)

        self.assertNotIn("env", run_mock.call_args.kwargs)
        command = run_mock.call_args.args[0]
        self.assertEqual(command[command.index("--model") + 1], "test-model")

    @patch("scripts.run_grader.subprocess.run")
    @patch("scripts.run_grader.require_codex_cli")
    def test_grader_rejects_incomplete_run(self, require_mock, run_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, iteration = prepare_iteration(root)
            manifest = load_iteration_manifest(iteration)
            run_dir = (
                iteration
                / manifest["evals"][0]["directory"]
                / CONFIG_NEW
                / "run-1"
            )
            outputs_dir = run_dir / "outputs"
            outputs_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "trace.jsonl").write_text("", encoding="utf-8")
            (outputs_dir / "final.md").write_text("Done", encoding="utf-8")
            (outputs_dir / "metrics.json").write_text(
                json.dumps({"run_status": "incomplete", "exit_code": 0}),
                encoding="utf-8",
            )
            (run_dir / "timing.json").write_text(
                json.dumps({"run_status": "incomplete", "exit_code": 0}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "not completed successfully"):
                run_grader(run_dir)

        require_mock.assert_not_called()
        run_mock.assert_not_called()

    @patch("scripts.run_grader.subprocess.run")
    @patch("scripts.run_grader.require_codex_cli")
    def test_grader_rejects_contaminated_evidence(self, require_mock, run_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, iteration = prepare_iteration(Path(temp_dir))
            run_dir = iteration_run_dirs(iteration)[0]
            write_completed_result(run_dir)
            metrics_path = run_dir / "outputs" / "metrics.json"
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            metrics["isolation_violations"] = [{"protected_root": "/source"}]
            metrics_path.write_text(json.dumps(metrics), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "not completed successfully"):
                run_grader(run_dir)

        require_mock.assert_not_called()
        run_mock.assert_not_called()


class BenchmarkAggregationTests(unittest.TestCase):
    def test_collects_codex_jsonl_metrics_without_double_counting_started_items(self):
        metrics = collect_metrics([
            {
                "type": "item.started",
                "item": {"type": "command_execution"},
            },
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "status": "completed",
                },
            },
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "hello"},
            },
            {
                "type": "item.completed",
                "item": {"type": "file_change", "status": "failed"},
            },
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 100,
                    "cached_input_tokens": 20,
                    "output_tokens": 30,
                },
            },
            {"type": "error", "message": "example failure"},
        ])

        self.assertEqual(
            metrics["tool_calls"],
            {"command_execution": 1, "file_change": 1},
        )
        self.assertEqual(metrics["total_tool_calls"], 2)
        self.assertEqual(metrics["total_steps"], 3)
        self.assertEqual(metrics["errors_encountered"], 2)
        self.assertEqual(metrics["transcript_chars"], 5)
        self.assertEqual(metrics["total_tokens"], 130)
        self.assertEqual(metrics["run_status"], "completed")

    def test_empty_trace_is_incomplete_and_not_clean(self):
        metrics = collect_metrics([])

        self.assertEqual(metrics["run_status"], "incomplete")
        self.assertEqual(metrics["errors_encountered"], 1)
        self.assertEqual(metrics["turns_completed"], 0)

    def test_nonzero_exit_code_marks_run_failed(self):
        metrics = collect_metrics([{
            "type": "turn.completed",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }], exit_code=2)

        self.assertEqual(metrics["run_status"], "failed")
        self.assertEqual(metrics["exit_code"], 2)
        self.assertEqual(metrics["errors_encountered"], 1)

    def test_writes_metrics_and_timing_in_framework_layout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            trace_path = run_dir / "trace.jsonl"
            trace_path.write_text(
                json.dumps({
                    "type": "turn.completed",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                }) + "\n",
                encoding="utf-8",
            )

            metrics_path, timing_path = write_run_metrics(
                trace_path,
                run_dir,
                2.5,
                0,
            )

            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            timing = json.loads(timing_path.read_text(encoding="utf-8"))

        self.assertEqual(metrics["total_tokens"], 15)
        self.assertEqual(timing["total_tokens"], 15)
        self.assertEqual(timing["duration_ms"], 2500)
        self.assertEqual(timing["total_duration_seconds"], 2.5)
        self.assertEqual(timing["run_status"], "completed")
        self.assertEqual(timing["exit_code"], 0)

    def test_reads_deterministic_metrics_and_timing_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, iteration = prepare_iteration(root)
            for run_dir in iteration_run_dirs(iteration):
                write_completed_result(run_dir)

            results = load_run_results(iteration)

        run = results[CONFIG_NEW][0]
        self.assertEqual(run["eval_id"], 7)
        self.assertEqual(run["eval_name"], "complete-example-task")
        self.assertEqual(run["time_seconds"], 12.5)
        self.assertEqual(run["tokens"], 4321)
        self.assertEqual(run["tool_calls"], 4)
        self.assertEqual(run["errors"], 0)

    def test_benchmark_reports_actual_run_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, iteration = prepare_iteration(root, runs=2)
            for run_dir in iteration_run_dirs(iteration):
                write_completed_result(run_dir)

            benchmark = generate_benchmark(iteration)

        self.assertEqual(benchmark["metadata"]["runs_per_configuration"], 2)
        self.assertEqual(
            benchmark["metadata"]["run_counts_by_configuration"],
            {
                CONFIG_NEW: {"7": 2},
                CONFIG_WITHOUT: {"7": 2},
            },
        )
        self.assertEqual(benchmark["metadata"]["executor_model"], "test-model")

    def test_aggregator_rejects_incomplete_execution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, iteration = prepare_iteration(root)
            run_dirs = iteration_run_dirs(iteration)
            for run_dir in run_dirs:
                write_completed_result(run_dir)
            write_completed_result(run_dirs[0], status="incomplete")

            with self.assertRaisesRegex(
                RuntimeError,
                "execution status is incomplete",
            ):
                load_run_results(iteration)


class ViewerLayoutTests(unittest.TestCase):
    def test_documented_run_layout_exposes_prompt_and_final_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, iteration = prepare_iteration(root)
            manifest = load_iteration_manifest(iteration)
            eval_dir = iteration / manifest["evals"][0]["directory"]
            run_dir = eval_dir / CONFIG_NEW / "run-1"
            write_completed_result(run_dir)
            (run_dir / "outputs" / "final.md").write_text(
                "The final answer",
                encoding="utf-8",
            )

            runs = VIEWER_MODULE.find_runs(iteration)

        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["prompt"], "Complete the example task")
        self.assertEqual(runs[0]["eval_id"], 7)
        self.assertEqual(runs[0]["outputs"][0]["name"], "final.md")
        self.assertEqual(runs[0]["outputs"][0]["content"], "The final answer")


class OptimizationLoopTests(unittest.TestCase):
    def create_skill(self, parent: Path) -> Path:
        skill_dir = parent / "example-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: example-skill\n"
            "description: Use for example tasks.\n"
            "---\n\n"
            "# Example\n",
            encoding="utf-8",
        )
        return skill_dir

    def test_small_stratified_eval_keeps_training_examples(self):
        eval_set = [
            {"query": "positive", "should_trigger": True},
            {"query": "negative", "should_trigger": False},
        ]

        train, test = split_eval_set(eval_set, holdout=0.4)

        self.assertCountEqual(train, eval_set)
        self.assertEqual(test, [])

    @patch("scripts.run_loop.run_eval")
    def test_loop_accepts_codex_eval_results(self, run_eval_mock):
        run_eval_mock.return_value = {
            "results": [{
                "query": "Do the example task",
                "should_trigger": True,
                "trigger_rate": 1.0,
                "triggers": 1,
                "runs": 1,
                "expected_runs": 1,
                "error_count": 0,
                "errors": [],
                "status": "completed",
                "pass": True,
            }],
            "summary": {
                "total": 1,
                "passed": 1,
                "failed": 0,
                "error_runs": 0,
                "queries_with_errors": 0,
                "incomplete_queries": 0,
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            skill_dir = self.create_skill(Path(temp_dir))
            result = run_loop(
                eval_set=[{
                    "query": "Do the example task",
                    "should_trigger": True,
                }],
                skill_path=skill_dir,
                description_override=None,
                num_workers=1,
                timeout=10,
                max_iterations=1,
                runs_per_query=1,
                trigger_threshold=0.5,
                holdout=0,
                model="test-model",
                verbose=False,
            )

        self.assertEqual(result["exit_reason"], "all_passed (iteration 1)")
        self.assertEqual(result["best_description"], "Use for example tasks.")

    @patch("scripts.run_loop.run_eval")
    def test_loop_stops_on_incomplete_infrastructure_run(self, run_eval_mock):
        run_eval_mock.return_value = {
            "results": [{
                "query": "Do the example task",
                "should_trigger": True,
                "trigger_rate": 1.0,
                "triggers": 1,
                "runs": 1,
                "expected_runs": 3,
                "error_count": 2,
                "errors": ["codex exec timed out", "transport failed"],
                "status": "incomplete",
                "pass": False,
            }],
            "summary": {
                "total": 1,
                "passed": 0,
                "failed": 1,
                "error_runs": 2,
                "queries_with_errors": 1,
                "incomplete_queries": 1,
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            skill_dir = self.create_skill(Path(temp_dir))
            with self.assertRaisesRegex(
                RuntimeError,
                "did not complete every requested run",
            ):
                run_loop(
                    eval_set=[{
                        "query": "Do the example task",
                        "should_trigger": True,
                    }],
                    skill_path=skill_dir,
                    description_override=None,
                    num_workers=1,
                    timeout=10,
                    max_iterations=1,
                    runs_per_query=1,
                    trigger_threshold=0.5,
                    holdout=0,
                    model="test-model",
                    verbose=False,
                )


if __name__ == "__main__":
    unittest.main()
