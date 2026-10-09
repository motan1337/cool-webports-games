const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const handlers = {};
const frameWindow = {};
const frame = { contentWindow: frameWindow, hidden: false, src: './game/index.html' };
const main = { hidden: true };
const status = { textContent: '' };
const button = { disabled: true, focus() {}, addEventListener() {} };
const selectors = { button, '[role="status"]': status, iframe: frame, main };
const context = {
  URL,
  location: { origin: 'https://kingdom.invalid', href: 'https://kingdom.invalid/' },
  document: { querySelector: name => selectors[name] },
  window: { addEventListener: (name, handler) => { handlers[name] = handler; } }
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname, 'pages/launch.js'), 'utf8'), context);
for (const event of [
  { origin: 'https://evil.invalid', source: frameWindow, data: 'kingdom-exit' },
  { origin: context.location.origin, source: {}, data: 'kingdom-exit' },
  { origin: context.location.origin, source: frameWindow, data: '<img src=x onerror=alert(1)>' },
  { origin: context.location.origin, source: frameWindow, data: { command: 'kingdom-exit' } }
]) {
  handlers.message(event);
  assert.equal(main.hidden, true);
  assert.equal(status.textContent, '');
}
handlers.message({ origin: context.location.origin, source: frameWindow, data: 'kingdom-exit' });
assert.equal(main.hidden, false);
assert.equal(frame.hidden, true);
assert.equal(frame.src, 'about:blank');
assert.equal(status.textContent, 'Game saved.');
assert.equal(button.disabled, false);
console.log('Launcher security checks passed: origin, frame identity, exact command, and fixed text response.');
