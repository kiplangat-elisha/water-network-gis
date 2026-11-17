"""Quality checks for water network GIS layers before they are loaded into PostGIS."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

logger = logging.getLogger(__name__)

DEFAULT_SNAP_TOLERANCE_M = 5.0
DEFAULT_NODE_TOLERANCE_M = 0.5


@dataclass
class ValidationReport:
    """Results of the network checks; each attribute lists offending IDs."""

    duplicate_pipe_ids: list[str] = field(default_factory=list)
    missing_diameter: list[str] = field(default_factory=list)
    dangling_ends: int = 0
    meters_far_from_pipe: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """True when no issue was found."""
        return not (
            self.duplicate_pipe_ids
            or self.missing_diameter
            or self.dangling_ends
            or self.meters_far_from_pipe
        )


def _require_projected(gdf: gpd.GeoDataFrame, name: str) -> None:
    if gdf.crs is None or not gdf.crs.is_projected:
        raise ValueError(f"{name} must be in a projected CRS (metres); got {gdf.crs}.")


def count_dangling_ends(
    pipes: gpd.GeoDataFrame, tolerance_m: float = DEFAULT_NODE_TOLERANCE_M
) -> int:
    """Count pipe end points that touch no other pipe.

    Some dangling ends are real (dead-end mains); a high count usually means
    digitising gaps. Complexity is O(n log n) through the spatial index.

    Args:
        pipes: LineString layer in a projected CRS.
        tolerance_m: Distance within which two end points are treated as connected.

    Returns:
        Number of end points with no other pipe within the tolerance.
    """
    _require_projected(pipes, "pipes")
    if pipes.empty:
        return 0
    ends: list[Point] = []
    owner: list[int] = []
    for idx, geom in zip(pipes.index, pipes.geometry, strict=True):
        coords = list(geom.coords)
        ends.extend([Point(coords[0]), Point(coords[-1])])
        owner.extend([idx, idx])
    ends_gdf = gpd.GeoDataFrame({"owner": owner}, geometry=ends, crs=pipes.crs)
    buffered = ends_gdf.copy()
    buffered["geometry"] = ends_gdf.buffer(tolerance_m)
    hits = gpd.sjoin(buffered, pipes[["geometry"]], predicate="intersects", how="left")
    touching_other = hits[hits["index_right"] != hits["owner"]].index.unique()
    return int(len(ends_gdf) - len(touching_other))


def validate_network(
    pipes: gpd.GeoDataFrame,
    meters: gpd.GeoDataFrame,
    snap_tolerance_m: float = DEFAULT_SNAP_TOLERANCE_M,
) -> ValidationReport:
    """Run all checks on pipes and customer meters.

    Args:
        pipes: Pipe layer with ``pipe_id`` and ``diameter_mm`` columns.
        meters: Meter layer with an ``account_no`` column.
        snap_tolerance_m: Maximum allowed distance from a meter to the nearest pipe.

    Returns:
        A ValidationReport listing every issue found.
    """
    _require_projected(pipes, "pipes")
    _require_projected(meters, "meters")
    if pipes.crs != meters.crs:
        raise ValueError("pipes and meters must share the same CRS.")

    report = ValidationReport()
    dup = pipes["pipe_id"][pipes["pipe_id"].duplicated(keep=False)]
    report.duplicate_pipe_ids = sorted(dup.astype(str).unique().tolist())
    report.missing_diameter = sorted(
        pipes.loc[pipes["diameter_mm"].isna(), "pipe_id"].astype(str).tolist()
    )
    report.dangling_ends = count_dangling_ends(pipes)

    if not meters.empty and not pipes.empty:
        nearest = gpd.sjoin_nearest(
            meters[["account_no", "geometry"]], pipes[["geometry"]], distance_col="dist_m"
        )
        far = nearest.loc[nearest["dist_m"] > snap_tolerance_m, "account_no"]
        report.meters_far_from_pipe = sorted(pd.unique(far.astype(str)).tolist())

    logger.info("Validation finished: clean=%s", report.is_clean)
    return report
