"""Track clan membership changes between runs.

Compares the current clan_members.json with the snapshot saved by the previous
run and appends joined / left / promoted / demoted events to member_events.json.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROLE_ORDER = {"member": 1, "elder": 2, "coLeader": 3, "leader": 4}
MAX_EVENTS = 300
# An API hiccup that returns a fraction of the roster must not look like a mass exodus.
MIN_ROSTER_RATIO = 0.5


def snapshot_from(members):
    return {
        member["tag"]: {"name": member.get("name"), "role": member.get("role", "member")}
        for member in members
        if member.get("tag")
    }


def diff_snapshots(old, new, now):
    events = []

    for tag, current in new.items():
        previous = old.get(tag)
        if previous is None:
            events.append({"date": now, "type": "joined", "tag": tag, "name": current["name"], "role": current["role"]})
            continue

        before = ROLE_ORDER.get(previous["role"], 0)
        after = ROLE_ORDER.get(current["role"], 0)
        if after != before:
            events.append({
                "date": now,
                "type": "promoted" if after > before else "demoted",
                "tag": tag,
                "name": current["name"],
                "from": previous["role"],
                "to": current["role"],
            })

    for tag, previous in old.items():
        if tag not in new:
            events.append({"date": now, "type": "left", "tag": tag, "name": previous["name"], "role": previous["role"]})

    return sorted(events, key=lambda event: (event["type"], event["name"] or ""))


def read_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def track(
    members_path="clan_members.json",
    snapshot_path="member_snapshot.json",
    events_path="member_events.json",
    now=None,
):
    """Update the snapshot and event log. Returns the new events, or None if nothing was tracked."""
    members = read_json(members_path, {}).get("memberList", [])
    if not members:
        return None

    now = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    current = snapshot_from(members)
    previous = read_json(snapshot_path, None)
    log = read_json(events_path, {"trackingSince": now, "events": []})

    if previous is None:
        write_json(snapshot_path, current)
        write_json(events_path, log)
        return []

    if len(previous) >= 10 and len(current) < len(previous) * MIN_ROSTER_RATIO:
        return None

    new_events = diff_snapshots(previous, current, now)
    if new_events:
        log["events"] = (new_events + log.get("events", []))[:MAX_EVENTS]
        write_json(events_path, log)
    if current != previous:
        write_json(snapshot_path, current)
    return new_events


if __name__ == "__main__":
    result = track()
    if result is None:
        print("Membership tracking skipped (no member data or suspicious roster size).")
    else:
        print(f"Membership tracking done: {len(result)} new event(s).")
