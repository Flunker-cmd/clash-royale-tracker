import json
import math
from datetime import datetime, timezone
from pathlib import Path

CLAN_TAG = "#L0G0Y0JP"
DECKS_PER_WAR = 16

# Default rules:
#   member with all 16 decks in each of the 3 latest wars -> promote to elder
#   member  <   500 fame in the latest war -> kick
#   elder   <  1600 fame in each of the 2 latest wars -> demote to member (elder works as an
#                  extra life); one such war gives a warning
# Co-leaders are appointed manually and never get a recommendation.
# The remaining criteria are optional filters that are off by default.
DEFAULT_CRITERIA = {
    "kickMemberLatestWarFame": 500,
    "kickMemberLatestWarFameEnabled": True,
    "promoteElderFullWars": 3,
    "promoteElderFullWarsEnabled": True,
    "demoteElderLatestWarFame": 1600,
    "demoteElderLatestWarFameEnabled": True,
    "demoteElderWeakWars": 2,
    "promoteElderAvgDecks": 14,
    "promoteElderAvgDecksEnabled": False,
    "promoteElderDonations": 50,
    "promoteElderDonationsEnabled": False,
    "kickAvgDecks": 8,
    "kickAvgDecksEnabled": False,
    "kickDonations": 30,
    "kickDonationsEnabled": False,
    "recentParticipationThreshold": 4,
    "recentParticipationEnabled": False,
}


def metric_is_enabled(criteria, metric_key):
    return criteria.get(f"{metric_key}Enabled", True) is not False


def merge_criteria(criteria=None):
    merged = DEFAULT_CRITERIA.copy()
    if criteria:
        merged.update(criteria)
    return merged


def parse_last_seen(value):
    if not value:
        return None

    try:
        for fmt in (
            "%Y%m%dT%H%M%S.%fZ",
            "%Y%m%dT%H%M%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
        ):
            try:
                dt = datetime.strptime(value, fmt)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue

        value = value.replace(" ", "T")
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None


def get_war_stats(history_data):
    total_weeks = len(history_data.get("items", []))
    stats = {}

    for week_index, race in enumerate(history_data.get("items", [])):
        clan_standing = next(
            (
                standing
                for standing in race.get("standings", [])
                if standing.get("clan", {}).get("tag") == CLAN_TAG
            ),
            None,
        )
        if not clan_standing:
            continue

        for participant in clan_standing.get("clan", {}).get("participants", []):
            tag = participant.get("tag")
            if not tag:
                continue

            entry = stats.setdefault(
                tag,
                {
                    "fame": 0,
                    "decks": 0,
                    "weeks": 0,
                    "history": [None] * total_weeks,
                    "fameHistory": [None] * total_weeks,
                },
            )

            decks_used = int(participant.get("decksUsed") or 0)
            fame_gained = int(participant.get("fame") or 0)
            entry["fame"] += fame_gained
            entry["decks"] += decks_used
            entry["weeks"] += 1
            entry["history"][week_index] = decks_used
            entry["fameHistory"][week_index] = fame_gained

    return stats, total_weeks


def full_war_streak(deck_history):
    """Number of wars in a row, counting back from the latest, with every deck used."""
    streak = 0
    for decks in deck_history:
        if decks is None or decks < DECKS_PER_WAR:
            break
        streak += 1
    return streak


def weak_war_streak(fame_history, limit):
    """Number of wars in a row, counting back from the latest, with fame below the limit."""
    streak = 0
    for fame in fame_history:
        if fame is None or fame >= limit:
            break
        streak += 1
    return streak


def member_summary(member, war_stats, total_weeks):
    tag = member.get("tag")
    war = war_stats.get(tag, {"fame": 0, "decks": 0, "weeks": 0, "history": [None] * total_weeks, "fameHistory": [None] * total_weeks})
    active_weeks = int(war.get("weeks") or 0)
    latest_war_participation = 0
    latest_war_fame = 0
    in_latest_war = bool(war.get("history")) and war["history"][0] is not None
    if war.get("history"):
        latest_war_participation = int(war["history"][0] or 0)
    if war.get("fameHistory"):
        latest_war_fame = int(war["fameHistory"][0] or 0)
    avg_fame = round(war.get("fame", 0) / active_weeks) if active_weeks else 0
    avg_decks = round(war.get("decks", 0) / active_weeks, 1) if active_weeks else 0
    donations = int(member.get("donations") or 0)
    donations_per_war = round(donations / active_weeks) if active_weeks else 0
    role = member.get("role", "member")
    last_seen = parse_last_seen(member.get("lastSeen"))

    if last_seen is not None:
        delta = datetime.now(timezone.utc) - last_seen
        last_seen_hours = delta.total_seconds() / 3600
    else:
        last_seen_hours = float("inf")

    return {
        "tag": tag,
        "name": member.get("name"),
        "role": role,
        "trophies": int(member.get("trophies") or 0),
        "donations": donations,
        "donationsPerWar": donations_per_war,
        "avgFame": avg_fame,
        "latestWarFame": latest_war_fame,
        "avgDecks": avg_decks,
        "totalDecks": int(war.get("decks") or 0),
        "activeWeeks": active_weeks,
        "latestWarParticipation": latest_war_participation,
        "fullWarStreak": full_war_streak(war.get("history") or []),
        "fameHistory": war.get("fameHistory") or [],
        "totalWeeks": total_weeks,
        "lastSeenHours": last_seen_hours,
        "inLatestWar": in_latest_war,
        "inactive": in_latest_war and latest_war_participation == 0,
    }


