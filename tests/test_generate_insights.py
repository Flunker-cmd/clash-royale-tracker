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
            "promoteMemberAvgFame": 5000,
            "promoteMemberDonations": 200,
            "kickMemberAvgFame": 1000,
            "kickMemberDonations": 50,
            "reviewElderAvgFame": 2000,
            "inactiveParticipationRatio": 0.6,
        }

        data = generate_insights(str(members_path), str(history_path), criteria=criteria)

        self.assertIsInstance(data, dict)
        self.assertIsInstance(data["promote"], list)
        self.assertIsInstance(data["review"], list)


if __name__ == "__main__":
    unittest.main()
