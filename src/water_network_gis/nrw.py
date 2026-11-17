"""Non-revenue water (NRW) per district metered area (DMA)."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

HIGH_NRW_THRESHOLD = 0.40  # share of input volume; above this a DMA is a hotspot
MEDIUM_NRW_THRESHOLD = 0.25


def classify_nrw(ratio: float) -> str:
    """Return 'high', 'medium', 'low' or 'no data' for an NRW ratio."""
    if pd.isna(ratio):
        return "no data"
    if ratio >= HIGH_NRW_THRESHOLD:
        return "high"
    if ratio >= MEDIUM_NRW_THRESHOLD:
        return "medium"
    return "low"


def nrw_by_dma(
    dmas: gpd.GeoDataFrame,
    meters: gpd.GeoDataFrame,
    billing: pd.DataFrame,
    input_volume: pd.DataFrame,
) -> pd.DataFrame:
    """Compute monthly NRW for each DMA.

    Args:
        dmas: Polygons with ``dma_id``.
        meters: Customer meter points with ``account_no``.
        billing: Columns ``account_no``, ``month``, ``billed_m3``.
        input_volume: Columns ``dma_id``, ``month``, ``input_m3`` (bulk meter readings).

    Returns:
        One row per DMA and month with billed, NRW volume, ratio and class.

    Raises:
        ValueError: If the layers use different CRSs or volumes are negative.
    """
    if dmas.crs != meters.crs:
        raise ValueError("dmas and meters must share the same CRS.")
    if (billing["billed_m3"] < 0).any() or (input_volume["input_m3"] < 0).any():
        raise ValueError("Volumes must be non-negative.")

    located = gpd.sjoin(
        meters[["account_no", "geometry"]], dmas[["dma_id", "geometry"]], predicate="within"
    )[["account_no", "dma_id"]]
    billed = (
        billing.merge(located, on="account_no", how="inner")
        .groupby(["dma_id", "month"], as_index=False)["billed_m3"]
        .sum()
    )
    out = input_volume.merge(billed, on=["dma_id", "month"], how="left")
    out["billed_m3"] = out["billed_m3"].fillna(0.0)
    out["nrw_m3"] = out["input_m3"] - out["billed_m3"]
    out["nrw_ratio"] = out["nrw_m3"].where(out["input_m3"] > 0) / out["input_m3"].where(
        out["input_m3"] > 0
    )
    out["nrw_class"] = out["nrw_ratio"].map(classify_nrw)
    return out.sort_values(["month", "nrw_ratio"], ascending=[True, False]).reset_index(drop=True)
