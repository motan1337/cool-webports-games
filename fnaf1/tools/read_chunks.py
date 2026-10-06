import json
import struct
import zlib
from pathlib import Path
from game_input import GAME_EXE, load_game

root = Path(__file__).resolve().parents[2]
data = load_game()
out = root / 'fnaf1' / 'analysis'
start = 2341701
assert data[start:start+4] == b'PAMU'
pos = start + 16
rows = []
while pos + 8 <= len(data):
    chunk_id, flags, size = struct.unpack_from('<HHI', data, pos)
    if size > len(data) - pos - 8:
        raise ValueError(f'Chunk extends beyond file at {pos:#x}')
    payload = data[pos+8:pos+8+size]
    row = dict(offset=pos, id=f'{chunk_id:04x}', flags=flags, size=size)
    if flags == 1:
        expected, packed = struct.unpack_from('<II', payload)
        try:
            payload = zlib.decompress(payload[8:])
            row['decoded_size'] = len(payload)
            row['size_matches'] = len(payload) == expected
        except zlib.error as exc:
            row['decode_error'] = str(exc)
    if len(payload) < 1024:
        row['preview_hex'] = payload[:180].hex()
        row['preview_utf16'] = payload[:180-len(payload[:180])%2].decode('utf-16le', 'replace')
    rows.append(row)
    pos += 8 + size
    if chunk_id == 0x7F7F:
        break
report = dict(signature_offset=start, header_hex=data[start:start+16].hex(),
              end_offset=pos, trailing_bytes=len(data)-pos, chunks=rows)
(out / 'chunk-inventory.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
for row in rows:
    print(row['id'], row['flags'], row['size'], ascii(row.get('preview_utf16', '')))
print('Chunks:', len(rows), 'Trailing bytes:', len(data)-pos)
