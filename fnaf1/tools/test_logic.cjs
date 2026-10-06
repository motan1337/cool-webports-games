const assert = require('node:assert/strict');
const data = require('../analysis/game-data.json');
const { FusionGame } = require(process.env.FNAF_RUNTIME || '../runtime.js');
const step = (game,count) => { for(let i=0;i<count;i++) game.step(); };
function office() {
  const game = new FusionGame(data,{random:()=>0.5});
  game.object(11).value=1; game.enter(3); step(game,2);
  game.input.x=640; game.input.y=360;
  return game;
}

const animation=office(),door=animation.object(59);
animation.action({type:2,number:17,object:59,parameters:[{value:12}]},new Map());
animation.animate(); animation.animate();
assert.equal(door.animationFrame,0,'Door frame zero persists at the exact animation threshold');
animation.animate();
assert.equal(door.animationFrame,1,'Door advances after exceeding the threshold');

const completion=office(),left=completion.object(59);
left.animation=12; left.animationFrame=15; left.animationProgress=100; left.animationDone=false; left.alt[0]=1;
completion.step();
assert.equal(left.alt[0],2,'Door completion is observed during the tick that completes it');
assert.equal(left.animation,13,'Completed closing changes to the closed-door animation in the same tick');
const single=office(),image=single.object(44);
image.animation=43; image.animationFrame=0; image.animationProgress=0; image.animationDone=false; image.cycles=0;
single.animate(); single.animate();
assert.equal(image.animationDone,false,'Finite single-frame animation remains active through its duration');
single.animate();
assert.equal(image.animationDone,true,'Finite single-frame animation can finish');

for(const [actor,ready,inOffice,doorId,command] of [[111,114,116,59,1],[120,115,117,60,2]]) {
  for(const closed of [false,true]) {
    const game=office(),character=game.object(actor),target=game.object(ready);
    character.x=target.x; character.y=target.y; character.alt[0]=1;
    game.object(doorId).alt[0]=closed?2:0; game.object(113).value=command;
    game.step();
    assert.equal(game.overlap(character,game.object(inOffice)),!closed,`Actor ${actor} respects its ${closed?'closed':'open'} door`);
    assert.equal(game.value(113),0,'Movement command is consumed once');
  }
}
const fox=office(); fox.object(59).alt[0]=2;
for(const [attack,cost] of [[1,10],[2,60],[3,110]]) {
  fox.object(128).value=5; const before=fox.value(104); fox.step();
  assert.equal(before-fox.value(104),cost,`Foxy blocked attack ${attack} uses its original escalating cost`);
  assert.equal(fox.object(120).alt[15],attack);
  fox.step();
}
const caught=office(); caught.object(128).value=5; caught.step();
assert.equal(caught.object(44).animation,52,'Foxy reaches its jumpscare with the left door open');
step(caught,80); assert.equal(caught.frame.index,4,'Foxy animation completion enters the death scene');

for(const [view,closed,expected] of [[1,false,140],[1,true,85],[42,false,86],[4,true,86],[0,false,86]]) {
  const game=office(),freddy=game.object(139),corner=game.object(86);
  freddy.x=corner.x; freddy.y=corner.y; freddy.alt[12]=2;
  game.object(49).value=view; game.object(60).alt[0]=closed?2:0;
  game.step();
  assert.deepEqual([freddy.x,freddy.y],[game.object(expected).x,game.object(expected).y],
    `Freddy respects door state and watched camera ${view}`);
}
const bear=office(),freddy=bear.object(139),inside=bear.object(140),screams=[];
freddy.x=inside.x; freddy.y=inside.y; bear.random=()=>0.25;
bear.audio={play(handle){if(handle===15)screams.push(bear.object(44).animationFrame);},stop(){},volume(){}};
step(bear,150);
assert.deepEqual(screams,[7],'Freddy screams once at original jumpscare frame 7');
assert.equal(bear.frame.index,4,'Freddy attack finishes in the death scene');

const boosts=office(),activity=()=>[112,121,127].map(id=>boosts.value(id));
const initial=activity();
for(const [hour,delta] of [[2,[1,0,0]],[3,[2,1,1]],[4,[3,2,2]]]) {
  boosts.object(123).value=hour; boosts.step(); boosts.step();
  assert.deepEqual(activity(),initial.map((value,i)=>value+delta[i]),`AI boost at ${hour} AM happens once`);
}

for(const [night,ending,flag] of [[5,9,'beatgame'],[6,11,'beat6'],[7,13,'beat7']]) {
  const storage={},game=new FusionGame(data,{storage,random:()=>0.5});
  game.object(11).value=night;
  for(const id of [141,142,143,144]) game.object(id).value=20;
  game.enter(6); step(game,550);
  assert.equal(game.frame.index,ending,`Night ${night} reaches its ending`);
  assert.equal(storage[`freddy/freddy/${flag}`],1,`Night ${night} records ${flag}`);
}
const custom=new FusionGame(data,{random:()=>0.5}); custom.enter(12); custom.step();
for(const [id,value] of [[141,1],[142,9],[143,8],[144,7]]) custom.object(id).value=value;
custom.step();
assert.equal(custom.value(189),1,'1987 combination activates the original Easter egg');
custom.object(141).value=2; custom.step();
assert.equal(custom.value(189),0,'Changing the 1987 combination deactivates it');
custom.enter(3); step(custom,2);
assert.deepEqual([138,112,121,127].map(id=>custom.value(id)),[2,9,8,7],'Custom AI values reach the night in the right order');
console.log('Animation timing, doors, Foxy penalties/death, Freddy cameras/attack/audio, hourly AI, endings, stars and custom AI passed.');
