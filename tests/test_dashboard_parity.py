"""The recommendation rules exist twice: in generate_insights.py and in index.html.

This test feeds the same scenarios through both so they cannot drift apart.
"""

import itertools
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from generate_insights import evaluate_member, merge_criteria

ROOT = Path(__file__).resolve().parent.parent

# What the dashboard prints for each action the Python side can return.
DASHBOARD_TEXT = {
    "promote": "Befordra till elder",
    "kick": "Kicka",
    "demote": "Degradera till medlem",
    "lowActivity": "Låg aktivitet nyligen",
}

CRITERIA_SETS = [
    {},
    {"promoteElderAvgDecksEnabled": True},
    {"promoteElderDonationsEnabled": True},
    {"kickAvgDecksEnabled": True},
    {"kickDonationsEnabled": True},
    {"recentParticipationEnabled": True},
    {"promoteElderLatestWarFameEnabled": False},
    {"kickMemberLatestWarFameEnabled": False, "demoteElderLatestWarFameEnabled": False},
    {
        "promoteElderAvgDecksEnabled": True,
        "promoteElderDonationsEnabled": True,
        "kickAvgDecksEnabled": True,
        "kickDonationsEnabled": True,
        "recentParticipationEnabled": True,
    },
]


def build_scenarios():
    members = [
        {
            "role": role,
            "inLatestWar": in_latest_war,
            "latestWarFame": fame,
            "avgDecks": avg_decks,
            "donationsPerWar": donations,
            "latestWarParticipation": participation,
        }
        for role, in_latest_war, fame, avg_decks, donations, participation in itertools.product(
            ["member", "elder", "coLeader", "leader"],
            [True, False],
            [0, 499, 500, 1599, 1600, 2499, 2500],
            [0, 7.9, 8, 14],
            [0, 29, 30, 50],
            [0, 3, 4, 16],
        )
    ]
    return [{"member": member, "criteria": criteria} for criteria in CRITERIA_SETS for member in members]


@unittest.skipUnless(shutil.which("node"), "node is required to run the dashboard logic")
class DashboardParityTests(unittest.TestCase):
    def test_python_and_dashboard_give_the_same_recommendations(self):
        scenarios = build_scenarios()

        with tempfile.TemporaryDirectory() as tmpdir:
            scenario_path = Path(tmpdir) / "scenarios.json"
            scenario_path.write_text(json.dumps(scenarios), encoding="utf-8")
            result = subprocess.run(
                ["node", str(ROOT / "tests" / "dashboard_logic.js"), str(scenario_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )
        dashboard_texts = json.loads(result.stdout)
        self.assertEqual(len(dashboard_texts), len(scenarios))

        mismatches = []
        for scenario, dashboard_text in zip(scenarios, dashboard_texts):
            action, _ = evaluate_member(scenario["member"], merge_criteria(scenario["criteria"]))
            expected = DASHBOARD_TEXT.get(action)
            actual = dashboard_text if dashboard_text in DASHBOARD_TEXT.values() else None
            if expected != actual:
                mismatches.append((scenario, expected, dashboard_text))

        self.assertEqual(mismatches[:3], [], f"{len(mismatches)} of {len(scenarios)} scenarios differ")


if __name__ == "__main__":
    unittest.main()
