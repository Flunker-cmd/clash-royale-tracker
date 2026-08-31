import json
import math
from datetime import datetime, timezone
from pathlib import Path

CLAN_TAG = "#L0G0Y0JP"

DEFAULT_CRITERIA = {
    "promoteElderAvgFame": 1800,
    "promoteElderAvgFameEnabled": True,
    "promoteElderDonations": 50,
    "promoteElderDonationsEnabled": False,
    "promoteCoLeaderAvgFame": 2500,
    "promoteCoLeaderAvgFameEnabled": True,
    "promoteCoLeaderDonations": 100,
    "promoteCoLeaderDonationsEnabled": False,
    "kickAvgFame": 400,
    "kickAvgFameEnabled": True,
    "kickDonations": 30,
    "kickDonationsEnabled": False,
    "recentParticipationThreshold": 4,
    "recentParticipationEnabled": True,
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


def member_summary(member, war_stats, total_weeks):
    tag = member.get("tag")
    war = war_stats.get(tag, {"fame": 0, "decks": 0, "weeks": 0, "history": [None] * total_weeks})
    active_weeks = int(war.get("weeks") or 0)
    latest_war_participation = 0
    if war.get("history"):
        latest_war_participation = int(war["history"][0] or 0)
    avg_fame = round(war.get("fame", 0) / active_weeks) if active_weeks else 0
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
        "donations": donations,
        "donationsPerWar": donations_per_war,
        "avgFame": avg_fame,
        "activeWeeks": active_weeks,
        "latestWarParticipation": latest_war_participation,
        "totalWeeks": total_weeks,
        "lastSeenHours": last_seen_hours,
        "inactive": latest_war_participation == 0,
    }


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

    min_active_weeks = max(1, math.ceil(total_weeks * 0.5))

    for member in summaries:
        recent_participation_ok = not metric_is_enabled(criteria, "recentParticipation") or member["latestWarParticipation"] >= criteria["recentParticipationThreshold"]
        elder_fame_ok = not metric_is_enabled(criteria, "promoteElderAvgFame") or member["avgFame"] >= criteria["promoteElderAvgFame"]
        elder_donations_ok = not metric_is_enabled(criteria, "promoteElderDonations") or member["donationsPerWar"] >= criteria["promoteElderDonations"]
        coleader_fame_ok = not metric_is_enabled(criteria, "promoteCoLeaderAvgFame") or member["avgFame"] >= criteria["promoteCoLeaderAvgFame"]
        coleader_donations_ok = not metric_is_enabled(criteria, "promoteCoLeaderDonations") or member["donationsPerWar"] >= criteria["promoteCoLeaderDonations"]

        if member["role"] == "member" and member["activeWeeks"] >= min_active_weeks and recent_participation_ok and elder_fame_ok and elder_donations_ok:
            promote.append({
                "name": member["name"],
                "avgFame": member["avgFame"],
                "donations": member["donations"],
                "donationsPerWar": member["donationsPerWar"],
                "reason": "Ready for Elder promotion",
            })
        elif member["role"] == "elder" and member["activeWeeks"] >= min_active_weeks and recent_participation_ok and coleader_fame_ok and coleader_donations_ok:
            promote.append({
                "name": member["name"],
                "avgFame": member["avgFame"],
                "donations": member["donations"],
                "donationsPerWar": member["donationsPerWar"],
                "reason": "Ready for Co-Leader promotion",
            })

        if member["inactive"]:
            inactive.append({
                "name": member["name"],
                "activeWeeks": member["activeWeeks"],
                "totalWeeks": member["totalWeeks"],
                "avgFame": member["avgFame"],
                "lastSeenHours": round(member["lastSeenHours"], 1) if member["lastSeenHours"] != float("inf") else None,
                "reason": "No participation in the latest war",
            })
        else:
            if not recent_participation_ok:
                review.append({
                    "name": member["name"],
                    "avgFame": member["avgFame"],
                    "donations": member["donations"],
                    "donationsPerWar": member["donationsPerWar"],
                    "reason": "Recent activity below threshold",
                })
            else:
                kick_fame_ok = not metric_is_enabled(criteria, "kickAvgFame") or member["avgFame"] < criteria["kickAvgFame"]
                kick_donations_ok = not metric_is_enabled(criteria, "kickDonations") or member["donationsPerWar"] < criteria["kickDonations"]
                if kick_fame_ok and kick_donations_ok:
                    review.append({
                        "name": member["name"],
                        "avgFame": member["avgFame"],
                        "donations": member["donations"],
                        "donationsPerWar": member["donationsPerWar"],
                        "reason": "Candidate for kick/demotion",
                    })

    active_warriors = sum(1 for member in summaries if member["activeWeeks"] >= max(1, math.ceil(total_weeks * 0.5)))
    avg_clan_fame = round(sum(member["avgFame"] for member in summaries) / len(summaries)) if summaries else 0
    top_performer = max(summaries, key=lambda m: m["avgFame"], default={"name": "N/A", "avgFame": 0})

    result = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "clanTag": CLAN_TAG,
            "activeMembers": len(current_members),
            "activeWarriors": active_warriors,
            "totalWeeks": total_weeks,
            "avgClanFame": avg_clan_fame,
            "topPerformer": top_performer.get("name"),
            "topPerformerAvgFame": top_performer.get("avgFame", 0),
        },
        "promote": sorted(promote, key=lambda item: item["avgFame"], reverse=True),
        "review": sorted(review, key=lambda item: item["avgFame"], reverse=True),
        "inactive": sorted(inactive, key=lambda item: item["activeWeeks"]),
        "topPerformer": {
            "name": top_performer.get("name"),
            "avgFame": top_performer.get("avgFame", 0),
            "role": top_performer.get("role"),
        },
    }

    return result


if __name__ == "__main__":
    output = generate_insights()
    output_path = Path("insights.json")
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Insights generated: {output_path}")
