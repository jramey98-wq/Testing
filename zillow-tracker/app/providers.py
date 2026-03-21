"""
Multi-provider real estate listing data.

Supported providers:
  - rentcast   : RentCast API (api.rentcast.io) — 50 free calls/month, best docs
  - realtor    : Realtor.com via RapidAPI (realty-in-us) — 500 free req/month
  - zillow     : Zillow via RapidAPI (zillow-com1) — existing provider

Set DATA_SOURCE env var to choose (default: rentcast).
Set the corresponding API key:
  - RENTCAST_API_KEY  for rentcast
  - RAPIDAPI_KEY      for realtor or zillow
"""

import os
import asyncio
import re
import httpx
from abc import ABC, abstractmethod
from app.models import Property

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


def _is_address_search(query: str) -> bool:
    """Detect if a search query looks like a street address vs a city/ZIP."""
    q = query.strip()
    if re.match(r'^\d{5}(-\d{4})?$', q):
        return False
    if re.match(r'^\d+\s+\w', q):
        return True
    street_words = (
        r'\b(st|street|ave|avenue|dr|drive|ln|lane|blvd|boulevard|ct|court|'
        r'way|pl|place|rd|road|cir|circle|pkwy|parkway|ter|terrace|hwy|highway|'
        r'trail|trl|loop|run|pass|path|row|walk|xing|crossing|'
        r'aly|alley|cres|crescent|sq|square|mews|grove|glen|knoll|ridge|'
        r'holw|hollow|frwy|freeway|spur|ramp|pike|turnpike)\b'
    )
    if re.search(street_words, q, re.IGNORECASE):
        return True
    if re.search(r'\b\d+\s+[A-Za-z]', q):
        return True
    if re.match(r'^[A-Za-z\s]+,\s*[A-Za-z]{2}$', q):
        return False
    if len(q.split(",")) >= 3:
        return True
    return False


def _parse_location(query: str) -> dict:
    """Parse a location query into city, state, zipcode components."""
    q = query.strip()
    # ZIP code
    zip_match = re.search(r'\b(\d{5})\b', q)
    zipcode = zip_match.group(1) if zip_match else ""

    parts = [p.strip() for p in q.split(",")]
    city = ""
    state = ""

    if len(parts) >= 2:
        city = parts[0]
        state_part = parts[1].strip()
        m = re.match(r'^([A-Za-z]{2})', state_part)
        if m:
            state = m.group(1).upper()
    elif len(parts) == 1 and not zipcode:
        city = parts[0]

    return {"city": city, "state": state, "zipcode": zipcode}


def _parse_address_parts(address: str) -> tuple[str, str, str, str]:
    """Parse an address string into (street, city, state, zipcode)."""
    parts = [p.strip() for p in address.split(",")]
    street = parts[0] if parts else address.strip()
    city = ""
    state = ""
    zipcode = ""

    if len(parts) >= 3:
        city = parts[1]
        state_zip = parts[2].strip()
        m = re.match(r'([A-Za-z]{2})\s*(\d{5})?', state_zip)
        if m:
            state = m.group(1).upper()
            zipcode = m.group(2) or ""
    elif len(parts) == 2:
        second = parts[1].strip()
        m = re.match(r'^([A-Za-z]{2})\s*(\d{5})?$', second)
        if m:
            state = m.group(1).upper()
            zipcode = m.group(2) or ""
        else:
            city = second

    if not zipcode:
        zip_match = re.search(r'\b(\d{5})\b', address)
        if zip_match:
            zipcode = zip_match.group(1)

    return street, city, state, zipcode


# ---------------------------------------------------------------------------
# Provider base class
# ---------------------------------------------------------------------------

