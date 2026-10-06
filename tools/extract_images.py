import binascii
import hashlib
import json
import struct
import zlib
from pathlib import Path
from game_input import GAME_EXE, load_game

root = Path(__file__).resolve().parents[2]
source = load_game()
chunks = json.loads((root / 'fnaf1/analysis/chunk-inventory.json').read_text())['chunks']
report_path = root / 'fnaf1/analysis/extraction-inventory.json'
report = json.loads(report_path.read_text())
bank = next(c for c in chunks if c['id'] == '6666')
bank_start = bank['offset']+8
out = root / 'fnaf1/extracted/images'
out.mkdir(parents=True, exist_ok=True)

def png_chunk(kind, payload):
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', binascii.crc32(kind+payload) & 0xFFFFFFFF)

for item in report['images']:
    pos = bank_start + item['bank_offset'] + 12
    raw = zlib.decompress(source[pos:pos+item['packed_size']])
    width, height = item['width'], item['height']
    assert item['mode'] == 4 and item['flags'] in (0, 16)
    alpha = bool(item['flags'] & 16)
    colors = raw[32:32+item['pixel_data_size']]
    color_stride = width*3 + (width*3 % 2)*3
    alpha_stride = width + (-width % 4)
    expected = height * (color_stride + (alpha_stride if alpha else 0))
    assert len(colors) == expected, (item['handle'], len(colors), expected)
    channels = 4 if alpha else 3
    scan = bytearray((width*channels+1)*height)
    for y in range(height):
        row = bytearray(width*channels)
        bgr = colors[y*color_stride:y*color_stride+width*3]
        row[0::channels] = bgr[2::3]
        row[1::channels] = bgr[1::3]
        row[2::channels] = bgr[0::3]
        if alpha:
            ap = color_stride*height+y*alpha_stride
            row[3::4] = colors[ap:ap+width]
        p = y*(width*channels+1)+1
        scan[p:p+len(row)] = row
    png = b'\x89PNG\r\n\x1a\n'
    png += png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6 if alpha else 2, 0, 0, 0))
    if not alpha:
        png += png_chunk(b'tRNS', struct.pack('>HHH', *raw[28:31]))
    png += png_chunk(b'IDAT', zlib.compress(scan, 6)) + png_chunk(b'IEND', b'')
    path = out / f'{item["handle"]:04d}.png'
    path.write_bytes(png)
    item['file'] = str(path)
    item['sha256'] = hashlib.sha256(png).hexdigest()
report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('Exported', len(report['images']), 'PNGs to', out)
