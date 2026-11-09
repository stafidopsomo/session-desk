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
  graph:null, media:null, entry:null, region:null, view:'library', mode:'pan', radius:60,
  color:'#f3c76a', session:null, stage:null, search:'', pollBusy:false, boundary:[],
  sourceOpen:false, drafts:{}, navOpen:new Set()};
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
  while(current&&!seen.has(current.id)){seen.add(current.id);chain.unshift(current.name);current=S.graph.entries.find(e=>e.id===current.parent);}
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
    <div class="cards">${S.overview.adventures.map(a => `<article class="card"><h2>${esc(a.name)}</h2>
      <p class="count">${a.maps} maps · ${a.pictures} pictures${a.warnings ? ` · ${a.warnings} import warnings` : ''}</p>
      ${button('adventure','Open adventure','',`data-id="${a.id}"`)}</article>`).join('')}</div>
    ${!S.overview.adventures.length ? '<div class="empty"><h2>Add your first adventure</h2><p>Use your existing local 5e.tools copy, or install one at a location you choose.</p></div>' : ''}</main>`;
}
async function openAdventure(aid) {
  S.aid = aid; S.graph = await request('adventure'); S.session = await request('session');
  S.media = dmMedia()[0]?.id || null;
  S.entry = S.graph.entries[0]?.id || null; S.region = null; S.view = 'library'; S.search = '';S.sourceOpen=false;S.drafts={};S.navOpen=new Set();
  renderAdventure();
}
function library() {
  const q=S.search.trim().toLowerCase(),entries=S.graph.entries,media=dmMedia();
  const pins=(S.graph.pins||[]).map(p=>({pin:p,item:(p.kind==='entry'?entries:media).find(x=>x.id===p.id)})).filter(x=>x.item);
  const pinnedHTML=pins.length?`<section class="pinned-resources"><h3>Pinned</h3>${pins.map(({pin:p,item})=>`<div class="pinned-row">${button(p.kind==='entry'?'entry':'media',esc(item.name),'item',`data-id="${item.id}"`)}${button('pin','×','quiet',`data-kind="${p.kind}" data-id="${p.id}" aria-label="Unpin ${esc(item.name)}"`)}</div>`).join('')}</section>`:'';
  const search=`<input id="search" placeholder="Find a source entry" value="${esc(S.search)}" aria-label="Find source entry">`;
  if(q){
    const matches=[...entries.filter(e=>`${e.name} ${e.text}`.toLowerCase().includes(q)).map(e=>({kind:'entry',...e})),
      ...media.filter(m=>m.name.toLowerCase().includes(q)).map(m=>({...m,mediaKind:m.kind,kind:'media'}))].slice(0,200);
    return pinnedHTML+search+`<div class="search-results">${matches.map(r=>button(r.kind,`${esc(r.name)}<small>${esc(r.kind==='entry'?breadcrumbs(r).slice(0,-1).join(' › '):r.mediaKind==='map'?'Map':'Image')}</small>`,'item',`data-id="${r.id}"`)).join('')||'<p class="muted">No matches.</p>'}</div>`;
  }
  const visible=entries.filter(e=>e.has_heading===true||(e.has_heading===undefined&&e.name!==e.key)),ids=new Set(visible.map(e=>e.id));
  const parent=id=>{const seen=new Set();while(id&&!ids.has(id)&&!seen.has(id)){seen.add(id);id=entries.find(e=>e.id===id)?.parent;}return id||null;};
  const nodes=visible.map((e,i)=>({id:e.id,parent:parent(e.parent),name:e.name,kind:'entry',order:e.order??i*2}));
  nodes.push(...media.map((m,i)=>({id:m.id,parent:parent(m.entry),name:m.name,kind:'media',mediaKind:m.kind,order:m.order??100000+i})));
  const tree=(pid,depth=0)=>nodes.filter(n=>n.parent===pid).sort((a,b)=>a.order-b.order).map(n=>{
    const children=nodes.some(x=>x.parent===n.id),active=n.kind==='entry'?S.entry===n.id&&S.sourceOpen:S.media===n.id;
    const label=button(n.kind,`${esc(n.name)}${n.kind==='media'?`<span class="badge" aria-hidden="true">${n.mediaKind==='map'?'map':'image'}</span>`:''}`,'item'+(active?' active':''),`data-id="${n.id}"`);
    return children?`<details data-nav="${n.id}" ${depth===0||S.navOpen.has(n.id)?'open':''}><summary>${label}</summary><div class="book-children">${tree(n.id,depth+1)}</div></details>`:label;
  }).join('');
  return pinnedHTML+search+`<nav class="book-navigation" aria-label="Adventure contents">${tree(null)}</nav><p>${button('add-picture','Add picture','quiet')}</p>`;
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
    ${['library','prepare','session'].map(v => button('view',v === 'prepare' ? 'Book / resources' : v[0].toUpperCase() + v.slice(1), S.view === v ? 'active' : '', `data-view="${v}"`)).join('')}
    ${button('workspace','Workspace','quiet',`data-id="${S.wid}"`)}</nav><main class="workspace"><aside class="library">${library()}</aside>
    <section class="center">${S.view === 'prepare' ? `<article class="sourceview book-content">${bookUpgradeHint()}${renderSource(selectedEntry(),sourceContext())}</article>` : `${S.view === 'session' ? '<div id="dm-tabs" class="tabs"></div>' : ''}${toolbar()}<div class="stage" id="stage"><canvas aria-label="Adventure map preview"></canvas></div>`}</section>
    <aside class="inspector" id="inspector"></aside></main>`;
  renderInspector(); bindSearch();
  if (S.view !== 'prepare') { S.stage = new Stage($('#stage'), false); S.stage.load(selectedMedia()); }
  if (S.view === 'session') renderTabs($('#dm-tabs'), S.session, false);
  const brush = $('#brush'); if (brush) brush.oninput = e => S.radius = +e.target.value;
}
function bindSearch() {
  const input = $('#search'); if (!input) return;
  input.oninput = e => {
    S.search = e.target.value; const position = e.target.selectionStart;
    $('.library').innerHTML = library(); bindSearch(); $('#search').focus(); $('#search').setSelectionRange(position,position);
  };
  const root=$('.library');if(!root.dataset.navBound){root.dataset.navBound='true';root.addEventListener('toggle',e=>{if(e.target.dataset.nav){if(e.target.open)S.navOpen.add(e.target.dataset.nav);else S.navOpen.delete(e.target.dataset.nav);}},true);}
}
function renderSidebar(){const root=$('.library');if(root){root.innerHTML=library();bindSearch();}}
function openEntry(id){
  capturePreparation();S.entry=id;S.sourceOpen=true;renderInspector();renderSidebar();
  if(S.view==='prepare')$('.sourceview').innerHTML=bookUpgradeHint()+renderSource(selectedEntry(),sourceContext());
}
function selectRegion(id){capturePreparation();S.region=id;const r=selectedRegion();if(r?.entry){S.entry=r.entry;S.sourceOpen=true;}renderInspector();renderSidebar();S.stage?.paint();}
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
  if (S.view === 'prepare') { root.innerHTML = entryEditor(selectedEntry()); return; }
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
let sourceJob = null, sourceValidation = null;
function dismiss() {
  if (sourceJob) { toast('Cancel the current operation before closing this window.'); return; }
  $('#dialog').close();
}
$('#dialog').addEventListener('cancel',e=>{if(sourceJob){e.preventDefault();toast('Cancel the current operation before closing this window.');}});
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
    if(result){dismiss();await openWorkspace(S.wid);toast(result.enriched?'Book formatting added; notes, boundaries and session preserved.':result.unchanged?'Already imported; preparation and session preserved.':'Adventure imported. Review maps and import warnings before sharing.');}
  } catch(error){sourceJob=null;jobStatus({kind:'import',state:'failed',error:error.message});sourceBusy(false);}
}
async function onAction(b) {
  const a = b.dataset.action, m = selectedMedia();
  if (a === 'settings') return showSettings();
  if (a === 'quit') { await request('quit'); $('#app').innerHTML = '<main class="home"><h1>Session Desk closed.</h1><p>Your workspace is saved. You can close this tab.</p></main>'; return; }
  if (a === 'home') { S.boot = await request('bootstrap'); return home(); }
  if (a === 'workspace') return openWorkspace(b.dataset.id);
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
  if (a === 'view') { capturePreparation();S.view = b.dataset.view; S.mode = 'pan'; S.search = '';if(S.view==='prepare')S.sourceOpen=true;return renderAdventure(); }
  if (a === 'entry') return openEntry(b.dataset.id);
  if (a === 'media') { capturePreparation();S.media = b.dataset.id; S.region = null; S.mode = 'pan';S.view='library';S.sourceOpen=false;return renderAdventure(); }
  if (a === 'region-entry') {openEntry(selectedRegion().entry);$('#room-source')?.scrollIntoView({block:'start'});return;}
  if (a === 'pin') {
    const kind=b.dataset.kind,id=b.dataset.id;
    const response=await request('pin',{kind,id,enabled:!pinned(kind,id)});S.graph.pins=response.pins;renderSidebar();
    for(const node of document.querySelectorAll('[data-action=pin]'))if(node.dataset.kind===kind&&node.dataset.id===id&&!node.closest('.pinned-resources'))node.textContent=pinned(kind,id)?'Unpin':'Pin resource';
    return;
  }
  if (a.startsWith('mode-')) { S.mode = a.slice(5); if (!isPlayer) renderAdventure(); else updateToolButtons(); return; }
  if (a === 'fit') return S.stage?.fit();
  if (a === 'zoom-in' || a === 'zoom-out') return S.stage?.zoom(a === 'zoom-in' ? 1.25 : .8);
  if (a === 'player') {
    const u = new URL(location.href); u.search = new URLSearchParams({view:'player',workspace:S.wid,adventure:S.aid});
    u.hash = 'player=' + S.boot.player_token; window.open(u,'sessiondesk-player'); return;
  }
  if (a === 'present') { await sessionAction('present'); toast('Presented. Open the player screen for your TV.'); return; }
  if (a === 'activate' || a === 'close') { await sessionAction(a,{media:b.dataset.id}); if (!isPlayer && a === 'activate') { S.media = b.dataset.id; renderAdventure(); } return; }
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
  if (a === 'backup') {
    const blob = await request('backup/export',{},true), url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = 'sessiondesk-workspace.zip'; link.click(); setTimeout(() => URL.revokeObjectURL(url),30000); return;
  }
  if (a === 'restore') return modal(`<h2>Restore workspace backup</h2><p>Creates a separate workspace. Existing workspaces remain untouched. The ZIP must be a Session Desk backup.</p><form data-form="restore"><input name="file" type="file" accept=".zip" required><div class="row"><button type="submit" class="primary">Restore backup</button>${button('dismiss','Cancel','quiet')}</div></form>`);
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
    if (form.dataset.form === 'picture') { await request('media/add',{name:data.name,data:await fileBytes(data.file)}); dismiss(); S.graph=await request('adventure'); renderAdventure(); toast('Picture imported. Review it before sharing.'); }
    if (form.dataset.form === 'restore') {
      const r=await fetch('/api/backup/restore',{method:'POST',headers:{'Content-Type':'application/zip',Authorization:'Bearer '+token},body:data.file});
      const w=await r.json();if(!r.ok)throw Error(w.error);dismiss();await openWorkspace(w.id);toast('Backup restored as a separate workspace.');
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
    this.fog=document.createElement('canvas'); this.fogKey=''; this.dead=false;
    this.resize=new ResizeObserver(() => { this.size(); this.paint(); }); this.resize.observe(root); this.size();
    this.keydown=e=>{ if(e.code==='Space' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) { e.preventDefault(); this.space=true; } };
    this.keyup=e=>{if(e.code==='Space'){if(this.space)e.preventDefault();this.space=false;}}; this.blur=()=>{this.space=false;this.drag=null;};
    window.addEventListener('keydown',this.keydown);window.addEventListener('keyup',this.keyup);window.addEventListener('blur',this.blur);
    this.canvas.onpointerdown=e=>this.down(e);this.canvas.onpointermove=e=>this.move(e);this.canvas.onpointerup=e=>this.up(e);this.canvas.onpointercancel=()=>{this.drag=null;};
    this.canvas.onwheel=e=>{e.preventDefault();this.zoom(e.deltaY<0?1.12:1/1.12);};
  }
  dispose(){this.dead=true;this.resize.disconnect();window.removeEventListener('keydown',this.keydown);window.removeEventListener('keyup',this.keyup);window.removeEventListener('blur',this.blur);}
  size(){this.w=this.root.clientWidth;this.h=this.root.clientHeight;this.dpr=Math.min(devicePixelRatio||1,2);this.canvas.width=this.w*this.dpr;this.canvas.height=this.h*this.dpr;}
  async load(media){
    if(!media){this.media=null;this.image=null;this.paint();return;}
    if(this.media?.id===media.id)return;
    this.media=media;this.image=null;this.fogKey='';this.ink=[];const image=new Image();
    image.onload=()=>{if(this.dead||this.media?.id!==media.id)return;this.image=image;this.fit();};
    image.onerror=()=>toast('Image could not be decoded. Check the imported file.');image.src=asset(media);
  }
  fit(){if(!this.media)return;this.scale=Math.min(this.w/this.media.width,this.h/this.media.height)*.95;this.x=(this.w-this.media.width*this.scale)/2;this.y=(this.h-this.media.height*this.scale)/2;this.paint();}
  zoom(factor){if(!this.media)return;const before=this.scale;this.scale=Math.max(.02,Math.min(15,this.scale*factor));const ratio=this.scale/before;this.x=this.w/2-(this.w/2-this.x)*ratio;this.y=this.h/2-(this.h/2-this.y)*ratio;this.paint();}
  point(e){const r=this.canvas.getBoundingClientRect();return [(e.clientX-r.left-this.x)/this.scale,(e.clientY-r.top-this.y)/this.scale];}
  clamp(p){return [Math.max(0,Math.min(this.media.width,p[0])),Math.max(0,Math.min(this.media.height,p[1]))];}
  down(e){
    if(!this.media||!this.image)return; const pan=this.space||e.button===1||S.mode==='pan';const p=this.point(e);
    if(!pan&&(p[0]<0||p[1]<0||p[0]>this.media.width||p[1]>this.media.height))return;
    this.canvas.setPointerCapture(e.pointerId);this.drag={pan,x:e.clientX,y:e.clientY,start:[e.clientX,e.clientY],points:[this.clamp(p)],mode:S.mode};
    if(!pan&&S.mode==='boundary')S.boundary=this.drag.points;
  }
  move(e){
    if(!this.drag)return;
    if(this.drag.pan){this.x+=e.clientX-this.drag.x;this.y+=e.clientY-this.drag.y;this.drag.x=e.clientX;this.drag.y=e.clientY;}
    else if(this.drag.points.length<(this.drag.mode==='boundary'?2000:1000)){
      this.drag.points.push(this.clamp(this.point(e)));if(this.drag.mode==='boundary')S.boundary=this.drag.points;
    }
    this.paint();
  }
  async up(e){
    const drag=this.drag;if(!drag)return;this.drag=null;
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
  else{S.boot=await request('bootstrap');home();}
  setInterval(poll,900);
}
start().catch(error=>{$('#app').innerHTML=`<main class="home"><h1>Open Session Desk from its launcher</h1><p>${esc(error.message)}</p></main>`;});
