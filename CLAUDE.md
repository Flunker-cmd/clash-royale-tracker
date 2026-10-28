# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A static dashboard (GitHub Pages) for the Clash Royale clan `#L0G0Y0JP`. There is no build step and no dependencies beyond the Python standard library.

## Commands

```
python -m unittest discover -s tests -t .                          # all tests
python -m unittest tests.test_track_members                        # one test file
python -m unittest tests.test_track_members.<Class>.<test_name>    # one test
python fetch_data.py         # needs CLASH_ROYALE_TOKEN in the environment
python track_members.py      # diffs clan_members.json against member_snapshot.json
```

To view the dashboard locally, serve the repo root over HTTP (e.g. `python -m http.server`). `index.html` loads the JSON files with `fetch()`, so opening it via `file://` fails.

## Architecture

The data flows one way. GitHub Actions (`.github/workflows/fetch.yml`) runs hourly. It runs `fetch_data.py`, then `track_members.py` and `track_war_days.py`. It then commits the resulting JSON files straight to `main` as "Auto-update clan data" (older ones say "Auto-update clan data and insights"), which is why the git log is full of those commits. Each commit triggers a GitHub Pages deployment.

- `fetch_data.py` calls the API through the `proxy.royaleapi.dev` proxy, not the official API host. It writes `clan_members.json` (roster), `clan_data.json` (current river race) and `history_data.json` (river race log, **newest war first**, so index 0 is the latest finished war).
- `track_members.py` keeps `member_snapshot.json` and appends joined/left/promoted/demoted events to `member_events.json`. It skips a run if the roster has shrunk to under half its previous size (`MIN_ROSTER_RATIO`), so an API hiccup does not look like a mass exodus. Events are capped at `MAX_EVENTS`.
- `track_war_days.py` writes `war_days.json`: per war day and player, today's decks and the decks used before that day (`base`). The API has no per-day history, so this is the only source for past days. A day's final count is the next day's `base` minus its own, which stays exact even though the last hourly run of a day misses late battles. The last day has no next day, so once the war is in `history_data.json` (`history[0]` with the same `sectionIndex`), `finish_war` sets the last day's count to the war's total `decksUsed` minus its `base` and marks the file `finished` with the `seasonId`. The dashboard shows a finished war between wars. The file is reset when a new war starts.
- `index.html` is a single ~3500-line file with inline CSS and JS. It fetches `clan_members.json`, `history_data.json`, `clan_data.json`, `member_events.json` and `war_days.json` and computes everything in the browser, including the promote/kick/demote recommendations (`getRecommendation`, defaults in `defaultCriteria`). That lets the user change the criteria live. The README documents the rules and defaults, so update it when they change.

The JSON data files are generated output committed to the repo. Don't hand-edit them. Expect them to change under you when you `git pull`.

### Rule semantics that are easy to get wrong

- Kick and demotion count **missed decks**, not fame (fame was used until October 2026). Kick is judged on the **latest finished war** (`history[0]`), not on averages: a member is kicked if decks used are below `kickMemberDeckShare` percent (default 75) of possible decks (`getPossibleDecks`). Elder demotion needs more missed decks (possible minus used) than `demoteElderMissedDecks` (default 0, i.e. not a full war) in `demoteElderWeakWars` wars in a row (`getWeakWarStreak`). A shorter streak gives the `warning` action ("Varning"), which the dashboard keeps out of the review counts. Promotion is judged on the full-war streak: wars in a row, counting back from `history[0]`, with all 16 decks used (`getFullWarStreak`). A war the player was not in breaks the streak. Averages are only used by the optional filters, which are off by default.
- Only `member` and `elder` are evaluated. Co-leaders and leaders get no recommendation. A member with no data for the latest war (`inLatestWar` false, e.g. newly joined) is skipped. A member whose latest `joined` event in `member_events.json` falls during the latest war (battle days start at `history[0].createdDate` minus four days) is only expected to play 4 decks per full day after the day they joined. The join day is excluded because the API cannot tell whether they already used their decks in another clan, and join times are only as precise as the hourly runs. Joining on the last day or after the war gives 0 possible decks, and the member is then treated as new (the war log can list a player from an earlier short stay with 0 decks).
- Kick/demote criteria trigger if **any** enabled one is hit. Promotion requires **all** enabled promotion criteria to be met.

## Conventions

- UI text in the dashboard is Swedish, while code, comments and README are English. Some comments in `fetch_data.py` are Swedish.
- Scripts run from the repo root and use relative paths for the JSON files.
