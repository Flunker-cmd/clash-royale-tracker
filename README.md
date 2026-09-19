# clash-royale-tracker

[Open the published dashboard](https://flunker-cmd.github.io/clash-royale-tracker/)

The dashboard shows current player trophies, war participation per week, and
recommendations for promotions, demotions and kicks.

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

The same rules are implemented in `generate_insights.py` (written to
`insights.json` by the workflow) and in `index.html`.
