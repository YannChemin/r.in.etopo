#!/usr/bin/env python3

############################################################################
#
# MODULE:       r.in.etopo
# AUTHOR(S):    Yann Chemin
# PURPOSE:      Downloads NOAA ETOPO 2022 topography and bathymetry (15, 30
#               or 60 arc-second) for an area through OPeNDAP, transferring
#               only the cells of the area, and imports it as a raster map.
#
# SPDX-License-Identifier: Unlicense
#
############################################################################

# %module
# % description: Downloads NOAA ETOPO 2022 global topography and bathymetry (15, 30 or 60 arc-second) for an area and imports it.
# % keyword: raster
# % keyword: import
# % keyword: bathymetry
# % keyword: elevation
# % keyword: ETOPO
# %end
# %option G_OPT_R_OUTPUT
# %end
# %option
# % key: resolution
# % type: string
# % required: no
# % options: auto,15s,30s,60s
# % answer: auto
# % description: ETOPO 2022 grid
# % descriptions: auto;Coarsest grid whose cells are not larger than the region's;15s;15 arc-second (about 450 m), 15 degree tiles;30s;30 arc-second (about 900 m), one global file;60s;60 arc-second (about 1.8 km), one global file
# %end
# %option
# % key: layer
# % type: string
# % required: no
# % options: surface,bed,geoid
# % answer: surface
# % description: ETOPO 2022 layer
# % descriptions: surface;Elevation of the surface: ice top, land and sea floor (m, EGM2008);bed;Elevation of the bedrock below the ice sheets (m, EGM2008), equal to surface elsewhere;geoid;EGM2008 geoid height above the WGS84 ellipsoid (m)
# %end
# %option
# % key: area
# % type: double
# % multiple: yes
# % required: no
# % key_desc: north,west,south,east
# % description: Bounding box in WGS84 degrees (default the current region, plus one grid cell)
# %end
# %option
# % key: resample
# % type: string
# % required: no
# % options: nearest,bilinear,bicubic,lanczos
# % answer: bilinear
# % description: Resampling method of r.import
# %end
# %option G_OPT_M_DIR
# % key: cache_dir
# % required: no
# % description: Directory to keep the downloaded windows in (GeoTIFF), reused by later runs
# %end
# %option
# % key: max_cells
# % type: integer
# % required: no
# % answer: 200000000
# % description: Largest window, in grid cells, that the module downloads
# %end
# %flag
# % key: b
# % description: Bathymetry only: set cells above sea level (0 m) to null
# %end
# %flag
# % key: n
# % description: Import at the native ETOPO resolution and extent of the area instead of the current region
# %end
# %flag
# % key: l
# % description: List the files and window sizes for the area, then exit
# %end

import atexit
import math
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import grass.script as gs

OPENDAP = "https://www.ngdc.noaa.gov/thredds/dodsC/global/ETOPO2022"
CATALOG = "https://www.ngdc.noaa.gov/thredds/catalog/global/ETOPO2022"
ARCSEC = {"15s": 15, "30s": 30, "60s": 60}
# File name suffix and folder of each layer.
LAYERS = {"surface": "surface", "bed": "bed", "geoid": "geoid"}
TILE_DEG = 15

TMP_DIR = None


def cleanup():
    if TMP_DIR and os.path.isdir(TMP_DIR):
        shutil.rmtree(TMP_DIR, ignore_errors=True)


def tile_name(lat_top, lon_left):
    """15 arc-second tiles are named by their north-west corner."""
    ns = "N" if lat_top >= 0 else "S"
    ew = "E" if lon_left >= 0 else "W"
    return "{}{:02d}{}{:03d}".format(ns, abs(lat_top), ew, abs(lon_left))


def tiles_for(area):
    """15 degree tiles covering area, as (lat_top, lon_left)."""
    n, w, s, e = area
    tops = range(
        int(math.ceil(n / TILE_DEG)) * TILE_DEG,
        int(math.floor(s / TILE_DEG)) * TILE_DEG,
        -TILE_DEG,
    )
    lefts = range(
        int(math.floor(w / TILE_DEG)) * TILE_DEG,
        int(math.ceil(e / TILE_DEG)) * TILE_DEG,
        TILE_DEG,
    )
    return [
        (t, lft) for t in tops for lft in lefts if -90 < t <= 90 and -180 <= lft < 180
    ]


