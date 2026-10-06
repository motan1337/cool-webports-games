import hashlib
import json
import re
import struct
import zlib
from pathlib import Path
from game_input import GAME_EXE, load_game

root = Path(__file__).resolve().parents[2]
source = load_game()
inventory = json.loads((root / 'fnaf1/analysis/chunk-inventory.json').read_text())
out = root / 'fnaf1/extracted'
out.mkdir(parents=True, exist_ok=True)

def inflate(data):
    return zlib.decompress(data, 15 if data[:1] == b'\x78' else -15)

key_table = None

def transform(data):
    table = key_table.copy()
    i = j = 0
    result = bytearray()
    for value in data:
        i = (i+1) & 255
        j = (j+table[i]) & 255
        table[i], table[j] = table[j], table[i]
        result.append(value ^ table[(table[i]+table[j]) & 255])
    return bytes(result)

def decode(flags, data):
    if flags == 0:
        return data
    if flags == 1:
        expected, size = struct.unpack_from('<II', data)
        assert size == len(data)-8
        result = inflate(data[8:])
        assert len(result) == expected
        return result
    if flags == 3 and key_table is not None:
        expected = struct.unpack_from('<I', data)[0]
        decrypted = transform(data[4:])
        size = struct.unpack_from('<I', decrypted)[0]
        assert size == len(decrypted)-4
        result = inflate(decrypted[4:])
        assert len(result) == expected
        return result
    if flags == 2 and key_table is not None:
        return transform(data)
    return None

strings = {}
for chunk in inventory['chunks']:
    if chunk['id'] in ('2224', '222e', '223b'):
        p = chunk['offset']+8
        strings[chunk['id']] = decode(chunk['flags'], source[p:p+chunk['size']]).decode('utf-16le').rstrip('\0')
key_bytes = bytes(b for value in (strings.get('222e', ''), strings.get('2224', ''), strings.get('223b', ''))
                  for b in value.encode('utf-16le') if b)
key = bytearray(key_bytes[:128].ljust(256, b'\0'))
key[len(key_bytes)+1] = (sum(key_bytes)*2) & 255
key_table = list(range(256))
j = k = 0
for i in range(256):
    if key[k] == 0:
        k = 0
    j = (j+key[k]+key_table[i]) & 255
    k = (k+1) & 255
    key_table[i], key_table[j] = key_table[j], key_table[i]

frames, sounds, images = [], [], []
for chunk in inventory['chunks']:
    start = chunk['offset']+8
    data = source[start:start+chunk['size']]
    chunk_id = int(chunk['id'], 16)
    if chunk_id == 0x3333:
        frame_dir = out / 'frames' / f'{len(frames):02d}'
        frame_dir.mkdir(parents=True, exist_ok=True)
        frame = dict(index=len(frames), chunks=[])
        pos = 0
        while pos+8 <= len(data):
            cid, flags, size = struct.unpack_from('<HHI', data, pos)
            assert pos+8+size <= len(data)
            raw = data[pos+8:pos+8+size]
            decoded = decode(flags, raw)
            path = frame_dir / f'{len(frame["chunks"]):02d}-{cid:04x}.bin'
            path.write_bytes(raw if decoded is None else decoded)
            frame['chunks'].append(dict(id=f'{cid:04x}', flags=flags, packed_size=size,
                                        decoded=decoded is not None, file=str(path)))
            if cid == 0x3335 and decoded is not None:
                frame['name'] = decoded.decode('utf-16le').rstrip('\0')
            if cid == 0x3334 and decoded is not None:
                frame['width'], frame['height'] = struct.unpack_from('<ii', decoded)
            pos += size+8
        assert pos == len(data)
        frames.append(frame)
    elif chunk_id == 0x6668:
        audio_dir = out / 'audio'
        audio_dir.mkdir(exist_ok=True)
        count = struct.unpack_from('<I', data)[0]
        pos = 4
        for _ in range(count):
            handle, checksum, refs, expected, flags, frequency, name_length = struct.unpack_from('<7I', data, pos)
            pos += 28
            if flags & 32:
                sample = data[pos:pos+expected]
                pos += expected
            else:
                size = struct.unpack_from('<I', data, pos)[0]
                pos += 4
                sample = inflate(data[pos:pos+size])
                pos += size
                assert len(sample) == expected
            name = sample[:name_length*2].decode('utf-16le').rstrip('\0')
            audio = sample if flags & 32 else sample[name_length*2:]
            suffix = '.wav' if audio[:4] == b'RIFF' else '.ogg' if audio[:4] == b'OggS' else '.bin'
            safe = re.sub(r'[^A-Za-z0-9._-]+', '_', name).strip('._')[:100] or 'sound'
            path = audio_dir / f'{handle-1:04d}-{safe}{suffix}'
            path.write_bytes(audio)
            sounds.append(dict(handle=handle-1, name=name, frequency=frequency, flags=flags,
                               size=len(audio), sha256=hashlib.sha256(audio).hexdigest(), file=str(path)))
        assert pos == len(data), (pos, len(data))
    elif chunk_id == 0x6666:
        count = struct.unpack_from('<I', data)[0]
        pos = 4
        for _ in range(count):
            offset = pos
            handle, expected, size = struct.unpack_from('<III', data, pos)
            pos += 12
            image = inflate(data[pos:pos+size])
            pos += size
            assert len(image) == expected
            checksum, refs, data_size, width, height, mode, flags = struct.unpack_from('<IIIhhBB', image)
            hotspot_x, hotspot_y, action_x, action_y = struct.unpack_from('<hhhh', image, 20)
            images.append(dict(handle=handle-1, bank_offset=offset, packed_size=size,
                               decoded_size=expected, pixel_data_size=data_size,
                               width=width, height=height, mode=mode, flags=flags,
                               hotspot=[hotspot_x, hotspot_y], action_point=[action_x, action_y]))
        assert pos == len(data), (pos, len(data))

report = dict(frames=frames, sounds=sounds, images=images)
(root / 'fnaf1/analysis/extraction-inventory.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('Frames:', len(frames), 'Images inspected:', len(images), 'Audio extracted:', len(sounds))
print('Frame names:', ascii([f.get('name', '(encoded)') for f in frames]))
print('Image modes:', sorted(set((i['mode'], i['flags']) for i in images)))
print('Audio types:', sorted(set(Path(s['file']).suffix for s in sounds)))
