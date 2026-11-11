import {bookContext,renderSource} from './book.js';
const $ = (s, root = document) => root.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fragment = new URLSearchParams(location.hash.slice(1));
const params = new URLSearchParams(location.search);
const isPlayer = params.get('view') === 'player' || fragment.has('player');
const tokenKey = isPlayer ? 'playerToken' : 'dmToken';
const token = fragment.get(isPlayer ? 'player' : 'dm') || sessionStorage.getItem(tokenKey) || '';
if (token) sessionStorage.setItem(tokenKey, token);
if (isPlayer) { sessionStorage.removeItem('dmToken'); window.opener = null; }
history.replaceState(null, '', location.pathname + location.search);
const S = {wid:params.get('workspace'), aid:params.get('adventure'), boot:null, overview:null,
  graph:null, media:null, entry:null, region:null, view:'media', mode:'pan', radius:60,
  color:'#f3c76a', session:null, stage:null, search:'', pollBusy:false, boundary:[],
  sourceOpen:false, drafts:{}, navOpen:new Set(), resourceType:'all'};
let toastTimer;
function toast(text) {
  $('#toast').textContent = text; $('#toast').style.display = 'block';
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').style.display = 'none', 6000);
}
async function request(path, body = {}, binary = false) {
  const r = await fetch('/api/' + path, {method:'POST', headers:{'Content-Type':'application/json',
    Authorization:'Bearer ' + token}, body:JSON.stringify({workspace:S.wid, adventure:S.aid, ...body})});
  if (!r.ok) { const e = await r.json(); throw Error(e.error || 'Request failed.'); }
  return binary ? r.blob() : r.json();
}
function asset(m) {
  return `/asset/${encodeURIComponent(S.wid)}/${m.asset}?token=${encodeURIComponent(token)}&adventure=${encodeURIComponent(S.aid)}`;
}
function mediaItems() { return S.graph ? [...S.graph.maps, ...S.graph.pictures] : []; }
function selectedMedia() { return mediaItems().find(x => x.id === S.media); }
function selectedEntry() { return S.graph?.entries.find(x => x.id === S.entry); }
function selectedRegion() { return selectedMedia()?.regions.find(x => x.id === S.region); }
function playerVariant(m) { return m.image_type==='mapPlayer'||(!m.image_type&&/player/i.test(m.source_path||'')); }
function dmMedia() { return mediaItems().filter(m=>!playerVariant(m)); }
function sourceContext() { if(S.bookCtx?.graph!==S.graph)S.bookCtx=bookContext(S.graph,asset);return S.bookCtx; }
function bookUpgradeHint(){return S.graph.book?'':'<p class="notice">Re-import this same adventure once to add the original book layout. Existing notes, boundaries and session are kept.</p>';}
function breadcrumbs(entry) {
  const chain=[],seen=new Set();let current=entry;
  const entries=navigationIndex().entries;
  while(current&&!seen.has(current.id)){seen.add(current.id);chain.unshift(current.name);current=entries.get(current.parent);}
  return chain;
}
function pinned(kind,id) { return (S.graph.pins||[]).some(p=>p.kind===kind&&p.id===id); }
function pinButton(kind,id) { return button('pin',pinned(kind,id)?'Unpin':'Pin resource','quiet',`data-kind="${kind}" data-id="${id}"`); }
function capturePreparation() {
  const form=$('form[data-form="preparation"]');if(!form?.dataset.entry)return;
  S.drafts[form.dataset.entry]={translation:$('[name=translation]',form).value,notes:$('[name=notes]',form).value,
    status:$('[name=approved]',form).checked?'approved':'draft'};
}
const button = (action, text, klass = '', extra = '') => `<button type="button" data-action="${action}" class="${klass}" ${extra}>${text}</button>`;
function header() {
  return `<header class="top"><div class="brand"><img src="/icon.svg" alt="">Session Desk</div>
    ${S.overview ? button('home', 'Workspaces', 'quiet') : ''}<span class="title muted">${esc(S.overview?.meta.name || 'Your table, locally')}</span>
    <span class="grow"></span>${button('player', 'Open player screen', '', S.aid ? '' : 'disabled')}
    ${button('settings', 'Settings', 'quiet', 'aria-expanded="false"')}</header>`;
}
function showSettings() {
  if ($('#settings')) { $('#settings').remove(); return; }
  const panel = document.createElement('section'); panel.id = 'settings'; panel.className = 'settings';
  panel.innerHTML = `<h2>Settings</h2><h3>Display</h3><label for="text-size">DM text size</label>
    <input id="text-size" type="range" min="85" max="150" value="${localStorage.getItem('textSize') || 100}">
    <label class="check"><input id="density" type="checkbox" ${document.body.classList.contains('dense') ? 'checked' : ''}>Compact layout</label>
    <hr><h3>AI</h3><label class="check"><input type="checkbox" role="switch" aria-label="AI" disabled>Off</label>
    <p class="muted">AI preparation is unavailable in this build. Import, edit, review and play without a provider.</p>
    <hr><small>${esc(S.boot?.version || 'Development build')} · local Windows preview</small><p>${button('quit', 'Quit app', 'quiet')}</p>`;
  document.body.append(panel);
  $('#text-size').oninput = e => { document.documentElement.style.setProperty('--scale', e.target.value / 100); localStorage.setItem('textSize', e.target.value); };
  $('#density').onchange = e => { document.body.classList.toggle('dense', e.target.checked); localStorage.setItem('density', String(e.target.checked)); };
}
function disposeStage() { S.stage?.dispose(); S.stage = null; }
function home() {
  disposeStage(); S.overview = null; S.graph = null; S.aid = null; S.wid = null;
  $('#app').innerHTML = header() + `<main class="home"><div class="intro"><p class="eyebrow">Prepare · review · play</p>
    <h1>A place for your next adventure.</h1><p>Keep your sources, preparation and table in one workspace. Everything stays on this computer.</p>
    <div class="row">${button('new-workspace','New workspace','primary')}${button('restore','Restore backup','quiet')}</div></div>
    ${S.boot.workspaces.length ? `<div class="cards">${S.boot.workspaces.map(w => `<article class="card"><h2>${esc(w.name)}</h2><p class="count">${esc(w.rules || '')} · ${esc(w.language || '')}</p>
      ${button('workspace','Open workspace','',`data-id="${w.id}" ${w.unavailable ? 'disabled' : ''}`)}</article>`).join('')}</div>` :
      `<section class="empty"><h2>Start with a clean workspace</h2><p>No adventures, characters or books are included. Create a workspace, then select your own local source library.</p></section>`}</main>`;
}
async function openWorkspace(wid) {
  S.wid = wid; S.overview = await request('workspace'); S.graph = null; S.aid = null; disposeStage();
  $('#app').innerHTML = header() + `<main class="home"><p class="eyebrow">Workspace</p><h1>${esc(S.overview.meta.name)}</h1>
    <p>${esc(S.overview.meta.rules)} · Preparation language: ${esc(S.overview.meta.language)}</p>
    <div class="row">${button('import','Add adventure','primary')}${button('backup','Export backup','quiet')}</div>
    ${(S.overview.modules||[]).filter(m=>m.enabled&&m.kind==='campaign-desk-v1'&&m.schema===1).map(m=>`<section class="card prepared-workspace"><h2>${esc(m.title)}</h2><p>Prepared campaign · ${m.summary?.maps||0} maps · ${m.summary?.characters||0} characters · authored scenes, resources and saved table state.</p><p>${S.overview.rules_connected?'2014 rules library connected.':'Connect your local 2014 library to use source links and character rules. Your campaign files are already imported.'}</p><div class="row">${button('prepared','Open prepared campaign','primary')}${button('connect-rules',S.overview.rules_connected?'Change rules library':'Connect 2014 library','quiet')}${button('workspace-files','Browse files','quiet')}</div></section>`).join('')}
    <div class="cards">${S.overview.adventures.map(a => `<article class="card"><h2>${esc(a.name)}</h2>
      <p class="count">${a.maps} maps · ${a.pictures} pictures${a.warnings ? ` · ${a.warnings} import warnings` : ''}</p>
      ${button('adventure','Open adventure','',`data-id="${a.id}"`)}</article>`).join('')}</div>
    ${!S.overview.adventures.length&&!S.overview.modules?.length ? '<div class="empty"><h2>Add your first adventure</h2><p>Use your existing local 5e.tools copy, or install one at a location you choose.</p></div>' : ''}</main>`;
}
async function openAdventure(aid) {
  S.aid = aid; S.graph = await request('adventure'); S.session = await request('session');
  S.media = dmMedia()[0]?.id || null;
  S.entry = S.graph.entries[0]?.id || null; S.region = null; S.view = S.media?'media':'text'; S.search = '';S.sourceOpen=false;S.drafts={};S.navOpen=new Set();S.resourceType='all';
  renderAdventure();
}
function navigationIndex() {
  if(S.navigation?.graph===S.graph)return S.navigation;
  const entries=new Map(S.graph.entries.map(e=>[e.id,e]));
  const visible=S.graph.entries.filter(e=>e.has_heading===true||(e.has_heading===undefined&&e.name!==e.key)),ids=new Set(visible.map(e=>e.id));
  const parent=id=>{const seen=new Set();while(id&&!ids.has(id)&&!seen.has(id)){seen.add(id);id=entries.get(id)?.parent;}return id||null;};
  const nodes=visible.map((e,i)=>({id:e.id,parent:parent(e.parent),name:e.name,kind:'entry',order:e.order??i*2}));
  nodes.push(...dmMedia().map((m,i)=>({id:m.id,parent:parent(m.entry),name:m.name,kind:'media',mediaKind:m.kind,order:m.order??100000+i})));
  const children=new Map();
  for(const n of nodes){if(!children.has(n.parent))children.set(n.parent,[]);children.get(n.parent).push(n);}
  for(const siblings of children.values())siblings.sort((a,b)=>a.order-b.order);
  return S.navigation={graph:S.graph,entries,children};
}
function resourceActive(kind,id) {return kind==='entry'?S.entry===id&&(S.view==='text'||S.sourceOpen):S.media===id&&S.view==='media';}
function navigationChildren(parent=null) {
  const {children}=navigationIndex();
  return (children.get(parent)||[]).map(n=>{
    const nested=children.has(n.id),open=S.navOpen.has(n.id);
    const toggle=nested?button('toggle-group',open?'▾':'▸','group-toggle',`data-id="${n.id}" aria-expanded="${open}" aria-label="${open?'Collapse':'Expand'} ${esc(n.name)}"`):'<span class="group-spacer"></span>';
    const label=button(n.kind,`${esc(n.name)}${n.kind==='media'?`<span class="badge" aria-hidden="true">${n.mediaKind==='map'?'map':'image'}</span>`:''}`,'item'+(resourceActive(n.kind,n.id)?' active':''),`data-id="${n.id}" ${resourceActive(n.kind,n.id)?'aria-current="true"':''}`);
    return `<div class="nav-node" data-node="${n.id}"><div class="nav-row">${toggle}${label}</div>${nested?`<div class="book-children" ${open?'':'hidden'}>${open?navigationChildren(n.id):''}</div>`:''}</div>`;
  }).join('');
}
function library() {
  const q=S.search.trim().toLowerCase(),entries=S.graph.entries,media=dmMedia();
  const pins=(S.graph.pins||[]).map(p=>({pin:p,item:(p.kind==='entry'?entries:media).find(x=>x.id===p.id)})).filter(x=>x.item);
  const pinnedHTML=pins.length?`<section class="pinned-resources"><h3>Pinned</h3>${pins.map(({pin:p,item})=>`<div class="pinned-row">${button(p.kind==='entry'?'entry':'media',esc(item.name),'item',`data-id="${item.id}"`)}${button('pin','×','quiet',`data-kind="${p.kind}" data-id="${p.id}" aria-label="Unpin ${esc(item.name)}"`)}</div>`).join('')}</section>`:'';
  const filtered=q||S.resourceType!=='all';
  const search=`<div class="resource-heading"><h2>Resources</h2>${button('collapse-all','Collapse all','quiet','title="Clear search filters and return to collapsed chapters"')}</div>${pinnedHTML}<input id="search" placeholder="Search adventure resources" value="${esc(S.search)}" aria-label="Search adventure resources">
    <label class="sr-only" for="resource-type">Resource type</label><select id="resource-type">${[['all','All types'],['text','Text'],['image','Images'],['map','Maps']].map(([value,label])=>`<option value="${value}" ${S.resourceType===value?'selected':''}>${label}</option>`).join('')}</select>`;
  if(filtered){
    const matches=[...entries.filter(e=>(S.resourceType==='all'||S.resourceType==='text')&&`${e.name} ${e.text}`.toLowerCase().includes(q)).map(e=>({kind:'entry',...e})),
      ...media.filter(m=>(S.resourceType==='all'||S.resourceType===(m.kind==='map'?'map':'image'))&&m.name.toLowerCase().includes(q)).map(m=>({...m,mediaKind:m.kind,kind:'media'}))].slice(0,200);
    return search+`<div class="search-results">${matches.map(r=>button(r.kind,`${esc(r.name)}<small>${esc(r.kind==='entry'?['Text',...breadcrumbs(r).slice(0,-1)].join(' · '):[r.mediaKind==='map'?'Map':'Image',...breadcrumbs(navigationIndex().entries.get(r.entry))].join(' · '))}</small>`,'item'+(resourceActive(r.kind,r.id)?' active':''),`data-id="${r.id}"`)).join('')||'<p class="muted">No matches.</p>'}</div>`;
  }
  return search+`<nav class="book-navigation" aria-label="Adventure contents">${navigationChildren()}</nav><p>${button('add-picture','Add picture','quiet')}</p>`;
}
function toolbar() {
  const m = selectedMedia();
  return `<div class="toolbar">${button('mode-pan','Pan',S.mode === 'pan' ? 'active' : '')}
    ${m?.kind === 'map' ? `${button('mode-reveal','Reveal',S.mode === 'reveal' ? 'active' : '')}${button('mode-hide','Hide',S.mode === 'hide' ? 'active' : '')}
      <label for="brush" class="muted">Brush</label><input id="brush" aria-label="Brush size" type="range" min="5" max="250" value="${S.radius}">` : ''}
    ${button('zoom-out','−','', 'aria-label="Zoom out"')}${button('fit','Fit')}${button('zoom-in','+','', 'aria-label="Zoom in"')}
    <span class="grow"></span><small>Space + drag to pan</small></div>`;
}
function renderAdventure() {
  capturePreparation();
  disposeStage();
  $('#app').innerHTML = header() + `<nav class="sectionnav"><strong>${esc(S.graph.name)}</strong><span class="spacer"></span>
    ${button('workspace','Workspace','quiet',`data-id="${S.wid}"`)}</nav><main class="workspace"><aside class="library">${library()}</aside>
    <section class="center"><div class="presentation"><span>On player screen</span><div id="dm-tabs" class="tabs"></div></div><div id="resource-content"></div></section>
    <aside class="inspector" id="inspector"></aside></main>`;
  bindSearch();renderContent();renderTabs($('#dm-tabs'),S.session,false);
}
function renderContent() {
  disposeStage();
  $('#resource-content').innerHTML=S.view==='text'?`<article class="sourceview book-content">${bookUpgradeHint()}${renderSource(selectedEntry(),sourceContext())}</article>`:`${toolbar()}<div class="stage" id="stage"><canvas aria-label="Adventure map preview"></canvas></div>`;
  if(S.view==='media'){S.stage=new Stage($('#stage'),false);S.stage.load(selectedMedia());}
  const brush=$('#brush');if(brush)brush.oninput=e=>{S.radius=+e.target.value;S.stage?.updateCursor();};
  renderInspector();updateSidebarSelection();
}
function bindSearch() {
  const input = $('#search'); if (!input) return;
  input.oninput = e => {
    S.search = e.target.value; const position = e.target.selectionStart;
    renderSidebar();$('#search').focus({preventScroll:true});$('#search').setSelectionRange(position,position);
  };
  $('#resource-type').onchange=e=>{S.resourceType=e.target.value;renderSidebar();$('#resource-type').focus({preventScroll:true});};
}
function renderSidebar(){const root=$('.library');if(root){const scroll=root.scrollTop;root.innerHTML=library();bindSearch();updateSidebarSelection();root.scrollTop=scroll;}}
function updateSidebarSelection(){for(const b of document.querySelectorAll('.library button[data-action="entry"],.library button[data-action="media"]')){const active=resourceActive(b.dataset.action,b.dataset.id);b.classList.toggle('active',active);if(active)b.setAttribute('aria-current','true');else b.removeAttribute('aria-current');}}
function toggleGroup(b) {
  const open=!S.navOpen.has(b.dataset.id),body=$('.book-children',b.closest('.nav-node'));
  if(open)S.navOpen.add(b.dataset.id);else S.navOpen.delete(b.dataset.id);
  b.setAttribute('aria-expanded',String(open));b.textContent=open?'▾':'▸';b.setAttribute('aria-label',`${open?'Collapse':'Expand'} ${navigationIndex().entries.get(b.dataset.id)?.name||'category'}`);
  body.hidden=!open;body.innerHTML=open?navigationChildren(b.dataset.id):'';
}
function openEntry(id,inline=false){
  capturePreparation();S.entry=id;S.sourceOpen=true;
  if(inline&&S.view==='media'){renderInspector();updateSidebarSelection();}
  else{S.view='text';renderContent();}
}
function openMedia(id){capturePreparation();S.media=id;S.region=null;S.mode='pan';S.view='media';S.sourceOpen=false;S.boundary=[];renderContent();}
function selectRegion(id){capturePreparation();S.region=id;const r=selectedRegion();if(r?.entry){S.entry=r.entry;S.sourceOpen=true;}renderInspector();updateSidebarSelection();S.stage?.paint();}
function entryEditor(entry) {
  if (!entry) return '<p class="muted">Select an entry to prepare.</p>';
  const prep = S.drafts[entry.id] || S.graph.preparation[entry.id] || {};
  return `<div class="row spread"><h2>${esc(entry.name)}</h2>${pinButton('entry',entry.id)}</div><p class="breadcrumb">${esc(breadcrumbs(entry).join(' › '))}</p>
    <form data-form="preparation" data-entry="${entry.id}"><label for="translation">Narration / translation</label><textarea id="translation" name="translation" rows="7">${esc(prep.translation || '')}</textarea>
    <label for="private-notes">DM notes · private</label><textarea id="private-notes" name="notes" rows="5">${esc(prep.notes || '')}</textarea>
    <label class="check"><input type="checkbox" name="approved" ${prep.status === 'approved' ? 'checked' : ''}>Reviewed and approved</label>
    <button type="submit" class="primary">Save preparation</button></form>
    <p class="muted">Source names stay as imported. This form does not reveal anything to players.</p>`;
}
function renderInspector() {
  capturePreparation();
  const root = $('#inspector'); if (!root) return;
  if (S.view === 'text') { root.innerHTML = entryEditor(selectedEntry()); return; }
  const m = selectedMedia();
  if (!m) { root.innerHTML = '<h2>No media imported</h2><p class="muted">Read the import warnings or add a local picture.</p>' + warnings(); return; }
  const r = selectedRegion();
  root.innerHTML = `<p class="eyebrow">${m.kind === 'map' ? 'Map' : 'Picture'}</p><div class="row spread"><h2>${esc(m.name)}</h2>${pinButton('media',m.id)}</div>
    <p class="locator">${esc(m.source_path)}</p><label class="check"><input id="safe" type="checkbox" ${m.player_safe ? 'checked' : ''}>I reviewed this image for secrets and spoilers; safe to share</label>
    <p class="warning">Imported maps may contain secret doors or room labels. Fog cannot remove details within a revealed area. Choose a player-safe image before sharing.</p>
    ${button('present','Present to players','primary',m.player_safe ? '' : 'disabled')}
    ${m.kind === 'map' ? `<hr><h3>Rooms / areas</h3><select id="region-select" aria-label="Select map region"><option value="">Choose a room or area</option>${m.regions.map(x => `<option value="${x.id}" ${r?.id === x.id ? 'selected' : ''}>${esc(x.name)}</option>`).join('')}</select>
    ${r ? `<h3 class="room-title">${esc(r.name)}</h3><div class="room-boundary"><span>Room boundary</span>
      ${S.mode==='boundary'?`${button('save-boundary','Save boundary')}${button('cancel-boundary','Cancel','quiet')}<p>Drag around the complete room edge on the map, release, then save.</p>`:button('boundary','Draw boundary','quiet')}
      </div><p><small>${r.points.length?'The current boundary is outlined on the map. Draw a replacement if needed.':'Draw the room edge to enable room reveal. The brush is also available.'}</small></p>
      ${button('reveal-region','Reveal room','',r.points.length ? '' : 'disabled')}${r.entry ? button('region-entry','Read / prepare source','quiet') : ''}` : '<p class="muted">Click a room to read it here. Selection does not reveal it.</p>'}
      <hr><div class="row">${button('show-map','Reveal whole map','quiet')}${button('reset-fog','Reset fog','quiet')}</div>` : ''}
    ${S.sourceOpen&&selectedEntry()?`<section id="room-source"><hr>${bookUpgradeHint()}<article class="book-content inline-source">${renderSource(selectedEntry(),sourceContext())}</article>${entryEditor(selectedEntry())}</section>`:''}
    <hr><label for="shared-note">Shared player notes</label><textarea id="shared-note" rows="4">${esc(S.session?.notes[m.id] || '')}</textarea>${button('share-note','Save shared note')}
    ${warnings()}`;
  $('#safe').onchange = async e => {
    try { await request('media/review',{media:m.id,player_safe:e.target.checked}); m.player_safe = e.target.checked; S.session = await request('session'); renderInspector(); }
    catch (error) { toast(error.message); }
  };
  const selector = $('#region-select'); if (selector) selector.onchange = e => selectRegion(e.target.value);
}
function warnings() {
  return S.graph.warnings.length ? `<details class="warnings"><summary>Import warnings (${S.graph.warnings.length})</summary>${S.graph.warnings.map(w => `<p>${esc(w)}</p>`).join('')}</details>` : '';
}
function renderTabs(root, session, player) {
  if (!root) return;
  const tabs = player ? session.tabs : session.tabs.map(id => mediaItems().find(x => x.id === id)).filter(Boolean);
  root.innerHTML = tabs.map(t => `<div class="tab ${session.active === t.id ? 'active' : ''}">${button('activate',esc(t.name),'',`data-id="${t.id}"`)}${button('close','×','',`data-id="${t.id}" aria-label="Close ${esc(t.name)}"`)}</div>`).join('') +
    (tabs.length ? button('close-all','Close all','quiet') : '<small class="muted">Nothing is being presented.</small>');
}
async function sessionAction(action, extra = {}) {
  const result = await request('session/action',{action,media:S.media,...extra});
  S.session = result;
  if (isPlayer) updatePlayer();
  else { renderTabs($('#dm-tabs'),S.session,false); S.stage?.paint(); }
}
function modal(html) { const d = $('#dialog'); d.innerHTML = html; d.showModal(); }
let sourceJob = null, sourceValidation = null, transferJob = null;
function dismiss() {
  if (sourceJob||transferJob) { toast('Cancel the current operation before closing this window.'); return; }
  $('#dialog').close();
}
$('#dialog').addEventListener('cancel',e=>{if(sourceJob||transferJob){e.preventDefault();toast('Cancel the current operation before closing this window.');}});
function importDialog() {
  sourceValidation = null;
  modal(`${button('dismiss','×','quiet dialog-close','aria-label="Close Add adventure"')}<h2>Add adventure</h2><p class="muted">Connect a local source library, then choose your adventure.</p>
    <div class="row source-modes">${button('source-existing','Use existing copy','active')}${button('source-install','Install local copy')}</div>
    <div id="source-form"></div><div id="source-status" role="status" aria-live="polite"></div><div id="inventory"></div>`);
  existingSourceForm();
}
function existingSourceForm(path='',images='') {
  $('#source-form').innerHTML=`<form data-form="inspect"><label for="library-path">5e.tools library folder</label>
    <div class="row"><input name="path" id="library-path" required value="${esc(path)}" placeholder="Folder containing data/adventures.json">${button('pick-folder','Choose folder','quiet')}</div>
    <details><summary>Separate image folder · optional</summary><label for="image-path">Image library folder</label><input name="images" id="image-path" value="${esc(images)}" placeholder="Uses the library’s img folder"></details>
    <div class="row"><button type="submit" class="primary">Validate copy</button>${button('dismiss','Close','quiet')}</div></form>`;
  for(const input of $('#source-form').querySelectorAll('input'))input.addEventListener('input',()=>{
    sourceValidation=null;$('#inventory').innerHTML='';$('#source-status').innerHTML='';
  });
}
async function validateSource() {
  sourceValidation=null;$('#inventory').innerHTML='';$('#source-status').innerHTML='<p>Checking local copy…</p>';
  try {
    const path=$('#library-path').value,images=$('#image-path').value;
    const result=await request('library',{path,images});sourceValidation={...result,selectedPath:path,selectedImages:images};
    $('#source-status').innerHTML=`<div class="notice success"><strong>✓ Local 5e.tools copy found</strong><p>${result.version ? `Version ${esc(result.version)} · ` : ''}${result.available} of ${result.adventures.length} adventure data files found.</p>
      <p>${result.download_images ? 'Adventure images will download during import, as selected at installation.' : result.images_found ? 'Image folder found.' : 'No images found. Text can still be imported; missing images will be reported.'}</p></div>`;
    $('#inventory').innerHTML=`<label for="adventure-source">Choose adventure</label><select id="adventure-source">${result.adventures.map(a=>`<option value="${esc(a.id)}" ${a.available?'':'disabled'}>${esc(a.name)}${a.available?'':' · data missing'}</option>`).join('')}</select><p>${button('import-adventure','Import adventure','primary',result.available?'':'disabled')}</p>`;
  } catch(error) { $('#source-status').innerHTML=`<div class="notice error"><strong>Copy not validated</strong><p>${esc(error.message)}</p></div>`; }
}
function sourceBusy(busy) {
  for(const node of document.querySelectorAll('#source-form input,#source-form button,#source-form select,#inventory button,#inventory select,.source-modes button'))node.disabled=busy;
}
function jobStatus(state) {
  const root=$('#source-status');if(!root)return;
  const verb=state.kind==='install'?'Installation':'Import';
  if(['failed','cancelled'].includes(state.state)) {
    root.innerHTML=`<div class="notice error"><strong>${verb} ${state.state==='failed'?'stopped':'cancelled'}</strong><p>${esc(state.error||'Operation cancelled.')}</p>${state.error_code?`<small>Reference: ${esc(state.error_code)}</small>`:''}</div>`;
    return;
  }
  root.innerHTML=`<div class="notice"><strong>${esc(state.message||verb+' in progress')}</strong><p>${state.total?`${Math.floor(state.done/1024/1024)} / ${Math.ceil(state.total/1024/1024)} MB`:state.kind==='import'?'Reading source entries and images…':'Preparing local files…'}</p>
    <progress ${state.total?`max="${state.total}" value="${state.done}"`:''}></progress><p>${button('cancel-source-job',state.cancel_requested?'Stopping…':'Cancel '+(state.kind==='install'?'installation':'import'),'quiet',`data-id="${state.id}" ${state.cancel_requested?'disabled':''}`)}</p></div>`;
}
async function trackSourceJob(job) {
  sourceJob=job;sourceBusy(true);jobStatus(job);
  try {
    while(true) {
      await new Promise(resolve=>setTimeout(resolve,500));
      const state=await request('import/status',{job:job.id});sourceJob=state;
      if(state.state==='complete')return state.result;
      jobStatus(state);
      if(['failed','cancelled'].includes(state.state))return null;
    }
  } catch(error) {
    await request('import/cancel',{job:job.id}).catch(()=>{});
    // A lost connection ends polling/progress too. Recheck rather than silently
    // starting a duplicate job whose outcome is unknown.
    jobStatus({...job,state:'failed',error:'Connection lost. Reopen the app to check whether the operation completed. '+error.message});
    return null;
  } finally { sourceJob=null;sourceBusy(false); }
}
async function fileBytes(file) {
  if (!file || file.size > 64 * 1024 * 1024) throw Error('Select a file up to 64 MB.');
  return new Promise((resolve,reject) => { const r = new FileReader(); r.onload = () => resolve(r.result.split(',')[1]); r.onerror = reject; r.readAsDataURL(file); });
}
async function importAdventure() {
  const source = $('#adventure-source')?.value; if (!source) throw Error('Choose an available adventure.');
  if(sourceJob||!sourceValidation)return;
  sourceJob={kind:'import',state:'starting'};sourceBusy(true);
  try {
    const job=await request('import/start',{path:sourceValidation.selectedPath,images:sourceValidation.selectedImages,source});
    const result=await trackSourceJob(job);
    if(result){dismiss();await openWorkspace(S.wid);toast(result.repaired_assets?`Repaired ${result.repaired_assets} source image(s); preparation and session preserved.`:result.enriched?'Book formatting added; notes, boundaries and session preserved.':result.unchanged?'Already imported; preparation and session preserved.':'Adventure imported. Review maps and import warnings before sharing.');}
  } catch(error){sourceJob=null;jobStatus({kind:'import',state:'failed',error:error.message});sourceBusy(false);}
}
function transferStatus(job) {
  const root=$('#transfer-status');if(!root)return;
  const title=job.kind==='export'?'Workspace backup':'Workspace restore';
  if(['failed','cancelled'].includes(job.state)) {
    root.innerHTML=`<div class="notice error"><strong>${title} ${job.state==='cancelled'?'cancelled':'stopped'}</strong><p>${esc(job.error||'Operation stopped. Existing workspaces are unchanged.')}</p></div>
      <p>${job.kind==='export'?button('backup','Retry backup','primary'):''}${button('dismiss','Close','quiet')}</p>`;
    return;
  }
  if(job.state==='complete'&&job.kind==='export'){
    root.innerHTML=`<div class="notice success"><strong>Backup ready</strong><p>Your workspace, preparation, session and images are included.</p></div>
      <p><a id="backup-download" class="download-button" href="/download/${job.id}?token=${encodeURIComponent(token)}" download="sessiondesk-workspace.zip">Download backup</a> ${button('dismiss','Close','quiet')}</p>`;
    return;
  }
  const finishing=job.state==='committing';
  root.innerHTML=`<div class="notice"><strong>${finishing?'Finishing restore':esc(job.message||title)}</strong>
    <p>${job.total?`${Math.floor(job.done/1024/1024)} / ${Math.ceil(job.total/1024/1024)} MB`:'Preparing workspace files…'}</p>
    <progress ${job.total?`max="${job.total}" value="${job.done}"`:''}></progress>
    <p>${button('cancel-transfer',finishing?'Finishing…':job.cancel_requested?'Stopping…':'Cancel','quiet',finishing||job.cancel_requested?'disabled':'')}</p></div>`;
}
async function runTransfer(job,file=null) {
  const controller=new AbortController();transferJob={...job,controller};
  const restoreForm=file?$('form[data-form="restore"]'):null;
  if(restoreForm)for(const control of restoreForm.elements)control.disabled=true;
  let uploadError=null;
  if(file)fetch('/api/backup/upload/'+job.id,{method:'POST',headers:{'Content-Type':'application/zip',Authorization:'Bearer '+token},body:file,signal:controller.signal})
    .then(async response=>{const data=await response.json();if(!response.ok)throw Error(data.error||'Upload failed.');})
    .catch(error=>{uploadError=error;});
  transferStatus(job);
  try{
    while(true){
      await new Promise(resolve=>setTimeout(resolve,350));
      const state=await request('job/status',{job:job.id});transferJob={...state,controller};
      transferStatus(state);
      if(state.state==='complete')return state.result;
      if(['failed','cancelled'].includes(state.state))return null;
      if(uploadError){await request('job/cancel',{job:job.id});controller.abort();uploadError=null;}
    }
  }catch(error){
    controller.abort();await request('job/cancel',{job:job.id}).catch(()=>{});
    transferStatus({...job,state:'failed',error:'Connection lost. Reopen the app to check saved workspaces before retrying.'});
    return null;
  }finally{controller.abort();transferJob=null;if(restoreForm)for(const control of restoreForm.elements)control.disabled=false;}
}
async function exportBackup(){
  if(transferJob)return;
  const job=await request('backup/export/start');
  modal(`${button('dismiss','×','quiet dialog-close','aria-label="Close backup window"')}<h2>Export workspace backup</h2><div id="transfer-status" role="status" aria-live="polite"></div>`);
  const result=await runTransfer(job);
  if(result)$('#backup-download')?.click();
}
async function onAction(b) {
  const a = b.dataset.action, m = selectedMedia();
  if (a === 'settings') return showSettings();
  if (a === 'quit') { await request('quit'); $('#app').innerHTML = '<main class="home"><h1>Session Desk closed.</h1><p>Your workspace is saved. You can close this tab.</p></main>'; return; }
  if (a === 'home') { S.boot = await request('bootstrap'); return home(); }
  if (a === 'workspace') return openWorkspace(b.dataset.id);
  if (a === 'prepared') {const result=await request('campaign/open');location.assign(result.url);return;}
  if (a === 'connect-rules') {const result=await request('pick-folder');if(result.path){await request('campaign/source',{path:result.path});await openWorkspace(S.wid);toast('2014 rules library connected.');}return;}
  if (a === 'workspace-files') {
    const result=await request('module/files');
    const link=(record,name)=>`<a href="/asset/${S.wid}/${record.asset}?token=${encodeURIComponent(token)}&name=${encodeURIComponent(name.split('/').at(-1))}" target="_blank" rel="noopener">${esc(name)}</a>`;
    const groups=new Map();for(const file of result.files){const parent=file.path.includes('/')?file.path.split('/')[0]:'Campaign files';if(!groups.has(parent))groups.set(parent,[]);groups.get(parent).push(file);}
    return modal(`${button('dismiss','×','quiet dialog-close','aria-label="Close workspace files"')}<h2>Workspace files</h2><p>Private campaign files. Source and preparation scripts are preserved as downloads; they are never executed.</p>${result.original?`<p>${link(result.original,'original-recovery.zip')}</p>`:''}${[...groups].map(([name,files])=>`<details><summary>${esc(name)} (${files.length})</summary><ul>${files.map(f=>`<li>${link(f,f.path)}</li>`).join('')}</ul></details>`).join('')}`);
  }
  if (a === 'adventure') return openAdventure(b.dataset.id);
  if (a === 'dismiss') return dismiss();
  if (a === 'new-workspace') return modal(`<h2>New workspace</h2><form data-form="workspace"><label for="workspace-name">Name</label><input name="name" id="workspace-name" required maxlength="100" autofocus>
    <label>Preparation language</label><input name="language" value="English" maxlength="80"><label>Rules profile</label><select name="rules"><option>Unspecified</option><option>2014</option><option>2024</option><option>Other</option></select>
    <div class="row"><button type="submit" class="primary">Create workspace</button>${button('dismiss','Cancel','quiet')}</div></form>`);
  if (a === 'import') return importDialog();
  if (a === 'source-existing') {
    if(sourceJob)return;sourceValidation=null;existingSourceForm();$('#source-status').innerHTML='';$('#inventory').innerHTML='';
    document.querySelectorAll('.source-modes button').forEach(x=>x.classList.toggle('active',x===b));return;
  }
  if (a === 'source-install') {
    if(sourceJob)return;const options=await request('library/options');sourceValidation=null;$('#source-status').innerHTML='';$('#inventory').innerHTML='';
    document.querySelectorAll('.source-modes button').forEach(x=>x.classList.toggle('active',x===b));
    $('#source-form').innerHTML=`<form data-form="install"><p>5e.tools ${esc(options.rules)} · v${esc(options.version)} · approximately ${options.download_mb} MB for the core copy.</p>
      <label for="install-location">Install location · new or empty folder</label><input id="install-location" name="location" required placeholder="Choose where to keep your local library"><p>${button('pick-install-folder','Choose location','quiet')}</p>
      <label class="check"><input type="checkbox" name="include_images" checked>Include adventure images as needed</label><p class="muted">${esc(options.image_mode)} Without this option, the copy has text and tools only.</p>
      <div class="row"><button type="submit" class="primary">Install and validate</button>${button('dismiss','Close','quiet')}</div></form>`;return;
  }
  if (a === 'pick-install-folder') {const result=await request('pick-folder',{purpose:'install'});if(result.path)$('#install-location').value=result.path.replace(/[\\/]$/,'')+'/5etools-2014';return;}
  if (a === 'pick-folder') { const result = await request('pick-folder'); if (result.path) {$('#library-path').value = result.path;await validateSource();} return; }
  if (a === 'import-adventure') return importAdventure();
  if (a === 'cancel-source-job') { await request('import/cancel',{job:b.dataset.id});b.disabled=true;b.textContent='Stopping…';return; }
  if (a === 'toggle-group') return toggleGroup(b);
  if (a === 'collapse-all') {S.navOpen.clear();S.search='';S.resourceType='all';renderSidebar();$('.library').scrollTop=0;return;}
  if (a === 'entry') return openEntry(b.dataset.id,!!b.closest('#room-source'));
  if (a === 'media') return openMedia(b.dataset.id);
  if (a === 'region-entry') {openEntry(selectedRegion().entry,true);const source=$('#room-source'),root=$('#inspector');if(source)root.scrollTop+=source.getBoundingClientRect().top-root.getBoundingClientRect().top;return;}
  if (a === 'pin') {
    const kind=b.dataset.kind,id=b.dataset.id;
    const response=await request('pin',{kind,id,enabled:!pinned(kind,id)});S.graph.pins=response.pins;renderSidebar();
    for(const node of document.querySelectorAll('[data-action=pin]'))if(node.dataset.kind===kind&&node.dataset.id===id&&!node.closest('.pinned-resources'))node.textContent=pinned(kind,id)?'Unpin':'Pin resource';
    return;
  }
  if (a.startsWith('mode-')) { S.mode = a.slice(5);updateToolButtons();if(!isPlayer)renderInspector();S.stage?.paint();return; }
  if (a === 'fit') return S.stage?.fit();
  if (a === 'zoom-in' || a === 'zoom-out') return S.stage?.zoom(a === 'zoom-in' ? 1.25 : .8);
  if (a === 'player') {
    const u = new URL(location.href); u.search = new URLSearchParams({view:'player',workspace:S.wid,adventure:S.aid});
    u.hash = 'player=' + S.boot.player_token; window.open(u,'sessiondesk-player'); return;
  }
  if (a === 'present') { await sessionAction('present'); toast('Presented. Open the player screen for your TV.'); return; }
  if (a === 'activate' || a === 'close') { await sessionAction(a,{media:b.dataset.id}); if (!isPlayer && a === 'activate') openMedia(b.dataset.id); return; }
  if (a === 'close-all') return sessionAction('close_all');
  if (a === 'share-note') { await sessionAction('note',{text:$('#shared-note').value}); toast('Shared notes saved.'); return; }
  if (a === 'reset-fog') { if (!confirm('Cover this entire map again? Existing fog strokes will be cleared.')) return; return sessionAction('reset_fog'); }
  if (a === 'show-map') { if (!confirm('Reveal every detail of this map to players?')) return; return sessionAction('show_map'); }
  if (a === 'reveal-region') return sessionAction('reveal_region',{region:S.region});
  if (a === 'boundary') { S.mode = 'boundary'; S.boundary = [];renderInspector();S.stage?.paint();toast('Drag around the complete room edge, then Save boundary.'); return; }
  if (a === 'cancel-boundary') {S.mode='pan';S.boundary=[];renderInspector();S.stage?.paint();return;}
  if (a === 'save-boundary') {
    if(S.boundary.length<3)throw Error('Draw a closed room boundary on the map first.');
    const r = selectedRegion(); await request('media/review',{media:m.id,region:{id:r.id,points:S.boundary,role:r.role||'room',verified:true}});
    S.graph = await request('adventure'); S.mode = 'pan';S.boundary=[]; S.stage.media=selectedMedia(); renderInspector(); S.stage.paint(); toast('Room boundary saved.'); return;
  }
  if (a === 'add-picture') return modal(`<h2>Add local picture</h2><form data-form="picture"><label>Display name</label><input name="name" required maxlength="200"><label>PNG, JPEG, WebP or GIF · up to 48 MB</label><input name="file" type="file" accept="image/png,image/jpeg,image/webp,image/gif" required><div class="row"><button type="submit" class="primary">Import picture</button>${button('dismiss','Cancel','quiet')}</div></form>`);
  if (a === 'backup') return exportBackup();
  if (a === 'restore') return modal(`${button('dismiss','×','quiet dialog-close','aria-label="Close restore window"')}<h2>Restore workspace backup</h2><p>Choose a Session Desk workspace backup or a prepared-campaign recovery ZIP. Restore creates a separate workspace with its files and saved state.</p><form data-form="restore"><input name="file" type="file" accept=".zip" required><div class="row"><button type="submit" class="primary">Restore backup</button>${button('dismiss','Cancel','quiet')}</div></form><div id="transfer-status" role="status" aria-live="polite"></div>`);
  if (a === 'cancel-transfer'&&transferJob){
    const state=await request('job/cancel',{job:transferJob.id});
    if(state.state!=='committing')transferJob.controller.abort();
    transferStatus(state);return;
  }
  if (a === 'clear-ink') { await request('ink',{media:S.media,action:'clear'}); S.stage.ink=[]; S.stage.paint(); return; }
}
document.addEventListener('click', e => { const b = e.target.closest('button[data-action]'); if (b && !b.disabled) onAction(b).catch(error => toast(error.message)); });
document.addEventListener('submit', async e => {
  const form = e.target.closest('form[data-form]'); if (!form) return; e.preventDefault();
  const submit = $('button[type=submit]',form); submit.disabled = true;
  try {
    const data = Object.fromEntries(new FormData(form));
    if (form.dataset.form === 'workspace') { const w = await request('workspace/create',data); dismiss(); await openWorkspace(w.id); }
    if (form.dataset.form === 'inspect') {
      await validateSource();
    }
    if (form.dataset.form === 'install') {
      if(sourceJob)return;
      sourceJob={kind:'install',state:'starting'};sourceBusy(true);
      const job=await request('library/install',{location:data.location,include_images:data.include_images==='on'});
      const result=await trackSourceJob(job);
      if(result){existingSourceForm(result.path);await validateSource();}
    }
    if (form.dataset.form === 'preparation') {
      const eid=form.dataset.entry;
      const saved = await request('prepare',{entry:eid,translation:data.translation,notes:data.notes,status:data.approved ? 'approved' : 'draft'});
      S.graph.preparation[eid]=saved;delete S.drafts[eid];toast('Preparation saved.');
    }
    if (form.dataset.form === 'picture') { await request('media/add',{name:data.name,data:await fileBytes(data.file)}); dismiss(); S.graph=await request('adventure');renderSidebar();renderContent();toast('Picture imported. Review it before sharing.'); }
    if (form.dataset.form === 'restore') {
      if(transferJob)return;
      const job=await request('backup/restore/start',{size:data.file.size});
      const restored=await runTransfer(job,data.file);
      if(restored){dismiss();await openWorkspace(restored.id);toast('Backup restored as a separate workspace.');}
    }
  } catch(error) {
    if(form.dataset.form==='install'){sourceJob=null;sourceBusy(false);jobStatus({kind:'install',state:'failed',error:error.message});}
    else toast(error.message);
  } finally { submit.disabled=false; }
});

