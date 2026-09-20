# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A static dashboard (GitHub Pages) for the Clash Royale clan `#L0G0Y0JP`. There is no build step and no dependencies beyond the Python standard library. Node.js is optional, for one test.

## Commands

```
python -m unittest discover -s tests -t .                          # all tests
python -m unittest tests.test_track_members                        # one test file
python -m unittest tests.test_track_members.<Class>.<test_name>    # one test
python fetch_data.py         # needs CLASH_ROYALE_TOKEN in the environment
python generate_insights.py  # reads clan_members.json + history_data.json, writes insights.json
python track_members.py      # diffs clan_members.json against member_snapshot.json
```

To view the dashboard locally, serve the repo root over HTTP (e.g. `python -m http.server`). `index.html` loads the JSON files with `fetch()`, so opening it via `file://` fails.

## Architecture

The data flows one way. GitHub Actions (`.github/workflows/fetch.yml`) runs hourly. It runs `fetch_data.py`, then `generate_insights.py`, then `track_members.py`. It then commits the resulting JSON files straight to `main` as "Auto-update clan data and insights", which is why the git log is full of those commits.

- `fetch_data.py` calls the API through the `proxy.royaleapi.dev` proxy, not the official API host. It writes `clan_members.json` (roster), `clan_data.json` (current river race) and `history_data.json` (river race log, **newest war first**, so index 0 is the latest finished war).
- `generate_insights.py` turns those files into `insights.json`.
- `track_members.py` keeps `member_snapshot.json` and appends joined/left/promoted/demoted events to `member_events.json`. It skips a run if the roster has shrunk to under half its previous size (`MIN_ROSTER_RATIO`), so an API hiccup does not look like a mass exodus. Events are capped at `MAX_EVENTS`.
- `index.html` is a single ~2500-line file with inline CSS and JS. It does **not** read `insights.json`. It fetches `clan_members.json`, `history_data.json`, `clan_data.json` and `member_events.json` and recomputes everything in the browser. That lets the user change the criteria live.

The JSON data files are generated output committed to the repo. Don't hand-edit them. Expect them to change under you when you `git pull`.

### The recommendation rules are duplicated

The promote/kick/demote/low-activity rules exist twice: `evaluate_member` in `generate_insights.py` and `getRecommendation` in `index.html`. Change both together, and keep `DEFAULT_CRITERIA` in Python in sync with `defaultCriteria` in the HTML. The README documents the rules and defaults, so update it as well.

`tests/test_dashboard_parity.py` guards this. It runs a grid of scenarios through both implementations and fails on any disagreement. To do this, `tests/dashboard_logic.js` extracts the `<script>` block from `index.html` (the regex `/<script>([\s\S]*)<\/script>/`) and runs it in a `vm` sandbox with a fake DOM. So:

- `index.html` must keep a single plain `<script>` block, or the extraction breaks.
- New top-level DOM access in that script needs a matching stub in `dashboard_logic.js`.
- The parity test compares the dashboard's displayed Swedish text (`Befordra till elder`, `Kicka`, ...), so changing that wording means updating `DASHBOARD_TEXT` in the test.
- The test is skipped if `node` is not on PATH.

### Rule semantics that are easy to get wrong

- Everything is judged on the **latest finished war** (fame in `history[0]`), not on averages. Averages are only used by the optional filters, which are off by default.
- Only `member` and `elder` are evaluated. Co-leaders and leaders get no recommendation. A member with no data for the latest war (`inLatestWar` false, e.g. newly joined) is skipped.
- Kick/demote criteria trigger if **any** enabled one is hit. Promotion requires **all** enabled promotion criteria to be met.

## Conventions

- UI text in the dashboard is Swedish, while code, comments and README are English. Some comments in `fetch_data.py` are Swedish.
- Scripts run from the repo root and use relative paths for the JSON files.
