import {setupAtlasSplitter,setupDisplaySettings} from './layout.js';
import {AtlasMap, assetUrl} from './map.js';
import {setupTokens} from './tokens.js';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data, state, view='atlas', detailMode=false, filter='all', toastTimer, busy=0, queue=Promise.resolve(), selectedAsset;
let displayedMap='', listKey='', detailKey='';
let collection='auto', noteTimer;
const COLLECTIONS={'sunless-citadel':'Sunless Citadel','forge-of-fury':'Forge of Fury',waterdeep:'Waterdeep','sword-coast':'Sword Coast','session-00':'Session 0','session-01':'Session 1',party:'Party portraits'};
function currentCollection(){return currentMap().kind==='dungeon'?(currentMap().adventureId||'sunless-citadel'):currentMap().id==='waterdeep'?'waterdeep':'sword-coast';}
function encounterPanel(encounter){
  if(!encounter)return '';
  const level=encounter.partyLevel||data.encounters.partyLevel, size=encounter.partySize||data.encounters.partySize;
  const text=value=>esc(Array.isArray(value)?value.join('\n'):value||'').replace(/\n/g,'<br>');
  const nameLink=c=>c.statLink?`<a target="_blank" rel="noopener" href="${esc(c.statLink)}">${esc(c.name)} ↗</a>`:esc(c.name);
  const roster=encounter.instances?.length?`<p><b>Separate rooms—use only the chamber entered:</b></p><ul>${encounter.instances.map(i=>`<li><b>${esc(i.name)}:</b> ${esc(i.creatures)}</li>`).join('')}</ul><details><summary>Creature stat references</summary><p>${(encounter.creatures||[]).map(nameLink).join(' · ')}</p></details>`:encounter.creatures?.length?`<table><thead><tr><th>Count</th><th>Creature</th><th>HP</th></tr></thead><tbody>${encounter.creatures.map(c=>`<tr><td>${esc(c.count)}</td><td>${nameLink(c)}</td><td>${esc(c.hp??'See stats')}</td></tr>${c.notes?`<tr><td colspan="3" class="creature-note">${text(c.notes)}</td></tr>`:''}`).join('')}</tbody></table>`:'';
  return `<section class="table-encounter"><h3>Level ${esc(level)} · ${esc(size)} characters · play at the table</h3><strong>${esc(encounter.title|| (encounter.combat?'Encounter':'No combat by default'))}</strong>${roster}${encounter.setup?`<p><b>Setup:</b> ${text(encounter.setup)}</p>`:''}${encounter.tactics?`<p><b>Run it:</b> ${text(encounter.tactics)}</p>`:''}${encounter.adjustment?`<p><b>Adjust if needed:</b> ${text(encounter.adjustment)}</p>`:''}${encounter.risk?`<p><b>Watch for:</b> ${text(encounter.risk)}</p>`:''}<small>${esc(encounter.source||'Campaign level-3 encounter plan')}</small></section>`;
}
function renderPlayerTabs(){
  $('closeAllTabs').disabled=!(state.tabs||[]).length;
  $('presentationTabs').innerHTML=(state.tabs||[]).map(t=>`<div class="presentation-tab ${t.id===state.activeTabId?'active':''}"><button data-show-tab="${esc(t.id)}" title="Show ${esc(t.title)} on the TV">${t.kind==='map'?'◈':t.kind==='guide'?'▤':'▧'} ${esc(t.title)}</button><button class="tab-close" data-close-tab="${esc(t.id)}" aria-label="Close player tab ${esc(t.title)}">×</button></div>`).join('');
  document.querySelectorAll('[data-show-tab]').forEach(b=>b.onclick=()=>action({action:'tab-select',id:b.dataset.showTab}));
  document.querySelectorAll('[data-close-tab]').forEach(b=>b.onclick=()=>action({action:'tab-close',id:b.dataset.closeTab}));
}
$('closeAllTabs').onclick=()=>action({action:'tab-close-all'});
function toast(message){$('toast').textContent=message;$('toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),2600);}
function action(payload){
  busy++;$('connection').innerHTML='<span class="status-dot"></span> Saving…';
  const next=queue.then(async()=>{const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const result=await r.json();if(!r.ok)throw Error(result.error||'Could not save');state=result;renderState();return result;});
  queue=next.catch(error=>toast(error.message)).finally(()=>{busy--;if(!busy)$('connection').innerHTML='<span class="status-dot"></span> All changes saved';});
  return queue;
}
const atlas=new AtlasMap($('mapCanvas'),{
  onZoom:percent=>$('zoomLabel').textContent=percent+'%',
  onLoad:(ready,error)=>{$('mapLoading').hidden=ready;if(error)$('mapLoading').textContent=error;},
  onSelect:async(place,shape,hide)=>{
    detailMode=true;atlas.selectedShape=shape;
    await action({action:'location',id:place.id});
    renderDetails();
  },
  onStroke:stroke=>action({action:'brush',...stroke}),
  onPing:p=>action({action:'ping',x:p.x/currentMap().width,y:p.y/currentMap().height})
});
const tokenControls=setupTokens($('tokenTools'),{atlas,action,getState:()=>state,onArm:()=>document.querySelector('[data-tool="rooms"]').click()});
function currentMap(){return data.maps.find(m=>m.id===state.mapId)||data.maps[0];}
function currentPlace(){return currentMap()?.locations.find(p=>p.id===state.locationId);}
function setView(next){
  if(next==='library'&&view!=='library'){libraryPath='';$('assetSearch').value='';}
  view=next;
  for(const id of ['atlas','library','sessions','opening','shopping','characters','aftermath']){$(id+'View').hidden=id!==next;$(id+'Nav').classList.toggle('active',id===next);}
  $('breadcrumb').textContent=({atlas:'ATLAS',library:'IMAGE LIBRARY',sessions:'SESSION DECKS',opening:'START THE ADVENTURE',shopping:'SHOPS & SUPPLIES',characters:'CHARACTERS',aftermath:'AFTER THE CITADEL'})[next];
  if(next==='atlas')requestAnimationFrame(()=>atlas.resize());
  if(next==='library')renderLibrary();if(next==='sessions')renderSessions();if(next==='opening')renderOpening();if(next==='characters')renderCharacters();
  if(next==='aftermath')renderAftermath();
}
async function renderAftermath(){
  const {mountChapter}=await import('/static/after-citadel.js');
  await mountChapter($('aftermathView'),{data,action,setView,encounterPanel,toast});
}
function renderNav(){
  $('mapCount').textContent=data.maps.length;$('assetCount').textContent=data.assets.length;
  const groups=(data.campaign?.mapGroups||[{title:'Maps',prefix:''}]).map(g=>[g.title,m=>g.mapIds?.includes(m.id)||g.adventureId&&m.adventureId===g.adventureId||g.prefix!==undefined&&m.id.startsWith(g.prefix)]);
  const opened=new Set([...$('mapNav').querySelectorAll('details[open]')].map(el=>el.dataset.group));
  $('mapNav').innerHTML=groups.map(([title,match])=>'<details class="nav-group" data-group="'+esc(title)+'" '+(opened.has(title)?'open':'')+'><summary>'+esc(title)+'</summary>'+data.maps.filter(match).map(m=>'<button class="map-nav-item '+(m.id===state.mapId?'active':'')+'" data-map="'+esc(m.id)+'"><span class="map-dot"></span><span>'+esc(m.title)+'<small>'+(m.kind==='dungeon'?'Dungeon map':'Regional map')+'</small></span></button>').join('')+'</details>').join('');
  $('mapNav').querySelectorAll('button').forEach(b=>b.onclick=async()=>{setView('atlas');detailMode=false;atlas.selectedShape=0;await action({action:'map',mapId:b.dataset.map});});
}
function renderState(){
  if(!data||!state)return;
  renderPlayerTabs();
  if(view==='opening')renderOpening();
  const m=currentMap();if(!m){$('mapLoading').textContent='No maps found in this prepared workspace.';return;}
  const dungeon=m.kind==='dungeon';
  if(displayedMap!==m.id){
    displayedMap=m.id;listKey='';detailMode=false;renderNav();$('placeSearch').value='';
    $('mapTitle').textContent=m.title;$('mapSubtitle').textContent=m.subtitle||'';$('mapEyebrow').textContent=data.campaign.title||'PREPARED CAMPAIGN';
    $('mapMeta').textContent=dungeon?`${m.locations.length} areas · ${m.partySize||data.encounters.partySize} level-${m.partyLevel||data.encounters.partyLevel} characters · fights at the table`:`${m.locations.length} places to explore`;
    $('mapCorner').textContent=m.title.toUpperCase();$('mapCornerSub').textContent=m.subtitle||data.campaign.title||'Prepared campaign';
    $('levelNotes').hidden=!m.runningNotes;$('levelNotes').open=false;$('levelNotesText').textContent=m.runningNotes||'';
    $('worldTools').hidden=dungeon;$('dungeonTools').hidden=!dungeon;document.querySelectorAll('.dungeon-only').forEach(e=>e.hidden=!dungeon);
    $('mapHelp').textContent=dungeon?'Click room for DM notes · use Reveal to share · Space + drag to pan · Alt-click to ping':'Scroll to zoom · drag to pan · click a marker';
    $('placeSearch').placeholder=dungeon?'Find a room…':'Find a place…';
    $('sourceCard').innerHTML=`<span class="source-label">FROM YOUR LIBRARY</span><p>${esc(m.source||'Local 5e.tools library')}</p><a href="${esc(m.sourceLink||'/reference/index.html')}" target="_blank" rel="noopener">${m.original?'Read campaign preparation':'Read source in 5e.tools'} ↗</a>`;
    $('mapFooter').textContent=m.original?'ORIGINAL CAMPAIGN FLOORPLAN · PLAYER-SAFE VIEW':dungeon?'OFFICIAL BOOK MAP · PLAYER-SAFE VIEW':'OFFICIAL MAP · CAMPAIGN LOCATIONS';
  }
  $('blackout').classList.toggle('is-on',state.blackout);$('blackout').title=state.blackout?'Restore player screen':'Black out player screen';
  $('returnPlayerMap').hidden=!state.overlay;
  document.querySelector('.live-badge').innerHTML='<span></span> '+(state.blackout?'TV BLACKOUT':state.overlay?'PICTURE ON TV':'PLAYER MAP');
  $('fogStatus').textContent=dungeon?`${state.revealed?.length||0} areas revealed · changes saved`:(state.overlay?'Picture is on the player screen':'Click a place to discover more');
  
  $('undoFog').disabled=!(state.fogState?.operations?.length);
  atlas.set(m,state);
  tokenControls.update(state);
  const key=JSON.stringify([m.id,state.locationId,state.revealed,atlas.selectedShape,state.roomNotes]);
  if(key!==listKey){listKey=key;renderPlaces();renderDetails();}
}
function renderPlaces(){
  const m=currentMap(),q=$('placeSearch').value.toLowerCase();$('locationCount').textContent=m.locations.length;
  $('locationList').innerHTML=m.locations.filter(p=>(p.name+' '+(p.number||'')).toLowerCase().includes(q)).map(p=>{
    const shown=state.revealed?.some(id=>id.startsWith(p.id+':'));
    return `<button class="place-item ${state.locationId===p.id?'selected':''} ${shown?'revealed':''}" data-location="${esc(p.id)}"><span class="place-symbol">${p.number|| (p.kind==='ward'?'◇':'⌖')}</span><span><span class="place-name">${esc(p.name.replace(/^\d+\.\s*/,''))}</span><span class="place-kind">${esc(m.kind==='dungeon'?(shown?'Revealed area':'Hidden from players'):p.kind||'Location')}</span></span><span class="place-arrow">›</span></button>`;
  }).join('')||'<div class="empty-state">No places found.</div>';
  $('locationList').querySelectorAll('button').forEach(b=>b.onclick=async()=>{atlas.selectedShape=0;detailMode=true;await action({action:'location',id:b.dataset.location});atlas.focus(currentPlace());renderDetails();});
}
function renderDetails(){
  if(document.activeElement?.id==='roomNotes'||$('narrationEditor')?.dataset.roomKey===currentMap().id+':'+currentPlace()?.id)return;
  $('locationList').hidden=detailMode;$('locationDetail').hidden=!detailMode;document.querySelector('.place-search').hidden=detailMode;
  $('sourceCard').hidden=detailMode;
  $('placesTab').classList.toggle('active',!detailMode);$('detailsTab').classList.toggle('active',detailMode);
  const p=currentPlace(),m=currentMap();
  if(!p){$('locationDetail').innerHTML='<div class="empty-state">Choose a place on the map or from the list.</div>';return;}
  const dungeon=m.kind==='dungeon',shape=atlas.selectedShape||0,shown=state.revealed?.includes(`${p.id}:${shape}`);
  const key=m.id+':'+p.id+':'+shape;
  if(detailKey!==key){$('locationDetail').scrollTop=0;detailKey=key;}
  $('locationDetail').innerHTML=`<div class="detail-kicker">${dungeon?'AREA '+p.number+(p.shapes.length>1?' · SECTION '+(shape+1):''):esc(p.kind||'Location')}</div><h2>${esc(p.name.replace(/^\d+\.\s*/,''))}</h2>${p.picture?`<img class="detail-picture" src="${assetUrl(p.picture)}" alt="${esc(p.name)}">`:''}<p>${esc(p.summary||'')}</p>${p.campaignPlacement?'<div class="outline-badge">OUR CAMPAIGN PLACEMENT</div>':''}<div class="detail-actions">${dungeon?`<button class="button gold" id="toggleRoom">${shown?'Hide this area':'Reveal this area'}</button>`:''}<button class="button" id="focusPlace">⛶ &nbsp; Focus on map</button>${p.picture?'<button class="button" id="showRoomPicture">↗ &nbsp; Show picture to players</button>':''}</div>${p.dmNotes?`<div class="dm-note"><strong>DM NOTES · ONLY YOU SEE THIS</strong><p>${esc(p.dmNotes).replace(/\n/g,'<br>')}</p></div>`:''}<p class="detail-source">SOURCE<br>${esc(p.source||m.source||'Local 5e.tools library')}</p><a class="detail-source" href="${esc(p.sourceLink||m.sourceLink||'/reference/index.html')}" target="_blank" rel="noopener">Open source ↗</a>`;
  if($('toggleRoom')){$('toggleRoom').textContent='Reveal remaining fog';$('toggleRoom').onclick=()=>action({action:'room',id:p.id,shape,reveal:true});const hide=document.createElement('button');hide.className='button';hide.textContent='Hide this room';hide.onclick=()=>action({action:'room',id:p.id,shape,reveal:false});$('toggleRoom').after(hide);}
  $('focusPlace').onclick=()=>atlas.focus(p);
  if(p.targetMap){const button=document.createElement('button');button.className='button gold';button.textContent='Explore '+(data.maps.find(x=>x.id===p.targetMap)?.title||'map')+' →';button.onclick=()=>action({action:'map',mapId:p.targetMap});$('locationDetail').querySelector('.detail-actions').prepend(button);}
  if($('showRoomPicture'))$('showRoomPicture').onclick=()=>present(p.picture);
  const scene=p.scenes?.find(s=>s.shape===shape);
  if(scene){const show=document.createElement('button');show.className='button gold';show.textContent='Show room scene';show.disabled=!shown;show.title=shown?'Show the prepared scene with a clickable map preview':'Reveal this room first';show.onclick=()=>action({action:'room-scene',mapId:m.id,id:p.id,shape});$('locationDetail').querySelector('.detail-actions').append(show);}
  if(p.readAloudGr){
    const narration=document.createElement('section');narration.className='greek-narration';
    narration.innerHTML=`<div class="detail-kicker">GREEK NARRATION · ${p.narrationKind==='original-observation'?'ORIGINAL OBSERVATION':'READ ALOUD'}</div><p lang="el">${esc(p.readAloudGr).replace(/\n/g,'<br>')}</p>${p.deliveryNote?`<small>${esc(p.deliveryNote)}</small>`:''}${(p.additionalPassages||[]).map(part=>`<details><summary>${esc(part.trigger||part.title||'Additional passage')}</summary><p lang="el">${esc(part.readAloudGr||part.text||'').replace(/\n/g,'<br>')}</p></details>`).join('')}`;
    $('locationDetail').querySelector('.detail-actions').after(narration);
    if((data.campaign.narrationMaps||[]).includes(m.id)){
      const edit=document.createElement('button');edit.className='button small';edit.textContent='Edit Greek narration';narration.append(edit);
      edit.onclick=()=>{
        edit.hidden=true;const form=document.createElement('form');form.id='narrationEditor';form.dataset.roomKey=m.id+':'+p.id;
        form.innerHTML=`<label for="narrationText">Greek read-aloud · DM preparation</label><textarea id="narrationText" lang="el" maxlength="20000" rows="10">${esc(p.readAloudGr)}</textarea><div class="detail-actions"><button class="button gold" type="submit">Save narration</button><button class="button" type="button" id="cancelNarration">Cancel</button></div><small role="status" id="narrationStatus">Saved to the room's preparation, separate from the shared notepad.</small>`;
        narration.append(form);$('cancelNarration').onclick=()=>{form.remove();edit.hidden=false;};
        form.onsubmit=async e=>{e.preventDefault();const button=form.querySelector('[type=submit]');button.disabled=true;try{const response=await fetch('/api/narration',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mapId:m.id,id:p.id,readAloudGr:$('narrationText').value})});const result=await response.json();if(!response.ok)throw Error(result.error||'Could not save narration');p.readAloudGr=result.readAloudGr;form.remove();renderDetails();toast('Greek narration saved');}catch(error){$('narrationStatus').textContent=error.message;button.disabled=false;}};
      };
    }
  }
  if(p.npcDialogueGr?.length){const lines=document.createElement('section');lines.className='greek-narration npc-dialogue';lines.innerHTML='<h3>NPC dialogue · Greek</h3><small>Optional lines · use only what this NPC knows.</small>'+p.npcDialogueGr.map(n=>`<details open><summary>${esc(n.speaker)}</summary><small>${esc(n.when||'')}</small>${n.lines.map(l=>`<p lang="el"><b>${esc(l.cue)}:</b> ${esc(l.lineGr)}</p>`).join('')}</details>`).join('');$('locationDetail').querySelector('.detail-actions').after(lines);}
  if(dungeon){
    const notebook=document.createElement('section');notebook.className='shared-notepad';
    notebook.innerHTML=`<label for="roomNotes">SHARED ROOM NOTEPAD</label><p>Visible to players when this area is revealed.</p><textarea id="roomNotes" maxlength="20000" placeholder="What the party sees, encounters, or leaves here…">${esc(state.roomNotes?.[`${p.id}:${shape}`]||'')}</textarea><small id="noteStatus">Saved automatically</small>`;
    $('locationDetail').querySelector('.detail-actions').after(notebook);
    $('roomNotes').oninput=e=>{clearTimeout(noteTimer);const text=e.target.value;$('noteStatus').textContent='Saving…';noteTimer=setTimeout(async()=>{await action({action:'room-note',mapId:m.id,id:p.id,shape,text});if($('noteStatus'))$('noteStatus').textContent='Saved · shared with players';},500);};
  }
  if(p.encounter)$('locationDetail').querySelector('.detail-actions').insertAdjacentHTML('afterend',encounterPanel(p.encounter));
  for(const cue of p.privateCues||[]){
    const beat=document.createElement('details');beat.className='private-story-cue';
    beat.innerHTML=`<summary>${esc(cue.title)} · DM only</summary><p>${esc(cue.trigger||cue.goal)}</p><p lang="el">${esc(cue.readAloudGr)}</p>${(cue.npcLines||[]).map(n=>`<p lang="el"><b>${esc(n.speaker)}:</b> ${esc(n.lineGr)}</p>`).join('')}<button class="button small">Open full scene</button>`;
    beat.querySelector('button').onclick=()=>{$('aftermathView').dataset.scene=cue.id;setView('aftermath');};
    $('locationDetail').querySelector('.detail-actions').after(beat);
  }
  if(m.adventureId==='forge-of-fury'){
    const narration=$('locationDetail').querySelector('.greek-narration');
    if(narration)$('locationDetail').querySelector('.detail-actions').after(narration);
  }
}
async function present(path){await action({action:'picture',path});toast('Picture sent to the player screen');}
function assetGroup(a){if(a.path.startsWith('sessions/'))return 'session';if(a.category==='map'||a.path.startsWith('maps/'))return 'map';if(['illustration','portrait','room-scene'].includes(a.category))return 'illustration';return 'reference';}
function assetCard(a,index){const pdf=a.path.toLowerCase().endsWith('.pdf');return `<button class="asset-card" data-asset="${index}"><div class="asset-card-image">${pdf?'<span class="pdf-placeholder">PDF</span>':`<img src="${assetUrl(a.path)}" alt="${esc(a.title)}" loading="lazy">`}<span class="asset-badge">${a.spoiler?'DM REFERENCE':'CAN PRESENT'}</span></div><div class="asset-card-info"><strong>${esc(a.title)}</strong><small>${esc(a.category?.replaceAll('-',' ')||'image')}</small></div></button>`;}
function bindAssets(root){root.querySelectorAll('[data-asset]').forEach(b=>b.onclick=()=>previewAsset(data.assets[Number(b.dataset.asset)]));}
let libraryPath='';
function renderLibrary(){
  const prefix=libraryPath?libraryPath+'/':'';
  $('collectionTabs').innerHTML='<button id="libraryHome">Folders</button>'+libraryPath.split('/').filter(Boolean).map((part,i)=>'<button data-library-path="'+esc(libraryPath.split('/').slice(0,i+1).join('/'))+'">'+esc(part)+'</button>').join('');
  $('libraryHome').onclick=()=>{libraryPath='';$('assetSearch').value='';renderLibrary();};
  document.querySelectorAll('[data-library-path]').forEach(button=>button.onclick=()=>{libraryPath=button.dataset.libraryPath;$('assetSearch').value='';renderLibrary();});
  const q=$('assetSearch').value.toLowerCase(),items=data.assets.map((a,i)=>({a,i})).filter(({a})=>a.path.startsWith(prefix));
  const folders=[...new Set(items.map(({a})=>a.path.slice(prefix.length).split('/')).filter(parts=>parts.length>1).map(parts=>parts[0]))].sort();
  const files=items.filter(({a})=>(q||!a.path.slice(prefix.length).includes('/'))&&(filter==='all'||assetGroup(a)===filter)&&(a.title+' '+a.path).toLowerCase().includes(q));
  $('libraryTotal').textContent=folders.length+' FOLDERS · '+items.length+' FILES';
  $('assetGrid').innerHTML=(!q?folders.map(name=>'<button class="folder-card" data-folder="'+esc(prefix+name)+'"><span class="folder-icon">▰</span><strong>'+esc(name)+'</strong><small>Open folder →</small></button>').join(''):'')+files.map(({a,i})=>assetCard(a,i)).join('');
  if(!$('assetGrid').innerHTML)$('assetGrid').innerHTML='<p>No matching files.</p>';
  document.querySelectorAll('[data-folder]').forEach(button=>button.onclick=()=>{libraryPath=button.dataset.folder;renderLibrary();});bindAssets($('assetGrid'));
}
function previewAsset(a){
  selectedAsset=a;const pdf=a.path.toLowerCase().endsWith('.pdf');$('assetPreview').innerHTML=pdf?`<iframe src="${assetUrl(a.path)}" title="${esc(a.title)}"></iframe>`:`<img src="${assetUrl(a.path)}" alt="${esc(a.title)}">`;
  $('assetInfo').innerHTML=`<div class="detail-kicker">${a.spoiler?'DM REFERENCE · KEPT OFF THE PLAYER SCREEN':esc(a.category||'CAMPAIGN IMAGE')}</div><h2>${esc(a.title)}</h2><code>${esc(a.path)}</code><p>${esc(a.source||a.sourcePage||'Local campaign asset')}</p><div class="detail-actions">${!a.spoiler&&!pdf?'<button class="button gold" id="presentAsset">↗ Show to players</button>':''}<a class="button" href="${assetUrl(a.path)}" target="_blank" rel="noopener">Open original ↗</a>${a.sourceUrl?`<a class="button" href="${esc(a.sourceUrl)}" target="_blank" rel="noopener">Source ↗</a>`:''}<button class="button" id="returnMap">Return TV to map</button></div>`;
  if($('presentAsset'))$('presentAsset').onclick=()=>present(a.path);
  $('returnMap').onclick=()=>{action({action:'map-view'});toast('Player screen returned to map');};
  $('assetDialog').showModal();
}
function renderSessions(){
  const guide=data.guide||{cards:[]};
  const tour=guide.cards.length?`<section class="world-guide"><div class="eyebrow">SESSION 0 · THE WORLD IN PLAY</div><h2>${esc(guide.title)}</h2><p>${esc(guide.description)}</p><div class="guide-cards">${guide.cards.map(c=>`<article class="guide-card"><span class="detail-kicker">${c.optional?'OPTIONAL DEEPER DIVE':'ESSENTIAL'}</span><h3>${esc(c.title)}</h3><p>${esc(c.summary)}</p><details><summary>Greek narration & table prompt</summary><p class="guide-greek" lang="el">${esc(c.readAloudGr).replace(/\n/g,'<br>')}</p><p><strong>Ask the table:</strong> ${esc(c.prompt||'')}</p><p>${esc(c.dmNotes||'')}</p><small>${esc(c.source||'')}</small></details><div class="detail-actions"><button class="button gold" data-book="${esc(c.id)}">Show book section</button><button class="button" data-guide="${esc(c.id)}">Show summary</button></div></article>`).join('')}</div></section>`:'';
  const deck=s=>`<section class="session-section"><h2>${esc(s.title)}</h2><p>${esc(s.description)}</p><div class="asset-grid">${s.slides.map(sl=>{const index=data.assets.findIndex(a=>a.path===sl.path);return index>=0?assetCard({...data.assets[index],title:sl.title||data.assets[index].title},index):'';}).join('')}</div></section>`;
  const starter=data.sessions.filter(s=>['session-00','session-01'].includes(s.id));
  const other=data.sessions.filter(s=>!['session-00','session-01'].includes(s.id));
  $('sessionDecks').innerHTML='<details class="starter-decks"><summary>Starter materials · world introduction and opening sessions</summary>'+tour+starter.map(deck).join('')+'</details>'+other.map(deck).join('');bindAssets($('sessionDecks'));
  document.querySelectorAll('[data-book]').forEach(b=>b.onclick=()=>action({action:'book-section',cardId:b.dataset.book}));
  document.querySelectorAll('[data-guide]').forEach(b=>b.onclick=()=>action({action:'guide',cardId:b.dataset.guide}));
}
let openingKey='';
function renderOpening(){
  const scenes=data.opening?.scenes||[];
  if(!scenes.length){$('openingScene').textContent='No opening scenes are available.';return;}
  const index=Math.max(0,scenes.findIndex(s=>s.id===state.openingSceneId));
  const scene=scenes[index];
  if(openingKey===scene.id)return;
  openingKey=scene.id;
  $('openingProgress').textContent=`SCENE ${index+1} OF ${scenes.length}`;
  $('openingOutline').innerHTML=scenes.map((s,i)=>`<button class="opening-step ${s.id===scene.id?'active':''}" data-scene="${esc(s.id)}"><span>${i+1}</span><span>${esc(s.title)}<small>${esc(s.duration||s.stage||'')}</small></span></button>`).join('');
  document.querySelectorAll('[data-scene]').forEach(b=>b.onclick=()=>action({action:'opening-scene',id:b.dataset.scene}));
  const image=scene.picture?data.assets.find(a=>a.path===scene.picture):null;
  $('openingScene').innerHTML=`<div class="scene-heading"><span class="detail-kicker">${esc(scene.stage||'OPENING')}</span><h2>${esc(scene.title)}</h2><p>${esc(scene.goal||'')}</p></div><div class="scene-material"><section class="scene-readaloud"><h3>Read aloud · Greek</h3><p lang="el">${esc(scene.readAloudGr||'').replace(/\n/g,'<br>')}</p></section>${image?`<aside class="scene-picture"><img src="${assetUrl(image.path)}" alt="${esc(image.title)}"><button class="button gold" id="presentSceneImage">Show picture to players</button><small>${esc(image.title)}</small></aside>`:''}</div><section class="scene-run"><h3>Run this scene</h3><ol>${(scene.run||[]).map(t=>`<li>${esc(t)}</li>`).join('')}</ol></section>${scene.npcLines?.length?`<section class="scene-dialogue"><h3>NPC lines · Greek</h3>${scene.npcLines.map(line=>`<div><strong>${esc(line.speaker)}</strong><p lang="el">${esc(line.lineGr)}</p></div>`).join('')}</section>`:''}${scene.facts?.length?`<details class="scene-reference"><summary>Details to have ready</summary><ul>${scene.facts.map(t=>`<li>${esc(t)}</li>`).join('')}</ul></details>`:''}<section class="scene-next"><h3>Move on when</h3><p>${esc(scene.next||'')}</p></section><div class="scene-actions">${scene.mapId?'<button class="button" id="presentSceneMap">Show this location on the map</button>':''}${scene.mapId?.startsWith('citadel-')?'<button class="button gold" id="useDungeonControls">Use dungeon controls →</button>':''}${scene.sourceLink?`<a class="button" target="_blank" rel="noopener" href="${esc(scene.sourceLink)}">Open book source · DM only ↗</a>`:''}</div><p class="detail-source">${esc(scene.source||'')}</p><div class="scene-paging"><button class="button" id="previousScene" ${index===0?'disabled':''}>← Previous scene</button><button class="button gold" id="nextScene" ${index===scenes.length-1?'disabled':''}>Next scene →</button></div>`;
  if($('presentSceneImage'))$('presentSceneImage').onclick=()=>present(scene.picture);
  if(scene.encounter)$('openingScene').querySelector('.scene-run').insertAdjacentHTML('afterend',encounterPanel(scene.encounter));
  if(scene.shopping){const button=document.createElement('button');button.className='button gold';button.textContent='Open Castle Ward shops →';button.onclick=()=>setView('shopping');$('openingScene').querySelector('.scene-actions').prepend(button);}
  if(scene.extraPictures?.length){const related=document.createElement('section');related.className='scene-related';related.setAttribute('aria-label','More scene pictures');related.innerHTML=scene.extraPictures.map(path=>{const asset=data.assets.find(a=>a.path===path);return asset&&!asset.spoiler?`<figure class="scene-picture-choice"><img src="${assetUrl(path)}" alt="${esc(asset.title)}" loading="lazy"><figcaption>${esc(asset.title)}</figcaption><button class="button" data-scene-picture="${esc(path)}">Show ${esc(asset.title)}</button></figure>`:'';}).join('');$('openingScene').querySelector('.scene-material').after(related);related.querySelectorAll('button').forEach(b=>b.onclick=()=>present(b.dataset.scenePicture));}
  for(const reference of scene.references||[]){const link=document.createElement('a');link.className='button';link.href=reference.url;link.target='_blank';link.rel='noopener';link.textContent=reference.title+' · DM ↗';$('openingScene').querySelector('.scene-actions').append(link);}
  if($('presentSceneMap'))$('presentSceneMap').onclick=async()=>{await action({action:'map',mapId:scene.mapId});if(scene.targetLocationId)await action({action:'location',id:scene.targetLocationId});toast('Map sent to the player screen');};
  if($('useDungeonControls'))$('useDungeonControls').onclick=async()=>{await action({action:'map',mapId:scene.mapId});if(scene.targetLocationId)await action({action:'location',id:scene.targetLocationId});setView('atlas');};
  $('previousScene').onclick=()=>action({action:'opening-scene',id:scenes[Math.max(0,index-1)].id});
  $('nextScene').onclick=()=>action({action:'opening-scene',id:scenes[Math.min(scenes.length-1,index+1)].id});
}
$('atlasNav').onclick=()=>setView('atlas');$('libraryNav').onclick=()=>setView('library');$('sessionsNav').onclick=()=>setView('sessions');
$('openingNav').onclick=()=>setView('opening');
$('aftermathNav').onclick=()=>setView('aftermath');
$('shoppingNav').onclick=()=>setView('shopping');
$('presentShop').onclick=()=>action({action:'shop-catalog'});
$('shopMap').onclick=async()=>{const cue=data.campaign.shoppingCue;if(cue){await action({action:'map',mapId:cue.mapId});await action({action:'location',id:cue.locationId});}};
$('startAfterCreation').hidden=true;$('startAfterCreation').onclick=()=>setView('opening');
$('placesTab').onclick=()=>{detailMode=false;renderDetails();};$('detailsTab').onclick=()=>{detailMode=true;renderDetails();};
$('placeSearch').oninput=renderPlaces;$('assetSearch').oninput=renderLibrary;
$('assetFilters').querySelectorAll('button').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll('#assetFilters button').forEach(x=>x.classList.toggle('active',x===b));renderLibrary();});
document.querySelectorAll('[data-tool]').forEach(b=>b.onclick=()=>{atlas.tool=b.dataset.tool;document.querySelectorAll('[data-tool]').forEach(x=>x.classList.toggle('active',x===b));$('mapCanvas').style.cursor=atlas.tool==='rooms'?'grab':'crosshair';});
$('brushSize').oninput=e=>{atlas.radius=Number(e.target.value);$('brushSize').setAttribute('aria-valuetext',e.target.value+' map pixels');$('brushSizeValue').textContent=e.target.value;atlas.draw();};
$('fitMap').onclick=()=>atlas.fit();$('zoomIn').onclick=()=>atlas.zoom(1.4);$('zoomOut').onclick=()=>atlas.zoom(1/1.4);
$('undoFog').onclick=()=>action({action:'undo'});
$('resetFog').onclick=()=>{$('resetExplanation').textContent='Your reveals and brush strokes on this level will be cleared. '+(currentMap().initialRevealed?.length?'Only the entrance will remain visible.':'The whole level will be hidden.');$('resetDialog').showModal();};
$('cancelReset').onclick=()=>$('resetDialog').close();
$('confirmReset').onclick=async()=>{await action({action:'reset'});$('resetDialog').close();toast('Fog reset to the starting view');};
$('blackout').onclick=()=>action({action:'blackout',value:!state.blackout});
$('returnPlayerMap').onclick=()=>action({action:'map-view'});
$('openPlayer').onclick=()=>{const w=window.open('/player','campaign-player','popup=yes,width=1280,height=800');if(!w)toast('Allow popups to open the player screen. You can also open /player in another tab.');else toast('Drag the player window to the TV. Press F for fullscreen.');};
$('closeDialog').onclick=()=>$('assetDialog').close();$('assetDialog').onclick=e=>{if(e.target===$('assetDialog'))$('assetDialog').close();};
async function poll(){try{if(!busy){const r=await fetch('/api/state');if(!r.ok)throw Error();const next=await r.json();if(next.version!==state?.version||next.tableVersion!==state?.tableVersion){state=next;renderState();}$('connection').innerHTML='<span class="status-dot"></span> All changes saved';}}catch{$('connection').textContent='Connection lost · retrying…';}finally{setTimeout(poll,700);}}
try{const responses=await Promise.all([fetch('/api/data'),fetch('/api/state')]);if(responses.some(r=>!r.ok))throw Error('Could not load campaign data');[data,state]=await Promise.all(responses.map(r=>r.json()));renderNav();window.preparedCapabilities(data);renderState();const requestedView=new URLSearchParams(location.search).get('view');if(['atlas','library','sessions','opening','shopping','characters','aftermath'].includes(requestedView)&&!$(requestedView+'Nav')?.hidden)setView(requestedView);poll();}catch(error){$('mapLoading').textContent=error.message;toast(error.message);}

$('charactersNav').onclick=()=>setView('characters');
async function renderCharacters(){
  const {mountCharacters}=await import('/static/characters.js');
  await mountCharacters($('characterCards'));
}

setupAtlasSplitter();
setupDisplaySettings();
