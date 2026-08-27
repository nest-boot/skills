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
from scripts.aggregate_benchmark import generate_benchmark, load_run_results
from scripts.collect_codex_metrics import collect_metrics, write_run_metrics
from scripts.run_eval import (
    build_skill_fixture,
    output_shows_skill_load,
    summarize_query_result,
)
from scripts.run_loop import run_loop, split_eval_set


VIEWER_MODULE_PATH = SKILL_ROOT / "eval-viewer" / "generate_review.py"
VIEWER_SPEC = importlib.util.spec_from_file_location(
    "skill_creator_generate_review",
    VIEWER_MODULE_PATH,
)
VIEWER_MODULE = importlib.util.module_from_spec(VIEWER_SPEC)
assert VIEWER_SPEC.loader is not None
VIEWER_SPEC.loader.exec_module(VIEWER_MODULE)


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


class DescriptionOptimizerTests(unittest.TestCase):
    @patch("scripts.improve_description.subprocess.run")
    def test_uses_output_schema_and_parses_description(self, run_mock):
        run_mock.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='{"new_description":"Use for focused example tasks."}',
            stderr="",
        )

        raw, description = _call_codex("Improve this description", "test-model")

        self.assertEqual(
            json.loads(raw),
            {"new_description": "Use for focused example tasks."},
        )
        self.assertEqual(description, "Use for focused example tasks.")
        command = run_mock.call_args.args[0]
        self.assertIn("--output-schema", command)
        self.assertIn(str(DESCRIPTION_SCHEMA), command)
        self.assertIn("--model", command)
        self.assertEqual(command[-1], "-")


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
            benchmark_dir = Path(temp_dir)
            eval_dir = benchmark_dir / "eval-0"
            run_dir = eval_dir / "with_skill" / "run-1"
            outputs_dir = run_dir / "outputs"
            outputs_dir.mkdir(parents=True)

            (eval_dir / "eval_metadata.json").write_text(
                json.dumps({"eval_id": 7}),
                encoding="utf-8",
            )
            (run_dir / "grading.json").write_text(
                json.dumps({
                    "expectations": [],
                    "summary": {
                        "passed": 0,
                        "failed": 0,
                        "total": 0,
                        "pass_rate": 0,
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
            (run_dir / "timing.json").write_text(
                json.dumps({
                    "total_duration_seconds": 12.5,
                    "total_tokens": 4321,
                    "run_status": "completed",
                    "exit_code": 0,
                }),
                encoding="utf-8",
            )
            (outputs_dir / "metrics.json").write_text(
                json.dumps({
                    "total_tool_calls": 4,
                    "errors_encountered": 1,
                    "run_status": "completed",
                    "exit_code": 0,
                }),
                encoding="utf-8",
            )

            results = load_run_results(benchmark_dir)

        run = results["with_skill"][0]
        self.assertEqual(run["eval_id"], 7)
        self.assertEqual(run["time_seconds"], 12.5)
        self.assertEqual(run["tokens"], 4321)
        self.assertEqual(run["tool_calls"], 4)
        self.assertEqual(run["errors"], 1)

    def test_benchmark_reports_actual_run_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            benchmark_dir = Path(temp_dir)
            run_dir = benchmark_dir / "eval-0" / "with_skill" / "run-1"
            outputs_dir = run_dir / "outputs"
            outputs_dir.mkdir(parents=True)
            (run_dir / "grading.json").write_text(json.dumps({
                "expectations": [],
                "summary": {
                    "passed": 1,
                    "failed": 0,
                    "total": 1,
                    "pass_rate": 1.0,
                },
                "user_notes_summary": {},
            }))
            (outputs_dir / "metrics.json").write_text(json.dumps({
                "run_status": "completed",
                "errors_encountered": 0,
            }))

            benchmark = generate_benchmark(benchmark_dir)

        self.assertEqual(benchmark["metadata"]["runs_per_configuration"], 1)
        self.assertEqual(
            benchmark["metadata"]["run_counts_by_configuration"],
            {"with_skill": {"0": 1}},
        )

    def test_aggregator_rejects_incomplete_execution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            benchmark_dir = Path(temp_dir)
            run_dir = benchmark_dir / "eval-0" / "with_skill" / "run-1"
            outputs_dir = run_dir / "outputs"
            outputs_dir.mkdir(parents=True)
            (run_dir / "grading.json").write_text(json.dumps({
                "expectations": [],
                "summary": {
                    "passed": 1,
                    "failed": 0,
                    "total": 1,
                    "pass_rate": 1.0,
                },
                "user_notes_summary": {},
            }))
            (outputs_dir / "metrics.json").write_text(json.dumps({
                "run_status": "incomplete",
                "errors_encountered": 1,
            }))

            with self.assertRaisesRegex(
                RuntimeError,
                "execution status is incomplete",
            ):
                load_run_results(benchmark_dir)


class ViewerLayoutTests(unittest.TestCase):
    def test_documented_run_layout_exposes_prompt_and_final_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            eval_dir = root / "eval-descriptive-name"
            run_dir = eval_dir / "with_skill" / "run-1"
            outputs_dir = run_dir / "outputs"
            outputs_dir.mkdir(parents=True)
            (eval_dir / "eval_metadata.json").write_text(json.dumps({
                "eval_id": 7,
                "prompt": "Return a concise answer",
                "assertions": [],
            }))
            (outputs_dir / "final.md").write_text("The final answer")
            (outputs_dir / "metrics.json").write_text(json.dumps({
                "run_status": "completed",
                "errors_encountered": 0,
            }))

            runs = VIEWER_MODULE.find_runs(root)

        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["prompt"], "Return a concise answer")
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
