from app.models import Property, PriceComparison


def analyze_prices(properties: list[Property]) -> list[PriceComparison]:
    """Calculate price increases and sort by biggest percentage gain.

    Preserves the first property's position (for address searches where
    the searched property must stay first).
    """
    if not properties:
        return []

    # Check if first property is a searched-address placeholder or primary
    first = properties[0]
    first_is_primary = first.zpid.startswith("searched-") or first.zpid.startswith("demo-addr-")

    comparisons = []
    primary_comparison = None

    for i, prop in enumerate(properties):
        # Keep placeholder/primary properties even with price 0
        is_primary = (i == 0 and first_is_primary)

        if prop.current_price <= 0 and not is_primary:
            continue

        if prop.current_price > 0 and prop.last_sold_price and prop.last_sold_price > 0:
            increase = prop.current_price - prop.last_sold_price
            pct = (increase / prop.last_sold_price) * 100
            comp = PriceComparison(
                property=prop,
                price_increase=round(increase, 2),
                price_increase_pct=round(pct, 2),
                has_prior_sale=True,
            )
        else:
            comp = PriceComparison(
                property=prop,
                has_prior_sale=prop.last_sold_price is not None and prop.last_sold_price > 0,
            )

        if is_primary:
            primary_comparison = comp
        else:
            comparisons.append(comp)

    # Sort: properties with prior sales first (by % desc), then those without
    with_sales = [c for c in comparisons if c.has_prior_sale]
    without_sales = [c for c in comparisons if not c.has_prior_sale]

    with_sales.sort(key=lambda c: c.price_increase_pct or 0, reverse=True)
    without_sales.sort(key=lambda c: c.property.current_price, reverse=True)

    sorted_results = with_sales + without_sales

    # Primary address always first
    if primary_comparison:
        return [primary_comparison] + sorted_results

    return sorted_results
