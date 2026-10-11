import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'tools/python'))
import UnityPy

durations = {}
for obj in UnityPy.load(str(root / 'Kingdom_Data')).objects:
    if obj.type.name != 'AudioClip':
        continue
    data = obj.read_typetree()
    name, seconds = data['m_Name'], data['m_Length']
    if name in durations and abs(durations[name] - seconds) > 0.0001:
        raise ValueError('Ambiguous audio duration: ' + name)
    durations[name] = seconds
path = root / 'unity-web/Assets/Resources/KingdomAudioDurations.json'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({'clips': [{'name': name, 'seconds': seconds} for name, seconds in sorted(durations.items())]}))
print('Recorded durations for', len(durations), 'audio clips')
