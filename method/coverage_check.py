# How complete are OpenStreetMap's buildings here? Against the state's 2022 building mask (DEW, LiDAR and imagery,
# 0.5 m cells, CC BY): the share of the mask's building area in the council area that an OpenStreetMap outline covers.
import sys, json
import numpy as np, rasterio, geopandas as gpd
from rasterio.windows import from_bounds
from rasterio.features import rasterize
from shapely.geometry import shape
lga = gpd.GeoDataFrame.from_features(json.load(open('raw/lga_adelaide.geojson'))['features'], crs=4326).to_crs(7854)
b = gpd.read_file('tables/buildings.geojson').to_crs(7854)
with rasterio.open('raw/lidar/UrbanBuildings2022.tif') as src:
    print(src.crs, src.res, src.nodata)
    w = from_bounds(*lga.total_bounds, src.transform).round_offsets().round_lengths()
    m = src.read(1, window=w, masked=True); tr = src.window_transform(w)
mask = (~np.ma.getmaskarray(m)) & (np.ma.filled(m, 0) == 1)
inl = rasterize([(g, 1) for g in lga.geometry], out_shape=mask.shape, transform=tr).astype(bool)
osm = rasterize([(g, 1) for g in b.geometry], out_shape=mask.shape, transform=tr).astype(bool)
osm2 = rasterize([(g.buffer(1.5), 1) for g in b.geometry], out_shape=mask.shape, transform=tr).astype(bool)
A = (mask & inl).sum() * 0.25
out = {'mask_building_ha': round(A / 1e4, 1), 'osm_building_ha': round((osm & inl).sum() * 0.25 / 1e4, 1), 'mask_covered_by_osm': round(float((mask & inl & osm).sum() * 0.25 / A), 3), 'mask_covered_by_osm_within_1_5m': round(float((mask & inl & osm2).sum() * 0.25 / A), 3), 'osm_on_mask': round(float((mask & inl & osm).sum() / (osm & inl).sum()), 3)}
print(out); json.dump(out, open('work/coverage.json', 'w'))
# what is missing: the mask's patches further than 1.5 m from any outline, by size
from scipy import ndimage as ndi
miss = mask & inl & ~osm2
lab, n = ndi.label(miss); ar = ndi.sum(miss, lab, range(1, n + 1)) * 0.25
big = ar >= 20
bins = [(20, 100), (100, 400), (400, 2000), (2000, 1e9)]
o2 = {'patches_20m2_plus': int(big.sum()), 'area_ha': round(float(ar[big].sum() / 1e4), 1), 'by_size': {f'{a}-{int(b) if b < 1e9 else "up"} m2': [int(((ar >= a) & (ar < b)).sum()), round(float(ar[(ar >= a) & (ar < b)].sum() / 1e4), 1)] for a, b in bins}}
print(o2); out.update(missing=o2); json.dump(out, open('work/coverage.json', 'w'), default=float)
from PIL import Image
img = np.zeros(mask.shape + (3,), np.uint8) + 255; img[inl] = (240, 236, 228); img[mask & inl & osm2] = (150, 150, 150); img[miss] = (200, 40, 40)
Image.fromarray(img[::4, ::4]).save('checks/coverage.png')
