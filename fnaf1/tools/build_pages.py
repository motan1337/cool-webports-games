import base64
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = root / 'pages'
output.mkdir(exist_ok=True)
html = (root / 'play.html').read_text(encoding='utf-8')
script_hashes = []

def inline_script(match):
    source = (root / match.group(1)).read_text(encoding='utf-8')
    source = re.sub(r'</script', r'<\\/script', source, flags=re.I)
    digest = base64.b64encode(hashlib.sha256(source.encode('utf-8')).digest()).decode()
    script_hashes.append("'sha256-" + digest + "'")
    return '<script>' + source + '</script>'

html = re.sub(r'<script src="([^"]+)"></script>', inline_script, html)
style = re.search(r'<style>(.*?)</style>', html, re.S).group(1)
style_hash = base64.b64encode(hashlib.sha256(style.encode('utf-8')).digest()).decode()
csp = ("default-src 'none'; script-src " + ' '.join(script_hashes)
       + "; style-src 'sha256-" + style_hash + "'; img-src 'self'; connect-src 'self';"
       + " media-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
meta_csp = csp.replace(" frame-ancestors 'none';", '')
html = html.replace('  <title>', '  <meta http-equiv="Content-Security-Policy" content="' + meta_csp + '">\n  <title>', 1)
(output / 'index.html').write_text(html, encoding='utf-8')
(output / '_headers').write_text(
    '/*\n  Content-Security-Policy: ' + csp
    + '\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n', encoding='utf-8')

files = [output / 'index.html', output / '_headers']
for folder in ('extracted/images', 'extracted/audio'):
    for source in sorted((root / folder).iterdir()):
        if not source.is_file():
            continue
        target = output / folder / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files.append(target)

assert len(files) < 1000, 'Dashboard Direct Upload supports at most 1000 files'
assert max(p.stat().st_size for p in files) <= 25 * 1024 * 1024
assert '<script src=' not in html
assert not any(token in html for token in ('serviceWorker', 'CACHE_GAME', 'save-file', 'Export save', 'Import save', 'Keep offline'))
data = json.loads((root / 'analysis/game-data.json').read_text(encoding='utf-8'))
assert all((output / sample['path']).is_file() for sample in data['sounds'])
assert all((output / 'extracted/images' / f"{image['handle']:04}.png").is_file() for image in data['images'])
assert set(p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()) == set(p.relative_to(output).as_posix() for p in files), 'Unexpected deploy files'
report = dict(file_count=len(files), html_bytes=(output / 'index.html').stat().st_size,
              largest_file_bytes=max(p.stat().st_size for p in files),
              total_bytes=sum(p.stat().st_size for p in files),
              scripts_inlined=len(script_hashes), images=len(data['images']), sounds=len(data['sounds']))
(root / 'analysis/pages-build.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
archive_path = root / 'dist/fnaf1-pages.zip'
archive_path.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for file in files:
        archive.write(file, file.relative_to(output).as_posix())
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
print(json.dumps(report, indent=2))
print('Pages folder:', output)
print('Upload ZIP:', archive_path)
