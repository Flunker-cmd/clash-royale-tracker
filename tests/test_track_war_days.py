import json
import tempfile
import unittest
from pathlib import Path

from track_war_days import CLAN_TAG, finish_war, track, update_war_days, war_day

NOW = "2026-09-19T12:00:00Z"


def participant(tag, used, today, name=None):
    return {"tag": tag, "name": name or tag, "decksUsed": used, "decksUsedToday": today}


def race(period_index, participants, period_type="warDay", section=1):
    return {
        "periodType": period_type,
        "periodIndex": period_index,
        "sectionIndex": section,
        "clan": {"participants": participants},
    }


class WarDayTests(unittest.TestCase):
    def test_maps_period_index_to_war_day(self):
        self.assertEqual(war_day(race(10, [])), 1)
        self.assertEqual(war_day(race(13, [])), 4)
        self.assertEqual(war_day(race(18, [], period_type="colosseum")), 2)
        self.assertEqual(war_day(race(8, [], period_type="training")), 0)


class UpdateWarDaysTests(unittest.TestCase):
    def test_training_day_records_nothing(self):
        self.assertIsNone(update_war_days(None, race(8, [], period_type="training"), NOW))

    def test_records_todays_decks_and_base(self):
        state = update_war_days(None, race(11, [participant("#A", 6, 2)]), NOW)

        self.assertEqual(state["warKey"], "1:10")
        self.assertEqual(state["days"]["2"]["players"]["#A"], {"name": "#A", "base": 4, "decks": 2})

    def test_next_day_finalizes_previous_day_from_base(self):
        # The last run on day 1 saw 2 decks, but the player finished all 4 before the reset.
        state = update_war_days(None, race(10, [participant("#A", 2, 2)]), NOW)
        state = update_war_days(state, race(11, [participant("#A", 5, 1)]), NOW)

        self.assertEqual(state["days"]["1"]["players"]["#A"]["decks"], 4)
        self.assertEqual(state["days"]["2"]["players"]["#A"]["decks"], 1)

    def test_player_missing_today_keeps_last_seen_count(self):
        state = update_war_days(None, race(10, [participant("#A", 3, 3)]), NOW)
        state = update_war_days(state, race(11, []), NOW)

        self.assertEqual(state["days"]["1"]["players"]["#A"]["decks"], 3)

    def test_new_war_starts_fresh(self):
        state = update_war_days(None, race(12, [participant("#A", 8, 4)]), NOW)
        state = update_war_days(state, race(17, [participant("#B", 4, 4)], section=2), NOW)

        self.assertEqual(state["warKey"], "2:17")
        self.assertEqual(list(state["days"]), ["1"])
        self.assertEqual(list(state["days"]["1"]["players"]), ["#B"])


def history(participants, section=1, season=136, clan_tag=CLAN_TAG):
    standings = [
        {"clan": {"tag": "#OTHER", "participants": [participant("#A", 16, 0)]}},
        {"clan": {"tag": clan_tag, "participants": participants}},
    ]
    return {"items": [{"seasonId": season, "sectionIndex": section, "standings": standings}]}


def four_days(sunday_seen):
    """A war tracked through all four days where the last run on Sunday saw `sunday_seen` decks."""
    state = None
    for day in range(4):
        today = sunday_seen if day == 3 else 4
        state = update_war_days(state, race(10 + day, [participant("#A", 4 * day + today, today)]), NOW)
    return state


class FinishWarTests(unittest.TestCase):
    def test_sunday_count_comes_from_war_total(self):
        # The last run on Sunday saw 1 deck, but the player played all 4 before the war ended.
        state = finish_war(four_days(1), history([participant("#A", 16, 0)]))

        self.assertEqual(state["days"]["4"]["players"]["#A"]["decks"], 4)
        self.assertTrue(state["finished"])
        self.assertEqual(state["seasonId"], 136)

    def test_never_lowers_a_count_or_goes_above_four(self):
        state = finish_war(four_days(3), history([participant("#A", 13, 0)]))
        self.assertEqual(state["days"]["4"]["players"]["#A"]["decks"], 3)

        state = finish_war(four_days(1), history([participant("#A", 30, 0)]))
        self.assertEqual(state["days"]["4"]["players"]["#A"]["decks"], 4)

    def test_player_missing_from_log_keeps_last_seen_count(self):
        state = finish_war(four_days(2), history([participant("#B", 16, 0)]))

        self.assertEqual(state["days"]["4"]["players"]["#A"]["decks"], 2)
        self.assertTrue(state["finished"])

    def test_log_of_another_war_changes_nothing(self):
        state = four_days(1)
        self.assertIsNone(finish_war(state, history([participant("#A", 16, 0)], section=2)))
        self.assertIsNone(finish_war(state, {"items": []}))
        self.assertIsNone(finish_war({"warKey": None, "days": {}}, history([])))

    def test_war_without_a_saved_sunday_is_not_finished(self):
        state = None
        for day in range(3):
            state = update_war_days(state, race(10 + day, [participant("#A", 4 * day + 4, 4)]), NOW)

        self.assertIsNone(finish_war(state, history([participant("#A", 16, 0)])))


class TrackTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.race = root / "race.json"
        self.days = root / "days.json"
        self.history = root / "history.json"
        self.history.write_text(json.dumps({"items": []}), encoding="utf-8")

    def run_track(self):
        return track(str(self.race), str(self.days), str(self.history), now=NOW)

    def test_training_day_creates_empty_file_then_war_day_records(self):
        self.race.write_text(json.dumps(race(8, [], period_type="training")), encoding="utf-8")
        self.assertEqual(self.run_track(), 0)
        self.assertEqual(json.loads(self.days.read_text(encoding="utf-8")), {"warKey": None, "days": {}})

        self.race.write_text(json.dumps(race(12, [participant("#A", 9, 1)])), encoding="utf-8")
        self.assertEqual(self.run_track(), 3)
        saved = json.loads(self.days.read_text(encoding="utf-8"))
        self.assertEqual(saved["days"]["3"]["players"]["#A"]["base"], 8)

    def test_training_day_after_war_finishes_saved_war(self):
        self.days.write_text(json.dumps(four_days(1)), encoding="utf-8")
        self.history.write_text(json.dumps(history([participant("#A", 16, 0)])), encoding="utf-8")
        self.race.write_text(json.dumps(race(14, [], period_type="training")), encoding="utf-8")

        self.assertEqual(self.run_track(), 0)
        saved = json.loads(self.days.read_text(encoding="utf-8"))
        self.assertTrue(saved["finished"])
        self.assertEqual(saved["days"]["4"]["players"]["#A"]["decks"], 4)


if __name__ == "__main__":
    unittest.main()
