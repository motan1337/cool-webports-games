import json
import struct
from pathlib import Path

root = Path(__file__).resolve().parents[2]
report = json.loads((root / 'fnaf1/analysis/extraction-inventory.json').read_text())
frames = []
for frame in report['frames']:
    chunk = next((c for c in frame['chunks'] if c['id'] == '333d'), None)
    if not chunk:
        continue
    data = Path(chunk['file']).read_bytes()
    marker = data.index(b'ERev')
    size = struct.unpack_from('<I', data, marker+4)[0]
    pos = marker+8
    end = marker+8+size
    events = []
    while pos < end:
        length = abs(struct.unpack_from('<h', data, pos)[0])
        assert length >= 16 and pos+length <= end, (frame['index'], pos, length, end)
        events.append(dict(offset=pos, size=length, conditions=data[pos+2],
                           actions=data[pos+3], flags=struct.unpack_from('<H', data, pos+4)[0]))
        pos += length
    assert pos == end
    frames.append(dict(index=frame['index'], name=frame['name'], event_count=len(events),
                       condition_count=sum(e['conditions'] for e in events),
                       action_count=sum(e['actions'] for e in events), events=events))
(root / 'fnaf1/analysis/event-inventory.json').write_text(json.dumps(frames, indent=2), encoding='utf-8')
for frame in frames:
    print(frame['index'], frame['name'], frame['event_count'], 'event groups')
