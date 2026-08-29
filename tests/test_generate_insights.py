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


if __name__ == "__main__":
    unittest.main()
