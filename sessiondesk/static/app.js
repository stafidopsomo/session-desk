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
  color:'#f3c76a', session:null, stage:null, search:'', pollBusy:false, boundary:[]};
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
const button = (action, text, klass = '', extra = '') => `<button data-action="${action}" class="${klass}" ${extra}>${text}</button>`;
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
    <hr><small>${esc(S.boot?.version || '0.1.0-dev.1')} · local Windows preview</small><p>${button('quit', 'Quit app', 'quiet')}</p>`;
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
    ${!S.overview.adventures.length ? '<div class="empty"><h2>Add your first adventure</h2><p>Import from an existing local 5e.tools adventure and image library. No source files are downloaded.</p></div>' : ''}</main>`;
}
async function openAdventure(aid) {
  S.aid = aid; S.graph = await request('adventure'); S.session = await request('session');
  S.media = S.graph.maps[0]?.id || S.graph.pictures[0]?.id || null;
  S.entry = S.graph.entries[0]?.id || null; S.region = null; S.view = 'library'; S.search = '';
  renderAdventure();
}
function library() {
  const q = S.search.toLowerCase();
  if (S.view === 'prepare') {
    const entries = S.graph.entries.filter(x => x.name.toLowerCase().includes(q)).slice(0,400);
    return `<input id="search" placeholder="Find a source entry" value="${esc(S.search)}" aria-label="Find source entry">${entries.map(e =>
      button('entry',esc(e.name) + (S.graph.preparation[e.id]?.status === 'approved' ? ' <span class="badge">✓</span>' : ''),
        'item' + (S.entry === e.id ? ' active' : ''),`data-id="${e.id}"`)).join('')}<small>Showing ${entries.length} entries. Search to narrow the list.</small>`;
  }
  const group = (items, title, open) => `<details ${open ? 'open' : ''}><summary>${title} <small>${items.length}</small></summary>${items.filter(m => m.name.toLowerCase().includes(q)).map(m =>
    button('media',esc(m.name),'item' + (S.media === m.id ? ' active' : ''),`data-id="${m.id}"`)).join('')}</details>`;
  return `<input id="search" placeholder="Find a map or picture" value="${esc(S.search)}" aria-label="Find media">${group(S.graph.maps,'Maps',true)}
    ${[...new Set(S.graph.pictures.map(x => x.chapter))].map(c => group(S.graph.pictures.filter(x => x.chapter === c), c < 0 ? 'Your pictures' : `Pictures · chapter ${c + 1}`,false)).join('')}
    <p>${button('add-picture','Add picture','quiet')}</p>`;
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
  disposeStage();
  $('#app').innerHTML = header() + `<nav class="sectionnav"><strong>${esc(S.graph.name)}</strong><span class="spacer"></span>
    ${['library','prepare','session'].map(v => button('view',v === 'prepare' ? 'Prepare / review' : v[0].toUpperCase() + v.slice(1), S.view === v ? 'active' : '', `data-view="${v}"`)).join('')}
    ${button('workspace','Workspace','quiet',`data-id="${S.wid}"`)}</nav><main class="workspace"><aside class="library">${library()}</aside>
    <section class="center">${S.view === 'prepare' ? `<article class="sourceview"><p class="eyebrow">Original source</p><h2>${esc(selectedEntry()?.name || 'Select an entry')}</h2>
      <div class="source">${esc(selectedEntry()?.text || '')}</div></article>` : `${S.view === 'session' ? '<div id="dm-tabs" class="tabs"></div>' : ''}${toolbar()}<div class="stage" id="stage"><canvas aria-label="Adventure map preview"></canvas></div>`}</section>
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
}
function entryEditor(entry) {
  if (!entry) return '<p class="muted">Select an entry to prepare.</p>';
  const prep = S.graph.preparation[entry.id] || {};
  return `<h2>${esc(entry.name)}</h2><p class="locator">Source ${esc(S.graph.source)} · chapter ${entry.chapter + 1}<br>Entry ${esc(entry.key || '(unkeyed)')}<br>JSON path ${esc(entry.path.join(' / '))}</p>
    <form data-form="preparation"><label for="translation">Narration / translation</label><textarea id="translation" name="translation" rows="7">${esc(prep.translation || '')}</textarea>
    <label for="private-notes">DM notes · private</label><textarea id="private-notes" name="notes" rows="5">${esc(prep.notes || '')}</textarea>
    <label class="check"><input type="checkbox" name="approved" ${prep.status === 'approved' ? 'checked' : ''}>Reviewed and approved</label>
    <button type="submit" class="primary">Save preparation</button></form>
    <p class="muted">Source names stay as imported. This form does not reveal anything to players.</p>`;
}
function renderInspector() {
  const root = $('#inspector'); if (!root) return;
  if (S.view === 'prepare') { root.innerHTML = entryEditor(selectedEntry()); return; }
  const m = selectedMedia();
  if (!m) { root.innerHTML = '<h2>No media imported</h2><p class="muted">Read the import warnings or add a local picture.</p>' + warnings(); return; }
  const r = selectedRegion();
  root.innerHTML = `<p class="eyebrow">${m.kind === 'map' ? 'Map' : 'Picture'} · ${m.width} × ${m.height}</p><h2>${esc(m.name)}</h2>
    <p class="locator">${esc(m.source_path)}</p><label class="check"><input id="safe" type="checkbox" ${m.player_safe ? 'checked' : ''}>I reviewed this image for secrets and spoilers; safe to share</label>
    <p class="warning">Imported maps may contain secret doors or room labels. Fog cannot remove details within a revealed area. Choose a player-safe image before sharing.</p>
    ${button('present','Present to players','primary',m.player_safe ? '' : 'disabled')}
    ${m.kind === 'map' ? `<hr><h3>Regions</h3><select id="region-select" aria-label="Select map region"><option value="">Choose a region</option>${m.regions.map(x => `<option value="${x.id}" ${r?.id === x.id ? 'selected' : ''}>${esc(x.name)}${x.verified ? ' ✓' : ' · review'}</option>`).join('')}</select>
    ${r ? `<p class="warning">${esc(r.review_note)}</p><label for="region-role">Region represents</label><select id="region-role">${['unknown','room','feature','landing','area'].map(x => `<option ${r.role === x ? 'selected' : ''}>${x}</option>`).join('')}</select>
      <label for="region-points">Boundary · image pixel coordinates</label><textarea id="region-points" rows="4">${esc(JSON.stringify(r.points))}</textarea>
      <div class="row">${button('boundary','Draw boundary','quiet')}${button('verify-region','Save / verify boundary')}</div>
      <p><small>Click boundary vertices on the map, then Save / verify. Source regions are not assumed to be rooms.</small></p>
      ${button('reveal-region','Reveal region','',r.verified ? '' : 'disabled')}${r.entry ? button('region-entry','Read / prepare source','quiet') : ''}` : '<p class="muted">Click a region to inspect it. Selection does not reveal it.</p>'}
      <hr><div class="row">${button('show-map','Reveal whole map','quiet')}${button('reset-fog','Reset fog','quiet')}</div>` : ''}
    <hr><label for="shared-note">Shared player notes</label><textarea id="shared-note" rows="4">${esc(S.session?.notes[m.id] || '')}</textarea>${button('share-note','Save shared note')}
    ${warnings()}`;
  $('#safe').onchange = async e => {
    try { await request('media/review',{media:m.id,player_safe:e.target.checked}); m.player_safe = e.target.checked; S.session = await request('session'); renderInspector(); }
    catch (error) { toast(error.message); }
  };
  const selector = $('#region-select'); if (selector) selector.onchange = e => { S.region = e.target.value; renderInspector(); S.stage?.paint(); };
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
function dismiss() { $('#dialog').close(); }
function importDialog() {
  modal(`<h2>Add adventure</h2><p class="muted">Select your existing local 5e.tools library. Files are read only when you choose to inspect or import.</p>
    <form data-form="inspect"><label for="library-path">Library folder</label><div class="row"><input name="path" id="library-path" required placeholder="Folder containing data/adventures.json">${button('pick-folder','Choose folder','quiet')}</div>
    <label for="image-path">Image library folder · optional</label><input name="images" id="image-path" placeholder="Defaults to the selected library’s img folder">
    <div class="row"><button type="submit" class="primary">Inspect library</button>${button('dismiss','Cancel','quiet')}</div></form><div id="inventory"></div>`);
}
async function fileBytes(file) {
  if (!file || file.size > 64 * 1024 * 1024) throw Error('Select a file up to 64 MB.');
  return new Promise((resolve,reject) => { const r = new FileReader(); r.onload = () => resolve(r.result.split(',')[1]); r.onerror = reject; r.readAsDataURL(file); });
}
async function importAdventure() {
  const source = $('#adventure-source')?.value; if (!source) throw Error('Choose an available adventure.');
  const job = await request('import/start',{path:$('#library-path').value,images:$('#image-path').value,source});
  $('#inventory').innerHTML = '<p>Importing source entries and local images…</p><progress></progress>' + button('cancel-import','Cancel import','quiet',`data-id="${job.id}"`);
  while (true) {
    await new Promise(resolve => setTimeout(resolve,500));
    const state = await request('import/status',{job:job.id});
    if (state.state === 'complete') { dismiss(); await openWorkspace(S.wid); toast(state.result.unchanged ? 'Already imported; preparation and session preserved.' : 'Adventure imported. Review maps and import warnings before sharing.'); return; }
    if (['failed','cancelled'].includes(state.state)) throw Error(state.error);
  }
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
  if (a === 'pick-folder') { const result = await request('pick-folder'); if (result.path) $('#library-path').value = result.path; return; }
  if (a === 'import-adventure') return importAdventure();
  if (a === 'cancel-import') { await request('import/cancel',{job:b.dataset.id}); return; }
  if (a === 'view') { S.view = b.dataset.view; S.mode = 'pan'; S.search = ''; return renderAdventure(); }
  if (a === 'entry') { S.entry = b.dataset.id; return renderAdventure(); }
  if (a === 'media') { S.media = b.dataset.id; S.region = null; S.mode = 'pan'; return renderAdventure(); }
  if (a === 'region-entry') { S.entry = selectedRegion().entry; S.view = 'prepare'; S.search = ''; return renderAdventure(); }
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
  if (a === 'boundary') { S.mode = 'boundary'; S.boundary = []; $('#region-points').value = '[]'; toast('Click the boundary vertices on the map, then Save / verify boundary.'); return; }
  if (a === 'verify-region') {
    const r = selectedRegion(); await request('media/review',{media:m.id,region:{id:r.id,points:JSON.parse($('#region-points').value),role:$('#region-role').value,verified:true}});
    S.graph = await request('adventure'); S.mode = 'pan'; S.stage.media=selectedMedia(); renderInspector(); S.stage.paint(); toast('Region boundary verified.'); return;
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
      const result = await request('library',data); $('#inventory').innerHTML = `<label for="adventure-source">Adventure</label><select id="adventure-source">${result.adventures.map(a => `<option value="${esc(a.id)}" ${a.available ? '' : 'disabled'}>${esc(a.name)}${a.available ? '' : ' · data missing'}</option>`).join('')}</select><p>${button('import-adventure','Import adventure','primary')}</p>`;
    }
    if (form.dataset.form === 'preparation') {
      const saved = await request('prepare',{entry:S.entry,translation:data.translation,notes:data.notes,status:data.approved ? 'approved' : 'draft'});
      S.graph.preparation[S.entry]=saved; toast('Preparation saved.');
    }
    if (form.dataset.form === 'picture') { await request('media/add',{name:data.name,data:await fileBytes(data.file)}); dismiss(); S.graph=await request('adventure'); renderAdventure(); toast('Picture imported. Review it before sharing.'); }
    if (form.dataset.form === 'restore') {
      const r=await fetch('/api/backup/restore',{method:'POST',headers:{'Content-Type':'application/zip',Authorization:'Bearer '+token},body:data.file});
      const w=await r.json();if(!r.ok)throw Error(w.error);dismiss();await openWorkspace(w.id);toast('Backup restored as a separate workspace.');
    }
  } catch(error) { toast(error.message); } finally { submit.disabled=false; }
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
  }
  move(e){
    if(!this.drag)return;
    if(this.drag.pan){this.x+=e.clientX-this.drag.x;this.y+=e.clientY-this.drag.y;this.drag.x=e.clientX;this.drag.y=e.clientY;}
    else if(this.drag.points.length<1000)this.drag.points.push(this.clamp(this.point(e)));
    this.paint();
  }
  async up(e){
    const drag=this.drag;if(!drag)return;this.drag=null;
    if(this.canvas.hasPointerCapture(e.pointerId))this.canvas.releasePointerCapture(e.pointerId);
    try {
      if(drag.pan){
        if(!this.player&&Math.hypot(e.clientX-drag.start[0],e.clientY-drag.start[1])<5){
          const p=this.point(e);const r=this.media.regions.find(r=>inPolygon(r.points,...p));
          if(r){S.region=r.id;renderInspector();this.paint();}
        }return;
      }
      if(drag.mode==='boundary'&&!this.player){S.boundary.push(this.clamp(this.point(e)));$('#region-points').value=JSON.stringify(S.boundary.map(p=>p.map(Math.round)));this.paint();return;}
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
        if(S.mode==='boundary'&&S.boundary.length){this.path(c,S.boundary);c.strokeStyle='#f3c76a';c.lineWidth=2/this.scale;c.stroke();}
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
  document.documentElement.style.setProperty('--scale',(localStorage.getItem('textSize')||100)/100);document.body.classList.toggle('dense',localStorage.getItem('density')==='true');
  if(isPlayer){if(!S.wid||!S.aid)throw Error('Open this player screen from an adventure.');playerShell();S.session=await request('player');updatePlayer();}
  else{S.boot=await request('bootstrap');home();}
  setInterval(poll,900);
}
start().catch(error=>{$('#app').innerHTML=`<main class="home"><h1>Open Session Desk from its launcher</h1><p>${esc(error.message)}</p></main>`;});
