import json
import os
import urllib.error
import urllib.request

CLAN_TAG = "%23L0G0Y0JP"
TOKEN = os.environ.get("CLASH_ROYALE_TOKEN")

url = f"https://proxy.royaleapi.dev/v1/clans/{CLAN_TAG}/currentriverrace"

req = urllib.request.Request(url)
req.add_header("Authorization", f"Bearer {TOKEN}")
req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

try:
  with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())
    with open("clan_data.json", "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=2)
    print("Data sparad i clan_data.json")
except urllib.error.HTTPError as e:
  print(f"HTTP-fel {e.code}: {e.reason}")
  print(e.read().decode())
  exit(1)
except Exception as e:
  print(f"Ett fel uppstod: {e}")
  exit(1)
