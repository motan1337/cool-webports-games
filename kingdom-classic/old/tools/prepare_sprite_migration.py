import json
import math
from pathlib import Path
import re
import struct

root = Path(__file__).resolve().parents[1]
project = root / 'unity-web'
source = root / 'recovered/ExportedProject/Assets/Sprite'

def values(text, label):
    body = re.search(r'^    ' + label + r':\s*\n(.*?)(?=^    \w|\Z)', text, re.M | re.S)[1]
    return {k: float(v) for k, v in re.findall(r'(x|y|width|height): ([\d.eE+-]+)', body)}

items = []
for path in sorted(source.glob('*.asset')):
    text = path.read_text()
    texture = re.search(r'^    texture:.*guid: ([a-f0-9]{32})', text, re.M)[1]
    uv = [float(x) for x in re.search(r'uvTransform: \{x: ([^,]+), y: ([^,]+), z: ([^,]+), w: ([^}]+)', text).groups()]
    ppu = float(re.search(r'm_PixelsToUnits: (\S+)', text)[1])
    vertices = [[float(x), float(y)] for x, y in re.findall(r'pos: \{x: ([^,]+), y: ([^,]+)', text)]
    raw_indices = bytes.fromhex(re.search(r'^    indices: *(\w*)', text, re.M)[1])
    triangles = list(struct.unpack('<' + 'H' * (len(raw_indices) // 2), raw_indices))
    if not vertices or not triangles:
        print('Skipping empty original sprite', path.name)
        continue
    rectangle = values(text, 'textureRect')
    left = math.floor(min(rectangle['x'], *(v[0] * uv[0] + uv[1] for v in vertices)))
    bottom = math.floor(min(rectangle['y'], *(v[1] * uv[2] + uv[3] for v in vertices)))
    right = math.ceil(max(rectangle['x'] + rectangle['width'], *(v[0] * uv[0] + uv[1] for v in vertices)))
    top = math.ceil(max(rectangle['y'] + rectangle['height'], *(v[1] * uv[2] + uv[3] for v in vertices)))
    assert uv[0] == ppu and uv[2] == ppu, path
    assert max(triangles) < len(vertices) and len(triangles) % 3 == 0, path
    border = [float(x) for x in re.search(r'm_Border: \{x: ([^,]+), y: ([^,]+), z: ([^,]+), w: ([^}]+)', text).groups()]
    items.append({'path': 'Assets/Sprite/' + path.name, 'textureGuid': texture,
                  'name': re.search(r'm_Name: (.+)', text)[1], 'ppu': ppu,
                  'rect': [left, bottom, right - left, top - bottom],
                  'pivot': [(uv[1] - left) / (right - left), (uv[3] - bottom) / (top - bottom)],
                  'border': border, 'vertices': [{'x': x, 'y': y} for x, y in vertices], 'triangles': triangles})
(root / 'analysis/sprite-migration.json').write_text(json.dumps({'items': items}, separators=(',', ':')))
print('Prepared exact geometry and texture mapping for', len(items), 'sprites')
