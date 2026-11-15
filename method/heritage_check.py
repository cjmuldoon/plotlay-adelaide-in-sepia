# SA Heritage Places (Data.SA, Department for Housing and Urban Development, CC BY): what does it say about when a
# place was built? Only the listing's own fields and free text; nothing here infers a year.
import json, re, collections
import geopandas as gpd
from shapely.geometry import shape
lga = shape(json.load(open('raw/lga_adelaide.geojson'))['features'][0]['geometry'])
g = gpd.read_file('raw/heritage/SAHeritagePlacesPoly_GDA2020.geojson')
print(len(g), g.columns.tolist())
a = g[g.geometry.representative_point().within(lga)].copy()
print('in the council area:', len(a))
for c in a.columns:
    if c == 'geometry': continue
    v = a[c].dropna(); v = v[v.astype(str).str.strip() != '']
    print(f'  {c}: filled {len(v)}, distinct {v.nunique()}, e.g. {[str(x)[:70] for x in v.unique()[:4]]}')
a.drop(columns='geometry').to_csv('work/heritage_adelaide.csv', index=False)
