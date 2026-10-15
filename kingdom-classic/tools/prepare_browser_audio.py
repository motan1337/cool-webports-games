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

ambient = {'crickets_v2', 'forest_wind_v2', 'kingdom_bustle', 'nature_1', 'nature_2', 'rain', 'summer_meadow', 'wind'}
for clip in sorted((assets / 'AudioClip').glob('*.ogg')):
    path = clip.with_suffix('.ogg.meta')
    original = path.read_text()
    decoded = clip.stem in ambient
    text = re.sub(r'(?m)^(\s*)loadType: \d+', r'\g<1>loadType: ' + ('0' if decoded else '1'), original)
    text = re.sub(r'(?m)^(\s*)preloadAudioData: \d+', r'\g<1>preloadAudioData: ' + ('1' if decoded else '0'), text)
    text = re.sub(r'(?m)^(\s*)loadInBackground: \d+', r'\g<1>loadInBackground: ' + ('0' if decoded else '1'), text)
    text = re.sub(r'(?m)^(\s*)quality: [\d.]+', r'\g<1>quality: 0.7', text)
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
path = assets / 'AudioMixerController/Ambient Mixer.mixer'
text = path.read_text()
start = text.index('  m_ExposedParameters:')
end = text.index('  m_AudioMixerGroupViews:', start)
entries = [
    ('a2ce5e3b2d477974c910f43d54a67172', 'WindVol'),
    ('05b3bd6b7ece0aa4a9d1ed2476a1c830', 'ForestWindVol'),
    ('d45cb0c2627b8a84096140917c1aedd7', 'RainVol'),
    ('1bcbb82fba095a6459982849f36b62d5', 'MeadowVol'),
    ('6fa7d8b3bd7dd9d4baa51500e204a4e7', 'ForestVol')
]
text = text[:start] + '  m_ExposedParameters:\n' + ''.join('  - guid: ' + guid + '\n    name: ' + name + '\n' for guid, name in entries) + text[end:]
path.write_text(text)
changes.append(path.relative_to(assets).as_posix())
report = {'changed': changes, 'shortEffectDecodedBytes': decoded_bytes,
          'longClips': 'Music uses compressed-in-memory async loading; eight looping ambient clips preload decoded.'}
(root / 'analysis/browser-audio-import.json').write_text(json.dumps(report, indent=2))
print('Updated', len(changes), 'audio assets; short effect PCM budget', decoded_bytes)
