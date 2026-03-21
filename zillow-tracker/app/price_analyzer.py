from app.models import Property, PriceComparison


def analyze_prices(properties: list[Property]) -> list[PriceComparison]:
    """Calculate price increases and sort by biggest percentage gain."""
    comparisons = []

    for prop in properties:
        if prop.current_price <= 0:
            continue

        if prop.last_sold_price and prop.last_sold_price > 0:
            increase = prop.current_price - prop.last_sold_price
            pct = (increase / prop.last_sold_price) * 100
            comparisons.append(PriceComparison(
                property=prop,
                price_increase=round(increase, 2),
                price_increase_pct=round(pct, 2),
                has_prior_sale=True,
            ))
        else:
            comparisons.append(PriceComparison(
                property=prop,
                has_prior_sale=False,
            ))

    # Sort: properties with prior sales first (by % desc), then those without
    with_sales = [c for c in comparisons if c.has_prior_sale]
    without_sales = [c for c in comparisons if not c.has_prior_sale]

    with_sales.sort(key=lambda c: c.price_increase_pct or 0, reverse=True)
    without_sales.sort(key=lambda c: c.property.current_price, reverse=True)

    return with_sales + without_sales
