# r.in.etopo

GRASS GIS addon that downloads the NOAA ETOPO 2022 global relief model
(topography and bathymetry, 15, 30 or 60 arc-second) for an area and
imports it as a raster map.

- Only the cells of the area are transferred, through OPeNDAP on the NCEI
  THREDDS server; no account is needed.
- `resolution=auto` matches the region's cell size; `layer` is the
  surface, the bedrock below the ice, or the EGM2008 geoid.
- `-b` keeps the sea floor only; `-n` imports at native resolution.

See [r.in.etopo.md](r.in.etopo.md) for the manual.

## Install

```sh
make -C grass-addons/src/raster/r.in.etopo MODULE_TOPDIR=/path/to/grass
```

## Tests

```sh
python3 -m pytest tests            # offline
python3 -m pytest -m network tests # live catalogue query
```

## Licence

The Unlicense (public domain), see [LICENSE](LICENSE).
