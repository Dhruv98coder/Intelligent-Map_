
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PRIMARY_FILE = DATA_DIR / "delhi_metro_clean_2026.csv"
FARE_FILE = DATA_DIR / "fare_data.csv"
# Kept only as a legacy fallback for matching/QA; routing does not use it.
LEGACY_NETWORK_FILE = DATA_DIR / "Delhi-Metro-Network.csv"

def load_primary_metro():
    if not PRIMARY_FILE.exists():
        raise FileNotFoundError(f"Primary 2026 metro dataset not found: {PRIMARY_FILE}")
    return pd.read_csv(PRIMARY_FILE, dtype=str, keep_default_na=False)

def load_fares():
    if not FARE_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(FARE_FILE, dtype=str, keep_default_na=False)

def load_all_metro_data():
    return {"primary": load_primary_metro(), "fares": load_fares()}
