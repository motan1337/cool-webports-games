import argparse
import gzip
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--pages', type=Path, default=root / 'pages')
pages = parser.parse_args().pages.resolve()
framework = gzip.decompress(next((pages / 'game/Build').glob('*.framework.js.unityweb')).read_bytes()).decode()
html = (pages / 'game/index.html').read_text()
for token in ['kingdomHammerAudio', 'KingdomBeginGameplayChecks', 'KingdomReportGameplayChecks', 'gameplay-check-results']:
    assert token not in framework, 'Development bridge in release: ' + token
for token in ['<button', "SendMessage('KingdomGameplayChecks'", 'data-test-key']:
    assert token not in html, 'Development control in release: ' + token
manifest = json.loads((pages / 'asset-manifest.json').read_text())
for relative, entry in manifest['files'].items():
    digest = hashlib.sha256()
    size = 0
    for part in entry['parts']:
        data = (pages / part['path']).read_bytes()
        assert len(data) == part['bytes']
        assert hashlib.sha256(data).hexdigest() == part['sha256']
        digest.update(data)
        size += len(data)
    assert size == entry['bytes'] and digest.hexdigest() == entry['sha256']
with zipfile.ZipFile(pages.with_suffix('.zip')) as archive:
    assert archive.testzip() is None
    for path in pages.rglob('*'):
        if path.is_file():
            assert archive.read(path.relative_to(pages).as_posix()) == path.read_bytes()
report = {'buildId': manifest['buildId'], 'releaseDiagnosticsExcluded': True, 'segmentIntegrity': True,
          'zipMatchesFolder': True, 'zipBytes': pages.with_suffix('.zip').stat().st_size}
(root / 'analysis/gameplay-release-verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
