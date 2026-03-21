"""
Listing client — routes searches through the configured data provider.

Falls back to demo data when no API key is configured.
"""

import random
import re
from app.models import Property
from app.providers import (
    get_provider,
    _is_address_search,
    _parse_address_parts,
)

# Re-export for backwards compatibility with main.py
is_address_search = _is_address_search

# Expose provider info
_provider = get_provider()
PROVIDER_NAME = _provider.name if _provider else "demo"
API_CONFIGURED = _provider is not None


async def search_by_address(address: str) -> list[Property]:
    """Search for a specific property by address."""
    provider = get_provider()
    if not provider:
        return _generate_demo_address(address)
    return await provider.search_address(address)


async def search_properties(location: str) -> list[Property]:
    """Search for properties by location."""
    provider = get_provider()
    if not provider:
        return _generate_demo_data(location)
    return await provider.search_area(location)


# ---------------------------------------------------------------------------
# Popular cities (for autocomplete suggestions)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Demo data generators (unchanged)
# ---------------------------------------------------------------------------

def _make_zillow_url(detail_url, address="", city="", state="", zipcode=""):
    if detail_url:
        url = detail_url.strip()
        if url.startswith("/"):
            return "https://www.zillow.com" + url
        if url.startswith("http"):
            return url
        return "https://www.zillow.com/" + url
    parts = [address, city, state, zipcode]
    query = " ".join(p for p in parts if p).strip()
    if query:
        encoded = query.replace(" ", "-").replace(",", "").replace(".", "")
        return f"https://www.zillow.com/homes/{encoded}_rb/"
    return "https://www.zillow.com"


def _generate_demo_address(address: str) -> list[Property]:
    """Generate a demo property for an address search."""
    random.seed(hash(address.lower().strip()))

    street, city, state, zipcode = _parse_address_parts(address)
    if not city:
        city = "Unknown City"
    if not state:
        state = "TX"
    if not zipcode:
        zipcode = f"{random.randint(10000, 99999)}"

    beds = random.randint(2, 5)
    baths = random.choice([1.0, 1.5, 2.0, 2.5, 3.0, 3.5])
    sqft = random.randint(1200, 4000)
    base_price = random.randint(200000, 900000)
    multiplier = random.choice([1.05, 1.10, 1.15, 1.20, 1.30, 1.40, 1.55, 0.95, 0.90])
    current_price = round(base_price * multiplier, -3)
    years_ago = random.randint(1, 12)
    sold_year = 2026 - years_ago
    sold_month = random.randint(1, 12)

    properties = [
        Property(
            zpid=f"demo-addr-{hash(address) % 10000}",
            address=street, city=city, state=state, zipcode=zipcode,
            current_price=current_price,
            last_sold_price=float(base_price),
            last_sold_date=f"{sold_year}-{sold_month:02d}-01",
            home_type=random.choice(["SINGLE_FAMILY", "TOWNHOUSE", "CONDO"]),
            bedrooms=beds, bathrooms=baths, living_area=sqft,
            image_url=None,
            detail_url=_make_zillow_url(None, street, city, state, zipcode),
        )
    ]

    street_names = ["Oak", "Maple", "Cedar", "Pine", "Elm", "Birch", "Willow", "Walnut",
                    "Cherry", "Spruce", "Ash", "Hickory", "Magnolia", "Sycamore"]
    suffixes = ["St", "Ave", "Dr", "Ln", "Blvd", "Ct", "Way", "Pl"]

    for i in range(9):
        num = random.randint(100, 9999)
        st = random.choice(street_names)
        suf = random.choice(suffixes)
        nearby_addr = f"{num} {st} {suf}"
        b_price = random.randint(max(100000, base_price - 200000), base_price + 200000)
        mult = random.choice([0.90, 0.95, 1.02, 1.05, 1.10, 1.15, 1.20, 1.30, 1.40])
        c_price = round(b_price * mult, -3)
        ya = random.randint(1, 12)

        properties.append(Property(
            zpid=f"demo-nearby-{i}-{hash(address) % 10000}",
            address=nearby_addr, city=city, state=state, zipcode=zipcode,
            current_price=c_price,
            last_sold_price=float(b_price),
            last_sold_date=f"{2026 - ya}-{random.randint(1,12):02d}-01",
            home_type=random.choice(["SINGLE_FAMILY", "TOWNHOUSE", "CONDO"]),
            bedrooms=random.randint(2, 5),
            bathrooms=random.choice([1.0, 1.5, 2.0, 2.5, 3.0]),
            living_area=random.randint(1000, 4000),
            image_url=None,
            detail_url=_make_zillow_url(None, nearby_addr, city, state, zipcode),
        ))

    return properties


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

        demo_addr = f"{num} {street} {suffix}"
        demo_zip = f"{random.randint(10000, 99999)}"
        properties.append(Property(
            zpid=f"demo-{i}-{hash(location) % 10000}",
            address=demo_addr, city=city, state=state, zipcode=demo_zip,
            current_price=current_price,
            last_sold_price=float(base_price),
            last_sold_date=f"{sold_year}-{sold_month:02d}-01",
            home_type=random.choice(["SINGLE_FAMILY", "TOWNHOUSE", "CONDO"]),
            bedrooms=beds, bathrooms=baths, living_area=sqft,
            image_url=None,
            detail_url=_make_zillow_url(None, demo_addr, city, state, demo_zip),
        ))

    return properties
