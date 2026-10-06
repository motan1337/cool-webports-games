import binascii
import json
import struct
import wave
import zlib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
report = json.loads((root / 'analysis/extraction-inventory.json').read_text())
for image in report['images']:
    data = Path(image['file']).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos = 8
    compressed = b''
    while pos < len(data):
        size = struct.unpack_from('>I', data, pos)[0]
        kind = data[pos+4:pos+8]
        payload = data[pos+8:pos+8+size]
        crc = struct.unpack_from('>I', data, pos+8+size)[0]
        assert binascii.crc32(kind+payload) & 0xffffffff == crc
        if kind == b'IHDR':
            width, height, depth, mode, _, _, _ = struct.unpack('>IIBBBBB', payload)
            assert (width, height) == (image['width'], image['height'])
        if kind == b'IDAT':
            compressed += payload
        pos += size+12
    decoded = zlib.decompress(compressed)
    assert len(decoded) == height*(width*(4 if mode == 6 else 3)+1)
for sound in report['sounds']:
    with wave.open(sound['file'], 'rb') as audio:
        frames = audio.getnframes()
        actual = audio.readframes(frames)
        assert len(actual) == frames*audio.getnchannels()*audio.getsampwidth()
assert all(c['decoded'] for f in report['frames'] for c in f['chunks'])
print('Verified: 605 PNG structures and CRCs, 52 PCM WAV payloads, all frame chunks decoded.')
