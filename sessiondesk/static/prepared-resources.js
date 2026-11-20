import {esc} from './campaign.js';
import {renderRoomSource} from './book.js';
const catalogs=new WeakMap();

function loadCatalog(surface,call){
  if(!catalogs.has(surface)){
    const catalog=call('data').then(data=>{
      const archivedMaps=new Set(data.campaign.archivedMapIds||[]);
      const archivedAssets=data.campaign.archivedAssetPrefixes||[];
      data.maps=data.maps.filter(map=>!archivedMaps.has(map.id));
      data.assets=data.assets.filter(asset=>!archivedMaps.has(asset.mapId)&&!archivedAssets.some(prefix=>asset.path.startsWith(prefix)));
      return data;
    }).catch(error=>{catalogs.delete(surface);throw error;});
    catalogs.set(surface,catalog);
  }
  return catalogs.get(surface);
}

export async function mountPrepared(surface,{base,href,route,selection,setupInspectorResize,isCurrent}){
  let alive=true,timer,atlas,selectedRoom=selection.room;
  let selectedShape=0;
  const call=async(path,body)=>{const response=await fetch(base+'/api/'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});const result=await response.json();if(!response.ok)throw Error(result.error||'Campaign request failed');return result;};
  const data=await loadCatalog(surface,call);
  if(!isCurrent())return;
  const map=data.maps.find(candidate=>candidate.id===selection.map)||data.maps[0];
  if(!map){surface.textContent='No prepared maps to display.';return;}
  let layout=surface.querySelector('.campaign-map-layout');
  if(!layout){
    const groupFor=m=>(data.campaign.mapGroups||[]).filter(g=>g.prefix&&m.id.startsWith(g.prefix)).sort((a,b)=>b.prefix.length-a.prefix.length)[0]?.title||m.group||m.adventureId||'General';
    surface.innerHTML=`<main class="campaign-map-layout"><aside class="campaign-index"><h2>Resources</h2>${[...new Set(data.maps.map(m=>groupFor(m)))].map(group=>`<details open><summary>${esc(group)}</summary>${data.maps.filter(m=>(groupFor(m))===group).map(m=>`<a class="book-entry" data-map-id="${esc(m.id)}" href="${href({section:'resources',prepared:'1',map:m.id,room:null})}">${esc(m.title)}</a>`).join('')}</details>`).join('')}<details><summary>Images (${data.assets.length})</summary>${data.assets.map((a,i)=>`<button data-picture="${i}">${esc(a.title||a.name||a.path.split('/').at(-1))}</button>`).join('')}</details></aside></main>`;
    layout=surface.querySelector('.campaign-map-layout');
  }
  const index=layout.querySelector('.campaign-index');
  for(const link of index.querySelectorAll('[data-map-id]')){
    const selected=link.dataset.mapId===map.id;
    link.classList.toggle('active',selected);
    if(selected)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
  }
  const oldPanel=layout.querySelector('.prepared-map-content');
  const root=document.createElement('div');
  root.className='prepared-map-content';
  root.innerHTML='<section class="campaign-map-main"><p role="status">Loading map…</p></section>';
  if(oldPanel)oldPanel.replaceWith(root);else layout.append(root);
  const current=()=>alive&&isCurrent()&&root.isConnected;
  const dispose=()=>{alive=false;clearTimeout(timer);atlas?.dispose();};
  let state;
  try {
    state=await call('map-state?mapId='+encodeURIComponent(map.id));
  }catch(error){
    if(current())root.querySelector('[role=status]').textContent=error.message;
    return dispose;
  }
  if(!current())return dispose;
  root.innerHTML=`<section class="campaign-map-main"><h1>${esc(map.title)}</h1><div class="row map-tools"><button id="present-map" class="primary">Present map</button><button data-tool="rooms" class="active">Pan / rooms</button><button data-tool="reveal">Reveal</button><button data-tool="hide">Hide</button><label>Brush <input id="preview-brush" type="range" min="5" max="250" value="48"></label><button id="fit-map">Fit</button><button id="undo-map">Undo fog</button></div><p id="map-status" role="status">Inspecting only · use Present map to show this map</p><div class="preview-map-stage"><canvas id="preview-map" tabindex="0" aria-label="Campaign map"></canvas><span id="preview-map-loading">Loading map…</span></div><div id="preview-player-tabs" class="tabs"></div></section><div class="inspector-divider" role="separator" aria-label="Resize room panel" aria-controls="prepared-room-panel" aria-orientation="vertical" aria-valuemin="280" tabindex="0"></div><aside class="campaign-room" id="prepared-room-panel"><label>Room<select id="preview-room"><option value="">Choose a room</option>${map.locations.map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('')}</select></label><div id="preview-room-detail"></div></aside>`;
  const status=root.querySelector('#map-status');let loaded=false;root.querySelector('#preview-room').disabled=true;root.querySelectorAll('.map-tools button').forEach(b=>b.disabled=true);
  const act=async body=>{if(!current())return;try{await call('action',{mapId:map.id,...body});await refresh();}catch(e){status.textContent=e.message;}};
  const localState=()=>({...state,locationId:selectedRoom});
  const [{AtlasMap},{renderEncounter}]=await Promise.all([
    import(base+'/static/map.js'),import(base+'/static/after-citadel.js')
  ]);
  if(!current())return dispose;
  setupInspectorResize(layout);
  const assetUrl=path=>base+'/assets/'+path.split('/').map(encodeURIComponent).join('/');
  const paragraph=(text,lang='')=>text?`<p class="book-paragraph"${lang?' lang="'+lang+'"':''}>${esc(text)}</p>`:'';
  const prepSection=(title,content)=>content?`<section class="room-prep"><h3>${title}</h3>${content}</section>`:'';
  const sources=new Map();
  async function showRoomSource(room, container){
    try {
      if(!sources.has(room.id)){
        const query=new URLSearchParams({mapId:map.id,roomId:room.id});
        sources.set(room.id,call('room-source?'+query).catch(error=>{sources.delete(room.id);throw error;}));
      }
      const {entry}=await sources.get(room.id);
      if(!container.isConnected)return;
      if(entry)container.innerHTML=renderRoomSource(entry,base+'/reference/');
      else container.textContent='The matching book entry is unavailable in the connected library.';
    }catch{
      if(container.isConnected)container.textContent='Could not load the book entry. Select the room again to retry.';
    }
  }
  const details=()=>{
    const room=map.locations.find(place=>place.id===selectedRoom);
    root.querySelector('#preview-room').value=room?.id||'';
    const panel=root.querySelector('#preview-room-detail');
    if(!room){panel.innerHTML='<p>Select a room to read it.</p>';return;}
    const roomKey=room.id+':'+selectedShape;
    const scene=room.scenes?.find(scene=>scene.shape===selectedShape);
    const art=scene?.path||room.picture;
    const revealed=state.revealed?.includes(roomKey);
    const passages=(room.additionalPassages||[]).map(part=>
      `<details><summary>${esc(part.trigger||part.title||'Additional passage')}</summary>${paragraph(part.readAloudGr||part.text,'el')}</details>`).join('');
    const dialogue=(room.npcDialogueGr||[]).map(npc=>
      `<details><summary>${esc(npc.speaker)}</summary>${paragraph(npc.when)}
        ${(npc.lines||[{lineGr:npc.lineGr}]).map(line=>paragraph([line.cue,line.lineGr].filter(Boolean).join(': '),'el')).join('')}</details>`).join('');
    const cues=(room.privateCues||[]).map(cue=>
      `<details class="room-prep"><summary>${esc(cue.title)} · DM only</summary>
        ${paragraph(cue.trigger||cue.goal)}${paragraph(cue.readAloudGr,'el')}
        ${(cue.npcLines||[]).map(line=>paragraph([line.speaker,line.lineGr].filter(Boolean).join(': '),'el')).join('')}
        ${(cue.run||[]).map(step=>paragraph(step)).join('')}</details>`).join('');
    panel.innerHTML=`<h2>${esc(room.name)}</h2>${paragraph(room.summary)}
      <div class="row"><button id="focus-room">Focus on map</button>
        ${map.kind==='dungeon'?'<button id="reveal-room">Reveal room</button><button id="hide-room">Hide room</button>':''}
        ${scene?`<button id="show-room-scene" ${revealed?'':'disabled'}>Show room scene</button>`:''}
      </div>
      ${room.readAloudGr||passages?`<section class="book-content room-prep"><h3>Greek narration</h3><aside class="book-box readaloud">${paragraph(room.readAloudGr,'el')}${passages}</aside>${room.deliveryNote?`<small>${esc(room.deliveryNote)}</small>`:''}</section>`:''}
      ${room.sourceLink?`<section class="book-content room-prep"><h3>From the book</h3><div data-room-source>Loading book entry…</div><p><a href="${esc(room.sourceLink)}" target="_blank" rel="noopener noreferrer">Open source in 5e.tools ↗</a></p></section>`:''}
      ${prepSection('DM notes',paragraph(room.dmNotes))}
      ${room.encounter?prepSection('Encounter',renderEncounter(room.encounter,data.encounters)):''}
      ${prepSection('NPC dialogue · Greek',dialogue)}
      ${cues}
      ${art?`<details class="room-prep"><summary>Room image</summary><img class="preview-picture" src="${assetUrl(art)}" alt="${esc(room.name)}" loading="lazy"></details>`:''}
      ${map.kind==='dungeon'?`<p>${(room.shapes||[]).some((_,i)=>state.revealed.includes(room.id+':'+i))?'Room has revealed areas':'Room is hidden'}</p>
        <label>Shared player notes<textarea id="room-notes" rows="5" maxlength="20000">${esc(state.roomNotes?.[roomKey]||'')}</textarea></label>
        <button id="save-room-notes">Save shared notes</button>`:''}`;
    const source=panel.querySelector('[data-room-source]');
    if(source)showRoomSource(room,source);
    panel.querySelector('#focus-room').onclick=()=>atlas.focus(room);
    for(const [id,reveal] of [['reveal-room',true],['hide-room',false]]){
      const control=panel.querySelector('#'+id);
      if(control)control.onclick=async()=>{
        for(let shape=0;shape<room.shapes.length;shape++)await act({action:'room',id:room.id,shape,reveal});
        if(alive&&selectedRoom===room.id)details();
      };
    }
    const sceneButton=panel.querySelector('#show-room-scene');
    if(sceneButton)sceneButton.onclick=()=>act({action:'room-scene',id:room.id,shape:selectedShape});
    const notes=panel.querySelector('#save-room-notes');
    if(notes)notes.onclick=()=>act({action:'room-note',id:room.id,shape:selectedShape,text:panel.querySelector('#room-notes').value});
  };
  function selectRoom(id,shape=0){
    root.querySelector('#prepared-room-panel').scrollTop=0;
    selectedRoom=id;
    selectedShape=shape;
    atlas.selectedShape=shape;
    route({room:id||null},{render:false});
    details();
    atlas.set(map,localState());
  }
  atlas=new AtlasMap(root.querySelector('canvas'),{onSelect:(room,shape)=>selectRoom(room.id,shape),
    onStroke:stroke=>act({action:'brush',...stroke}),onLoad:(ready,error)=>{loaded=ready;if(error)status.textContent=error;}});
  atlas.resize();await atlas.set(map,localState());
  if(!current()){dispose();return;}
  details();
  root.querySelector('#preview-room').onchange=event=>selectRoom(event.target.value);
  root.querySelectorAll('[data-tool]').forEach(b=>b.onclick=()=>{atlas.tool=b.dataset.tool;root.querySelectorAll('[data-tool]').forEach(x=>x.classList.toggle('active',x===b));atlas.draw();});
  root.querySelector('#preview-brush').oninput=e=>{atlas.radius=Number(e.target.value);atlas.draw();};
  root.querySelector('#fit-map').onclick=()=>atlas.fit();root.querySelector('#undo-map').onclick=()=>act({action:'undo'});
  root.querySelector('#present-map').onclick=()=>act({action:'map'});
  index.querySelectorAll('[data-picture]').forEach(b=>b.onclick=()=>{if(!current())return;const a=data.assets[Number(b.dataset.picture)];const panel=root.querySelector('#preview-room-detail');panel.innerHTML=`<h2>${esc(a.title||a.name||'Picture')}</h2><img class="preview-picture" src="${base}/assets/${a.path.split('/').map(encodeURIComponent).join('/')}" alt="${esc(a.title||'')}"><button id="present-picture" ${a.spoiler?'disabled title="DM reference only"':''}>Present picture</button>`;panel.querySelector('button').onclick=()=>act({action:'picture',path:a.path,title:a.title||a.name||'Picture'});});
  async function refresh(){const next=await call('map-state?mapId='+encodeURIComponent(map.id));if(!current())return;state=next;await atlas.set(map,localState());if(!current())return;status.textContent=(state.tabs||[]).some(t=>t.mapId===map.id)?'On player screen · saved fog active':'Inspecting only · use Present map to show this map';}
  async function poll(){try{await refresh();}catch{}if(current())timer=setTimeout(poll,1200);}
  await refresh();
  if(!current()){dispose();return;}
  root.querySelector('#preview-room').disabled=false;root.querySelectorAll('.map-tools button').forEach(b=>b.disabled=false);root.querySelector('#preview-map-loading').hidden=loaded;timer=setTimeout(poll,1200);
  return dispose;
}
