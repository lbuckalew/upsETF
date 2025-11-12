from pathlib import Path
import requests
from datetime import datetime
import json

DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

AV_BASE = "https://www.alphavantage.co/query"
TIMEOUT = 30

def cache_path_for(symbol: str) -> Path:
    return DATA_DIR / f"{symbol.upper()}.json"

def load_cached(symbol: str) -> dict | None:
    p = cache_path_for(symbol)
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_cache(symbol: str, payload: dict) -> None:
    p = cache_path_for(symbol)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

def fetch_etf_profile(symbol: str, api_key: str, force_refresh: bool, log_fn) -> dict:
    sym = symbol.upper().strip()
    if not sym:
        raise ValueError("Empty ticker")
    if not force_refresh:
        cached = load_cached(sym)
        if cached:
            log_fn(f"[cache] Using cached {sym}")
            return cached

    params = {
        "function": "ETF_PROFILE",
        "symbol": sym,
        "apikey": api_key.strip()
    }
    url = AV_BASE
    log_fn(f"[net] GET {url} ... ({sym})")
    r = requests.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    data["ticker"] = sym
    data["fetched_at"] = datetime.now().isoformat()
    data.pop("sectors", None)
    for h in data["holdings"]:
        if h['symbol'] == "n/a":
            h['symbol'] = h['description'].upper().replace(" ", "_")
    # Basic sanity checks
    if not isinstance(data, dict) or "holdings" not in data:
        # Alpha Vantage returns "Note" when rate-limited; or "Information" for guidance.
        note = data.get("Note") or data.get("Information") or str(data)[:200]
        raise RuntimeError(f"Unexpected response for {sym}: {note}")
    save_cache(sym, data)
    return data