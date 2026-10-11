const buildId = '__BUILD_ID__';
let manifestPromise;

function validateManifest(value) {
  if (!value || value.buildId !== buildId || !value.files || typeof value.files !== 'object' || Array.isArray(value.files)) {
    throw new Error('Asset manifest does not match this build.');
  }
  const files = Object.entries(value.files);
  if (files.length > 32) throw new Error('Asset manifest contains too many files.');
  const hashPattern = /^[a-f0-9]{64}$/;
  const types = new Set(['application/octet-stream', 'application/wasm', 'application/javascript', 'text/javascript']);
  for (const [name, entry] of files) {
    if (!/^game\/(?:[A-Za-z0-9_-][A-Za-z0-9_.-]*\/)*[A-Za-z0-9_-][A-Za-z0-9_.-]*$/.test(name) ||
        !entry || !Number.isSafeInteger(entry.bytes) || entry.bytes < 1 || entry.bytes > 1073741824 ||
        !hashPattern.test(entry.sha256) || !types.has(entry.contentType) ||
        !Array.isArray(entry.parts) || entry.parts.length < 1 || entry.parts.length > 64) {
      throw new Error('Asset manifest contains an invalid file.');
    }
    let total = 0;
    for (let index = 0; index < entry.parts.length; index++) {
      const piece = entry.parts[index];
      const expectedPath = 'segments/' + entry.sha256 + '.' + String(index).padStart(4, '0') + '.bin';
      if (!piece || piece.path !== expectedPath || !Number.isSafeInteger(piece.bytes) ||
          piece.bytes < 1 || piece.bytes > 16777216 || !hashPattern.test(piece.sha256)) {
        throw new Error('Asset manifest contains an invalid segment.');
      }
      total += piece.bytes;
    }
    if (total !== entry.bytes) throw new Error('Asset manifest contains an invalid total size.');
  }
  return value;
}

function manifest() {
  if (!manifestPromise) {
    manifestPromise = fetch(new URL('asset-manifest.json?v=' + buildId, self.registration.scope), { cache: 'no-store', redirect: 'error' })
      .then(response => {
        if (!response.ok) throw new Error('Asset manifest is unavailable.');
        return response.json();
      }).then(validateManifest).catch(error => {
        manifestPromise = undefined;
        throw error;
      });
  }
  return manifestPromise;
}

self.addEventListener('install', event => event.waitUntil(self.skipWaiting()));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));

async function serve(request) {
  const url = new URL(request.url);
  const scope = new URL(self.registration.scope);
  if (url.origin !== scope.origin || !url.pathname.startsWith(scope.pathname) || request.method !== 'GET') {
    return fetch(request);
  }
  let relative;
  try {
    relative = decodeURIComponent(url.pathname.slice(scope.pathname.length));
  } catch {
    return new Response('Invalid asset path.', { status: 400, headers: { 'Content-Type': 'text/plain', 'X-Content-Type-Options': 'nosniff' } });
  }
  const files = (await manifest()).files;
  const entry = Object.prototype.hasOwnProperty.call(files, relative) ? files[relative] : undefined;
  if (!entry) return fetch(request);
  let part = 0;
  const stream = new ReadableStream({
    async pull(controller) {
      if (part === entry.parts.length) {
        controller.close();
        return;
      }
      const piece = entry.parts[part++];
      try {
        const response = await fetch(new URL(piece.path, scope), { cache: 'no-store', redirect: 'error' });
        if (!response.ok) throw new Error('Asset segment failed: ' + piece.path);
        const bytes = new Uint8Array(await response.arrayBuffer());
        if (bytes.byteLength !== piece.bytes) throw new Error('Asset segment is incomplete: ' + piece.path);
        const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)))
          .map(value => value.toString(16).padStart(2, '0')).join('');
        if (hash !== piece.sha256) throw new Error('Asset segment does not match this build: ' + piece.path);
        controller.enqueue(bytes);
      } catch (error) {
        controller.error(error);
      }
    }
  });
  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': entry.contentType, 'Content-Length': String(entry.bytes), 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' }
  });
}

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  const scope = new URL(self.registration.scope);
  if (url.origin === scope.origin && url.pathname.startsWith(scope.pathname + 'game/')) {
    event.respondWith(serve(event.request));
  }
});
