import json
import tempfile
import unittest
from pathlib import Path

from generate_insights import DEFAULT_CRITERIA, generate_insights

CLAN = "#L0G0Y0JP"


def war(*participants):
    """One finished war. Each participant is (tag, fame, decksUsed)."""
    return {
        "standings": [{
            "clan": {
                "tag": CLAN,
                "participants": [
                    {"tag": tag, "fame": fame, "decksUsed": decks}
                    for tag, fame, decks in participants
                ],
            }
        }]
    }


def run_insights(members, wars, criteria=None):
    """members: list of (tag, name, role, donations). wars: newest war first."""
    members_data = {
        "memberList": [
            {"tag": tag, "name": name, "role": role, "donations": donations}
            for tag, name, role, donations in members
        ]
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        members_path = Path(tmpdir) / "members.json"
        history_path = Path(tmpdir) / "history.json"
        members_path.write_text(json.dumps(members_data), encoding="utf-8")
        history_path.write_text(json.dumps({"items": wars}), encoding="utf-8")
        return generate_insights(str(members_path), str(history_path), criteria=criteria)


def names(items):
    return [item["name"] for item in items]


class DefaultRulesTests(unittest.TestCase):
    def test_default_boundaries_for_members_and_elders(self):
        data = run_insights(
            [
                ("#M499", "KickMe", "member", 0),
                ("#M500", "Safe", "member", 0),
                ("#M2499", "AlmostElder", "member", 0),
                ("#M2500", "PromoteMe", "member", 0),
                ("#E1599", "DemoteMe", "elder", 0),
                ("#E1600", "ElderSafe", "elder", 0),
                ("#E3000", "StrongElder", "elder", 0),
            ],
            [war(
                ("#M499", 499, 16),
                ("#M500", 500, 16),
                ("#M2499", 2499, 16),
                ("#M2500", 2500, 16),
                ("#E1599", 1599, 16),
                ("#E1600", 1600, 16),
                ("#E3000", 3000, 16),
            )],
        )

        reviewed = {item["name"]: item["reason"] for item in data["review"]}
        self.assertEqual(names(data["promote"]), ["PromoteMe"])
        self.assertEqual(reviewed, {
            "KickMe": "Candidate for kick",
            "DemoteMe": "Candidate for elder demotion",
        })

    def test_elder_below_kick_threshold_is_demoted_not_kicked(self):
        data = run_insights(
            [("#E1", "Weak", "elder", 0)],
            [war(("#E1", 100, 2))],
        )

        self.assertEqual(data["review"][0]["reason"], "Candidate for elder demotion")

    def test_co_leaders_and_leaders_are_never_evaluated(self):
        data = run_insights(
            [
                ("#C1", "CoLeaderStrong", "coLeader", 500),
                ("#C2", "CoLeaderIdle", "coLeader", 0),
                ("#L1", "Leader", "leader", 0),
            ],
            [war(("#C1", 4000, 16), ("#C2", 0, 0), ("#L1", 0, 0))],
        )

        self.assertEqual(data["promote"], [])
        self.assertEqual(data["review"], [])

    def test_member_without_latest_war_data_is_not_kicked(self):
        data = run_insights(
            [("#N1", "Newcomer", "member", 0), ("#O1", "Veteran", "member", 0)],
            [war(("#O1", 2600, 16)), war(("#O1", 2600, 16), ("#N1", 2600, 16))],
        )

        self.assertNotIn("Newcomer", names(data["review"]))
        self.assertNotIn("Newcomer", names(data["inactive"]))
        self.assertEqual(names(data["promote"]), ["Veteran"])

    def test_zero_participation_member_is_kicked_and_listed_as_inactive(self):
        data = run_insights(
            [("#A2", "Bob", "member", 10)],
            [war(("#A2", 0, 0))],
        )

        self.assertEqual(names(data["inactive"]), ["Bob"])
        self.assertEqual(data["review"][0]["reason"], "Candidate for kick")

    def test_optional_criteria_are_off_by_default(self):
        for key in (
            "promoteElderAvgDecksEnabled",
            "promoteElderDonationsEnabled",
            "kickAvgDecksEnabled",
            "kickDonationsEnabled",
            "recentParticipationEnabled",
        ):
            self.assertFalse(DEFAULT_CRITERIA[key], key)

        # Few decks and no donations, but fame is what counts by default.
        data = run_insights(
            [("#A4", "Dana", "member", 0)],
            [war(("#A4", 3000, 5))],
        )

        self.assertEqual(names(data["promote"]), ["Dana"])


class OptionalCriteriaTests(unittest.TestCase):
    def test_promotion_requires_every_enabled_criterion(self):
        members = [("#A1", "Alice", "member", 300)]
        wars = [war(("#A1", 3000, 10)), war(("#A1", 3000, 10)), war(("#A1", 3000, 10))]

        blocked = run_insights(members, wars, {"promoteElderAvgDecksEnabled": True})
        self.assertEqual(blocked["promote"], [])

        allowed = run_insights(
            members,
            wars,
            {
                "promoteElderAvgDecksEnabled": True,
                "promoteElderAvgDecks": 10,
                "promoteElderDonationsEnabled": True,
                "promoteElderDonations": 100,
            },
        )
        promoted = allowed["promote"][0]
        self.assertEqual(promoted["name"], "Alice")
        self.assertEqual(promoted["donations"], 300)
        self.assertEqual(promoted["donationsPerWar"], 100)

    def test_promotion_can_run_on_optional_criteria_alone(self):
        data = run_insights(
            [("#A1", "Alice", "member", 0)],
            [war(("#A1", 1200, 16))],
            {"promoteElderLatestWarFameEnabled": False, "promoteElderAvgDecksEnabled": True},
        )

        self.assertEqual(names(data["promote"]), ["Alice"])

    def test_no_enabled_promotion_criteria_promotes_nobody(self):
        data = run_insights(
            [("#A1", "Alice", "member", 0)],
            [war(("#A1", 4000, 16))],
            {"promoteElderLatestWarFameEnabled": False},
        )

        self.assertEqual(data["promote"], [])

    def test_any_enabled_kick_criterion_flags_member(self):
        members = [("#A1", "Alice", "member", 0)]
        wars = [war(("#A1", 800, 6))]

        self.assertEqual(run_insights(members, wars)["review"], [])

        flagged = run_insights(members, wars, {"kickAvgDecksEnabled": True})
        self.assertEqual(names(flagged["review"]), ["Alice"])
        self.assertEqual(flagged["review"][0]["details"], ["Average decks per war 6.0 < 8"])

        flagged = run_insights(members, wars, {"kickDonationsEnabled": True})
        self.assertEqual(names(flagged["review"]), ["Alice"])

    def test_optional_kick_criteria_demote_elders(self):
        data = run_insights(
            [("#E1", "Elder", "elder", 0)],
            [war(("#E1", 2000, 6))],
            {"kickAvgDecksEnabled": True},
        )

        self.assertEqual(data["review"][0]["reason"], "Candidate for elder demotion")

    def test_recent_participation_flags_and_blocks_promotion(self):
        data = run_insights(
            [("#A3", "Charlie", "member", 200)],
            [war(("#A3", 5000, 1))],
            {"recentParticipationEnabled": True, "recentParticipationThreshold": 4},
        )

        self.assertNotIn("Charlie", names(data["promote"]))
        self.assertEqual(data["review"][0]["reason"], "Recent activity below threshold")


class OutputShapeTests(unittest.TestCase):
    def test_generate_insights_creates_summary_and_lists(self):
        data = generate_insights("clan_members.json", "history_data.json")

        for key in ("summary", "promote", "review", "inactive", "topPerformer", "generatedAt"):
            self.assertIn(key, data)
        self.assertIsInstance(data["summary"], dict)
        for key in ("promote", "review", "inactive"):
            self.assertIsInstance(data[key], list)


if __name__ == "__main__":
    unittest.main()
