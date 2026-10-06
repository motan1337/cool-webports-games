const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(require.resolve('../pages/index.html'),'utf8').replace(/\r\n?/g,'\n');
const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map(match=>match[1]);
assert.equal(scripts.length,4);
const nodes=new Map();
for(const id of ['game','stage','message','error','start','gate','pause','fullscreen']) nodes.set(id,{
  style:{},width:1280,height:720,clientWidth:1280,clientHeight:720,
  getContext(){return {};},addEventListener(){},focus(){this.focused=true;}
});
const sandbox={console,document:{querySelector:s=>nodes.get(s.slice(1)),addEventListener(){}},
  addEventListener(){},localStorage:{getItem:()=>null},requestAnimationFrame(){},
  AudioContext:class {
    constructor(){this.state='suspended';}
    async resume(){this.state='running';}
  }};
sandbox.window=sandbox;
const context=vm.createContext(sandbox);
for(const script of scripts) vm.runInContext(script,context);
assert.equal(typeof nodes.get('start').onclick,'function','Packaged scripts install the Play handler');
(async()=>{
  await nodes.get('start').onclick();
  assert.equal(nodes.get('gate').hidden,true,'Play hides the startup overlay');
  assert.equal(vm.runInContext('started',context),true,'Play starts the simulation');
  assert.equal(vm.runInContext('soundContext.state',context),'running','Play resumes audio');
  assert.equal(nodes.get('game').focused,true,'Play gives the canvas keyboard focus');
  assert.equal(vm.runInContext('game.frame.index',context),0,'The packaged game initializes its warning scene');
  console.log('All four packaged scripts initialize, and the actual Play handler starts the game.');
})().catch(error=>{console.error(error);process.exitCode=1;});
