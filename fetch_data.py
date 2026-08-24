import json
import os
import urllib.error
import urllib.request

CLAN_TAG = "%23L0G0Y0JP"
TOKEN = os.environ.get("CLASH_ROYALE_TOKEN")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}


def fetch_url(url):
  req = urllib.request.Request(url, headers=headers)
  with urllib.request.urlopen(req) as response:
    return json.loads(response.read().decode())


try:
  current_race = fetch_url(
      f"https://proxy.royaleapi.dev/v1/clans/{CLAN_TAG}/currentriverrace"
  )
  with open("clan_data.json", "w", encoding="utf-8") as f:
    json.dump(current_race, f, ensure_ascii=False, indent=2)

  race_log = fetch_url(
      f"https://proxy.royaleapi.dev/v1/clans/{CLAN_TAG}/riverracelog"
  )
  with open("history_data.json", "w", encoding="utf-8") as f:
    json.dump(race_log, f, ensure_ascii=False, indent=2)

  print("Både nuvarande data och historik har sparats.")
except urllib.error.HTTPError as e:
  print(f"HTTP-fel {e.code}: {e.reason}")
  print(e.read().decode())
  exit(1)
except Exception as e:
  print(f"Ett fel uppstod: {e}")
  exit(1)
