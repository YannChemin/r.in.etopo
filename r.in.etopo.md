## DESCRIPTION

*r.in.etopo* downloads the NOAA ETOPO 2022 global relief model (land
topography and ocean bathymetry, NOAA NCEI) for an area and imports it as
a raster map. ETOPO 2022 merges GEBCO, multibeam surveys, Copernicus and
other land models into seamless grids at 15, 30 and 60 arc-seconds
(about 450 m, 900 m and 1.8 km), with heights in metres above the
EGM2008 geoid (negative below sea level).

Only the cells of the area are transferred: the module reads index
windows of the NCEI THREDDS server through OPeNDAP (no account needed).
At 15 arc-seconds the grid is split in 15 x 15 degree tiles, and an area
across tile edges is read from each tile and mosaicked.

### Resolution and layers

**resolution=auto** (default) picks the coarsest grid whose cells are not
larger than those of the current region. **layer** chooses between:

| Layer | Content |
|---|---|
| surface | Elevation of the surface: top of the ice sheets, land, sea floor |
| bed | Elevation of the bedrock below the ice sheets (equal to *surface* outside them) |
| geoid | EGM2008 geoid height above the WGS84 ellipsoid |

At 15 arc-seconds the *bed* tiles exist only where ice makes the bed
differ from the surface (62 of 288 tiles); elsewhere the module reads the
*surface* tile, which is the bed there.

### Import

By default the window is imported on the current region (extent and
resolution) with *r.import*, as *r.in.dem* does. With **-n**, it is
imported at the native ETOPO resolution over the area. **-b** keeps the
bathymetry only (cells above 0 m set to null). The map gets the *etopo2*
colour table, its units and vertical datum.

## NOTES

The area defaults to the current region plus one grid cell. Areas crossing
the antimeridian are not supported; import the two sides separately.
**max_cells** (200 million by default) stops a request that would be very
large (the whole world at 15 arc-seconds is 3.7 billion cells): use a
coarser resolution or a smaller area. Downloaded windows are kept in
**cache_dir** as GeoTIFF and reused.

ETOPO 2022 is a relief model, not a navigation chart: in shallow coastal
waters its 450 m cells smooth channels, reefs and dredged areas.

## EXAMPLES

Bathymetry of the southern Arabian Gulf at native 15 arc-second
resolution, land removed:

```sh
r.in.etopo -n -b output=bathy15 resolution=15s area=26.8,54.0,24.8,57.0
r.univar bathy15
```

Relief on the current region at the matching resolution:

```sh
g.region n=2965000 s=2745000 w=200000 e=500000 res=1000
r.in.etopo output=relief
```

## SEE ALSO

*[r.import](https://grass.osgeo.org/grass-stable/manuals/r.import.html),
[r.in.dem](r.in.dem.md),
[r.in.srtm.region](https://grass.osgeo.org/grass-stable/manuals/addons/r.in.srtm.region.html),
[t.in.hycom](t.in.hycom.md)*

## REFERENCES

- NOAA National Centers for Environmental Information (2022). ETOPO 2022
  15 Arc-Second Global Relief Model. doi:10.25921/fd45-gt74.

## AUTHORS

Yann Chemin
