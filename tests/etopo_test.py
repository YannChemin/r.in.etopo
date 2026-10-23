"""Tests of the tile naming, tile cover, URLs and window reading of
r.in.etopo. Offline, except the test marked network."""

import numpy as np
import pytest


def test_tile_name(etopo):
    assert etopo.tile_name(30, 45) == "N30E045"
    assert etopo.tile_name(0, -15) == "N00W015"
    assert etopo.tile_name(-60, 0) == "S60E000"
    assert etopo.tile_name(-75, -180) == "S75W180"


def test_tiles_for(etopo):
    assert etopo.tiles_for([26.8, 54.0, 24.8, 57.0]) == [(30, 45)]
    # Across a tile corner: four tiles, north-west first.
    assert etopo.tiles_for([16.0, 44.0, 14.0, 46.0]) == [
        (30, 30),
        (30, 45),
        (15, 30),
        (15, 45),
    ]
    assert etopo.tiles_for([-70.0, 0.0, -80.0, 20.0]) == [
        (-60, 0),
        (-60, 15),
        (-75, 0),
        (-75, 15),
    ]


def test_url(etopo):
    assert etopo.url("15s", "surface", "N30E045").endswith(
        "/15s/15s_surface_elev_netcdf/ETOPO_2022_v1_15s_N30E045_surface.nc"
    )
    assert etopo.url("30s", "bed", "N90W180").endswith(
        "/30s/30s_bed_elev_netcdf/ETOPO_2022_v1_30s_N90W180_bed.nc"
    )
    assert etopo.url("60s", "geoid", "N90W180").endswith(
        "/60s/60s_geoid_netcdf/ETOPO_2022_v1_60s_N90W180_geoid.nc"
    )


class FakeVar:
    def __init__(self, a):
        self.a = a

    def __getitem__(self, k):
        return self.a[k]


def test_read_window_north_up(etopo):
    d = 1 / 240.0
    lat = 15 + d / 2 + np.arange(3600) * d
    lon = 45 + d / 2 + np.arange(3600) * d
    z = np.add.outer(np.arange(3600), np.zeros(3600)).astype("float32")  # Row index.
    ds = {"lat": FakeVar(lat), "lon": FakeVar(lon), "z": FakeVar(np.ma.masked_array(z))}
    arr, gt = etopo.read_window(ds, [25.1, 55.0, 25.0, 55.1])
    assert arr.shape == (24, 24)
    assert arr[0, 0] > arr[-1, 0]  # Northern row first.
    assert gt[0] == pytest.approx(55.0, abs=1e-9)
    assert gt[3] == pytest.approx(25.1, abs=1e-9)
    assert gt[1] == pytest.approx(d) and gt[5] == pytest.approx(-d)
    assert etopo.read_window(ds, [10.0, 55.0, 9.0, 56.0]) is None


@pytest.mark.network
def test_bed_tiles_live(etopo):
    tiles = etopo.bed_tiles()
    assert len(tiles) == 62
    assert "S75W180" in tiles and "N30E045" not in tiles
