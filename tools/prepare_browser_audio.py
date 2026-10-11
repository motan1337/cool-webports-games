import json
from pathlib import Path
import re
import wave

root = Path(__file__).resolve().parents[1]
assets = root / 'unity-web/Assets'
changes = []
decoded_bytes = 0
for clip in sorted((assets / 'AudioClip').glob('*.wav')):
    with wave.open(str(clip), 'rb') as audio:
        duration = audio.getnframes() / audio.getframerate()
        if duration > 20:
            continue
        decoded_bytes += audio.getnframes() * audio.getnchannels() * 4
    path = clip.with_suffix(clip.suffix + '.meta')
    original = path.read_text()
    text = re.sub(r'(?m)^(\s*)loadType: \d+', r'\g<1>loadType: 0', original)
    text = re.sub(r'(?m)^(\s*)preloadAudioData: \d+', r'\g<1>preloadAudioData: 1', text)
    text = re.sub(r'(?m)^(\s*)loadInBackground: \d+', r'\g<1>loadInBackground: 0', text)
    if text != original:
        path.write_text(text)
        changes.append(path.relative_to(assets).as_posix())

path = assets / 'AudioMixerController/Main Mixer.mixer'
text = path.read_text()
start = text.index('  m_ExposedParameters:')
end = text.index('  m_AudioMixerGroupViews:', start)
entries = [
    ('53bdcf663c27f594788d8c4b2ed9a463', 'MasterVol'),
    ('9cefe013409ed9b4b8f733b3363012a6', 'MusicVol'),
    ('c53eb3a464a519842902da672133491f', 'EffectsVol'),
    ('56fd79deb20204c4198aa59d13770824', 'AmbientVol'),
    ('d59811e08dd950646bbc6e7d89864263', 'UIVol')
]
text = text[:start] + '  m_ExposedParameters:\n' + ''.join('  - guid: ' + guid + '\n    name: ' + name + '\n' for guid, name in entries) + text[end:]
path.write_text(text)
changes.append(path.relative_to(assets).as_posix())
report = {'changed': changes, 'shortEffectDecodedBytes': decoded_bytes,
          'longClips': 'Retain compressed import settings; playback waits for readiness.'}
(root / 'analysis/browser-audio-import.json').write_text(json.dumps(report, indent=2))
print('Updated', len(changes), 'audio assets; short effect PCM budget', decoded_bytes)
