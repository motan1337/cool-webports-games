const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const events = {};
let resumes = 0;
let starts = 0;
const blocked = { mediaElement: { paused: true, ended: false, currentTime: 3 }, _startPlayback(offset) { assert.equal(offset, 3); starts++; } };
const makeSource = flags => Object.assign({ mediaElement: { paused: true, ended: false, currentTime: 0 }, _startPlayback() { throw Error('Inactive audio restarted'); } }, flags);
const context = {
  Module: { deinitializers: [] }, LibraryManager: { library: {} }, mergeInto: Object.assign,
  WEBAudio: { audioContext: { state: 'suspended', resume() { resumes++; return Promise.resolve(); } }, audioInstances: {
    1: { source: blocked }, 2: { source: makeSource({ isStopped: true }) },
    3: { source: makeSource({ pauseRequested: true }) }, 4: { source: makeSource({ playPromise: {} }) },
    5: { source: makeSource({ playTimeout: 42 }) }, 6: { buffer: {} },
    7: { source: makeSource({ mediaElement: { paused: true, ended: true } }) },
    8: { source: makeSource({ mediaElement: { paused: false, ended: false } }) }
  } },
  window: { addEventListener(name, callback) { events[name] = callback; }, removeEventListener(name) { delete events[name]; } },
  console
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../unity-web/Assets/Plugins/KingdomBrowser.jslib'), 'utf8'), context);
const api = context.LibraryManager.library;
api.KingdomInstallAudioUnlock();
api.KingdomInstallAudioUnlock();
assert.equal(context.Module.deinitializers.length, 1);
assert.deepEqual(Object.keys(events).sort(), ['keydown', 'pointerdown', 'touchstart']);
events.keydown({ isTrusted: false });
assert.equal(resumes, 0);
assert.equal(starts, 0);
api.KingdomSetAudioPaused(1);
events.keydown({ isTrusted: true });
assert.equal(resumes, 1);
assert.equal(starts, 0);
api.KingdomSetAudioPaused(0);
context.WEBAudio.audioContext.state = 'running';
events.keydown({ isTrusted: true });
assert.equal(starts, 1);
assert.equal(resumes, 1);
context.Module.deinitializers[0]();
assert.equal(Object.keys(events).length, 0);
console.log('Browser audio checks passed: keyboard activation, blocked media retry, pause/stop/pending guards and cleanup.');
