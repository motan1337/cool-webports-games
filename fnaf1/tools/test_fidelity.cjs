const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { FusionGame } = require('../runtime.js');
const data = JSON.parse(fs.readFileSync(path.join(__dirname, '../analysis/game-data.json'), 'utf8'));
function office(night = 1) {
  const game = new FusionGame(data, { random: () => 0.5 });
  game.object(11).value = night;
  game.enter(3);
  game.step(); game.step();
  return game;
}
const step = (game, count) => { for (let i = 0; i < count; i++) game.step(); };
const game = office();
assert.equal(game.value(108), 1, 'Idle power usage is one unit');
const meter = game.object(108);
for (const [value, handle] of [[1,212],[2,213],[3,214],[4,456],[5,455]]) {
  meter.value = value;
  assert.equal(game.counterImageHandle(meter), handle, `Usage ${value} selects its original bar image`);
}
meter.value = 1;
const controls = game.object(55);
for (let mask = 0; mask < 32; mask++) {
  controls.alt = Array.from({length:5}, (_, i) => (mask >> i) & 1);
  game.action(game.frame.events[174].actions.find(a => a.object === 108), new Map());
  assert.equal(game.value(108), Math.min(5, 1 + controls.alt.reduce((a,b) => a+b,0)), `Usage formula for control mask ${mask}`);
}
for (const usage of [1,2,3,4,5]) {
  const g = office();
  g.object(55).alt = Array.from({length:5}, (_, i) => i < usage-1 ? 1 : 0);
  g.action(g.frame.events[174].actions.find(a => a.object === 108), new Map());
  const before = g.value(104);
  g.action(g.frame.events[176].actions[0], new Map());
  assert.equal(before-g.value(104), usage, `Original drain action consumes ${usage} units`);
}
const idle = office();
const before = idle.value(104);
step(idle, 600);
assert.equal(before-idle.value(104), 10, 'Ten idle seconds consume ten internal units, one displayed percent');
assert.equal(idle.value(105), Math.trunc(idle.value(104)/10), 'Power percentage uses the original integer division');
for (const [night, extra] of [[1,0],[2,10],[3,12],[4,15],[5,20]]) {
  const g = office(night), initial = g.value(104);
  step(g,3600);
  assert.equal(initial-g.value(104), 60+extra, `Night ${night} includes its original extra drain schedule`);
}
for (const [id, expected] of [[62,2],[63,2],[66,2],[67,2]]) {
  const g = office();
  const obj=g.object(id), box=g.bounds(obj);
  g.input.x=box.x+box.width/2-g.scrollOffset(obj); g.input.y=box.y+box.height/2;
  g.input.click=true; step(g,50);
  assert.equal(g.value(108),expected, `Control ${id} adds one usage unit`);
  g.input.click=true; step(g,50);
  assert.equal(g.value(108),1, `Control ${id} returns usage to idle`);
}
const monitor = office();
const trigger = monitor.object(70), triggerBox = monitor.bounds(trigger);
monitor.input.x = triggerBox.x + triggerBox.width/2;
monitor.input.y = triggerBox.y + triggerBox.height/2;
step(monitor,50);
assert.ok(monitor.value(49) > 0, 'Monitor raises through the original events');
assert.equal(monitor.value(108),2, 'Monitor adds one usage unit');
const blackout = office();
blackout.object(104).value = 0; step(blackout,2);
assert.equal(blackout.value(125),1, 'Empty power starts the original outage sequence');
assert.equal(blackout.object(108).visible,false, 'Usage meter disappears during the outage');
console.log('Meter images, all 32 usage combinations, drain timing on nights 1-5, controls, monitor and outage passed.');

const title = new FusionGame(data);
title.enter(1);
const background = title.object(13), startY = background.y;
step(title,80);
assert.equal(background.y,startY+50,'Title path speed 5 advances 50 pixels in 80 ticks');
step(title,1148);
assert.equal(background.y,startY+767,'Title path approaches its 768-pixel endpoint');
step(title,1);
assert.equal(background.y,startY,'Title path loops and repositions at its endpoint');
const soundCalls = [];
const win = new FusionGame(data,{audio:{play(...args){soundCalls.push(args);},stop(){},volume(){}}});
win.object(11).value=1; win.enter(6);
const digit = win.object(153);
step(win,8);
assert.equal(digit.y,295,'5 AM digit travels upward at speed 3');
assert.equal(win.object(156).alt[0] || 0,0,'Celebration waits for movement to finish');
assert.equal(soundCalls.length,1,'Only the start sound plays before the digit stops');
step(win,290);
assert.equal(digit.y,187,'Digit has not reached its endpoint after 298 ticks');
assert.equal(digit.movementStopped,false);
step(win,1);
assert.equal(digit.y,186,'Digit reaches the original 112-pixel endpoint');
assert.equal(digit.movementStopped,true);
assert.equal(win.object(156).alt[0],1,'Stopped condition starts the celebration');
assert.equal(soundCalls.length,2,'Cheer plays once after the digit stops');
step(win,40);
assert.equal(soundCalls.length,2,'Cheer does not repeat each tick');
const emptyPath=office(), follower=emptyPath.object(41), origin=[follower.x,follower.y];
emptyPath.movePaths();
assert.deepEqual([follower.x,follower.y],origin,'Empty office path introduces no movement');
console.log('Original title path loop, 5-to-6 AM movement, stopped condition and cheer timing passed.');
for (let frame=0; frame<data.frames.length; frame++) {
  const scene=new FusionGame(data,{random:()=>0.37});
  scene.object(11).value=1; scene.enter(frame);
  step(scene,1200);
}
console.log('All 17 scene entry and 20-second simulation checks passed.');
