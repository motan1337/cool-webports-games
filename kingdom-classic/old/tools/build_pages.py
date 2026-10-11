import argparse
import base64
import hashlib
import json
import mimetypes
import re
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 25 * 1024 * 1024
CHUNK_SIZE = 16 * 1024 * 1024
parser = argparse.ArgumentParser()
parser.add_argument('--build', type=Path, default=ROOT / 'build/webgl-release')
parser.add_argument('--output', type=Path, default=ROOT / 'pages')
args = parser.parse_args()
source = args.build.resolve()
target = args.output.resolve()
if not (source / 'index.html').is_file():
    raise SystemExit('No compiled Unity WebGL index.html at ' + str(source) + '. Build the game before packaging it.')
files = sorted(p for p in source.rglob('*') if p.is_file())
if not any(p.suffix in ['.wasm', '.js', '.jsgz'] for p in files):
    raise SystemExit('No Unity JavaScript or WebAssembly runtime found.')
if any(p.suffix in ['.br', '.gz'] for p in files):
    raise SystemExit('Use disabled Unity compression, or Unity decompression fallback (.unityweb). HTTP-compressed .br/.gz files need a separate loader adaptation.')
if source == target or source in target.parents or target in source.parents:
    raise SystemExit('Build and Pages output folders must be separate.')
if target.exists():
    raise SystemExit('Output folder already exists. Choose a new output path to preserve the previous build.')
archive = target.parent / (target.name + '.zip')
if archive.exists():
    raise SystemExit('ZIP already exists. Choose a new output path.')
target.mkdir(parents=True)
manifest = {'files': {}}
all_files = []
for p in files:
    relative = 'game/' + p.relative_to(source).as_posix()
    digest = hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
    all_files.append({'path': relative, 'bytes': p.stat().st_size, 'sha256': digest})
    if p.stat().st_size <= LIMIT:
        out = target / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)
        continue
    entry = {'bytes': p.stat().st_size, 'sha256': digest,
             'contentType': 'application/wasm' if p.suffix == '.wasm' else mimetypes.guess_type(p.name)[0] or 'application/octet-stream',
             'parts': []}
    with p.open('rb') as stream:
        i = 0
        while data := stream.read(CHUNK_SIZE):
            path = 'segments/' + digest + '.%04d.bin' % i
            out = target / path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            entry['parts'].append({'path': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
            i += 1
    manifest['files'][relative] = entry
templates = sorted(p for p in (ROOT / 'tools/pages').rglob('*') if p.is_file())
template_hashes = [(p.relative_to(ROOT / 'tools/pages').as_posix(), hashlib.sha256(p.read_bytes()).hexdigest()) for p in templates]
build_id = hashlib.sha256(json.dumps([all_files, template_hashes, 'security-policy-v1'], sort_keys=True).encode()).hexdigest()[:20]
manifest['buildId'] = build_id
(target / 'asset-manifest.json').write_text(json.dumps(manifest, separators=(',', ':')), encoding='utf-8')
for p in templates:
    destination = target / p.relative_to(ROOT / 'tools/pages')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix in ['.js', '.html', '.css', '.json']:
        destination.write_text(p.read_text(encoding='utf-8').replace('__BUILD_ID__', build_id), encoding='utf-8')
    else:
        shutil.copy2(p, destination)
inline_scripts = set()
inline_styles = set()
for html in target.rglob('*.html'):
    text = html.read_bytes().decode('utf-8')
    for tag, hashes in [('script', inline_scripts), ('style', inline_styles)]:
        for attributes, body in re.findall(r'<' + tag + r'\b([^>]*)>(.*?)</' + tag + r'\s*>', text, re.I | re.S):
            if tag == 'script' and re.search(r'\bsrc\s*=', attributes, re.I):
                continue
            normalized = body.replace('\r\n', '\n').replace('\r', '\n')
            hashes.add("'sha256-" + base64.b64encode(hashlib.sha256(normalized.encode()).digest()).decode() + "'")
policy = "; ".join([
    "default-src 'none'",
    "script-src 'self' blob: 'wasm-unsafe-eval' " + ' '.join(sorted(inline_scripts)),
    "script-src-attr 'none'",
    "style-src 'self' " + ' '.join(sorted(inline_styles)),
    "style-src-attr 'none'",
    "connect-src 'self'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    "media-src 'self' blob:",
    "worker-src 'self' blob:",
    "frame-src 'self'",
    "frame-ancestors 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'"
])
(target / '_headers').write_text('''/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: same-origin
  X-Frame-Options: SAMEORIGIN
  Cache-Control: no-cache
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
  Content-Security-Policy: ''' + policy + '\n', encoding='utf-8')
published = sorted(p for p in target.rglob('*') if p.is_file())
oversize = [str(p) for p in published if p.stat().st_size > LIMIT]
if oversize or len(published) > 1000:
    raise SystemExit('Dashboard upload limits exceeded: ' + str(oversize) + ', file count ' + str(len(published)))
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in published:
        z.write(p, p.relative_to(target).as_posix())
with zipfile.ZipFile(archive) as z:
    if z.testzip():
        raise SystemExit('ZIP integrity check failed.')
report = {'buildId': build_id, 'source': str(source), 'output': str(target), 'zip': str(archive),
          'content_security_policy': policy,
          'files': len(published), 'largest_file': max(p.stat().st_size for p in published),
          'segmented_files': len(manifest['files']), 'original_files': all_files}
report_path = ROOT / 'analysis' / ('pages-' + build_id + '.json')
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'original_files'}, indent=2))
