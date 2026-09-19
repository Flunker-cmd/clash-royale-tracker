# clash-royale-tracker

[Open the published dashboard](https://flunker-cmd.github.io/clash-royale-tracker/)

A dashboard for the clan `#L0G0Y0JP`: war participation, recommendations for
promotions, demotions and kicks, the war in progress, and how the clan develops
over time.

## Default rules

Recommendations are based on the fame a player earned in the **latest finished
war** (one war = Thursday to Sunday):

- Member with at least 2500 fame: promote to Elder
- Member with less than 500 fame: kick
- Elder with less than 1600 fame: demote to Member (Elder works as an extra life)
- Co-Leaders are appointed manually and never get a recommendation
- Members with no data for the latest war (newly joined) are not evaluated

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
- **War in progress**: which day it is, decks played today and in total, and who
  still has decks left today (with a button that copies the list for the clan chat).
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
| `generate_insights.py` | Writes `insights.json` with the same rules as the dashboard |
| `track_members.py` | Compares members with `member_snapshot.json`, appends to `member_events.json` |
| `index.html` | The dashboard (computes everything live from the JSON files) |
| `.github/workflows/fetch.yml` | Runs the three scripts every hour and commits the data |

The recommendation rules exist in both `generate_insights.py` and `index.html`.
`tests/test_dashboard_parity.py` runs the same scenarios through both and fails
if they ever disagree.

## Tests

```
python -m unittest discover -s tests -t .
```

The parity test needs Node.js and is skipped without it.
