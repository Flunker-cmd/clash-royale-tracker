import json
import tempfile
import unittest
from pathlib import Path

from generate_insights import generate_insights


class GenerateInsightsTests(unittest.TestCase):
    def test_generate_insights_creates_summary_and_lists(self):
        members_path = Path("clan_members.json")
        history_path = Path("history_data.json")

        data = generate_insights(str(members_path), str(history_path))

        self.assertIsInstance(data, dict)
        self.assertIn("summary", data)
        self.assertIn("promote", data)
        self.assertIn("review", data)
        self.assertIn("inactive", data)
        self.assertIn("topPerformer", data)
        self.assertIn("generatedAt", data)

        self.assertIsInstance(data["summary"], dict)
        self.assertIsInstance(data["promote"], list)
        self.assertIsInstance(data["review"], list)
        self.assertIsInstance(data["inactive"], list)

    def test_generate_insights_respects_custom_criteria(self):
        members_path = Path("clan_members.json")
        history_path = Path("history_data.json")
        criteria = {
            "promoteElderAvgFame": 5000,
            "promoteElderDonations": 200,
            "promoteCoLeaderAvgFame": 6000,
            "promoteCoLeaderDonations": 250,
            "kickAvgFame": 1000,
            "kickDonations": 50,
        }

        data = generate_insights(str(members_path), str(history_path), criteria=criteria)

        self.assertIsInstance(data, dict)
        self.assertIsInstance(data["promote"], list)
        self.assertIsInstance(data["review"], list)

    def test_generate_insights_ignores_disabled_metric(self):
        members = {
            "memberList": [
                {
                    "tag": "#A1",
                    "name": "Alice",
                    "role": "member",
                    "donations": 1000,
                    "lastSeen": "2024-01-01T00:00:00Z",
                }
            ]
        }
        history = {
            "items": [
                {
                    "standings": [
                        {
                            "clan": {
                                "tag": "#L0G0Y0JP",
                                "participants": [
                                    {"tag": "#A1", "fame": 100, "decksUsed": 16}
                                ],
                            }
                        }
                    ]
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            members_path = Path(tmpdir) / "members.json"
            history_path = Path(tmpdir) / "history.json"
            members_path.write_text(json.dumps(members), encoding="utf-8")
            history_path.write_text(json.dumps(history), encoding="utf-8")

            criteria = {
                "promoteElderAvgFame": 2000,
                "promoteElderAvgFameEnabled": False,
                "promoteElderDonations": 500,
                "promoteElderDonationsEnabled": True,
                "promoteCoLeaderAvgFame": 2500,
                "promoteCoLeaderAvgFameEnabled": True,
                "promoteCoLeaderDonations": 1000,
                "promoteCoLeaderDonationsEnabled": True,
                "kickAvgFame": 100,
                "kickAvgFameEnabled": True,
                "kickDonations": 50,
                "kickDonationsEnabled": True,
            }

            data = generate_insights(str(members_path), str(history_path), criteria=criteria)

            self.assertEqual(data["promote"][0]["name"], "Alice")


if __name__ == "__main__":
    unittest.main()
