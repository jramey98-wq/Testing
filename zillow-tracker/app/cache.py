import json
import os
from datetime import datetime, timedelta
from app.models import Property

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "price_history.json")


def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {"searches": {}, "price_history": {}}


def _save_cache(data: dict) -> None:
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_cached_search(location: str, max_age_hours: int = 24) -> list[Property] | None:
    cache = _load_cache()
    key = location.lower().strip().replace(" ", "-").replace(",", "")
    entry = cache.get("searches", {}).get(key)
    if not entry:
        return None

    cached_time = datetime.fromisoformat(entry["timestamp"])
    if datetime.now() - cached_time > timedelta(hours=max_age_hours):
        return None

    return [Property(**p) for p in entry["properties"]]


def save_search(location: str, properties: list[Property]) -> None:
    cache = _load_cache()
    key = location.lower().strip().replace(" ", "-").replace(",", "")

    cache.setdefault("searches", {})[key] = {
        "timestamp": datetime.now().isoformat(),
        "properties": [p.model_dump() for p in properties],
    }

    # Track price history per property
    today = datetime.now().strftime("%Y-%m-%d")
    history = cache.setdefault("price_history", {})
    for prop in properties:
        prop_history = history.setdefault(prop.zpid, [])
        # Only add if we don't already have today's entry
        if not prop_history or prop_history[-1]["date"] != today:
            prop_history.append({"date": today, "price": prop.current_price})

    _save_cache(cache)


def get_price_history(zpid: str) -> list[dict]:
    cache = _load_cache()
    return cache.get("price_history", {}).get(zpid, [])
