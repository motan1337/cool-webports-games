'use strict';
const canvas = document.querySelector('#game');
const context = canvas.getContext('2d', { alpha: false });
const stage = document.querySelector('#stage');
function fitViewport() {
  const scale = Math.min(stage.clientWidth / canvas.width, stage.clientHeight / canvas.height);
  canvas.style.width = `${canvas.width * scale}px`;
  canvas.style.height = `${canvas.height * scale}px`;
}
if ('ResizeObserver' in window) new ResizeObserver(fitViewport).observe(stage);
window.addEventListener('resize', fitViewport);
fitViewport();
const message = document.querySelector('#message');
const errorPanel = document.querySelector('#error');
const resources = new Map();
const masks = new Map();
const panoramas = new Map();
let clock = 0, accumulator = 0, started = false, paused = false, busy = false, neutralAfterStep = false;
let soundContext;
const audioBuffers = new Map();
const audioPending = new Map();
const channels = new Map();
const volumes = new Map();
let audioGeneration = 0;
const storageKey = 'fnaf1-archive-save-v1';
let saveData = {};
try { saveData = JSON.parse(localStorage.getItem(storageKey) || '{}'); } catch (_) {}

function fail(error) {
  paused = true;
  errorPanel.hidden = false;
  errorPanel.textContent = `${error.stack || error}\n\nFrame: ${game.frame.index}, tick: ${game.tickCount}\nRecent events: ${JSON.stringify(game.trace.slice(-15))}`;
  console.error(error);
}
function loadImage(handle) {
  if (handle === undefined) return Promise.resolve(null);
  let entry = resources.get(handle);
  if (entry) { entry.last = performance.now(); return entry.promise; }
  const image = new Image();
  entry = { image, last: performance.now(), ready: false };
  entry.promise = new Promise((resolve, reject) => {
    image.onload = () => { entry.ready = true; resolve(image); };
    image.onerror = () => reject(new Error(`Cannot load extracted image ${handle}`));
    image.src = `extracted/images/${String(handle).padStart(4, '0')}.png`;
  });
  resources.set(handle, entry);
  return entry.promise;
}
function maskFor(handle) {
  const entry = resources.get(handle);
  if (!entry?.ready) return null;
  let mask = masks.get(handle);
  if (!mask) {
    const surface = document.createElement('canvas');
    surface.width = entry.image.width; surface.height = entry.image.height;
    const ctx = surface.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(entry.image, 0, 0);
    const rgba = ctx.getImageData(0, 0, surface.width, surface.height).data;
    const alpha = new Uint8Array(surface.width * surface.height);
    for (let i = 0; i < alpha.length; i++) alpha[i] = rgba[i * 4 + 3];
    mask = { alpha, width: surface.width, height: surface.height }; masks.set(handle, mask);
  }
  return mask;
}
function hitTest(handle, x, y) {
  const mask = maskFor(handle);
  if (!mask) return true;
  return mask.alpha[Math.floor(y) * mask.width + Math.floor(x)] > 0;
}
function pixelOverlap(a,b,boxA,boxB) {
  const ma = a.def.new_flags & 4 ? null : maskFor(game.imageHandle(a));
  const mb = b.def.new_flags & 4 ? null : maskFor(game.imageHandle(b));
  if (!ma && !mb) return true;
  const left = Math.ceil(Math.max(boxA.x,boxB.x)), right = Math.floor(Math.min(boxA.x+boxA.width,boxB.x+boxB.width));
  const top = Math.ceil(Math.max(boxA.y,boxB.y)), bottom = Math.floor(Math.min(boxA.y+boxA.height,boxB.y+boxB.height));
  for (let y=top;y<bottom;y++) for (let x=left;x<right;x++) {
    if ((!ma || ma.alpha[Math.floor(y-boxA.y)*ma.width+Math.floor(x-boxA.x)]) && (!mb || mb.alpha[Math.floor(y-boxB.y)*mb.width+Math.floor(x-boxB.x)])) return true;
  }
  return false;
}
async function soundBuffer(handle) {
  if (audioBuffers.has(handle)) return audioBuffers.get(handle);
  if (audioPending.has(handle)) return audioPending.get(handle);
  const sample = FNAF_DATA.sounds.find(s => s.handle === handle);
  if (!sample) throw new Error(`Missing sound ${handle}`);
  const pending = fetch(sample.path).then(r => {
    if (!r.ok) throw new Error(`Cannot load ${sample.path}`);
    return r.arrayBuffer();
  }).then(raw => soundContext.decodeAudioData(raw)).then(buffer => {
    audioBuffers.set(handle, buffer); audioPending.delete(handle); return buffer;
  });
  audioPending.set(handle, pending);
  return pending;
}
const audio = {
  stop() {
    audioGeneration++;
    for (const channel of channels.values()) channel.source?.stop();
    channels.clear();
  },
  volume(channel, value) {
    volumes.set(channel, Math.min(1, Math.max(0, value / 100)));
    channels.get(channel)?.gain?.gain.setValueAtTime(volumes.get(channel), soundContext.currentTime);
  },
  play(handle, channel, repeats) {
    if (!soundContext) return;
    const old = channels.get(channel);
    old?.source?.stop();
    const entry = { generation: audioGeneration, handle };
    channels.set(channel, entry);
    soundBuffer(handle).then(buffer => {
      if (entry.generation !== audioGeneration || channels.get(channel) !== entry) return;
      const source = soundContext.createBufferSource(), gain = soundContext.createGain();
      source.buffer = buffer; source.loop = repeats === 0 || repeats > 1;
      gain.gain.value = volumes.get(channel) ?? 1;
      source.connect(gain).connect(soundContext.destination);
      entry.source = source; entry.gain = gain;
      source.start();
      if (repeats > 1) source.stop(soundContext.currentTime + buffer.duration * repeats);
    }).catch(fail);
  }
};
const game = new FusionGame(FNAF_DATA, { audio, storage: saveData, hitTest, overlapTest: pixelOverlap,
  onSave: data => { try { localStorage.setItem(storageKey, JSON.stringify(data)); } catch (_) { message.textContent = 'Browser storage is unavailable. Progress will last only for this session.'; } } });

