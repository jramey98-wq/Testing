import json
import os
import random
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

        # For demo properties with no history yet, generate simulated history
        if not prop_history and prop.zpid.startswith("demo-"):
            prop_history.extend(_generate_demo_history(prop))

        # Only add today's entry if we don't already have it
        if not prop_history or prop_history[-1]["date"] != today:
            prop_history.append({"date": today, "price": prop.current_price})

    _save_cache(cache)


def get_price_history(zpid: str) -> list[dict]:
    cache = _load_cache()
    return cache.get("price_history", {}).get(zpid, [])


def get_cached_cities() -> list[str]:
    """Return a list of previously searched cities."""
    cache = _load_cache()
    return list(cache.get("searches", {}).keys())


def _generate_demo_history(prop: Property) -> list[dict]:
    """Generate simulated price history data points for demo properties."""
    random.seed(hash(prop.zpid))
    history = []

    if not prop.last_sold_price or not prop.last_sold_date:
        return history

    try:
        sold_date = datetime.strptime(prop.last_sold_date, "%Y-%m-%d")
    except ValueError:
        return history

    # Generate monthly/quarterly data points from sold date to now
    current = sold_date
    now = datetime.now()
    price = prop.last_sold_price
    target = prop.current_price
    total_days = (now - sold_date).days
    if total_days <= 0:
        return history

    # Determine step size based on time span
    if total_days > 365 * 3:
        step_days = 90  # quarterly for long spans
    elif total_days > 365:
        step_days = 60  # bimonthly
    else:
        step_days = 30  # monthly

    price_diff = target - price
    steps = max(1, total_days // step_days)
    step_increase = price_diff / steps

    i = 0
    while current < now:
        # Add some noise to make it look realistic
        noise = random.uniform(-0.02, 0.02) * price
        point_price = price + (step_increase * i) + noise
        point_price = max(point_price, price * 0.7)  # floor at 70% of original
        history.append({
            "date": current.strftime("%Y-%m-%d"),
            "price": round(point_price, 2),
        })
        current += timedelta(days=step_days)
        i += 1

    return history
