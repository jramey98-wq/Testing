import os
import random
import asyncio
import httpx
from app.models import Property

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "zillow-com1.p.rapidapi.com"

# Rate limiter: simple timestamp tracking
_last_request_time = 0.0


async def _rate_limit():
    global _last_request_time
    import time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 1.0:
        await asyncio.sleep(1.0 - elapsed)
    _last_request_time = time.time()


async def search_properties(location: str, max_pages: int = 5) -> list[Property]:
    """Search for properties by location. Falls back to demo data if no API key.
    Fetches multiple pages to return all available listings.
    """
    if not RAPIDAPI_KEY:
        return _generate_demo_data(location)

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
    }

    all_results = []
    page = 1

    async with httpx.AsyncClient(timeout=30.0) as client:
        while page <= max_pages:
            await _rate_limit()

            resp = await client.get(
                f"https://{RAPIDAPI_HOST}/propertyExtendedSearch",
                headers=headers,
                params={
                    "location": location,
                    "status_type": "ForSale",
                    "home_type": "Houses",
                    "page": str(page),
                },
            )
            resp.raise_for_status()
            data = resp.json()

            props = data.get("props") or []
            if not props:
                break

            for item in props:
                try:
                    all_results.append(Property(
                        zpid=str(item.get("zpid", "")),
                        address=item.get("address", "Unknown"),
                        city=item.get("addressCity", location.split(",")[0].strip()),
                        state=item.get("addressState", ""),
                        zipcode=item.get("addressZipcode", ""),
                        current_price=float(item.get("price", 0)),
                        last_sold_price=_safe_float(item.get("zestimate")) or _safe_float(item.get("lastSoldPrice")),
                        last_sold_date=item.get("dateSold"),
                        home_type=item.get("propertyType"),
                        bedrooms=_safe_int(item.get("bedrooms")),
                        bathrooms=_safe_float(item.get("bathrooms")),
                        living_area=_safe_int(item.get("livingArea")),
                        image_url=item.get("imgSrc"),
                        detail_url=item.get("detailUrl"),
                    ))
                except (ValueError, TypeError):
                    continue

            total_pages = data.get("totalPages", 1)
            if page >= total_pages:
                break
            page += 1

    return all_results


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


# Popular US cities for suggestions
POPULAR_CITIES = [
    "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX",
    "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA",
    "Dallas, TX", "Austin, TX", "San Jose, CA", "Jacksonville, FL",
    "Fort Worth, TX", "Columbus, OH", "Charlotte, NC", "Indianapolis, IN",
    "San Francisco, CA", "Seattle, WA", "Denver, CO", "Nashville, TN",
    "Oklahoma City, OK", "El Paso, TX", "Washington, DC", "Boston, MA",
    "Las Vegas, NV", "Portland, OR", "Memphis, TN", "Louisville, KY",
    "Baltimore, MD", "Milwaukee, WI", "Albuquerque, NM", "Tucson, AZ",
    "Fresno, CA", "Mesa, AZ", "Sacramento, CA", "Atlanta, GA",
    "Kansas City, MO", "Omaha, NE", "Colorado Springs, CO", "Raleigh, NC",
    "Miami, FL", "Tampa, FL", "Orlando, FL", "Minneapolis, MN",
    "Cleveland, OH", "Pittsburgh, PA", "St. Louis, MO", "Cincinnati, OH",
    "Honolulu, HI", "Anchorage, AK",
]


def _generate_demo_data(location: str) -> list[Property]:
    """Generate realistic demo data for testing without an API key."""
    random.seed(hash(location.lower().strip()))

    streets = [
        "Oak", "Maple", "Cedar", "Pine", "Elm", "Birch", "Willow", "Walnut",
        "Cherry", "Spruce", "Ash", "Hickory", "Magnolia", "Sycamore", "Poplar",
        "Cypress", "Juniper", "Redwood", "Sequoia", "Laurel", "Dogwood",
        "Chestnut", "Hawthorn", "Aspen", "Beech", "Cottonwood", "Pecan",
        "Alder", "Hemlock", "Linden",
    ]
    suffixes = ["St", "Ave", "Dr", "Ln", "Blvd", "Ct", "Way", "Pl", "Cir", "Rd"]
    city = location.split(",")[0].strip() if "," in location else location.strip()
    state = location.split(",")[1].strip()[:2].upper() if "," in location else "TX"

    # Generate a city-appropriate price range
    city_lower = city.lower()
    if any(c in city_lower for c in ["san francisco", "new york", "los angeles", "san jose", "boston", "seattle"]):
        price_range = (500000, 2500000)
    elif any(c in city_lower for c in ["miami", "denver", "portland", "washington", "chicago", "san diego"]):
        price_range = (350000, 1500000)
    elif any(c in city_lower for c in ["austin", "nashville", "raleigh", "charlotte", "atlanta"]):
        price_range = (250000, 1000000)
    else:
        price_range = (150000, 800000)

    properties = []
    for i in range(40):
        num = random.randint(100, 9999)
        street = random.choice(streets)
        suffix = random.choice(suffixes)
        beds = random.randint(2, 6)
        baths = random.choice([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])
        sqft = random.randint(1000, 4500)

        base_price = random.randint(*price_range)
        multiplier = random.choice([
            0.85, 0.92, 0.97, 1.02, 1.05, 1.08, 1.12, 1.15, 1.20,
            1.25, 1.30, 1.40, 1.55, 1.70, 1.85, 2.10, 2.40, 1.10, 1.06, 1.18,
        ])
        current_price = round(base_price * multiplier, -3)

        years_ago = random.randint(1, 15)
        sold_month = random.randint(1, 12)
        sold_year = 2026 - years_ago

        properties.append(Property(
            zpid=f"demo-{i}-{hash(location) % 10000}",
            address=f"{num} {street} {suffix}",
            city=city,
            state=state,
            zipcode=f"{random.randint(10000, 99999)}",
            current_price=current_price,
            last_sold_price=float(base_price),
            last_sold_date=f"{sold_year}-{sold_month:02d}-01",
            home_type=random.choice(["SINGLE_FAMILY", "TOWNHOUSE", "CONDO"]),
            bedrooms=beds,
            bathrooms=baths,
            living_area=sqft,
            image_url=None,
            detail_url=None,
        ))

    return properties