function imageDraw(handle, x, y, opacity = 1) {
  const entry = resources.get(handle);
  if (!entry?.ready) return;
  entry.last = performance.now();
  context.globalAlpha = opacity;
  context.drawImage(entry.image, Math.round(x), Math.round(y));
}
function drawCounter(obj, x, y) {
  const def = obj.def;
  if (!def.counter_frames || !def.display) return;
  if (def.display === 4) {
    const handle = game.counterImageHandle(obj);
    const img = game.images.get(handle);
    imageDraw(handle, x - (img?.hotspot[0] || 0), y - (img?.hotspot[1] || 0), obj.opacity);
    return;
  }
  let digits = String(Math.trunc(obj.value));
  if (def.digits & 15) digits = digits.padStart(def.digits & 15, '0');
  const handles = [...digits].map(c => def.counter_frames[c === '-' ? 10 : Number(c)]);
  const width = handles.reduce((total, h) => total + (game.images.get(h)?.width || 0), 0);
  let left = x - width;
  for (const handle of handles) {
    const image = game.images.get(handle);
    imageDraw(handle, left, y - (image?.height || 0), obj.opacity);
    left += image?.width || 0;
  }
}
function drawText(obj, x, y) {
  const paragraph = obj.def.paragraphs?.[0];
  if (!paragraph) return;
  const font = FNAF_DATA.fonts[paragraph.font] || { name: 'Consolas', height: -27, weight: 400 };
  const height = Math.abs(font.height);
  context.font = `${font.weight >= 700 ? 'bold ' : ''}${height}px "${font.name}", monospace`;
  context.fillStyle = `rgb(${paragraph.color.join(',')})`;
  context.textBaseline = 'top'; context.textAlign = paragraph.flags & 1 ? 'center' : 'left';
  const left = x + (paragraph.flags & 1 ? obj.def.width / 2 : 0);
  for (const [i, line] of paragraph.text.split(/\r?\n/).entries()) context.fillText(line, left, y + i * height * 1.15);
}
function render() {
  canvas.dataset.frame = String(game.frame.index);
  canvas.dataset.tick = String(game.tickCount);
  canvas.dataset.power = String(game.value(104));
  canvas.dataset.usage = String(game.value(108));
  canvas.dataset.usageImage = String(game.object(108) ? game.counterImageHandle(game.object(108)) : '');
  canvas.dataset.viewing = String(game.value(49));
  canvas.dataset.scroll = String(game.scrollX);
  canvas.dataset.overlayOffset = String(game.object(75) ? game.scrollOffset(game.object(75)) : 0);
  context.globalAlpha = 1; context.globalCompositeOperation = 'source-over'; context.fillStyle = '#000'; context.fillRect(0, 0, 1280, 720);
  const ordered = game.instances.filter(o => !o.destroyed && o.visible).sort((a, b) => a.layer - b.layer || (a.def.type <= 1 ? -1 : 0) - (b.def.type <= 1 ? -1 : 0));
  for (const obj of ordered) {
    context.globalCompositeOperation = obj.def.ink === 9 ? 'lighter' : 'source-over';
    const x = obj.x - game.scrollOffset(obj), y = obj.y;
    if (obj.def.perspective) {
      let effect = panoramas.get(obj.id);
      if (!effect) { effect = new Panorama(obj.def.perspective); panoramas.set(obj.id, effect); }
      effect.draw(context, canvas, x, y);
    }
    else if (obj.def.type === 7) drawCounter(obj, x, y);
    else if (obj.def.type === 3) { context.globalAlpha = obj.opacity; drawText(obj, x, y); }
    else {
      const handle = game.imageHandle(obj), img = game.images.get(handle);
      imageDraw(handle, x - (img?.hotspot[0] || 0), y - (img?.hotspot[1] || 0), obj.opacity);
    }
  }
  context.globalAlpha = 1;
}
function neededImages() {
  const handles = new Set();
  for (const obj of game.instances) {
    if (obj.destroyed || !obj.visible) continue;
    const def = obj.def;
    if (def.type === 7) for (const handle of def.counter_frames || []) handles.add(handle);
    else {
      const handle = game.imageHandle(obj);
      if (handle !== undefined) handles.add(handle);
      const dir = game.direction(obj);
      if (dir && dir.frames.length > 1) for (const handle of dir.frames) handles.add(handle);
    }
  }
  for (const event of game.frame.events) for (const condition of event.conditions) {
    if (condition.type < 0 || condition.number !== -4) continue;
    for (const id of [condition.object,condition.parameters[0].object]) for (const obj of game.list(id)) {
      const handle = game.imageHandle(obj);
      if (handle !== undefined && !(obj.def.new_flags & 4)) handles.add(handle);
    }
  }
  return handles;
}
function trimImages(protectedHandles) {
  let pixels = [...resources.values()].reduce((sum, r) => sum + (r.ready ? r.image.width * r.image.height : 0), 0);
  if (pixels < 40000000) return;
  for (const [handle, entry] of [...resources.entries()].sort((a, b) => a[1].last - b[1].last)) {
    if (protectedHandles.has(handle) || !entry.ready) continue;
    pixels -= entry.image.width * entry.image.height;
    resources.delete(handle); masks.delete(handle); entry.image.src = '';
    if (pixels < 30000000) break;
  }
}
function scheduleResources() {
  const needed = neededImages();
  const missing = [...needed].filter(h => !resources.get(h)?.ready);
  if (!missing.length) { trimImages(needed); return false; }
  if (!busy) {
    busy = true; message.textContent = `Loading ${missing.length} images...`;
    Promise.all(missing.map(loadImage)).then(() => {
      busy = false; accumulator = 0;
      message.textContent = 'Touch or move toward a side to look around. Tap buttons to use them.';
    }).catch(fail);
  }
  return true;
}
function loop(now) {
  const elapsed = clock ? Math.min(100, now - clock) : 0; clock = now;
  try {
    if (started && !paused && !document.hidden && !scheduleResources()) {
      accumulator += elapsed;
      while (accumulator >= 1000 / FNAF_DATA.frame_rate) {
        game.step(); accumulator -= 1000 / FNAF_DATA.frame_rate;
        if (neutralAfterStep) { game.input.x = 640; game.input.y = 360; neutralAfterStep = false; }
        if (game.stopped) {
          paused = true; audio.stop();
          message.textContent = 'Game ended. Reload to return to the title screen.';
          break;
        }
        if (scheduleResources()) break;
      }
    }
    render();
  } catch (error) { fail(error); }
  requestAnimationFrame(loop);
}
function point(event) {
  const rect = canvas.getBoundingClientRect();
  game.input.x = (event.clientX - rect.left) * 1280 / rect.width;
  game.input.y = (event.clientY - rect.top) * 720 / rect.height;
}
function resetInput() {
  game.input.click = false;
  game.input.pressed.clear(); game.input.held.clear();
  game.input.x = 640; game.input.y = 360;
  neutralAfterStep = false;
}
canvas.addEventListener('pointermove', event => {
  if (started && !paused && !document.hidden) point(event);
});
canvas.addEventListener('pointerdown', event => {
  if (!started || paused || document.hidden) return;
  event.preventDefault(); point(event); game.input.click = true;
  canvas.focus({ preventScroll: true });
  canvas.setPointerCapture(event.pointerId);
  soundContext?.resume();
});
canvas.addEventListener('pointercancel', resetInput);
canvas.addEventListener('pointerup', event => {
  if (event.pointerType !== 'mouse') {
    const viewing = game.value(49);
    if (game.frame.index === 3 && viewing === 0) neutralAfterStep = true;
  }
});
const keyCode = event => ({ Escape: 27, Enter: 13, ArrowUp: 38, ArrowDown: 40, Delete: 46,
  '1': 49, '2': 50, c: 67, C: 67, d: 68, D: 68 }[event.key] || event.key.toUpperCase().charCodeAt(0));
