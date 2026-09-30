"""Record how many decks each player used on each day of the current war.

The API only reports decks used today and decks used in the whole war, so past
days are lost unless we save them. Every run stores, per player, the decks used
before today ("base") and today's decks. When the next day has been seen, the
difference between the two days' bases gives the exact count for the earlier
day, even if the last run of that day happened before the player's last battle.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

DECKS_PER_DAY = 4
WAR_DAYS = 4
WAR_PERIOD_TYPES = ("warDay", "colosseum")


def war_day(race):
    """Return the war day (1-4) of the current river race, or 0 outside war days."""
    if race.get("periodType") not in WAR_PERIOD_TYPES:
        return 0
    # periodIndex counts days through the season: 3 training days and 4 war days per week.
    day = int(race.get("periodIndex", 0)) % 7 - 2
    return day if 1 <= day <= WAR_DAYS else 0


def update_war_days(state, race, now):
    """Return the new state after recording the snapshot `race`, or None if it is not a war day."""
    day = war_day(race)
    if not day:
        return None

    war_key = f"{race.get('sectionIndex', 0)}:{int(race['periodIndex']) - day + 1}"
    if not state or state.get("warKey") != war_key:
        state = {"warKey": war_key, "days": {}}

    players = {}
    for participant in race.get("clan", {}).get("participants", []):
        tag = participant.get("tag")
        if not tag:
            continue
        today = int(participant.get("decksUsedToday", 0))
        players[tag] = {
            "name": participant.get("name"),
            "base": int(participant.get("decksUsed", 0)) - today,
            "decks": today,
        }

    state["days"][str(day)] = {"updated": now, "players": players}

    # Yesterday's final count is the growth of the base between yesterday and today.
    previous = state["days"].get(str(day - 1))
    if previous:
        for tag, before in previous["players"].items():
            current = players.get(tag)
            if current is not None:
                played = min(DECKS_PER_DAY, current["base"] - before["base"])
                before["decks"] = max(before["decks"], played)

    return state


def read_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def track(race_path="clan_data.json", days_path="war_days.json", now=None):
    """Update war_days.json. Returns the recorded war day, or 0 if nothing was recorded."""
    race = read_json(race_path, {})
    now = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    previous = read_json(days_path, None)
    state = update_war_days(previous, race, now)
    if state is None:
        # The workflow commits this file, so it has to exist before the first war day too.
        if previous is None:
            write_json(days_path, {"warKey": None, "days": {}})
        return 0
    write_json(days_path, state)
    return war_day(race)


if __name__ == "__main__":
    recorded = track()
    print(f"War day {recorded} recorded." if recorded else "No war day in progress, nothing recorded.")
