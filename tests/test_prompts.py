from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from triathlon_agent.agents import syntax_guard
from triathlon_agent.compiler import compile_session_to_event
from triathlon_agent.contracts import validate_agent_output
from triathlon_agent.prompt_loader import load_prompts


PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


class RunningPromptTests(unittest.TestCase):
    def test_master_loads_existing_running_doctrines(self) -> None:
        prompts = load_prompts(PROMPT_DIR)
        master = prompts["master_prompt.md"]
        load_section = master.split("## Load these files first\n", 1)[1].split(
            "Also load these schema files", 1
        )[0]
        references = re.findall(r"`([a-z_]+\.md)`", load_section)

        self.assertIn("jack_daniels_run_doctrine.md", references)
        self.assertIn("threshold_testing_doctrine.md", references)
        for name in references:
            with self.subTest(prompt=name):
                self.assertIn(name, prompts)
        self.assertIn("## Running-only scope", master)
        for name, content in prompts.items():
            with self.subTest(prompt=name):
                for obsolete in (
                    "andrew_coggan_bike_doctrine.md",
                    "bike_sweet_spot",
                    "bike_threshold",
                    "bike_vo2",
                    "coggan_20",
                    "%FTP",
                    "% FTP",
                    "70.3",
                    "Ironman",
                ):
                    self.assertNotIn(obsolete, content)

    def test_running_scope_preserves_required_legacy_contract(self) -> None:
        prompts = load_prompts(PROMPT_DIR)
        for name in ("training_philosophy_auditor.md", "orchestrator.md"):
            with self.subTest(prompt=name):
                self.assertIn("coggan_alignment", prompts[name])
                self.assertIn('"pass"', prompts[name])
                self.assertIn("not applicable", prompts[name])
        for name in ("orchestrator.md", "threshold_testing_doctrine.md"):
            with self.subTest(prompt=name):
                self.assertIn('discipline: "run"', prompts[name])
                self.assertIn('sport: "Run"', prompts[name])
                self.assertIn("apply", prompts[name])

    def test_planner_running_examples_validate_and_compile(self) -> None:
        planner = load_prompts(PROMPT_DIR)["head_coach_planner.md"]
        examples = re.findall(r"```json\n(.*?)\n```", planner, re.DOTALL)
        self.assertEqual(len(examples), 2)
        for index, example in enumerate(examples):
            with self.subTest(example=index):
                session = {
                    "day": "Tuesday",
                    "date": "2026-03-10",
                    "discipline": "Run",
                    "session_name": "Threshold run",
                    "objective": "Develop running threshold",
                    "duration_min": 60,
                    "intensity_guidance": "Threshold effort",
                    "primary_metric": "Pace" if index == 0 else "HR",
                    "daniels_type": "T",
                    "blocks": json.loads(example),
                    "execution_notes": [],
                    "success_criteria": "Complete the intended effort",
                    "cut_first": "Defer if unwell",
                }
                if index == 1:
                    session["threshold_test"] = {
                        "discipline": "run",
                        "protocol": "friel_30_run",
                    }
                payload = {
                    "agent": "head_coach_planner",
                    "strategic_theme": "Running threshold",
                    "key_sessions": [],
                    "adaptations_targeted": [],
                    "sessions": [session],
                }
                self.assertEqual(
                    validate_agent_output("head_coach_planner", payload), []
                )
                event = compile_session_to_event(session, run_id="prompt-test")
                reviewed = syntax_guard.review(event)
                self.assertEqual(event["type"], "Run")
                self.assertEqual(reviewed["status"], "valid")
                self.assertTrue(reviewed["push_ready"])
                if index == 1:
                    self.assertIn(
                        "Test Effort\n- 10m\n- 20m", reviewed["final_description"]
                    )
