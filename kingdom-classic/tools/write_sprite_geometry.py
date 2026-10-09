import json
from pathlib import Path
import re
import struct
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'tools/python'))
from PIL import Image

project = root / 'unity-web'
textures = {}
for meta in (project / 'Assets/Texture2D').glob('*.meta'):
    guid = re.search(r'^guid: (\w+)', meta.read_text(), re.M)[1]
    textures[guid] = meta.with_suffix('')

report = []
for item in json.loads((root / 'analysis/sprite-migration.json').read_text())['items']:
    path = project / item['path']
    text = path.read_text()
    assert 'm_VertexData:' in text, path
    with Image.open(textures[item['textureGuid']]) as image:
        width, height = image.size
    original = (root / 'recovered/ExportedProject' / item['path']).read_text()
    scale_x, pivot_x, scale_y, pivot_y = [float(x) for x in re.search(r'uvTransform: \{x: ([^,]+), y: ([^,]+), z: ([^,]+), w: ([^}]+)', original).groups()]
    if item.get('empty'):
        scale_x, pivot_x, scale_y, pivot_y = item['ppu'], 0.5, item['ppu'], 0.5
    points = item['vertices']
    positions = b''.join(struct.pack('<fff', v['x'], v['y'], 0) for v in points)
    positions += bytes((-len(positions)) % 16)
    uv = b''.join(struct.pack('<ff', (v['x'] * scale_x + pivot_x) / width, (v['y'] * scale_y + pivot_y) / height) for v in points)
    buffer = positions + uv
    indices = struct.pack('<' + 'H' * len(item['triangles']), *item['triangles'])
    for label, value in [('vertexCount', len(points)), ('m_VertexCount', len(points)), ('indexCount', len(item['triangles'])), ('m_DataSize', len(buffer))]:
        text = re.sub(r'(' + label + r': )\d+', lambda m: m[1] + str(value), text)
    text = re.sub(r'(m_IndexBuffer: )\w+', lambda m: m[1] + indices.hex(), text)
    text = re.sub(r'(_typelessdata: )\w+', lambda m: m[1] + buffer.hex(), text)
    min_x, max_x = min(v['x'] for v in points), max(v['x'] for v in points)
    min_y, max_y = min(v['y'] for v in points), max(v['y'] for v in points)
    bounds = 'm_Center: {x: %.9g, y: %.9g, z: 0}\n        m_Extent: {x: %.9g, y: %.9g, z: 0}' % ((min_x + max_x) / 2, (min_y + max_y) / 2, (max_x - min_x) / 2, (max_y - min_y) / 2)
    text = re.sub(r'm_Center: \{[^}]+\}\n        m_Extent: \{[^}]+\}', bounds, text)
    path.write_text(text)
    report.append({'path': item['path'], 'vertices': len(points), 'triangles': len(item['triangles']) // 3, 'bufferBytes': len(buffer)})
(root / 'analysis/sprite-geometry-validation.json').write_text(json.dumps(report, indent=2))
print('Persisted exact geometry and UVs for', len(report), 'sprites')
