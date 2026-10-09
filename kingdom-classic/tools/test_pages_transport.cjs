const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const vm = require('node:vm');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '..');
fs.mkdirSync(path.join(root, 'analysis'), { recursive: true });
const fixture = fs.mkdtempSync(path.join(root, 'analysis', 'transport-test-'));
const build = path.join(fixture, 'build');
const pages = path.join(fixture, 'pages');
fs.mkdirSync(build);
fs.writeFileSync(path.join(build, 'index.html'), '<title>Hosting transport fixture, not a Unity game</title><script src="runtime.js"></script>');
fs.writeFileSync(path.join(build, 'runtime.js'), 'console.log("Hosting transport fixture");');
const original = Buffer.alloc(33 * 1024 * 1024 + 19);
for (let i = 0; i < original.length; i++) original[i] = (i * 31 + (i >>> 13)) & 255;
fs.writeFileSync(path.join(build, 'kingdom.data'), original);
const result = spawnSync('python', [path.join(__dirname, 'build_pages.py'), '--build', build, '--output', pages], { encoding: 'utf8' });
assert.equal(result.status, 0, result.stdout + result.stderr);
const manifest = JSON.parse(fs.readFileSync(path.join(pages, 'asset-manifest.json')));
const entry = manifest.files['game/kingdom.data'];
assert.equal(entry.parts.length, 3);
assert.ok(entry.parts.every(piece => piece.bytes <= 16 * 1024 * 1024));
assert.equal(fs.existsSync(path.join(pages, 'game', 'kingdom.data')), false);
let failureMode = '';
let manifestFailure = false;
let requestedParts = 0;
let claimed = false;
const handlers = {};
const context = {
  URL, Request, Response, ReadableStream, Uint8Array, crypto: crypto.webcrypto,
  self: {
    registration: { scope: 'https://test.invalid/kingdom/' },
    addEventListener(type, handler) { handlers[type] = handler; },
    skipWaiting() { return Promise.resolve(); },
    clients: { claim() { claimed = true; return Promise.resolve(); } }
  },
  async fetch(request) {
    const url = new URL(typeof request === 'string' ? request : request.url || request.href);
    const relative = url.pathname.slice('/kingdom/'.length);
    if (relative === 'asset-manifest.json' && manifestFailure) return new Response('', { status: 503 });
    if (relative.startsWith('segments/')) {
      requestedParts++;
      if (failureMode === 'http') return new Response('', { status: 404 });
      const data = fs.readFileSync(path.join(pages, relative));
      if (failureMode === 'truncated') return new Response(data.subarray(1));
      if (failureMode === 'changed') data[0] ^= 1;
      return new Response(data);
    }
    if (fs.existsSync(path.join(pages, relative)) && fs.statSync(path.join(pages, relative)).isFile()) {
      return new Response(fs.readFileSync(path.join(pages, relative)));
    }
    return new Response('network fallback');
  }
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(pages, 'asset-worker.js'), 'utf8'), context);
const request = new Request('https://test.invalid/kingdom/game/kingdom.data?cache=1');
(async () => {
  let activation;
  handlers.activate({ waitUntil(promise) { activation = promise; } });
  await activation;
  assert.equal(claimed, true);
  manifestFailure = true;
  await assert.rejects(() => context.serve(request), /manifest is unavailable/);
  manifestFailure = false;
  const response = await context.serve(request);
  assert.equal(response.headers.get('content-length'), String(original.length));
  assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
  const assembled = Buffer.from(await response.arrayBuffer());
  assert.ok(assembled.equals(original), 'Every byte must match the pre-segmented Unity data file.');
  assert.equal(crypto.createHash('sha256').update(assembled).digest('hex'), entry.sha256);
  for (const mode of ['http', 'truncated', 'changed']) {
    failureMode = mode;
    const broken = await context.serve(request);
    await assert.rejects(() => broken.arrayBuffer(), /Asset segment/);
  }
  failureMode = '';
  const small = await context.serve(new Request('https://test.invalid/kingdom/game/runtime.js'));
  assert.equal(await small.text(), fs.readFileSync(path.join(build, 'runtime.js'), 'utf8'));
  const outside = await context.serve(new Request('https://other.invalid/outside'));
  assert.equal(await outside.text(), 'network fallback');
  const malformed = await context.serve(new Request('https://test.invalid/kingdom/game/%ZZ'));
  assert.equal(malformed.status, 400);
  const rejectedManifests = [];
  for (const [name, change] of [
    ['wrong build', value => { value.buildId = 'wrong'; }],
    ['external segment', value => { value.files['game/kingdom.data'].parts[0].path = 'https://evil.invalid/a'; }],
    ['parent path', value => { value.files['game/kingdom.data'].parts[0].path = '../private'; }],
    ['HTML response', value => { value.files['game/kingdom.data'].contentType = 'text/html'; }],
    ['oversized segment', value => { value.files['game/kingdom.data'].parts[0].bytes = 16777217; }],
    ['invalid total', value => { value.files['game/kingdom.data'].bytes++; }],
    ['invalid hash', value => { value.files['game/kingdom.data'].parts[0].sha256 = 'bad'; }],
    ['reordered segment', value => { value.files['game/kingdom.data'].parts.reverse(); }],
    ['path traversal', value => { value.files['game/../private'] = value.files['game/kingdom.data']; }]
  ]) {
    const modified = structuredClone(manifest);
    change(modified);
    assert.throws(() => context.validateManifest(modified), /Asset manifest/);
    rejectedManifests.push(name);
  }
  const headers = fs.readFileSync(path.join(pages, '_headers'), 'utf8');
  assert.ok(headers.includes("default-src 'none'"));
  assert.ok(headers.includes("script-src-attr 'none'"));
  assert.ok(headers.includes("'wasm-unsafe-eval'"));
  assert.ok(!headers.includes("'unsafe-eval'") && !headers.includes("'unsafe-inline'"));
  const report = { fixture, recovered_bytes: assembled.length, segments: entry.parts.length,
    integrity: true, checked_failures: ['unavailable manifest with retry', 'missing segment', 'truncated segment', 'mismatched segment'],
    rejectedManifests, malformedPath: true, csp: true,
    note: 'Node transport test. No Unity engine or browser gameplay was run.' };
  fs.writeFileSync(path.join(root, 'analysis', 'pages-transport-validation.json'), JSON.stringify(report, null, 2));
  console.log('Pages transport checks passed:', assembled.length, 'bytes reconstructed from', entry.parts.length, 'segments.');
})().catch(error => { console.error(error); process.exitCode = 1; });
