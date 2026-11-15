# Adelaide in Sepia, step 1: OpenStreetMap's buildings inside the City of Adelaide (the council area: the city centre,
# North Adelaide and the Park Lands round them), each with the height the council's own 3D model gives it where the
# model covers it.
#   raw/osm_buildings.json   Overpass, buildings and building parts with their tags (ODbL)
#   raw/lga_adelaide.geojson ABS ASGS Edition 3 local government area 40070 (CC BY 4.0)
#   work/pts_*.npz           the council model as sample points (model_points.py; Data.SA, CC BY)
# -> work/osm_model.json     one row a building or part: tags, outline, area, and model_h / model_cover where measured
#
# The model's frame: metres east and north of its KML origin, turned 1.4 degrees clockwise (the heading three of the
# four KMZ files carry; align_check.py shows all four sit on OpenStreetMap's outlines with it, within 2 m). Its z is
# not a ground height (each block was moved to its own level), so a building's height is its roof above the lowest
# model surface close round it: the 90th percentile of the highest sample in each 1 m cell of the outline, less the
# 2nd percentile of the lowest samples within 8 m of it.
import json, glob, numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.ops import unary_union
from shapely import contains_xy
from pyproj import Transformer
LAT0, LNG0, HEAD = -34.90598031336, 138.5928082969, 1.4
T = Transformer.from_crs(4326, f'+proj=aeqd +lat_0={LAT0} +lon_0={LNG0} +ellps=GRS80 +units=m', always_xy=True)
lga = shape(json.load(open('raw/lga_adelaide.geojson'))['features'][0]['geometry'])
osm = json.load(open('raw/osm_buildings.json'))
def ring(g): return [(p['lon'], p['lat']) for p in g]
rows = []
for e in osm['elements']:
    t = e.get('tags', {})
    if e['type'] == 'way':
        r = ring(e.get('geometry', []))
        if len(r) < 4 or r[0] != r[-1]: continue
        poly = Polygon(r)
    else:
        outs = [ring(m['geometry']) for m in e.get('members', []) if m.get('role') == 'outer' and m.get('geometry')]
        inns = [ring(m['geometry']) for m in e.get('members', []) if m.get('role') == 'inner' and m.get('geometry')]
        outs = [o for o in outs if len(o) >= 4 and o[0] == o[-1]]; inns = [o for o in inns if len(o) >= 4 and o[0] == o[-1]]
        if not outs: continue
        polys = [Polygon(o, [i for i in inns if Polygon(o).contains(Polygon(i))]) for o in outs]
        poly = max(polys, key=lambda p: p.area) if len(polys) > 1 else polys[0]   # the largest outer ring (the others are small)
    if not poly.is_valid: poly = poly.buffer(0)
    if poly.is_empty or poly.geom_type != 'Polygon' or not lga.contains(poly.representative_point()): continue
    rows.append({'id': f"{e['type'][0]}{e['id']}", 'tags': t, 'poly': poly, 'part': 'building' not in t})
g = gpd.GeoDataFrame(rows, geometry=[r['poly'] for r in rows], crs=4326)
gl = g.geometry.apply(lambda p: Polygon([T.transform(*c) for c in p.exterior.coords], [[T.transform(*c) for c in i.coords] for i in p.interiors]))
g['area'] = gl.area
print('in the council area:', len(g), 'parts', int(g.part.sum()))
# the model: 1 m cells, highest and lowest sample
a = np.radians(HEAD); P = []
for f in sorted(glob.glob('work/pts_*.npz')):
    p = np.load(f)['p'].astype(np.float64)
    P.append(np.c_[p[:, 0] * np.cos(a) + p[:, 1] * np.sin(a), -p[:, 0] * np.sin(a) + p[:, 1] * np.cos(a), p[:, 2]])
P = np.concatenate(P)
x0, y0 = np.floor(P[:, 0].min()) - 20, np.floor(P[:, 1].min()) - 20
W, H = int(P[:, 0].max() - x0) + 21, int(P[:, 1].max() - y0) + 21
i, j = (P[:, 0] - x0).astype(int), (P[:, 1] - y0).astype(int); k = j * W + i
hi = np.full(W * H, -np.inf); lo = np.full(W * H, np.inf)
np.maximum.at(hi, k, P[:, 2]); np.minimum.at(lo, k, P[:, 2])
hi, lo = hi.reshape(H, W), lo.reshape(H, W)
print('model cells', int(np.isfinite(hi).sum()))
mh, mc = [], []
for poly in gl:
    bx0, by0, bx1, by1 = poly.bounds
    i0, i1, j0, j1 = max(0, int(bx0 - x0) - 9), min(W, int(bx1 - x0) + 10), max(0, int(by0 - y0) - 9), min(H, int(by1 - y0) + 10)
    if i1 <= i0 or j1 <= j0: mh.append(None); mc.append(0); continue
    gx, gy = np.meshgrid(x0 + np.arange(i0, i1) + 0.5, y0 + np.arange(j0, j1) + 0.5)
    inn = contains_xy(poly, gx, gy); near = contains_xy(poly.buffer(8), gx, gy)
    top = hi[j0:j1, i0:i1][inn]; top = top[np.isfinite(top)]; low = lo[j0:j1, i0:i1][near]; low = low[np.isfinite(low)]
    cover = len(top) / max(1, int(inn.sum()))
    if inn.sum() < 4 or cover < 0.3 or len(low) < 8: mh.append(None); mc.append(round(cover, 2)); continue
    mh.append(round(float(np.percentile(top, 90) - np.percentile(low, 2)), 1)); mc.append(round(cover, 2))
out = [{'id': r.id, 'part': bool(r.part), 'tags': r.tags, 'area': round(r.area, 1), 'model_h': mh[n], 'model_cover': mc[n],
        'ring': [[round(x, 7), round(y, 7)] for x, y in r.geometry.exterior.coords], 'holes': [[[round(x, 7), round(y, 7)] for x, y in i.coords] for i in r.geometry.interiors]} for n, r in enumerate(g.itertuples())]
json.dump({'osm_base': osm['osm3s']['timestamp_osm_base'], 'buildings': out}, open('work/osm_model.json', 'w'))
have = [o for o in out if o['model_h'] is not None]
print('with a model height:', len(have), 'of', len(out))
# check against OpenStreetMap's own heights and levels
import re
def num(v):
    m = re.match(r'\s*([0-9.]+)', str(v or '')); return float(m.group(1)) if m else None
hh = [(o['model_h'], num(o['tags'].get('height'))) for o in have if num(o['tags'].get('height'))]
ll = [(o['model_h'], 3 * num(o['tags'].get('building:levels'))) for o in have if num(o['tags'].get('building:levels')) and not o['part']]
for nm, v in [('height tag', hh), ('levels x 3', ll)]:
    v = np.array(v); d = v[:, 0] - v[:, 1]
    print(nm, len(v), 'median diff', round(float(np.median(d)), 1), 'median abs', round(float(np.median(abs(d))), 1), 'within 6 m', round(float((abs(d) <= 6).mean()), 3), 'corr', round(float(np.corrcoef(v.T)[0, 1]), 3))
top = sorted(have, key=lambda o: -o['model_h'])[:25]
for o in top: print(' ', o['model_h'], o['model_cover'], o['tags'].get('name'), o['tags'].get('height'), o['tags'].get('building:levels'), o['id'])
