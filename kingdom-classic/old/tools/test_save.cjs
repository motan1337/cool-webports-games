const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const pending = [];
let calls = 0;
let failures = 0;
let exits = 0;
const context = {
  Module: {}, LibraryManager: { library: {} },
  mergeInto: Object.assign,
  FS: { syncfs(populate, done) { assert.equal(populate, false); calls++; pending.push(done); } },
  console: { error() { failures++; } },
  window: { parent: { postMessage(message, origin) { assert.equal(message, 'kingdom-exit'); assert.equal(origin, 'http://localhost'); exits++; } } },
  location: { origin: 'http://localhost', reload() { exits++; } }
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../unity-web/Assets/Plugins/KingdomBrowser.jslib'), 'utf8'), context);
const flush = context.LibraryManager.library.KingdomSyncSave;
context._KingdomSyncSave = flush;
const quit = context.LibraryManager.library.KingdomExitGame;
flush();
flush();
flush();
assert.equal(calls, 1);
pending.shift()(null);
assert.equal(calls, 2);
pending.shift()(null);
assert.equal(context.Module.kingdomSaveSyncing, false);
flush();
pending.shift()(new Error('storage unavailable'));
assert.equal(failures, 1);
assert.equal(context.Module.kingdomSaveSyncing, false);
flush();
pending.shift()(null);
flush();
quit();
assert.equal(exits, 0);
pending.shift()(null);
assert.equal(exits, 0);
pending.shift()(null);
assert.equal(exits, 1);
quit();
pending.shift()(new Error('storage unavailable'));
assert.equal(exits, 1);
assert.equal(context.Module.kingdomExitPending, false);
context.window.parent = context.window;
quit();
pending.shift()(null);
assert.equal(exits, 2);
console.log('Save checks passed: coalescing, queued writes, storage recovery, exit waits for persistence, failed persistence cancels exit.');
