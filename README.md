# clash-royale-tracker

[Open the published dashboard](https://flunker-cmd.github.io/clash-royale-tracker/)

A dashboard for the clan `#L0G0Y0JP`: war participation, recommendations for
promotions, demotions and kicks, the war in progress, and how the clan develops
over time.

## Default rules

One war runs Thursday to Sunday, and a full war is all 16 decks used.

- Member with a full war in each of the **3 latest finished wars**: promote to
  Elder. A war with fewer decks, or one the player was not in the clan for,
  breaks the streak. Fame does not matter for promotion.
- Member who used less than 75% of their possible decks in the **latest
  finished war** (fewer than 12 of 16): kick. Kick and demotion count decks
  only; fame does not matter.
- Elder who missed decks in each of the **2 latest finished wars**: demote to
  Member (Elder works as an extra life). One such war gives a warning. A war the
  player was not in the clan for does not count as weak.
- A player who joined during the latest war only has to play the full days
  after the day they joined (4 decks per day). The day they joined does not
  count, since they may already have used their decks in another clan.
- Co-Leaders are appointed manually and never get a recommendation
- Members with no data for the latest war (newly joined) are not evaluated.
  Neither are players who joined on its last day or after it ended (the war log
  may list them from an earlier short stay in the clan).

The dashboard always opens with these defaults.

## Optional filters

These are off by default and can be switched on in the dashboard to explore the
data. Decks and donations are averages per participated war.

- Promotion: minimum average decks, minimum donations. Every enabled promotion
  criterion must be met.
- Kick / demotion: average decks below a limit, donations below a limit. Any
  enabled criterion is enough to trigger it.
- Participation limit: minimum decks used in the latest war.

## What the dashboard shows

- **Player table** with search, filters (recommendation, role, AFK only), sorting
  (also from the keyboard) and CSV export of whatever is currently shown. On
  phones each player becomes a card.
- **Player detail**: click a name to see stats, fame and decks per war, and a
  checklist of every rule with its outcome, so a recommendation can be explained.
- **River race** ("Flodkapplöpning"): every clan in the race as a boat sailing
  towards the finish line at 10 000 fame, with today's medals and daily rank, our
  result per earlier day of the war, and how far the boat would move if the day
  ended now. Between wars it shows the final standings of the latest race.
- **Opponents** ("Motståndet"): a card for our clan first, then one per other
  clan in the race with war trophies, meetings in the race log (between wars
  including the war just shown) and who came out ahead, placement, players and
  decks compared with ours, their best player and a fun fact.
- **War heroes** ("Krigets hjältar"): awards for the latest finished war (most
  fame, longest full-war streak, biggest improvement, boat attacks, donations,
  all 16 decks), plus the members one full war away from Elder and whether they
  are on track in the war in progress. The player detail shows the same progress
  towards Elder.
- **War in progress**: which day it is, decks played today and in total, and who
  still has decks left today (with a button that copies the list for the clan chat; copy confirmations appear as toasts).
  Click an earlier day of the war to see who played all, some or none of their
  decks that day (saved hourly by `track_war_days.py`, so only days after it started running).
  Between wars (training days) the panel shows the war that just ended until the
  next war starts: each day, or all days summed up per player ("Hela kriget").
- **Clan trend**: war trophies, total fame, decks used and placement per finished
  war, with hover details and a table view.
- **Member events**: who joined, left, was promoted or demoted (tracked from the
  day `track_members.py` first ran).
- **Share link**: copies a link that opens the page with your changed criteria and
  AFK marks. AFK marks are otherwise stored per browser.

## Files

| File | Purpose |
|---|---|
| `fetch_data.py` | Fetches members, current war and war log from the API |
| `track_members.py` | Compares members with `member_snapshot.json`, appends to `member_events.json` |
| `track_war_days.py` | Saves each player's decks per day of the current war to `war_days.json` |
| `index.html` | The dashboard (computes everything live from the JSON files, including the recommendation rules) |
| `.github/workflows/fetch.yml` | Runs the three scripts every hour and commits the data |

## Tests

```
python -m unittest discover -s tests -t .
```
