import json
import tempfile
import unittest
from pathlib import Path

from track_members import track

NOW = "2026-09-19T12:00:00Z"


def member(tag, name, role="member"):
    return {"tag": tag, "name": name, "role": role}


class TrackMembersTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.members = root / "members.json"
        self.snapshot = root / "snapshot.json"
        self.events = root / "events.json"

    def run_track(self, roster, now=NOW):
        self.members.write_text(json.dumps({"memberList": roster}), encoding="utf-8")
        return track(str(self.members), str(self.snapshot), str(self.events), now=now)

    def read_events(self):
        return json.loads(self.events.read_text(encoding="utf-8"))

    def test_first_run_saves_snapshot_without_events(self):
        result = self.run_track([member("#A", "Alice"), member("#B", "Bob")])

        self.assertEqual(result, [])
        self.assertEqual(set(json.loads(self.snapshot.read_text(encoding="utf-8"))), {"#A", "#B"})
        self.assertEqual(self.read_events(), {"trackingSince": NOW, "events": []})

    def test_detects_join_leave_promotion_and_demotion(self):
        self.run_track([member("#A", "Alice"), member("#B", "Bob", "elder"), member("#C", "Cleo", "elder")])
        result = self.run_track(
            [member("#A", "Alice", "elder"), member("#B", "Bob", "member"), member("#D", "Dan")],
            now="2026-09-20T12:00:00Z",
        )

        summary = {(event["type"], event["name"]) for event in result}
        self.assertEqual(summary, {
            ("promoted", "Alice"),
            ("demoted", "Bob"),
            ("left", "Cleo"),
            ("joined", "Dan"),
        })
        promoted = next(event for event in result if event["type"] == "promoted")
        self.assertEqual((promoted["from"], promoted["to"]), ("member", "elder"))
        self.assertEqual(len(self.read_events()["events"]), 4)

    def test_unchanged_roster_writes_nothing_new(self):
        roster = [member("#A", "Alice"), member("#B", "Bob")]
        self.run_track(roster)
        before = self.events.read_text(encoding="utf-8")

        self.assertEqual(self.run_track(roster, now="2026-09-20T12:00:00Z"), [])
        self.assertEqual(self.events.read_text(encoding="utf-8"), before)

    def test_newest_events_come_first(self):
        self.run_track([member("#A", "Alice")])
        self.run_track([member("#A", "Alice"), member("#B", "Bob")], now="2026-09-20T12:00:00Z")
        self.run_track([member("#A", "Alice"), member("#B", "Bob"), member("#C", "Cleo")], now="2026-09-21T12:00:00Z")

        self.assertEqual([event["name"] for event in self.read_events()["events"]], ["Cleo", "Bob"])

    def test_suspiciously_small_roster_is_ignored(self):
        roster = [member(f"#M{i}", f"Player {i}") for i in range(20)]
        self.run_track(roster)

        self.assertIsNone(self.run_track(roster[:3], now="2026-09-20T12:00:00Z"))
        self.assertEqual(self.read_events()["events"], [])
        self.assertEqual(len(json.loads(self.snapshot.read_text(encoding="utf-8"))), 20)

    def test_empty_roster_is_ignored(self):
        self.run_track([member("#A", "Alice")])

        self.assertIsNone(self.run_track([], now="2026-09-20T12:00:00Z"))
        self.assertEqual(self.read_events()["events"], [])


if __name__ == "__main__":
    unittest.main()
