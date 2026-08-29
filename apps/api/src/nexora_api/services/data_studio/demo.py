"""Reproducible synthetic demand history for Data Studio evaluation."""

from __future__ import annotations

from io import StringIO

import numpy as np
import pandas as pd

DEMO_SEED = 2042


def build_demo_frame() -> pd.DataFrame:
    """Generate two years of daily, heterogeneous product-location demand."""
    rng = np.random.default_rng(DEMO_SEED)
    dates = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    products = [
        ("NX-101", "Essentials", 34.0, 18.5),
        ("NX-102", "Essentials", 48.0, 22.0),
        ("NX-103", "Essentials", 27.0, 14.8),
        ("NX-104", "Essentials", 62.0, 31.0),
        ("NX-201", "Premium", 18.0, 45.0),
        ("NX-202", "Premium", 22.0, 52.0),
        ("NX-203", "Premium", 15.0, 67.0),
        ("NX-204", "Premium", 25.0, 39.0),
    ]
    locations = [("Lima Centro", 1.0), ("Arequipa Norte", 0.78)]
    records: list[dict[str, object]] = []

    for product_index, (product, category, baseline, base_price) in enumerate(products):
        for location, location_factor in locations:
            for day_index, date in enumerate(dates):
                weekly = 1.0 + 0.16 * np.sin(2 * np.pi * date.dayofweek / 7 + product_index)
                annual = 1.0 + 0.09 * np.sin(2 * np.pi * date.dayofyear / 365.25)
                trend = 1.0 + (0.00024 + product_index * 0.000015) * day_index
                promotion = bool(rng.random() < 0.075)
                price = base_price * (1 + 0.025 * np.sin(day_index / 83) + rng.normal(0, 0.008))
                promo_lift = 1.24 if promotion else 1.0
                expected = baseline * location_factor * weekly * annual * trend * promo_lift
                demand = max(
                    0, int(round(rng.normal(expected, max(2.0, np.sqrt(expected) * 0.72))))
                )
                stock = max(demand, int(round(expected * 1.45 + rng.normal(9, 5))))
                records.append(
                    {
                        "date": date.strftime("%Y-%m-%d"),
                        "product": product,
                        "category": category,
                        "location": location,
                        "demand": demand,
                        "price": round(float(price), 2),
                        "stock": stock,
                        "promotion": promotion,
                    }
                )

    frame = pd.DataFrame.from_records(records)
    all_indices = np.arange(len(frame))
    stockout_indices = rng.choice(all_indices, size=24, replace=False)
    remaining = np.setdiff1d(all_indices, stockout_indices)
    outlier_indices = rng.choice(remaining, size=14, replace=False)
    remaining = np.setdiff1d(remaining, outlier_indices)
    missing_demand_indices = rng.choice(remaining, size=12, replace=False)
    remaining = np.setdiff1d(remaining, missing_demand_indices)
    missing_price_indices = rng.choice(remaining, size=10, replace=False)

    frame.loc[stockout_indices, ["demand", "stock"]] = 0
    frame.loc[outlier_indices, "demand"] = frame.loc[outlier_indices, "demand"] * 5
    frame.loc[missing_demand_indices, "demand"] = np.nan
    frame.loc[missing_price_indices, "price"] = np.nan
    return frame


def build_demo_csv() -> bytes:
    output = StringIO()
    build_demo_frame().to_csv(output, index=False, lineterminator="\n")
    return output.getvalue().encode("utf-8")
