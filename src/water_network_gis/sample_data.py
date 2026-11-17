"""Synthetic sample network for demonstration and tests (no real utility data)."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point, box

from water_network_gis import PROJECT_CRS

SEED = 42
ORIGIN_X, ORIGIN_Y = 820_000.0, 9_880_000.0  # approximately Narok town in EPSG:21036


def make_sample(seed: int = SEED) -> dict[str, gpd.GeoDataFrame | pd.DataFrame]:
    """Build a small two-DMA network with customers, billing and bulk input volumes."""
    rng = np.random.default_rng(seed)
    pipes, ids = [], []
    for row in range(5):
        y = ORIGIN_Y + row * 200
        pipes.append(LineString([(ORIGIN_X, y), (ORIGIN_X + 1000, y)]))
        ids.append(f"P-H{row}")
    pipes.append(LineString([(ORIGIN_X, ORIGIN_Y), (ORIGIN_X, ORIGIN_Y + 800)]))
    ids.append("P-V0")
    pipe_gdf = gpd.GeoDataFrame(
        {"pipe_id": ids, "diameter_mm": [110, 90, 90, 75, 63, 160], "material": "uPVC"},
        geometry=pipes,
        crs=PROJECT_CRS,
    )
    dmas = gpd.GeoDataFrame(
        {"dma_id": ["DMA-A", "DMA-B"]},
        geometry=[
            box(ORIGIN_X - 50, ORIGIN_Y - 50, ORIGIN_X + 500, ORIGIN_Y + 850),
            box(ORIGIN_X + 500, ORIGIN_Y - 50, ORIGIN_X + 1050, ORIGIN_Y + 850),
        ],
        crs=PROJECT_CRS,
    )
    pts, accts = [], []
    for i in range(60):
        row = rng.integers(0, 5)
        x = ORIGIN_X + rng.uniform(10, 990)
        pts.append(Point(x, ORIGIN_Y + row * 200 + rng.uniform(-3, 3)))
        accts.append(f"ACC{i:04d}")
    meters = gpd.GeoDataFrame({"account_no": accts}, geometry=pts, crs=PROJECT_CRS)
    months = pd.to_datetime(["2026-01-01", "2026-02-01", "2026-03-01"])
    billing = pd.DataFrame(
        [(a, m, float(rng.uniform(5, 25))) for a in accts for m in months],
        columns=["account_no", "month", "billed_m3"],
    )
    input_volume = pd.DataFrame(
        [(d, m, v) for d, v in (("DMA-A", 900.0), ("DMA-B", 650.0)) for m in months],
        columns=["dma_id", "month", "input_m3"],
    )
    return {"pipes": pipe_gdf, "dmas": dmas, "meters": meters,
            "billing": billing, "input_volume": input_volume}