function inPolygon(points,x,y) {
  let hit=false; for(let i=0,j=points.length-1;i<points.length;j=i++) {
    const [xi,yi]=points[i], [xj,yj]=points[j];
    if ((yi>y)!==(yj>y) && x < (xj-xi)*(y-yi)/(yj-yi)+xi) hit=!hit;
  } return hit;
}
class Stage {
  constructor(root,player) {
    this.root=root; this.canvas=$('canvas',root); this.ctx=this.canvas.getContext('2d'); this.player=player;
    this.image=null; this.media=null; this.scale=1; this.x=0; this.y=0; this.space=false; this.drag=null; this.ink=[];
    this.pointer=null;this.cursor=document.createElement('div');this.cursor.className='brush-cursor';this.cursor.hidden=true;this.cursor.setAttribute('aria-hidden','true');root.append(this.cursor);
    this.fog=document.createElement('canvas'); this.fogKey=''; this.dead=false;
    this.resize=new ResizeObserver(() => { this.size(); this.paint(); }); this.resize.observe(root); this.size();
    this.keydown=e=>{ if(e.code==='Space' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) { e.preventDefault(); this.space=true;this.updateCursor(); } };
    this.keyup=e=>{if(e.code==='Space'){if(this.space)e.preventDefault();this.space=false;this.updateCursor();}}; this.blur=()=>{this.space=false;this.drag=null;this.pointer=null;this.updateCursor();};
    window.addEventListener('keydown',this.keydown);window.addEventListener('keyup',this.keyup);window.addEventListener('blur',this.blur);
    this.canvas.onpointerdown=e=>this.down(e);this.canvas.onpointermove=e=>this.move(e);this.canvas.onpointerup=e=>this.up(e);this.canvas.onpointercancel=()=>{this.drag=null;this.pointer=null;this.updateCursor();};
    this.canvas.onpointerleave=()=>{if(!this.drag){this.pointer=null;this.updateCursor();}};
    this.canvas.onwheel=e=>{e.preventDefault();this.zoom(e.deltaY<0?1.12:1/1.12);};
  }
  dispose(){this.dead=true;this.cursor.remove();this.resize.disconnect();window.removeEventListener('keydown',this.keydown);window.removeEventListener('keyup',this.keyup);window.removeEventListener('blur',this.blur);}
  size(){this.w=this.root.clientWidth;this.h=this.root.clientHeight;this.dpr=Math.min(devicePixelRatio||1,2);this.canvas.width=this.w*this.dpr;this.canvas.height=this.h*this.dpr;}
  async load(media){
    if(!media){this.media=null;this.image=null;this.paint();return;}
    if(this.media?.id===media.id&&this.media.asset===media.asset&&this.media.width===media.width&&this.media.height===media.height){this.media=media;return;}
    this.media=media;this.image=null;this.fogKey='';this.ink=[];const image=new Image();
    image.onload=()=>{if(this.dead||this.media?.id!==media.id||this.media.asset!==media.asset)return;this.image=image;this.fit();};
    image.onerror=()=>toast('Image could not be decoded. Check the imported file.');image.src=asset(media);
  }
  fit(){if(!this.media)return;this.scale=Math.min(this.w/this.media.width,this.h/this.media.height)*.95;this.x=(this.w-this.media.width*this.scale)/2;this.y=(this.h-this.media.height*this.scale)/2;this.paint();}
  zoom(factor){if(!this.media)return;const before=this.scale;this.scale=Math.max(.02,Math.min(15,this.scale*factor));const ratio=this.scale/before;this.x=this.w/2-(this.w/2-this.x)*ratio;this.y=this.h/2-(this.h/2-this.y)*ratio;this.paint();}
  point(e){const r=this.canvas.getBoundingClientRect();return [(e.clientX-r.left-this.x)/this.scale,(e.clientY-r.top-this.y)/this.scale];}
  rememberPointer(e){const rect=this.canvas.getBoundingClientRect();this.pointer=[e.clientX-rect.left,e.clientY-rect.top];}
  updateCursor(){
    const brush=!this.player&&this.media?.kind==='map'&&this.image&&['reveal','hide'].includes(S.mode)&&!this.space&&!this.drag?.pan;
    const p=this.pointer,inside=p&&this.media&&p[0]>=this.x&&p[1]>=this.y&&p[0]<=this.x+this.media.width*this.scale&&p[1]<=this.y+this.media.height*this.scale;
    this.cursor.hidden=!(brush&&inside);
    if(!this.cursor.hidden){const diameter=S.radius*this.scale*2;Object.assign(this.cursor.style,{left:p[0]+'px',top:p[1]+'px',width:diameter+'px',height:diameter+'px'});this.cursor.classList.toggle('hide-brush',S.mode==='hide');}
    this.canvas.style.cursor=this.space||S.mode==='pan'||this.drag?.pan?(this.drag?.pan?'grabbing':'grab'):!this.cursor.hidden?'none':'crosshair';
  }
  clamp(p){return [Math.max(0,Math.min(this.media.width,p[0])),Math.max(0,Math.min(this.media.height,p[1]))];}
  down(e){
    if(!this.media||!this.image)return; const pan=this.space||e.button===1||S.mode==='pan';const p=this.point(e);
    if(!pan&&(p[0]<0||p[1]<0||p[0]>this.media.width||p[1]>this.media.height))return;
    this.canvas.setPointerCapture(e.pointerId);this.drag={pan,x:e.clientX,y:e.clientY,start:[e.clientX,e.clientY],points:[this.clamp(p)],mode:S.mode};
    this.rememberPointer(e);this.updateCursor();
    if(!pan&&S.mode==='boundary')S.boundary=this.drag.points;
  }
  move(e){
    this.rememberPointer(e);
    if(!this.drag){this.updateCursor();return;}
    if(this.drag.pan){this.x+=e.clientX-this.drag.x;this.y+=e.clientY-this.drag.y;this.drag.x=e.clientX;this.drag.y=e.clientY;}
    else if(this.drag.points.length<(this.drag.mode==='boundary'?2000:1000)){
      this.drag.points.push(this.clamp(this.point(e)));if(this.drag.mode==='boundary')S.boundary=this.drag.points;
    }
    this.paint();
  }
  async up(e){
    const drag=this.drag;if(!drag)return;this.drag=null;this.rememberPointer(e);this.updateCursor();
    if(this.canvas.hasPointerCapture(e.pointerId))this.canvas.releasePointerCapture(e.pointerId);
    try {
      if(drag.pan){
        if(!this.player&&Math.hypot(e.clientX-drag.start[0],e.clientY-drag.start[1])<5){
          const p=this.point(e);const r=this.media.regions.find(r=>inPolygon(r.points,...p));
          if(r)selectRegion(r.id);
        }return;
      }
      if(drag.mode==='boundary'&&!this.player){S.boundary=drag.points;this.paint();return;}
      if(drag.mode==='pen'){const out=await request('ink',{media:this.media.id,action:'draw',points:drag.points,color:S.color});this.ink=out.strokes;this.paint();return;}
      if(!this.player&&['reveal','hide'].includes(drag.mode))await sessionAction('fog',{media:this.media.id,mode:drag.mode,points:drag.points,radius:S.radius});
    }catch(error){toast(error.message);}
  }
  path(ctx,points){ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));}
  stroke(ctx,stroke,radius){ctx.lineWidth=radius*2;ctx.lineCap='round';ctx.lineJoin='round';this.path(ctx,stroke.points);ctx.stroke();for(const p of [stroke.points[0],stroke.points.at(-1)]){ctx.beginPath();ctx.arc(...p,radius,0,Math.PI*2);ctx.fill();}}
  paint(){
    this.updateCursor();
    const c=this.ctx;c.setTransform(this.dpr,0,0,this.dpr,0,0);c.clearRect(0,0,this.w,this.h);
    if(!this.media||!this.image){c.fillStyle='#a4adba';c.font='16px Segoe UI';c.textAlign='center';c.fillText(this.media?'Loading image…':'Waiting for the DM to present something.',this.w/2,this.h/2);return;}
    c.save();c.translate(this.x,this.y);c.scale(this.scale,this.scale);c.drawImage(this.image,0,0,this.media.width,this.media.height);
    if(this.media.kind==='map'){
      const ops=S.session?.fog[this.media.id]||[];const key=JSON.stringify(ops);
      if(key!==this.fogKey){
        const factor=Math.min(1,4096/Math.max(this.media.width,this.media.height));this.fog.width=Math.ceil(this.media.width*factor);this.fog.height=Math.ceil(this.media.height*factor);
        const f=this.fog.getContext('2d');f.fillStyle='#0c1016';f.fillRect(0,0,this.fog.width,this.fog.height);f.scale(factor,factor);
        for(const op of ops){f.globalCompositeOperation=op.mode==='reveal'?'destination-out':'source-over';f.fillStyle='#0c1016';f.strokeStyle='#0c1016';
          if(op.polygon){this.path(f,op.polygon);f.closePath();f.fill();}else this.stroke(f,op,op.radius);}
        this.fogKey=key;
      }
      c.globalAlpha=this.player?1:.42;c.drawImage(this.fog,0,0,this.media.width,this.media.height);c.globalAlpha=1;
      if(!this.player){
        for(const region of this.media.regions){if(!region.points.length)continue;this.path(c,region.points);c.closePath();c.lineWidth=(region.id===S.region?3:1)/this.scale;c.strokeStyle=region.id===S.region?'#f3c76a':'#78a7be88';c.stroke();}
        if(S.mode==='boundary'&&S.boundary.length){this.path(c,S.boundary);if(!this.drag)c.closePath();c.strokeStyle='#f3c76a';c.fillStyle='#f3c76a22';c.lineWidth=2/this.scale;c.fill();c.stroke();}
      }
    }
    for(const stroke of this.ink){c.strokeStyle=stroke.color;c.fillStyle=stroke.color;this.stroke(c,stroke,3/this.scale);}
    if(this.drag&&!this.drag.pan&&this.drag.mode==='pen'){c.strokeStyle=S.color;c.fillStyle=S.color;this.stroke(c,this.drag,3/this.scale);}
    c.restore();
  }
}
function playerShell(){
  $('#app').innerHTML=`<main class="player"><div class="toolbar"><div class="brand"><img src="/icon.svg" alt="">Session Desk</div><span class="grow"></span>
    ${button('mode-pan','Pan','active')}${button('mode-pen','Draw')}
    <select id="pen-color" aria-label="Pen color"><option value="#f3c76a">Gold</option><option value="#e67070">Red</option><option value="#69b8ff">Blue</option><option value="#8bd6b1">Green</option></select>
    ${button('clear-ink','Clear drawings')}${button('zoom-out','−','', 'aria-label="Zoom out"')}${button('fit','Fit')}${button('zoom-in','+','', 'aria-label="Zoom in"')}<span id="connection" class="offline"></span></div>
    <div class="tabs" id="player-tabs"></div><div class="stage" id="stage"><canvas aria-label="Player presentation"></canvas></div><div class="shared-note" id="player-note" hidden></div></main>`;
  $('#pen-color').onchange=e=>S.color=e.target.value;S.stage=new Stage($('#stage'),true);
}
function updateToolButtons(){document.querySelectorAll('[data-action^="mode-"]').forEach(b=>b.classList.toggle('active',b.dataset.action==='mode-'+S.mode));}
function updatePlayer(){
  renderTabs($('#player-tabs'),S.session,true);const media=S.session.tabs.find(x=>x.id===S.session.active);S.media=media?.id||null;S.stage.load(media);S.stage.paint();
  const note=S.session.notes[S.media]||'';$('#player-note').textContent=note;$('#player-note').hidden=!note;
}
async function poll(){
  if(!S.wid||!S.aid||S.pollBusy)return;S.pollBusy=true;
  try {
    const next=await request(isPlayer?'player':'session');const changed=JSON.stringify(next)!==JSON.stringify(S.session);S.session=next;
    if(isPlayer){$('#connection').textContent='';if(changed)updatePlayer();}
    else if(changed){renderTabs($('#dm-tabs'),S.session,false);S.stage?.paint();}
    if(S.media&&S.session.tabs.some(t=>(typeof t==='string'?t:t.id)===S.media)&&S.stage){const ink=await request('ink',{media:S.media});S.stage.ink=ink.strokes;S.stage.paint();}
  }catch(error){if(isPlayer)$('#connection').textContent='Connection lost · your DM may need to reopen this window.';}
  finally{S.pollBusy=false;}
}
async function start(){
  const client=crypto.randomUUID();
  await request('client/ping',{client});
  setInterval(()=>request('client/ping',{client}).catch(()=>{}),10000);
  window.addEventListener('pagehide',()=>{
    fetch('/api/client/close',{method:'POST',keepalive:true,headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({client})}).catch(()=>{});
  });
  document.documentElement.style.setProperty('--scale',(localStorage.getItem('textSize')||100)/100);document.body.classList.toggle('dense',localStorage.getItem('density')==='true');
  if(isPlayer){if(!S.wid||!S.aid)throw Error('Open this player screen from an adventure.');playerShell();S.session=await request('player');updatePlayer();}
  else{S.boot=await request('bootstrap');if(S.wid)await openWorkspace(S.wid);else home();if(S.boot.recovered_operations)toast('Discarded an interrupted operation. Saved workspaces were kept.');}
  setInterval(poll,900);
}
start().catch(error=>{$('#app').innerHTML=`<main class="home"><h1>Open Session Desk from its launcher</h1><p>${esc(error.message)}</p></main>`;});