document.addEventListener('keydown', event => {
  if (!started || paused || document.hidden || event.target.closest('button,input,a')) return;
  const key = keyCode(event);
  if (!game.input.held.has(key)) game.input.pressed.add(key);
  game.input.held.add(key); event.preventDefault();
});
document.addEventListener('keyup', event => game.input.held.delete(keyCode(event)));
document.addEventListener('visibilitychange', () => {
  accumulator = 0; resetInput();
  if (document.hidden) soundContext?.suspend();
  else if (!paused) soundContext?.resume();
});
window.addEventListener('blur', resetInput);
document.querySelector('#start').onclick = async () => {
  soundContext = new (window.AudioContext || window.webkitAudioContext)();
  await soundContext.resume();
  document.querySelector('#gate').hidden = true; started = true; clock = 0;
  canvas.focus({ preventScroll: true });
};
document.querySelector('#pause').onclick = event => {
  paused = !paused; accumulator = 0; resetInput(); event.target.textContent = paused ? 'Resume' : 'Pause';
  if (paused) soundContext?.suspend(); else soundContext?.resume();
  if (!paused) canvas.focus({ preventScroll: true });
};
document.querySelector('#fullscreen').onclick = () => {
  const stage = document.querySelector('#stage');
  if (stage.requestFullscreen) stage.requestFullscreen().catch(() => {});
  else message.textContent = 'Rotate your device to landscape for the largest view.';
  canvas.focus({ preventScroll: true });
};
requestAnimationFrame(loop);