class ListingProvider(ABC):
    """Base class for real estate listing data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    async def search_area(self, location: str) -> list[Property]:
        """Search for listings in a city/zip area."""
        ...

    @abstractmethod
    async def search_address(self, address: str) -> list[Property]:
        """Search for a specific address + nearby listings."""
        ...


# ---------------------------------------------------------------------------
# RentCast provider
# ---------------------------------------------------------------------------

class RentCastProvider(ListingProvider):
    """RentCast API — https://api.rentcast.io/v1
    Free tier: 50 API calls/month.
    """

    BASE_URL = "https://api.rentcast.io/v1"

    def __init__(self):
        self._api_key = os.environ.get("RENTCAST_API_KEY", "")

    @property
    def name(self) -> str:
        return "rentcast"

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict:
        return {"X-Api-Key": self._api_key, "Accept": "application/json"}

    def _parse_listing(self, item: dict) -> Property | None:
        try:
            addr = item.get("formattedAddress") or item.get("addressLine1", "Unknown")
            city = item.get("city", "")
            state = item.get("state", "")
            zipcode = item.get("zipCode", "")
            price = _safe_float(item.get("price")) or 0

            return Property(
                zpid=str(item.get("id", "")),
                address=item.get("addressLine1", addr),
                city=city,
                state=state,
                zipcode=zipcode,
                current_price=price,
                last_sold_price=_safe_float(item.get("lastSalePrice")),
                last_sold_date=item.get("lastSaleDate"),
                home_type=item.get("propertyType"),
                bedrooms=_safe_int(item.get("bedrooms")),
                bathrooms=_safe_float(item.get("bathrooms")),
                living_area=_safe_int(item.get("squareFootage")),
                image_url=None,  # RentCast free tier may not include photos
                detail_url=self._build_listing_url(addr, city, state, zipcode),
            )
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _build_listing_url(address: str, city: str, state: str, zipcode: str) -> str:
        parts = [address, city, state, zipcode]
        query = " ".join(p for p in parts if p).strip()
        if query:
            encoded = query.replace(" ", "-").replace(",", "").replace(".", "")
            return f"https://www.realtor.com/realestateandhomes-search/{encoded}"
        return "https://www.realtor.com"

    async def search_area(self, location: str) -> list[Property]:
        loc = _parse_location(location)
        params: dict = {"limit": 500, "status": "Active"}

        if loc["zipcode"]:
            params["zipCode"] = loc["zipcode"]
        elif loc["city"] and loc["state"]:
            params["city"] = loc["city"]
            params["state"] = loc["state"]
        else:
            # Fall back to treating entire query as city
            params["city"] = location.split(",")[0].strip()
            if loc["state"]:
                params["state"] = loc["state"]

        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            await _rate_limit()
            resp = await client.get(
                f"{self.BASE_URL}/listings/sale",
                headers=self._headers(),
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            items = data if isinstance(data, list) else data.get("listings", data.get("results", []))
            for item in items:
                prop = self._parse_listing(item)
                if prop:
                    results.append(prop)

        return results

    async def search_address(self, address: str) -> list[Property]:
        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Direct address lookup
            await _rate_limit()
            try:
                resp = await client.get(
                    f"{self.BASE_URL}/listings/sale",
                    headers=self._headers(),
                    params={"address": address, "limit": 500, "status": "Active"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data if isinstance(data, list) else data.get("listings", data.get("results", []))
                    for item in items:
                        prop = self._parse_listing(item)
                        if prop:
                            results.append(prop)
            except Exception:
                pass

        if not results:
            # Create a placeholder for the searched address
            street, city, state, zipcode = _parse_address_parts(address)
            placeholder = Property(
                zpid=f"searched-{hash(address) % 100000}",
                address=street, city=city, state=state, zipcode=zipcode,
                current_price=0, detail_url=self._build_listing_url(street, city, state, zipcode),
            )
            results = [placeholder]

        return results


# ---------------------------------------------------------------------------
# Realtor.com provider (via RapidAPI "realty-in-us")
# ---------------------------------------------------------------------------

class RealtorProvider(ListingProvider):
    """Realtor.com API via RapidAPI — realty-in-us.p.rapidapi.com
    Free tier: ~500 requests/month.
    """

    HOST = "realty-in-us.p.rapidapi.com"

    def __init__(self):
        self._api_key = os.environ.get("RAPIDAPI_KEY", "")

    @property
    def name(self) -> str:
        return "realtor"

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict:
        return {
            "x-rapidapi-key": self._api_key,
            "x-rapidapi-host": self.HOST,
            "Content-Type": "application/json",
        }

    def _parse_result(self, item: dict) -> Property | None:
        try:
            loc = item.get("location", {})
            address_info = loc.get("address", {})
            street = address_info.get("line", "Unknown")
            city = address_info.get("city", "")
            state = address_info.get("state_code", "")
            zipcode = address_info.get("postal_code", "")

            price = _safe_float(item.get("list_price")) or 0
            desc = item.get("description", {})

            photos = item.get("photos", [])
            image_url = None
            if photos:
                first_photo = photos[0]
                if isinstance(first_photo, dict):
                    image_url = first_photo.get("href")
                elif isinstance(first_photo, str):
                    image_url = first_photo

            detail_url = item.get("href") or ""
            if detail_url and not detail_url.startswith("http"):
                detail_url = "https://www.realtor.com" + detail_url

            last_sold = item.get("last_sold_price")
            last_sold_date = item.get("last_sold_date")

            return Property(
                zpid=str(item.get("property_id", "")),
                address=street,
                city=city,
                state=state,
                zipcode=zipcode,
                current_price=price,
                last_sold_price=_safe_float(last_sold),
                last_sold_date=last_sold_date,
                home_type=desc.get("type"),
                bedrooms=_safe_int(desc.get("beds")),
                bathrooms=_safe_float(desc.get("baths")),
                living_area=_safe_int(desc.get("sqft")),
                image_url=image_url,
                detail_url=detail_url or self._build_url(street, city, state, zipcode),
            )
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _build_url(address: str, city: str, state: str, zipcode: str) -> str:
        parts = [address, city, state, zipcode]
        query = " ".join(p for p in parts if p).strip()
        if query:
            encoded = query.replace(" ", "-").replace(",", "").replace(".", "")
            return f"https://www.realtor.com/realestateandhomes-search/{encoded}"
        return "https://www.realtor.com"

    async def search_area(self, location: str) -> list[Property]:
        loc = _parse_location(location)
        payload: dict = {
            "limit": 200,
            "offset": 0,
            "status": ["for_sale"],
            "sort": {"direction": "desc", "field": "list_date"},
        }

        if loc["zipcode"]:
            payload["postal_code"] = loc["zipcode"]
        elif loc["city"] and loc["state"]:
            payload["city"] = loc["city"]
            payload["state_code"] = loc["state"]
        else:
            payload["city"] = location.split(",")[0].strip()

        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            await _rate_limit()
            resp = await client.post(
                f"https://{self.HOST}/properties/v3/list",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

            home_search = data.get("data", {}).get("home_search", {})
            items = home_search.get("results", [])

            for item in items:
                prop = self._parse_result(item)
                if prop:
                    results.append(prop)

        return results

    async def search_address(self, address: str) -> list[Property]:
        loc = _parse_location(address)
        payload: dict = {
            "limit": 20,
            "offset": 0,
            "status": ["for_sale"],
        }

        if loc["zipcode"]:
            payload["postal_code"] = loc["zipcode"]
        if loc["city"]:
            payload["city"] = loc["city"]
        if loc["state"]:
            payload["state_code"] = loc["state"]

        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            await _rate_limit()
            try:
                resp = await client.post(
                    f"https://{self.HOST}/properties/v3/list",
                    headers=self._headers(),
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    home_search = data.get("data", {}).get("home_search", {})
                    items = home_search.get("results", [])
                    for item in items:
                        prop = self._parse_result(item)
                        if prop:
                            results.append(prop)
            except Exception:
                pass

        if not results:
            street, city, state, zipcode = _parse_address_parts(address)
            placeholder = Property(
                zpid=f"searched-{hash(address) % 100000}",
                address=street, city=city, state=state, zipcode=zipcode,
                current_price=0, detail_url=self._build_url(street, city, state, zipcode),
            )
            results = [placeholder]

        return results


# ---------------------------------------------------------------------------
# Zillow provider (existing — via RapidAPI)
# ---------------------------------------------------------------------------

class ZillowProvider(ListingProvider):
    """Zillow API via RapidAPI — zillow-com1.p.rapidapi.com"""

    HOST = "zillow-com1.p.rapidapi.com"

    def __init__(self):
        self._api_key = os.environ.get("RAPIDAPI_KEY", "")

    @property
    def name(self) -> str:
        return "zillow"

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict:
        return {
            "x-rapidapi-key": self._api_key,
            "x-rapidapi-host": self.HOST,
        }

    @staticmethod
    def _make_zillow_url(detail_url: str | None, address: str = "", city: str = "", state: str = "", zipcode: str = "") -> str:
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

    def _parse_listing(self, item: dict, fallback_city: str = "") -> Property | None:
        try:
            addr = item.get("address", "Unknown")
            c = item.get("addressCity", fallback_city)
            s = item.get("addressState", "")
            z = item.get("addressZipcode", "")
            return Property(
                zpid=str(item.get("zpid", "")),
                address=addr, city=c, state=s, zipcode=z,
                current_price=float(item.get("price", 0)),
                last_sold_price=_safe_float(item.get("zestimate")) or _safe_float(item.get("lastSoldPrice")),
                last_sold_date=item.get("dateSold"),
                home_type=item.get("propertyType"),
                bedrooms=_safe_int(item.get("bedrooms")),
                bathrooms=_safe_float(item.get("bathrooms")),
                living_area=_safe_int(item.get("livingArea")),
                image_url=item.get("imgSrc"),
                detail_url=self._make_zillow_url(item.get("detailUrl"), addr, c, s, z),
            )
        except (ValueError, TypeError):
            return None

    async def search_area(self, location: str, max_pages: int = 5) -> list[Property]:
        all_results = []
        page = 1
        fallback_city = location.split(",")[0].strip() if "," in location else location.strip()

        async with httpx.AsyncClient(timeout=30.0) as client:
            while page <= max_pages:
                await _rate_limit()
                resp = await client.get(
                    f"https://{self.HOST}/propertyExtendedSearch",
                    headers=self._headers(),
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
                    prop = self._parse_listing(item, fallback_city)
                    if prop:
                        all_results.append(prop)
                total_pages = data.get("totalPages", 1)
                if page >= total_pages:
                    break
                page += 1

        return all_results

    async def search_address(self, address: str) -> list[Property]:
        primary_prop = None
        nearby = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Direct lookup
            await _rate_limit()
            try:
                resp = await client.get(
                    f"https://{self.HOST}/propertyByAddress",
                    headers=self._headers(),
                    params={"address": address},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data and isinstance(data, dict) and data.get("zpid"):
                        primary_prop = self._parse_detail(data, address)
            except Exception:
                pass

            # Extended search for nearby
            await _rate_limit()
            try:
                resp = await client.get(
                    f"https://{self.HOST}/propertyExtendedSearch",
                    headers=self._headers(),
                    params={"location": address, "status_type": "ForSale"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("props") or []:
                        prop = self._parse_listing(item)
                        if prop:
                            nearby.append(prop)
            except Exception:
                pass

        if primary_prop:
            nearby = [p for p in nearby if p.zpid != primary_prop.zpid]
            return [primary_prop] + nearby

        street, city, state, zipcode = _parse_address_parts(address)
        placeholder = Property(
            zpid=f"searched-{hash(address) % 100000}",
            address=street, city=city, state=state, zipcode=zipcode,
            current_price=0,
            detail_url=self._make_zillow_url(None, street, city, state, zipcode),
        )
        return [placeholder] + nearby

    def _parse_detail(self, data: dict, fallback_address: str) -> Property | None:
        try:
            address = data.get("address", {})
            if isinstance(address, dict):
                street = address.get("streetAddress", fallback_address)
                city = address.get("city", "")
                state = address.get("state", "")
                zipcode = address.get("zipcode", "")
            else:
                street = str(address) if address else fallback_address
                city = state = zipcode = ""

            price = (
                _safe_float(data.get("price"))
                or _safe_float(data.get("zestimate"))
                or _safe_float(data.get("rentZestimate"))
                or 0
            )

            return Property(
                zpid=str(data.get("zpid", "")),
                address=street, city=city, state=state, zipcode=zipcode,
                current_price=price,
                last_sold_price=_safe_float(data.get("lastSoldPrice")),
                last_sold_date=data.get("dateSold") or data.get("datePosted"),
                home_type=data.get("homeType") or data.get("propertyType"),
                bedrooms=_safe_int(data.get("bedrooms")),
                bathrooms=_safe_float(data.get("bathrooms")),
                living_area=_safe_int(data.get("livingArea")),
                image_url=data.get("imgSrc") or data.get("hiResImageLink"),
                detail_url=self._make_zillow_url(data.get("url") or data.get("detailUrl"), street, city, state, zipcode),
            )
        except (ValueError, TypeError):
            return None


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

PROVIDERS: dict[str, type[ListingProvider]] = {
    "rentcast": RentCastProvider,
    "realtor": RealtorProvider,
    "zillow": ZillowProvider,
}

DATA_SOURCE = os.environ.get("DATA_SOURCE", "").lower()


def get_provider() -> ListingProvider | None:
    """Return the configured provider, or None if no API key is set.

    Priority:
      1. DATA_SOURCE env var explicitly chooses a provider
      2. Auto-detect based on which API keys are set
    """
    if DATA_SOURCE and DATA_SOURCE in PROVIDERS:
        provider = PROVIDERS[DATA_SOURCE]()
        if provider.is_configured:
            return provider

    # Auto-detect: try each in order of preference
    for name in ["rentcast", "realtor", "zillow"]:
        provider = PROVIDERS[name]()
        if provider.is_configured:
            return provider

    return None