def url(res, layer, name):
    folder = "{}/{}_{}_{}".format(
        res, res, "geoid" if layer == "geoid" else layer + "_elev", "netcdf"
    )
    return "{}/{}/ETOPO_2022_v1_{}_{}_{}.nc".format(
        OPENDAP, folder, res, name, LAYERS[layer]
    )


def bed_tiles():
    """Names of the 15 arc-second bed tiles: they exist only where ice makes
    the bed differ from the surface (62 of 288 tiles)."""
    import re
    import urllib.request

    xml = (
        urllib.request.urlopen(
            "{}/15s/15s_bed_elev_netcdf/catalog.xml".format(CATALOG), timeout=120
        )
        .read()
        .decode()
    )
    return set(re.findall(r"_15s_([NS]\d{2}[EW]\d{3})_bed\.nc", xml))


def sources(res, layer, area):
    """OPeNDAP URLs covering area."""
    if res != "15s":
        return [url(res, layer, "N90W180")]
    have_bed = bed_tiles() if layer == "bed" else set()
    out = []
    for t, lft in tiles_for(area):
        name = tile_name(t, lft)
        if layer == "bed" and name not in have_bed:
            gs.verbose("No bed tile {}: the bed is the surface there".format(name))
            out.append(url(res, "surface", name))
        else:
            out.append(url(res, layer, name))
    return out


def auto_resolution(area):
    """Coarsest grid whose cells are not larger than the region's."""
    reg = gs.region()
    proj = gs.parse_command("g.proj", flags="g")
    if proj.get("units", "").lower().startswith("deg"):
        cell_deg = min(reg["nsres"], reg["ewres"])
    else:
        cell_deg = min(reg["nsres"], reg["ewres"]) / 111320.0
    for res in ("60s", "30s", "15s"):
        if ARCSEC[res] / 3600.0 <= cell_deg * 1.0001:
            return res
    return "15s"


def default_area(res_deg):
    info = gs.parse_command("g.region", flags="bg")
    n, w, s, e = (float(info[k]) for k in ("ll_n", "ll_w", "ll_s", "ll_e"))
    return [
        min(90.0, n + res_deg),
        max(-180.0, w - res_deg),
        max(-90.0, s - res_deg),
        min(180.0, e + res_deg),
    ]


def open_remote(u, retries=5):
    import netCDF4

    last = None
    for attempt in range(retries):
        try:
            return netCDF4.Dataset(u)
        except OSError as err:
            last = err
            time.sleep(min(60, 5 * 2**attempt))
    gs.fatal("Cannot open {} after {} attempts: {}".format(u, retries, last))


def read_window(ds, area):
    """Cells of ds inside area, north-up, with the GDAL geotransform."""
    import numpy as np

    lat = ds["lat"][:]
    lon = ds["lon"][:]
    n, w, s, e = area
    i0 = int(np.searchsorted(lat, s, side="left"))
    i1 = int(np.searchsorted(lat, n, side="right"))
    j0 = int(np.searchsorted(lon, w, side="left"))
    j1 = int(np.searchsorted(lon, e, side="right"))
    if i1 <= i0 or j1 <= j0:
        return None
    for attempt in range(5):
        try:
            z = ds["z"][i0:i1, j0:j1]
            break
        except (OSError, RuntimeError) as err:
            if attempt == 4:
                gs.fatal("OPeNDAP read failed: {}".format(err))
            time.sleep(5 * 2**attempt)
    z = np.ma.filled(z.astype("float32"), np.nan)[::-1]
    d = float(lat[1] - lat[0])
    gt = (float(lon[j0]) - d / 2, d, 0.0, float(lat[i1 - 1]) + d / 2, 0.0, -d)
    return z, gt


def write_tif(path, arr, gt):
    import numpy as np
    from osgeo import gdal, osr

    gdal.UseExceptions()
    rows, cols = arr.shape
    dst = gdal.GetDriverByName("GTiff").Create(
        str(path),
        cols,
        rows,
        1,
        gdal.GDT_Float32,
        options=["COMPRESS=DEFLATE", "TILED=YES"],
    )
    dst.SetGeoTransform(gt)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    dst.SetProjection(srs.ExportToWkt())
    band = dst.GetRasterBand(1)
    band.SetNoDataValue(-99999.0)
    band.WriteArray(np.where(np.isfinite(arr), arr, -99999.0).astype(np.float32))
    dst.FlushCache()
    dst = None


