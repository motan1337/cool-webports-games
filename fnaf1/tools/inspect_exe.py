import hashlib
import json
import re
import struct
from pathlib import Path
from game_input import GAME_EXE, load_game

root = Path(__file__).resolve().parents[2]
source = GAME_EXE
out = root / 'fnaf1' / 'analysis'
out.mkdir(parents=True, exist_ok=True)
data = load_game()
u16 = lambda p: struct.unpack_from('<H', data, p)[0]
u32 = lambda p: struct.unpack_from('<I', data, p)[0]
pe = u32(0x3C)
coff = pe + 4
optional = coff + 20
section_table = optional + u16(coff + 16)
sections = []
for i in range(u16(coff + 2)):
    p = section_table + 40 * i
    sections.append(dict(name=data[p:p+8].rstrip(b'\0').decode('ascii', 'replace'),
                         virtual_size=u32(p+8), rva=u32(p+12),
                         raw_size=u32(p+16), raw_offset=u32(p+20)))
end = max(s['raw_offset'] + s['raw_size'] for s in sections)
def file_offset(rva):
    for s in sections:
        if s['rva'] <= rva < s['rva'] + max(s['virtual_size'], s['raw_size']):
            return s['raw_offset'] + rva - s['rva']
    return rva
def cstring(p):
    return data[p:data.index(b'\0', p)].decode('ascii', 'replace')
directories = optional + (96 if u16(optional) == 0x10B else 112)
imports = []
import_rva = u32(directories + 8)
if import_rva:
    p = file_offset(import_rva)
    while any(data[p:p+20]):
        imports.append(cstring(file_offset(u32(p+12))))
        p += 20
markers = {}
for label, sig in {'clickteam': b'Clickteam', 'fusion': b'Fusion', 'MMF': b'MMF',
                   'PAMU': b'PAMU', 'PAME': b'PAME', 'PNG': b'\x89PNG\r\n\x1a\n',
                   'Ogg': b'OggS', 'RIFF': b'RIFF', 'ZIP': b'PK\x03\x04'}.items():
    positions = [m.start() for m in re.finditer(re.escape(sig), data)]
    markers[label] = {'count': len(positions), 'first_offsets': positions[:20]}
report = dict(source=str(source), size=len(data), sha256=hashlib.sha256(data).hexdigest(),
              machine=hex(u16(coff)), optional_magic=hex(u16(optional)),
              entry_rva=hex(u32(optional+16)), sections=sections, imports=imports,
              overlay_offset=end, overlay_size=len(data)-end,
              overlay_start_hex=data[end:end+128].hex(), markers=markers)
(out / 'binary-inventory.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
interesting = re.compile(rb'(?i)(clickteam|multimedia|fusion|\.mfx|\.dll|\.ogg|\.wav|\.png|\.mfa|\.ccn|http|copyright|freddy)')
lines = []
for match in re.finditer(rb'[\x20-\x7e]{5,}', data[:end]):
    if interesting.search(match.group()):
        lines.append(f'{match.start():08x} {match.group().decode("ascii")}')
(out / 'runtime-strings.txt').write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps(report, indent=2))
print('\nRuntime strings:\n' + '\n'.join(lines[:100]))
