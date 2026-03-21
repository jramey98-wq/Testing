from pydantic import BaseModel


class Property(BaseModel):
    zpid: str
    address: str
    city: str
    state: str
    zipcode: str
    current_price: float
    last_sold_price: float | None = None
    last_sold_date: str | None = None
    home_type: str | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    living_area: int | None = None
    image_url: str | None = None
    detail_url: str | None = None


class PriceComparison(BaseModel):
    property: Property
    price_increase: float | None = None
    price_increase_pct: float | None = None
    has_prior_sale: bool = False


class SearchResponse(BaseModel):
    query: str
    result_count: int
    results: list[PriceComparison]
    demo_mode: bool = False
    search_type: str = "area"  # "area" or "address"
