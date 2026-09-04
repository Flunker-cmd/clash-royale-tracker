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
            "promoteElderAvgDecks": 14,
            "promoteElderDonations": 200,
            "promoteCoLeaderAvgDecks": 16,
            "promoteCoLeaderDonations": 250,
            "kickAvgDecks": 8,
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
                "promoteElderAvgDecks": 14,
                "promoteElderAvgDecksEnabled": False,
                "promoteElderDonations": 500,
                "promoteElderDonationsEnabled": True,
                "promoteCoLeaderAvgDecks": 16,
                "promoteCoLeaderAvgDecksEnabled": True,
                "promoteCoLeaderDonations": 1000,
                "promoteCoLeaderDonationsEnabled": True,
                "kickAvgDecks": 8,
                "kickAvgDecksEnabled": True,
                "kickDonations": 50,
                "kickDonationsEnabled": True,
            }

            data = generate_insights(str(members_path), str(history_path), criteria=criteria)

            self.assertEqual(data["promote"][0]["name"], "Alice")

    def test_generate_insights_marks_zero_participation_as_inactive(self):
        members = {
            "memberList": [
                {
                    "tag": "#A2",
                    "name": "Bob",
                    "role": "member",
                    "donations": 10,
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
                                "participants": []
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

            data = generate_insights(str(members_path), str(history_path))

            self.assertEqual(data["inactive"][0]["name"], "Bob")

    def test_generate_insights_blocks_promotion_when_recent_participation_is_low(self):
        members = {
            "memberList": [
                {
                    "tag": "#A3",
                    "name": "Charlie",
                    "role": "member",
                    "donations": 200,
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
                                    {"tag": "#A3", "fame": 5000, "decksUsed": 1}
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
                "recentParticipationThreshold": 4,
                "recentParticipationEnabled": True,
            }

            data = generate_insights(str(members_path), str(history_path), criteria=criteria)

            self.assertNotIn("Charlie", [item["name"] for item in data["promote"]])
            self.assertIn("Charlie", [item["name"] for item in data["review"]])

    def test_generate_insights_allows_promotion_without_current_donations_when_disabled(self):
        members = {
            "memberList": [
                {
                    "tag": "#A4",
                    "name": "Dana",
                    "role": "member",
                    "donations": 0,
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
                                    {"tag": "#A4", "fame": 100, "decksUsed": 16}
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
                "promoteElderAvgDecks": 14,
                "promoteElderAvgDecksEnabled": True,
                "promoteElderDonations": 50,
                "promoteElderDonationsEnabled": False,
                "recentParticipationThreshold": 4,
                "recentParticipationEnabled": True,
            }

            data = generate_insights(str(members_path), str(history_path), criteria=criteria)

            self.assertIn("Dana", [item["name"] for item in data["promote"]])

    def test_generate_insights_uses_trophies_and_average_decks_for_decisions(self):
        members = {
            "memberList": [
                {
                    "tag": "#A6",
                    "name": "Fiona",
                    "role": "member",
                    "trophies": 7421,
                    "donations": 0,
                }
            ]
        }
        history = {
            "items": [
                {"standings": [{"clan": {"tag": "#L0G0Y0JP", "participants": [{"tag": "#A6", "fame": 10, "decksUsed": 14}]}}]},
                {"standings": [{"clan": {"tag": "#L0G0Y0JP", "participants": [{"tag": "#A6", "fame": 5000, "decksUsed": 14}]}}]},
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            members_path = Path(tmpdir) / "members.json"
            history_path = Path(tmpdir) / "history.json"
            members_path.write_text(json.dumps(members), encoding="utf-8")
            history_path.write_text(json.dumps(history), encoding="utf-8")

            data = generate_insights(str(members_path), str(history_path))
            summary = data["promote"][0]

            self.assertEqual(summary["avgDecks"], 14)
            self.assertEqual(summary["name"], "Fiona")
            self.assertNotIn("Fiona", [item["name"] for item in data["review"]])

    def test_generate_insights_uses_donations_per_war_metric(self):
        members = {
            "memberList": [
                {
                    "tag": "#A5",
                    "name": "Eve",
                    "role": "member",
                    "donations": 300,
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
                                    {"tag": "#A5", "fame": 1000, "decksUsed": 16}
                                ],
                            }
                        }
                    ]
                },
                {
                    "standings": [
                        {
                            "clan": {
                                "tag": "#L0G0Y0JP",
                                "participants": [
                                    {"tag": "#A5", "fame": 1000, "decksUsed": 16}
                                ],
                            }
                        }
                    ]
                },
                {
                    "standings": [
                        {
                            "clan": {
                                "tag": "#L0G0Y0JP",
                                "participants": [
                                    {"tag": "#A5", "fame": 1000, "decksUsed": 16}
                                ],
                            }
                        }
                    ]
                },
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            members_path = Path(tmpdir) / "members.json"
            history_path = Path(tmpdir) / "history.json"
            members_path.write_text(json.dumps(members), encoding="utf-8")
            history_path.write_text(json.dumps(history), encoding="utf-8")

            criteria = {
                "promoteElderAvgDecks": 14,
                "promoteElderAvgDecksEnabled": True,
                "promoteElderDonations": 100,
                "promoteElderDonationsEnabled": True,
                "recentParticipationThreshold": 4,
                "recentParticipationEnabled": True,
            }

            data = generate_insights(str(members_path), str(history_path), criteria=criteria)

            promoted = [item for item in data["promote"] if item["name"] == "Eve"]
            self.assertEqual(len(promoted), 1)
            self.assertEqual(promoted[0]["donations"], 300)
            self.assertEqual(promoted[0]["donationsPerWar"], 100)


if __name__ == "__main__":
    unittest.main()
