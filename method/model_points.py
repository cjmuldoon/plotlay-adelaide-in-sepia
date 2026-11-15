# The City of Adelaide's 3D model (Data.SA "3D Model of the City of Adelaide", CC BY; SketchUp blocks exported as
# COLLADA in four KMZ files, July 2016) read into sample points: every triangle's corners, edge middles and centre, in
# the file's own frame in metres, with the mesh it belongs to and its height above that mesh's lowest point.
#   python model_points.py <dae> <out.npz>
import sys, numpy as np
import xml.etree.ElementTree as ET
dae, out = sys.argv[1:3]
NS = '{http://www.collada.org/2005/11/COLLADASchema}'
unit, top = 1.0, np.eye(4)
P, G, n = [], [], 0
for ev, el in ET.iterparse(dae, events=('end',)):
    t = el.tag
    if t == NS + 'unit': unit = float(el.get('meter'))
    elif t == NS + 'visual_scene':
        m = el.find(f'.//{NS}matrix')
        if m is not None: top = np.array(m.text.split(), float).reshape(4, 4)
        el.clear()
    elif t == NS + 'geometry':
        mesh = el.find(NS + 'mesh')
        if mesh is not None:
            src = {s.get('id'): s for s in mesh.findall(NS + 'source')}
            v = mesh.find(NS + 'vertices')
            pid = [i.get('source')[1:] for i in v.findall(NS + 'input') if i.get('semantic') == 'POSITION'][0]
            pos = np.array(src[pid].find(NS + 'float_array').text.split(), float).reshape(-1, 3)
            for tri in mesh.findall(NS + 'triangles'):
                ins = tri.findall(NS + 'input'); stride = max(int(i.get('offset')) for i in ins) + 1
                voff = [int(i.get('offset')) for i in ins if i.get('semantic') == 'VERTEX'][0]
                p = tri.find(NS + 'p')
                if p is None or not p.text: continue
                idx = np.array(p.text.split(), int).reshape(-1, stride)[:, voff].reshape(-1, 3)
                a, b, c = pos[idx[:, 0]], pos[idx[:, 1]], pos[idx[:, 2]]
                pts = np.concatenate([a, b, c, (a + b) / 2, (b + c) / 2, (a + c) / 2, (a + b + c) / 3, (4 * a + b + c) / 6, (a + 4 * b + c) / 6, (a + b + 4 * c) / 6])
                P.append(pts); G.append(np.full(len(pts), n, np.int32))
            n += 1
        el.clear()
P = np.concatenate(P); G = np.concatenate(G)
P = (np.c_[P, np.ones(len(P))] @ top.T)[:, :3] * unit
np.savez_compressed(out, p=P.astype(np.float32), g=G)
print(dae, 'unit', unit, 'top', top[0, 0], 'meshes', n, 'points', len(P), 'x', P[:, 0].min(), P[:, 0].max(), 'y', P[:, 1].min(), P[:, 1].max(), 'z', np.percentile(P[:, 2], [0, 1, 50, 99, 100]))
