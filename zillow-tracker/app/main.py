from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os

from app.models import SearchResponse
from app.zillow_client import search_properties, RAPIDAPI_KEY, POPULAR_CITIES
from app.price_analyzer import analyze_prices
from app import cache

app = FastAPI(title="Zillow Price Tracker")

static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/api/search", response_model=SearchResponse)
async def search(location: str = Query(..., min_length=2, description="City, State or ZIP code")):
    # Check cache first
    cached = cache.get_cached_search(location)
    if cached:
        comparisons = analyze_prices(cached)
        return SearchResponse(
            query=location,
            result_count=len(comparisons),
            results=comparisons,
            demo_mode=not bool(RAPIDAPI_KEY),
        )

    try:
        properties = await search_properties(location)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch data: {str(e)}")

    if not properties:
        return SearchResponse(
            query=location,
            result_count=0,
            results=[],
            demo_mode=not bool(RAPIDAPI_KEY),
        )

    cache.save_search(location, properties)
    comparisons = analyze_prices(properties)

    return SearchResponse(
        query=location,
        result_count=len(comparisons),
        results=comparisons,
        demo_mode=not bool(RAPIDAPI_KEY),
    )


@app.get("/api/history/{zpid}")
async def price_history(zpid: str):
    history = cache.get_price_history(zpid)
    return {"zpid": zpid, "history": history}


@app.get("/api/cities")
async def get_cities():
    """Return popular cities and previously searched cities."""
    searched = cache.get_cached_cities()
    return {
        "popular": POPULAR_CITIES,
        "recent": searched,
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "api_key_configured": bool(RAPIDAPI_KEY),
        "mode": "live" if RAPIDAPI_KEY else "demo",
    }
