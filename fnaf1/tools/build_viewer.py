import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
report = json.loads((root / 'analysis/extraction-inventory.json').read_text())
assets = dict(images=[dict(handle=i['handle'], width=i['width'], height=i['height'],
                           path='extracted/images/'+Path(i['file']).name) for i in report['images']],
              sounds=[dict(handle=s['handle'], name=s['name'], path='extracted/audio/'+Path(s['file']).name)
                      for s in report['sounds']])
html = '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FNaF asset archive</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#171713;color:#e0dfce;font:16px Georgia,serif}
header{padding:24px;border-bottom:1px solid #57574a}h1{margin:0 0 8px;font-weight:normal}p{line-height:1.5}
button,input,select{font:14px Consolas,monospace;background:#262620;color:inherit;border:1px solid #757565;padding:10px}
nav{display:flex;gap:10px;flex-wrap:wrap;padding:16px}main{padding:0 16px 24px;display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}
article{border:1px solid #57574a;padding:10px;min-width:0}article img{width:100%;height:140px;object-fit:contain;background:#080808;cursor:pointer}
article p{margin:8px 0;font:12px Consolas,monospace;overflow-wrap:anywhere}audio{width:100%}
dialog{width:94vw;max-width:1600px;background:#171713;color:#e0dfce;border:1px solid #757565}dialog::backdrop{background:#000d}
dialog img{width:100%;max-height:80vh;object-fit:contain}a{color:inherit}#status{padding:0 16px}
</style>
<header><h1>Five Nights at Freddy's / asset archive</h1><p>605 images and 52 sounds extracted from your local executable. Assets decoded from the supported local executable.</p></header>
<nav><select id="kind" aria-label="Asset type"><option value="images">Images</option><option value="sounds">Sounds</option></select><input id="search" placeholder="Handle or sound name" aria-label="Search"><button id="previous">Previous</button><button id="next">Next</button></nav>
<p id="status"></p><main id="grid"></main><dialog id="preview"><button id="close">Close</button><p id="caption"></p><img id="full" alt="Selected extracted asset"></dialog>
<script>
const assets=ASSETS;
const kind=document.querySelector('#kind'),search=document.querySelector('#search'),grid=document.querySelector('#grid');
const preview=document.querySelector('#preview');let page=0;const perPage=36;
function render(){
 const list=assets[kind.value].filter(a=>`${a.handle} ${a.name||''}`.toLowerCase().includes(search.value.toLowerCase()));
 page=Math.max(0,Math.min(page,Math.ceil(list.length/perPage)-1));grid.replaceChildren();
 document.querySelector('#status').textContent=`${list.length} assets / page ${page+1} of ${Math.max(1,Math.ceil(list.length/perPage))}`;
 for(const a of list.slice(page*perPage,(page+1)*perPage)){
  const card=document.createElement('article'),label=document.createElement('p');
  label.textContent=`#${a.handle} / ${a.name||`${a.width} x ${a.height}`}`;
  if(kind.value==='images'){
   const img=document.createElement('img');img.src=a.path;img.alt=`Image ${a.handle}`;img.loading='lazy';
   img.onclick=()=>{document.querySelector('#full').src=a.path;document.querySelector('#caption').textContent=label.textContent;preview.showModal()};card.append(img);
  }else{const audio=document.createElement('audio');audio.src=a.path;audio.controls=true;audio.preload='none';card.append(audio)}
  const link=document.createElement('a');link.href=a.path;link.textContent='Open file';card.append(label,link);grid.append(card);
 }
}
kind.onchange=search.oninput=()=>{page=0;render()};
document.querySelector('#previous').onclick=()=>{page--;render()};document.querySelector('#next').onclick=()=>{page++;render()};
document.querySelector('#close').onclick=()=>preview.close();render();
</script></html>'''
(root / 'index.html').write_text(html.replace('ASSETS', json.dumps(assets).replace('<', '\\u003c')), encoding='utf-8')
print('Built', root / 'index.html')
