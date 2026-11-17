import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, Point, box

from water_network_gis import PROJECT_CRS
from water_network_gis.nrw import classify_nrw, nrw_by_dma
from water_network_gis.sample_data import make_sample
from water_network_gis.validate import count_dangling_ends, validate_network


def _pipes(lines, ids=None, diam=None):
    ids = ids or [f"P{i}" for i in range(len(lines))]
    diam = diam if diam is not None else [100] * len(lines)
    return gpd.GeoDataFrame({"pipe_id": ids, "diameter_mm": diam}, geometry=lines, crs=PROJECT_CRS)


def test_connected_pipes_have_two_dangling_ends():
    pipes = _pipes([LineString([(0, 0), (10, 0)]), LineString([(10, 0), (20, 0)])])
    assert count_dangling_ends(pipes) == 2


def test_empty_pipes():
    assert count_dangling_ends(_pipes([])) == 0


def test_validation_flags_issues():
    pipes = _pipes([LineString([(0, 0), (10, 0)]), LineString([(10, 0), (20, 0)])],
                   ids=["P1", "P1"], diam=[100, None])
    meters = gpd.GeoDataFrame({"account_no": ["A1", "A2"]},
                              geometry=[Point(5, 1), Point(5, 50)], crs=PROJECT_CRS)
    rep = validate_network(pipes, meters)
    assert rep.duplicate_pipe_ids == ["P1"]
    assert rep.missing_diameter == ["P1"]
    assert rep.meters_far_from_pipe == ["A2"]
    assert not rep.is_clean


def test_geographic_crs_rejected():
    pipes = _pipes([LineString([(0, 0), (1, 0)])]).set_crs("EPSG:4326", allow_override=True)
    with pytest.raises(ValueError):
        count_dangling_ends(pipes)


@pytest.mark.parametrize("ratio,expected", [(0.5, "high"), (0.3, "medium"), (0.1, "low"),
                                            (float("nan"), "no data")])
def test_classify(ratio, expected):
    assert classify_nrw(ratio) == expected


def test_nrw_simple_case():
    dmas = gpd.GeoDataFrame({"dma_id": ["D1"]}, geometry=[box(0, 0, 10, 10)], crs=PROJECT_CRS)
    meters = gpd.GeoDataFrame({"account_no": ["A", "B", "OUT"]},
                              geometry=[Point(1, 1), Point(2, 2), Point(50, 50)], crs=PROJECT_CRS)
    m = pd.Timestamp("2026-01-01")
    billing = pd.DataFrame({"account_no": ["A", "B", "OUT"], "month": [m] * 3,
                            "billed_m3": [30.0, 20.0, 99.0]})
    vol = pd.DataFrame({"dma_id": ["D1"], "month": [m], "input_m3": [100.0]})
    out = nrw_by_dma(dmas, meters, billing, vol)
    assert out.loc[0, "billed_m3"] == 50.0
    assert out.loc[0, "nrw_ratio"] == pytest.approx(0.5)
    assert out.loc[0, "nrw_class"] == "high"


def test_zero_input_gives_no_data():
    dmas = gpd.GeoDataFrame({"dma_id": ["D1"]}, geometry=[box(0, 0, 10, 10)], crs=PROJECT_CRS)
    meters = gpd.GeoDataFrame({"account_no": ["A"]}, geometry=[Point(1, 1)], crs=PROJECT_CRS)
    m = pd.Timestamp("2026-01-01")
    billing = pd.DataFrame({"account_no": ["A"], "month": [m], "billed_m3": [0.0]})
    vol = pd.DataFrame({"dma_id": ["D1"], "month": [m], "input_m3": [0.0]})
    out = nrw_by_dma(dmas, meters, billing, vol)
    assert out.loc[0, "nrw_class"] == "no data"


def test_negative_volume_rejected():
    d = make_sample()
    d["billing"].loc[0, "billed_m3"] = -1
    with pytest.raises(ValueError):
        nrw_by_dma(d["dmas"], d["meters"], d["billing"], d["input_volume"])


def test_sample_runs_end_to_end():
    d = make_sample()
    out = nrw_by_dma(d["dmas"], d["meters"], d["billing"], d["input_volume"])
    assert set(out["dma_id"]) == {"DMA-A", "DMA-B"}
    assert len(out) == 6
