# Method scripts

How the City of Adelaide's 3D model was read and joined to OpenStreetMap's outlines. They are here to show the method;
they expect the downloads in a `raw/` folder beside them and write to `work/`.

| Script | What it does |
|---|---|
| `model_points.py` | Reads one of the model's COLLADA files into sample points (every triangle's corners, edge middles and centre), in metres |
| `align_check.py` | Rasterises the points and OpenStreetMap's buildings at 2 m and finds the heading and shift where they overlap best (1.4 degrees, no shift) |
| `prep.py` | Keeps OpenStreetMap's buildings inside the City of Adelaide and gives each the model's height inside its outline |
| `coverage_check.py` | Compares the outlines with the state's 2022 building mask (0.5 m cells) |
| `heritage_check.py` | Looks through SA Heritage Places for construction years (it has listing dates only) |

Downloads: the Overpass API for OpenStreetMap's buildings and parts in the box -34.945, 138.570 to -34.895, 138.630;
"05 Adelaide City Council 3D Model for Multipatch" from https://data.sa.gov.au/data/dataset/3d-model; the ABS ASGS
Edition 3 local government area and suburb boundaries; the 2022 building footprints raster and SA Heritage Places from
Data.SA.

The choice between the model, OpenStreetMap's tags and an estimate is set out in the main README and applied again in
the notebook.