def main():
    global TMP_DIR
    options, flags = gs.parser()
    atexit.register(cleanup)
    TMP_DIR = tempfile.mkdtemp(prefix="r_in_etopo_")
    res = options["resolution"]
    if res == "auto":
        res = auto_resolution(None)
    cell = ARCSEC[res] / 3600.0
    if options["area"]:
        area = [float(v) for v in options["area"].split(",")]
        if len(area) != 4 or area[0] <= area[2] or area[3] <= area[1]:
            gs.fatal(
                "Area must be north,west,south,east with north > south and east > west"
            )
    else:
        area = default_area(cell)
    if area[3] - area[1] > 360 or area[1] < -180 or area[3] > 180:
        gs.fatal(
            "Areas crossing the antimeridian are not supported; import the east and west parts separately"
        )
    layer = options["layer"]
    srcs = sources(res, layer, area)
    ncells = int((area[0] - area[2]) / cell) * int((area[3] - area[1]) / cell)

    if flags["l"]:
        print(
            "resolution={}\nlayer={}\narea={:.4f},{:.4f},{:.4f},{:.4f}\ncells={}\nMB={:.1f}".format(
                res, layer, *area, ncells, ncells * 4 / 1e6
            )
        )
        for p in srcs:
            print("file={}".format(p))
        return 0
    if ncells > int(options["max_cells"]):
        gs.fatal(
            "The window has {} cells at {} (over max_cells={}); use a coarser resolution "
            "or a smaller area".format(ncells, res, options["max_cells"])
        )

    cache = Path(options["cache_dir"]) if options["cache_dir"] else Path(TMP_DIR)
    cache.mkdir(parents=True, exist_ok=True)
    pieces = []
    for k, src_url in enumerate(srcs):
        key = "etopo2022_{}_{}_{}_{:.4f}_{:.4f}_{:.4f}_{:.4f}.tif".format(
            res, layer, Path(src_url).stem.split("_")[4], *area
        )
        tif = cache / key
        if not tif.exists():
            ds = open_remote(src_url)
            win = read_window(ds, area)
            ds.close()
            if win is None:
                continue
            tmp = tif.with_name("." + tif.name)
            write_tif(tmp, *win)
            tmp.replace(tif)
        pieces.append(str(tif))
        gs.percent(k + 1, len(srcs), 1)
    if not pieces:
        gs.fatal("No ETOPO 2022 cell falls inside the area {}".format(area))

    src = pieces[0]
    if len(pieces) > 1:
        from osgeo import gdal

        gdal.UseExceptions()
        src = str(Path(TMP_DIR) / "mosaic.vrt")
        gdal.BuildVRT(src, pieces)
    out = options["output"]
    imp = dict(
        input=src,
        output=out,
        resample=options["resample"],
        overwrite=gs.overwrite(),
        quiet=True,
    )
    if flags["n"]:
        imp.update(extent="input", resolution="estimated")
    else:
        imp.update(extent="region", resolution="region")
    gs.run_command("r.import", **imp)
    if flags["b"]:
        tmp = "tmp_r_in_etopo_{}".format(os.getpid())
        gs.run_command("g.rename", raster=(out, tmp), quiet=True)
        gs.mapcalc("$out = if($tmp > 0, null(), $tmp)", out=out, tmp=tmp, quiet=True)
        gs.run_command("g.remove", type="raster", name=tmp, flags="f", quiet=True)
    gs.run_command("r.colors", map=out, color="etopo2", quiet=True)
    titles = {
        "surface": "surface elevation (ice top, land, sea floor)",
        "bed": "bedrock elevation",
        "geoid": "EGM2008 geoid height",
    }
    gs.run_command(
        "r.support",
        map=out,
        units="m",
        vdatum="EGM2008 (EPSG:3855)" if layer != "geoid" else "WGS84 ellipsoid",
        title="NOAA ETOPO 2022 {} {}{}".format(
            res, titles[layer], ", bathymetry only" if flags["b"] else ""
        ),
        source1="NOAA NCEI ETOPO 2022 v1, doi:10.25921/fd45-gt74",
        source2=OPENDAP,
    )
    gs.raster_history(out)
    gs.message(
        "Imported <{}> from ETOPO 2022 {} ({} file(s))".format(out, res, len(pieces))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
