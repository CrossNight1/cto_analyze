import pandas as pd
import requests
import io
import os

# Save data in a folder relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "cot_raw")
os.makedirs(DATA_DIR, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*"
}

years = range(2010, 2027)  # up to 2026 inclusive

dfs = []

for y in years:
    url = f"https://www.cftc.gov/files/dea/history/com_fin_txt_{y}.zip"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        df = pd.read_csv(io.BytesIO(r.content), compression='zip')
        df.to_csv(os.path.join(DATA_DIR, f"cot_{y}.csv"), index=False)
        dfs.append(df)
        print(f"✓ saved {y}")
    except Exception as e:
        print(f"✗ {y}: {e}")

# combine (optional, still raw)
if dfs:
    data = pd.concat(dfs, ignore_index=True)
    data.to_csv(os.path.join(DATA_DIR, "cot_full_2010_2026.csv"), index=False)
    print("✓ combined dataset saved")