def evaluate_member(member, criteria):
    """Return (action, details) for a member or elder.

    Actions: "kick", "demote", "warning", "lowActivity", "promote" or None.
    Downward criteria (kick/demote) trigger when any enabled one is hit;
    promotion requires every enabled promotion criterion to be met. An elder is
    demoted on fame only after several weak wars in a row and gets a warning
    before that. Co-leaders, leaders and members without data for the latest
    war are never evaluated.
    """
    role = member["role"]
    if role not in ("member", "elder") or not member["inLatestWar"]:
        return None, []

    down_checks = [
        ("kickAvgDecks", member["avgDecks"], "Average decks per war"),
        ("kickDonations", member["donationsPerWar"], "Donations per war"),
    ]
    if role == "member":
        down_checks.insert(0, ("kickMemberLatestWarFame", member["latestWarFame"], "Latest war fame"))
    down = [
        f"{label} {value} < {criteria[key]}"
        for key, value, label in down_checks
        if metric_is_enabled(criteria, key) and value < criteria[key]
    ]

    warning = []
    if role == "elder" and metric_is_enabled(criteria, "demoteElderLatestWarFame"):
        limit = criteria["demoteElderLatestWarFame"]
        needed = criteria["demoteElderWeakWars"]
        streak = weak_war_streak(member["fameHistory"], limit)
        if streak:
            text = f"Fame {member['latestWarFame']} < {limit} in {min(streak, needed)} of {needed} wars in a row"
            (down if streak >= needed else warning).insert(0, text)

    if down:
        return ("kick" if role == "member" else "demote"), down
    if warning:
        return "warning", warning

    if (
        metric_is_enabled(criteria, "recentParticipation")
        and member["latestWarParticipation"] < criteria["recentParticipationThreshold"]
    ):
        return "lowActivity", [
            f"Latest war decks {member['latestWarParticipation']} < {criteria['recentParticipationThreshold']}"
        ]

    if role == "member":
        up_checks = [
            ("promoteElderFullWars", member["fullWarStreak"], "Full wars in a row"),
            ("promoteElderAvgDecks", member["avgDecks"], "Average decks per war"),
            ("promoteElderDonations", member["donationsPerWar"], "Donations per war"),
        ]
        up_checks = [check for check in up_checks if metric_is_enabled(criteria, check[0])]
        if up_checks and all(value >= criteria[key] for key, value, _ in up_checks):
            return "promote", [f"{label} {value} >= {criteria[key]}" for key, value, label in up_checks]

    return None, []


def generate_insights(members_path="clan_members.json", history_path="history_data.json", criteria=None):
    criteria = merge_criteria(criteria)
    members_file = Path(members_path)
    history_file = Path(history_path)

    members_data = json.loads(members_file.read_text(encoding="utf-8"))
    history_data = json.loads(history_file.read_text(encoding="utf-8"))

    war_stats, total_weeks = get_war_stats(history_data)
    current_members = members_data.get("memberList", [])

    summaries = [member_summary(member, war_stats, total_weeks) for member in current_members]

    promote = []
    review = []
    inactive = []

    review_reasons = {
        "kick": "Candidate for kick",
        "demote": "Candidate for elder demotion",
        "warning": "Elder demotion warning",
        "lowActivity": "Recent activity below threshold",
    }

    for member in summaries:
        action, details = evaluate_member(member, criteria)
        entry = {
            "name": member["name"],
            "role": member["role"],
            "avgFame": member["avgFame"],
            "latestWarFame": member["latestWarFame"],
            "avgDecks": member["avgDecks"],
            "donations": member["donations"],
            "donationsPerWar": member["donationsPerWar"],
        }

        if action == "promote":
            promote.append({**entry, "reason": "Ready for Elder promotion", "details": details})
        elif action in review_reasons:
            review.append({**entry, "reason": review_reasons[action], "details": details})

        if member["inactive"]:
            inactive.append({
                "name": member["name"],
                "activeWeeks": member["activeWeeks"],
                "totalWeeks": member["totalWeeks"],
                "avgFame": member["avgFame"],
                "lastSeenHours": round(member["lastSeenHours"], 1) if member["lastSeenHours"] != float("inf") else None,
                "reason": "No participation in the latest war",
            })

    active_warriors = sum(1 for member in summaries if member["activeWeeks"] >= max(1, math.ceil(total_weeks * 0.5)))
    avg_clan_fame = round(sum(member["avgFame"] for member in summaries) / len(summaries)) if summaries else 0
    top_performer = max(summaries, key=lambda m: m["avgDecks"], default={"name": "N/A", "avgDecks": 0})

    result = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "clanTag": CLAN_TAG,
            "activeMembers": len(current_members),
            "activeWarriors": active_warriors,
            "totalWeeks": total_weeks,
            "avgClanFame": avg_clan_fame,
            "topPerformer": top_performer.get("name"),
            "topPerformerAvgDecks": top_performer.get("avgDecks", 0),
        },
        "promote": sorted(promote, key=lambda item: item["avgFame"], reverse=True),
        "review": sorted(review, key=lambda item: item["avgFame"], reverse=True),
        "inactive": sorted(inactive, key=lambda item: item["activeWeeks"]),
        "topPerformer": {
            "name": top_performer.get("name"),
            "avgFame": top_performer.get("avgFame", 0),
            "avgDecks": top_performer.get("avgDecks", 0),
            "role": top_performer.get("role"),
        },
    }

    return result


if __name__ == "__main__":
    output = generate_insights()
    output_path = Path("insights.json")
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Insights generated: {output_path}")
