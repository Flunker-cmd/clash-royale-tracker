import json
import tempfile
import unittest
from pathlib import Path

from track_war_days import track, update_war_days, war_day

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


class TrackTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.race = root / "race.json"
        self.days = root / "days.json"

    def test_training_day_creates_empty_file_then_war_day_records(self):
        self.race.write_text(json.dumps(race(8, [], period_type="training")), encoding="utf-8")
        self.assertEqual(track(str(self.race), str(self.days), now=NOW), 0)
        self.assertEqual(json.loads(self.days.read_text(encoding="utf-8")), {"warKey": None, "days": {}})

        self.race.write_text(json.dumps(race(12, [participant("#A", 9, 1)])), encoding="utf-8")
        self.assertEqual(track(str(self.race), str(self.days), now=NOW), 3)
        saved = json.loads(self.days.read_text(encoding="utf-8"))
        self.assertEqual(saved["days"]["3"]["players"]["#A"]["base"], 8)


if __name__ == "__main__":
    unittest.main()
