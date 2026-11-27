import json
import tempfile
import unittest
from pathlib import Path

from triathlon_agent.agents.head_coach_planner import impact_niggles
from triathlon_agent.threshold_testing import _has_niggle
from triathlon_agent.checkin import build_post_fetch_checkin, merge_checkin_answers
from triathlon_agent.utils import active_pain_text
from triathlon_agent.workflow import _pain_follow_ups


class MildPainTests(unittest.TestCase):
    def test_matching_mild_score_is_follow_up_only(self) -> None:
        self.assertEqual(active_pain_text("calf tight", {"calf": 4}), "")
        self.assertEqual(active_pain_text("Left calf tightness.", {"left calf": 0}), "")

    def test_score_of_five_stays_active(self) -> None:
        self.assertEqual(active_pain_text("calf tight", {"calf": 5}), "calf tight")

    def test_ambiguous_or_unknown_wording_stays_active(self) -> None:
        for text, scores in [
            ("calf tight and heel sore", {"calf": 4}),
            ("calf tight, heel numb", {"calf": 4}),
            ("both calves tight", {"calf": 4}),
            ("calf tight with running", {"calf": 4}),
            ("foot and heel sore", {"foot": 4}),
            ("left calf tight", {"calf": 4}),
            ("calf tight", {"left calf": 4}),
            ("left calf tight", {"left and right calf": 4}),
            ("calf tight", None),
            ("calf tight", {"calf": "high"}),
        ]:
            with self.subTest(text=text, scores=scores):
                self.assertTrue(active_pain_text(text, scores))

    def test_only_the_scored_complaint_is_removed(self) -> None:
        self.assertEqual(active_pain_text("calf tight, knee sore", {"calf": 4, "knee": 5}).strip(), "knee sore")

    def test_mild_score_does_not_restrict_but_five_does(self) -> None:
        mild = {"pain_or_niggles": "calf tight", "pain_scores": {"calf": 4}}
        self.assertFalse(_has_niggle(mild))
        self.assertEqual(impact_niggles({"weekly_checkin": mild}), [])
        severe = {"pain_or_niggles": "calf tight", "pain_scores": {"calf": 5}}
        self.assertTrue(_has_niggle(severe))
        self.assertEqual(impact_niggles({"weekly_checkin": severe}), ["calf"])


def _run(root: Path, name: str, date: str, athlete: str, scores: dict, *, recorded=True, override=False) -> Path:
    run = root / name
    run.mkdir()
    state = {"completed_steps": [], "override_flags": ["finalized_without_recorded_checkin"] if override else []}
    if recorded:
        state["checkin_recorded_at"] = "2026-01-01T00:00:00"
    (run / "planning_state.json").write_text(json.dumps(state))
    (run / "inputs.json").write_text(
        json.dumps({"local_inputs": {"athlete_profile": {"name": athlete}, "weekly_checkin": {}}})
    )
    (run / "weekly_checkin.json").write_text(json.dumps({"planning_date": date, "pain_scores": scores}))
    return run


class FollowUpTests(unittest.TestCase):
    def follow_ups(self, build) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root)
            current = root / "current"
            current.mkdir()
            return _pain_follow_ups(root, {"name": "Ann"}, "2026-03-08", current)

    def test_asks_about_mild_scores_even_without_approval_or_push(self) -> None:
        got = self.follow_ups(lambda r: _run(r, "a", "2026-03-01", "Ann", {"calf": 4, "knee": 0, "hip": 5}))
        self.assertEqual(got, {"calf": 4.0})

    def test_ignores_other_athletes_missing_names_overrides_and_unrecorded(self) -> None:
        def build(root: Path) -> None:
            _run(root, "b", "2026-03-01", "Bob", {"calf": 4})
            _run(root, "c", "2026-03-01", "", {"calf": 4})
            _run(root, "d", "2026-03-01", "Ann", {"calf": 4}, override=True)
            _run(root, "e", "2026-03-01", "Ann", {"calf": 4}, recorded=False)

        self.assertEqual(self.follow_ups(build), {})

    def test_latest_earlier_checkin_wins_and_same_week_is_skipped(self) -> None:
        def build(root: Path) -> None:
            _run(root, "old", "2026-02-22", "Ann", {"calf": 4})
            _run(root, "new", "2026-03-01", "Ann", {"knee": 2})
            _run(root, "same", "2026-03-08", "Ann", {"hip": 3})

        self.assertEqual(self.follow_ups(build), {"knee": 2.0})

    def test_question_is_added_and_the_score_is_not_a_current_answer(self) -> None:
        block = build_post_fetch_checkin("2026-03-08", pain_follow_ups={"calf": 4.0})
        question = next(q for q in block["questions"] if q["key"] == "pain_follow_up:calf")
        self.assertIn("calf", question["prompt"])
        self.assertNotIn("pain_follow_up:calf", [q["key"] for q in build_post_fetch_checkin("2026-03-08")["questions"]])


class MergeTests(unittest.TestCase):
    def test_partial_score_map_keeps_earlier_scores(self) -> None:
        first = merge_checkin_answers({"planning_date": "2026-03-08"}, {"pain_scores": {"calf": 4}})
        second = merge_checkin_answers(first, {"pain_scores": {"knee": 5}, "work_stress": 3})
        self.assertEqual(second["pain_scores"], {"calf": 4, "knee": 5})


if __name__ == "__main__":
    unittest.main()
