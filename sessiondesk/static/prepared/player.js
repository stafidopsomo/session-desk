import {AtlasMap, assetUrl} from './map.js';
import {setupTokens} from './tokens.js';
const roomLabel=id=>id==='house-outside'?'Outside':'Room '+id.replace(/^(?:forge-|house-)/,'');
const $=id=>document.getElementById(id);let state,selectedRoom=null,noteTimer,pictureRequest=0;
const atlas=new AtlasMap($('canvas'),{player:true,onSelect:(room,shape)=>{const scene=room.scenes?.find(s=>s.shape===shape);if(scene){selectedRoom=null;playerTabAction({action:'room-scene',mapId:state.mapId,id:room.id,shape});return;}selectedRoom={id:room.id,shape,mapId:state.mapId};showNotebook();},onZoom:p=>{if(!state?.overlay)$('viewZoom').textContent=p+'%';},onAnnotationChange:syncDrawingControls});
const photo=new AtlasMap($('pictureCanvas'),{player:true,onZoom:p=>{if(state?.overlay)$('viewZoom').textContent=p+'%';},onAnnotationChange:syncDrawingControls});
const tokenControls=setupTokens($('partyTools'),{atlas,action:playerTabAction,getState:()=>state,player:true});
const pictureSources=new Map();
let tabActions=Promise.resolve();
function playerTabAction(payload){
  tabActions=tabActions.catch(()=>{}).then(async()=>{try{const response=await fetch('/api/player-action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!response.ok)throw Error();await update(await response.json());$('lost').hidden=true;}catch{$('lost').hidden=false;}});
  return tabActions;
}
$('closeAllTabs').onclick=()=>playerTabAction({action:'tab-close-all'});
function activeViewer(){return state?.overlay?photo:atlas;}
function syncDrawingControls(){const history=activeViewer().inkHistory();$('undoDrawing').disabled=!history.length;$('clearDrawing').disabled=!history.length||!!history.at(-1)?.clear;}
async function showPicture(path,next){
  const request=++pictureRequest;$('pictureLoading').hidden=photo.map?.image===path&&!!photo.image;
  try{
    let image=pictureSources.get(path);
    if(!image){image=new Image();image.src=assetUrl(path);await image.decode();pictureSources.set(path,image);while(pictureSources.size>3)pictureSources.delete(pictureSources.keys().next().value);}
    if(request!==pictureRequest)return;
    photo.cacheImage(path,image);
    await photo.set({id:'picture:'+path,title:next.overlay.title||'Picture',kind:'picture',image:path,width:image.naturalWidth,height:image.naturalHeight,locations:[]},{...next,location:null,locationId:null,ping:null});
    $('pictureLoading').hidden=true;syncDrawingControls();
  }catch{$('pictureLoading').hidden=false;$('pictureLoading').textContent='Picture could not be loaded.';}
}
function showNotebook(){
  const visible=selectedRoom&&selectedRoom.mapId===state.mapId&&state.revealed.includes(`${selectedRoom.id}:${selectedRoom.shape}`)&&!state.overlay&&!state.guideCard&&!state.bookSection&&!state.emptyState;
  $('notebook').hidden=!visible;
  if(visible){$('noteTitle').textContent=roomLabel(selectedRoom.id)+(selectedRoom.shape?' · section '+(selectedRoom.shape+1):'');if(document.activeElement!==$('roomNotes'))$('roomNotes').value=state.roomNotes?.[`${selectedRoom.id}:${selectedRoom.shape}`]||'';}
  $('stage').classList.toggle('with-panel',visible||!$('location').hidden);
}
async function update(next){
  if(state&&(next.version<state.version||(next.version===state.version&&next.tableVersion<state.tableVersion)))return;
  const sceneChanged=!!state?.overlay?.scene!==!!next.overlay?.scene;
  const viewerFocused=[$('canvas'),$('pictureCanvas')].includes(document.activeElement);
  state=next;if(!next.map)return;
  const roomScene=!!next.overlay?.scene;$('stage').classList.toggle('scene-mode',roomScene);$('enlargeSceneMap').hidden=!roomScene;
  $('partyTools').hidden=next.map.kind!=='dungeon'||!!next.overlay||!!next.guideCard||!!next.bookSection||!!next.emptyState;
  $('stage').hidden=!!next.emptyState;
  $('viewTools').hidden=!!next.emptyState||!!next.guideCard||!!next.bookSection;
  $('viewFit').textContent=next.overlay?'Fit whole picture':next.map.kind==='dungeon'?'Fit revealed map':'Fit whole map';
  $('closeAllTabs').disabled=!(next.tabs||[]).length;
  $('playerTabs').replaceChildren(...(next.tabs||[]).map(t=>{const item=document.createElement('span');item.className='player-tab'+(t.id===next.activeTabId?' active':'');const label=document.createElement('button');label.className='player-tab-select';label.textContent=t.title;label.title='Show '+t.title;label.setAttribute('aria-label','Show '+t.title);label.setAttribute('aria-pressed',String(t.id===next.activeTabId));label.onclick=()=>playerTabAction({action:'tab-select',id:t.id});const close=document.createElement('button');close.className='player-tab-close';close.textContent='×';close.setAttribute('aria-label','Close '+t.title);close.onclick=()=>playerTabAction({action:'tab-close',id:t.id});item.append(label,close);return item;}));
  $('roomPicker').hidden=next.map.kind!=='dungeon'||!!next.overlay||!!next.guideCard||!!next.bookSection||!!next.emptyState;
  $('roomPicker').replaceChildren(new Option('Room notes…',''),...(next.revealed||[]).map(key=>new Option(roomLabel(key.split(':')[0])+(key.endsWith(':0')?'':' · section '+(Number(key.split(':')[1])+1)),key)));
  if(selectedRoom&&selectedRoom.mapId===next.mapId)$('roomPicker').value=`${selectedRoom.id}:${selectedRoom.shape}`;
  const mapChanged=atlas.map?.id!==next.map.id;
  $('blackout').hidden=!next.blackout;$('overlay').hidden=!next.overlay;$('guide').hidden=!next.guideCard;
  $('bookSection').hidden=!next.bookSection;
  if(next.bookSection)$('bookSection').title=next.bookSection.title||'Shared reference';
  if(next.bookSection&&$('bookSection').getAttribute('src')!==next.bookSection.url)$('bookSection').src=next.bookSection.url;
  if(next.overlay)await showPicture(next.overlay.path,next);else pictureRequest++;
  if(next.guideCard){const card=next.guideCard;$('guideTitle').textContent=card.title;$('guideSummary').textContent=card.summary||'';$('guidePrompt').textContent=card.prompt||'';const path=card.picture?assetUrl(card.picture):'';if(path){if($('guideImage').firstChild?.getAttribute('src')!==path){const img=new Image();img.src=path;img.alt='';$('guideImage').replaceChildren(img);}}else $('guideImage').replaceChildren();}
  $('location').hidden=!next.location||!!next.overlay||!!next.guideCard||!!next.bookSection;
  if(next.location){$('title').textContent=next.location.name;$('summary').textContent=next.location.summary;}
  showNotebook();await atlas.set(next.map,next);
  if(sceneChanged){atlas.resize();atlas.fit();}
  else if(mapChanged&&next.map.kind==='dungeon')atlas.fit();
  if(!next.overlay&&!next.guideCard&&!next.bookSection&&!next.emptyState)atlas.followReveal(next.playerFocus);
  tokenControls.update(next);
  if(viewerFocused)activeViewer().canvas.focus({preventScroll:true});
  syncDrawingControls();
}
$('roomNotes').oninput=e=>{clearTimeout(noteTimer);const target={...selectedRoom},text=e.target.value;$('noteStatus').textContent='Saving…';noteTimer=setTimeout(async()=>{try{const response=await fetch('/api/player-action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'room-note',mapId:target.mapId,id:target.id,shape:target.shape,text})});if(!response.ok)throw Error();$('noteStatus').textContent='Saved · shared with the table';}catch{$('noteStatus').textContent='Not saved · check the connection and try again';}},500);};
$('closeNotebook').onclick=()=>{selectedRoom=null;showNotebook();};
$('roomPicker').onchange=e=>{if(!e.target.value)return;const[id,shape]=e.target.value.split(':');selectedRoom={id,shape:Number(shape),mapId:state.mapId};showNotebook();};
async function poll(){try{const r=await fetch('/api/player-state');if(!r.ok)throw Error();const next=await r.json();$('lost').hidden=true;if(next.version!==state?.version||next.tableVersion!==state?.tableVersion)await update(next);}catch{$('lost').hidden=false;}finally{setTimeout(poll,500);}}
$('viewZoomIn').onclick=()=>activeViewer().zoom(1.3);$('viewZoomOut').onclick=()=>activeViewer().zoom(1/1.3);$('viewFit').onclick=()=>activeViewer().fit();
$('undoDrawing').onclick=()=>activeViewer().undoAnnotation();$('clearDrawing').onclick=()=>activeViewer().clearAnnotations();
document.querySelectorAll('[data-ink-tool]').forEach(button=>button.onclick=()=>{for(const viewer of[atlas,photo])viewer.annotationMode=button.dataset.inkTool;document.querySelectorAll('[data-ink-tool]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});for(const canvas of[$('canvas'),$('pictureCanvas')])canvas.style.cursor=button.dataset.inkTool==='pan'?'grab':'crosshair';});
$('inkColor').oninput=e=>{atlas.penColor=photo.penColor=e.target.value;};$('inkSize').oninput=e=>{atlas.penSize=photo.penSize=Number(e.target.value);activeViewer().draw();};
function fullscreen(){if(document.fullscreenElement)document.exitFullscreen();else document.documentElement.requestFullscreen().catch(()=>{$('hint').textContent='Use the browser fullscreen command (F11).';$('hint').hidden=false;});}
$('viewFullscreen').onclick=fullscreen;
document.addEventListener('keydown',e=>{if(e.target.matches('textarea,input'))return;if(e.key.toLowerCase()==='f')fullscreen();if(e.key==='0')activeViewer().fit();if(!e.target.matches('canvas')){if(e.key==='+'||e.key==='=')activeViewer().zoom(1.3);if(e.key==='-')activeViewer().zoom(1/1.3);}});
let hintTimer=setTimeout(()=>$('hint').hidden=true,6500);document.addEventListener('mousemove',()=>{clearTimeout(hintTimer);$('hint').hidden=false;hintTimer=setTimeout(()=>$('hint').hidden=true,2000);});poll();

$('enlargeSceneMap').onclick=()=>playerTabAction({action:'room-scene-map'});
