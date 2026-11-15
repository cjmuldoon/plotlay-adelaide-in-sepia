# Does the model sit on OpenStreetMap's footprints? Rasterise both at 2 m and find the best heading and shift.
import sys, json, numpy as np
from shapely.geometry import Polygon
from shapely import contains_xy
npz, = sys.argv[1:2]
LAT0, LNG0 = -34.90598031336, 138.5928082969
kx, ky = 111320 * np.cos(np.radians(LAT0)), 110922.0   # metres a degree at this latitude (GRS80, near enough for a check)
d = np.load(npz); P = d['p']
osm = json.load(open('raw/osm_buildings.json'))['elements']
x0, x1, y0, y1 = P[:, 0].min() - 100, P[:, 0].max() + 100, P[:, 1].min() - 100, P[:, 1].max() + 100
W, H = int((x1 - x0) / 2), int((y1 - y0) / 2)
gx, gy = np.meshgrid(x0 + 2 * np.arange(W) + 1, y0 + 2 * np.arange(H) + 1)
A = np.zeros((H, W), bool)
for e in osm:
    if e['type'] != 'way' or 'geometry' not in e: continue
    xy = [((g['lon'] - LNG0) * kx, (g['lat'] - LAT0) * ky) for g in e['geometry']]
    if len(xy) < 4: continue
    xs, ys = zip(*xy)
    if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1: continue
    i0, i1, j0, j1 = max(0, int((min(xs) - x0) / 2)), min(W, int((max(xs) - x0) / 2) + 1), max(0, int((min(ys) - y0) / 2)), min(H, int((max(ys) - y0) / 2) + 1)
    if i1 <= i0 or j1 <= j0: continue
    A[j0:j1, i0:i1] |= contains_xy(Polygon(xy), gx[j0:j1, i0:i1], gy[j0:j1, i0:i1])
print('osm cells', A.sum())
FA = np.fft.rfft2(A.astype(np.float32))
for hd in [0, 1.30667, 1.4, -1.30667, -1.4]:
    a = np.radians(hd)   # KML heading: clockwise from north
    X = P[:, 0] * np.cos(a) + P[:, 1] * np.sin(a); Y = -P[:, 0] * np.sin(a) + P[:, 1] * np.cos(a)
    B = np.zeros((H, W), np.float32)
    i, j = ((X - x0) / 2).astype(int), ((Y - y0) / 2).astype(int); ok = (i >= 0) & (i < W) & (j >= 0) & (j < H)
    B[j[ok], i[ok]] = 1
    c = np.fft.irfft2(FA * np.conj(np.fft.rfft2(B)), s=A.shape)
    k = np.unravel_index(c.argmax(), c.shape); dy, dx = [(v if v < n / 2 else v - n) * 2 for v, n in zip(k, c.shape)]
    print('heading', hd, 'best shift m (dx, dy)', dx, dy, 'overlap', round(float(c.max() / B.sum()), 3), 'no shift', round(float((A & (B > 0)).sum() / B.sum()), 3))
