const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const data = require('../analysis/game-data.json');
const { FusionGame } = require('../runtime.js');
const listeners = new Map(), nodes = new Map();
function surface(name) {
  return {
    style: {}, width:1280, height:720, clientWidth:1280, clientHeight:720,
    addEventListener(type, handler) { listeners.set(`${name}:${type}`,handler); },
    getContext() { return {}; },
    getBoundingClientRect() { return {left:0,top:0,width:1280,height:720}; },
    setPointerCapture() {},
    focus() { this.focused=true; },
    closest() { return name==='canvas'?null:this; }
  };
}
for(const id of ['game','stage','message','error','start','gate','pause','fullscreen']) nodes.set(id,surface(id==='game'?'canvas':id));
const document = {hidden:false,querySelector:selector=>nodes.get(selector.slice(1)),
  addEventListener:(type,handler)=>listeners.set(`document:${type}`,handler)};
const sandbox = vm.createContext({document,window:surface('window'),FNAF_DATA:data,FusionGame,console,
  localStorage:{getItem:()=>null},requestAnimationFrame:()=>{}});
vm.runInContext(fs.readFileSync(process.env.FNAF_PLAYER || require.resolve('../player.js'),'utf8'),sandbox);
const run=source=>vm.runInContext(source,sandbox);
const input=run('game.input');
const fire=(target,type,event={})=>listeners.get(`${target}:${type}`)(event);
const pointer={clientX:100,clientY:450,pointerId:1,pointerType:'touch',preventDefault(){}};
const key={key:'ArrowUp',target:nodes.get('game'),preventDefault(){}};
run('started=true; game.enter(3);');
fire('document','keydown',key); fire('canvas','pointerdown',pointer);
assert.equal(input.pressed.has(38),true); assert.equal(input.click,true);
nodes.get('pause').onclick({target:nodes.get('pause')});
assert.equal(input.click,false,'Pausing discards an unconsumed click');
assert.equal(input.pressed.size,0,'Pausing discards unconsumed key presses');
assert.equal(input.held.size,0,'Pausing releases held keys');
fire('canvas','pointerdown',pointer); fire('document','keydown',key);
assert.equal(input.click,false,'Clicks while paused cannot fire on resume');
assert.equal(input.pressed.size,0,'Keys while paused cannot fire on resume');
nodes.get('pause').onclick({target:nodes.get('pause')});
assert.equal(nodes.get('game').focused,true,'Resuming returns keyboard focus to the game');
fire('document','keydown',key); fire('canvas','pointerdown',pointer);
document.hidden=true; fire('document','visibilitychange');
assert.equal(input.click,false,'Hiding the tab discards an unconsumed click');
assert.equal(input.pressed.size,0,'Hiding the tab discards unconsumed key presses');
fire('document','keydown',key); fire('canvas','pointerdown',pointer);
assert.equal(input.held.size,0,'Hidden tabs cannot latch a held key');
assert.equal(input.click,false,'Hidden tabs cannot latch a click');
document.hidden=false; fire('document','visibilitychange');
fire('document','keydown',key); fire('canvas','pointerdown',pointer);
fire('window','blur');
assert.equal(input.held.size,0,'Losing window focus releases held keys even without keyup');
assert.equal(input.pressed.size,0); assert.equal(input.click,false);
fire('canvas','pointerdown',pointer); fire('canvas','pointercancel',pointer);
assert.equal(input.click,false,'Cancelled touch cannot activate a control');
assert.equal(input.x,640,'Cancelled touch stops side panning');
assert.equal(input.y,360,'Cancelled touch releases the light or monitor zone');
fire('canvas','pointerdown',pointer); fire('canvas','pointerup',pointer);
assert.equal(input.click,true,'A normal quick tap survives until its game tick');
assert.equal(run('neutralAfterStep'),true,'A normal touch release still neutralizes after its tick');
console.log('Pause, tab visibility, window focus, cancelled touch and quick-tap input checks passed.');
