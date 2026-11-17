// Native campaign data views. Imported prose is always escaped.
export const esc = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const text = s => typeof s==='string'?s:s==null?'':JSON.stringify(s,null,2);
const storageKey = wid => 'sessiondesk-preview-drafts:'+wid;
function drafts(wid){try{return JSON.parse(sessionStorage.getItem(storageKey(wid))||'{}');}catch{return {};}}
function remember(wid,key,value){const all=drafts(wid);if(value)all[key]=value;else delete all[key];sessionStorage.setItem(storageKey(wid),JSON.stringify(all));}
const field=(label,key,value,area=false)=>`<label for="campaign-${key}">${esc(label)}</label>${area?`<textarea id="campaign-${key}" name="${key}" rows="${key==='text'?18:4}">${esc(text(value))}</textarea>`:`<input id="campaign-${key}" name="${key}" value="${esc(text(value))}">`}`;
function reading(value){return String(value||'').split(/\n\n+/).map(p=>/^#{1,3} /.test(p)?`<h3>${esc(p.replace(/^#+ /,''))}</h3>`:`<p class="book-paragraph">${esc(p)}</p>`).join('');}
export async function mountBook(root,{api,route,href,wid,selection}){
  const book=await api('journal'); let dirty=false;
  const mission=selection.mission,group=mission?'missions':'entries';
  let selected=(book[group]||[]).find(e=>e.id===(mission||selection.entry))||(!mission?book.entries[0]:null);
  const nav=book.chapters.map(c=>`<details open><summary>${esc(c.title)}</summary>${book.entries.filter(e=>e.chapter===c.id).map(e=>`<a class="book-entry ${selected?.id===e.id?'active':''}" href="${href({section:'book',entry:e.id,mission:null})}">${esc(e.title)}</a>`).join('')}</details>`).join('');
  root.innerHTML=`<main class="campaign-layout"><aside class="campaign-index"><h2>Campaign Book</h2><a class="book-entry" href="${href({section:'book',mission:'all',entry:null})}">Missions (${book.missions.length})</a><button data-new="entries">New entry</button><button data-new="missions">New mission</button>${nav}</aside><article class="campaign-reading"><div id="book-body"></div></article></main>`;
  const body=root.querySelector('#book-body');
  if(mission==='all'){
    body.innerHTML=`<h1>Missions</h1><p class="muted">Offers, accepted work and outcomes. Rewards remain separate.</p><div class="mission-list">${book.missions.map(m=>`<a href="${href({section:'book',mission:m.id,entry:null})}" class="mission-card"><span class="status">${esc(m.status)}</span><h2>${esc(m.title)}</h2><p>${esc(m.nextStep||m.objective)}</p></a>`).join('')||'<p>No missions yet. Create one when an opportunity comes up.</p>'}</div>`;
  }else if(!selected){body.innerHTML='<h1>Your campaign</h1><p>Keep what happened, what is next, and the ideas you may use later.</p><p>Create an entry or a mission to begin.</p>';}
  else{
    const recordKey=group+':'+selected.id;let draft=drafts(wid)[recordKey];
    const showEditor=()=>{
      const values=draft?.fields||selected;
      body.innerHTML=`<h1>${esc(selected.title)}</h1><form id="book-edit">${field('Title','title',values.title)}${group==='entries'?`<label for="campaign-chapter">Chapter</label><select id="campaign-chapter" name="chapter">${book.chapters.map(c=>`<option value="${esc(c.id)}" ${values.chapter===c.id?'selected':''}>${esc(c.title)}</option>`).join('')}</select>${field('Record type / status','status',values.status)}${field('Text','text',values.text,true)}`:`<label for="campaign-status">Status</label><select id="campaign-status" name="status">${['Draft','Offered','Active','Resolved','Set aside'].map(s=>`<option ${values.status===s?'selected':''}>${s}</option>`).join('')}</select>${field('Contact / giver','giver',values.giver)}${field('Objective','objective',values.objective,true)}${field('Next step','nextStep',values.nextStep,true)}${field('Outcome','outcome',values.outcome,true)}${field('Reward offered','offered',values.reward?.offered,true)}${field('Reward awarded','awarded',values.reward?.awarded,true)}`}<div class="row"><button class="primary" type="submit">Save</button><button type="button" id="read-entry">Read</button><button type="button" id="copy-draft">Copy draft</button><button type="button" id="reload-entry">Reload saved record</button></div><p id="book-save" role="status">${draft?'Recovered unsaved draft.':''}</p></form>`;
      const form=body.querySelector('form');
      const valuesNow=()=>{const f=Object.fromEntries(new FormData(form));if(group==='missions'){f.reward={offered:f.offered||null,awarded:f.awarded||null};delete f.offered;delete f.awarded;}return f;};
      body.querySelector('#copy-draft').onclick=async()=>{await navigator.clipboard.writeText(JSON.stringify(valuesNow(),null,2));body.querySelector('#book-save').textContent='Draft copied.';};
      body.querySelector('#reload-entry').onclick=()=>{if(confirm('Replace this unsaved draft with the saved record? Copy any text you need first.')){remember(wid,recordKey,null);route({});}};
      form.oninput=()=>{dirty=true;remember(wid,recordKey,{revision:draft?.revision??selected.revision,fields:valuesNow()});};
      form.onchange=form.oninput;
      body.querySelector('#read-entry').onclick=()=>{if(dirty||draft){body.querySelector('#book-save').textContent='Your draft is kept. Save it before returning to the reading view.';return;}showReading();};
      form.onsubmit=async e=>{e.preventDefault();const status=body.querySelector('#book-save'),submit=form.querySelector('[type=submit]');submit.disabled=true;
        const current=drafts(wid)[recordKey];const fields=valuesNow();remember(wid,recordKey,{revision:current?.revision??selected.revision,fields});
        try{selected=await api('journal/patch',{collection:group,id:selected.id,revision:current?.revision??selected.revision,fields});remember(wid,recordKey,null);dirty=false;draft=null;status.textContent='Saved';showReading();}
        catch(error){status.textContent=error.message;status.className='save-error';}finally{submit.disabled=false;}};
    };
    const showReading=()=>{body.innerHTML=`<div class="row"><span class="status">${esc(selected.status)}</span><span class="grow"></span><button id="edit-entry">Edit</button></div><h1>${esc(selected.title)}</h1>${group==='entries'?reading(selected.text):`<dl>${[['Contact',selected.giver],['Objective',selected.objective],['Next step',selected.nextStep],['Completion criteria',selected.completionCriteria?.join('\n')],['Outcome',selected.outcome],['Reward offered',selected.reward?.offered],['Reward awarded',selected.reward?.awarded]].map(([k,v])=>`<dt>${k}</dt><dd class="book-paragraph">${esc(text(v)||'Not recorded')}</dd>`).join('')}</dl>`}`;body.querySelector('#edit-entry').onclick=showEditor;};
    if(draft)showEditor();else showReading();
  }
  root.querySelectorAll('[data-new]').forEach(button=>button.onclick=async()=>{try{const collection=button.dataset.new;const value=await api('journal/patch',{collection,create:true,fields:{title:collection==='entries'?'New entry':'New mission'}});route({section:'book',entry:collection==='entries'?value.id:null,mission:collection==='missions'?value.id:null});}catch(e){alert(e.message);}});
}

export async function mountParty(root,{api,href,route,selection,wid,preparedBase}){
  const roster=await api('party'); const selected=roster.characters.find(c=>c.id===selection.character)||roster.characters[0];
  root.innerHTML=`<main class="campaign-layout"><aside class="campaign-index"><h2>Party</h2>${roster.characters.map(c=>`<a class="book-entry ${c.id===selected?.id?'active':''}" href="${href({section:'party',character:c.id})}">${esc(c.name)}<small>Level ${esc(c.level)} · ${esc(c.class)}</small></a>`).join('')}${!roster.legacy?'<button id="new-character">Add character</button>':''}</aside><article class="campaign-reading" id="party-record"></article></main>`;
  const create=root.querySelector('#new-character');if(create)create.onclick=async()=>{const c=await api('journal/patch',{collection:'party',create:true,fields:{name:'New character'}});route({section:'party',character:c.id});};
  const target=root.querySelector('#party-record');
  if(!selected){target.innerHTML='<h1>Party</h1><p>Add a character when you are ready. Campaign missions can be tracked in the Book.</p>';return;}
  const key='party:'+selected.id,recovered=drafts(wid)[key],fields=recovered?.fields||selected;
  target.innerHTML=`<h1>${esc(selected.name)}</h1><p>Level ${esc(selected.level)} · ${esc(selected.class)} · ${esc(selected.race||'')}</p><form id="party-edit">${field('Name','name',fields.name)}${field('Concept','concept',fields.concept,true)}${field('Private notes','notes',fields.notes,true)}<button class="primary" type="submit">Save character notes</button><p id="party-status" role="status">${recovered?'Recovered unsaved draft.':''}</p></form>${roster.legacy?`<p><a target="_blank" rel="noopener" href="${esc(preparedBase)}/?view=characters">Open full sheet ↗</a></p>`:''}<h2>Personal threads</h2>${(selected.threads||[]).map(t=>`<details><summary>${esc(t.title)} · ${esc(t.status)}</summary><p>${esc(t.next)}</p><p class="book-paragraph">${esc(t.notes)}</p></details>`).join('')||'<p>No personal threads recorded.</p>'}<details><summary>Backstory</summary><div class="book-paragraph">${esc(selected.backstory||'Not recorded')}</div></details><details><summary>Recorded sheet values</summary><pre>${esc(JSON.stringify(selected.sheet||{},null,2))}</pre></details>`;
  const form=target.querySelector('form'),values=()=>Object.fromEntries(new FormData(form));let revision=recovered?.revision??selected.revision;
  form.oninput=()=>remember(wid,key,{revision,fields:values()});
  form.onsubmit=async e=>{e.preventDefault();const status=target.querySelector('#party-status');try{
    if(roster.legacy){for(const [field,value] of Object.entries(values())){if(value===text(selected[field]))continue;const next=await api('party/patch',{id:selected.id,revision,field,value});revision=next.characters.find(c=>c.id===selected.id).revision;selected[field]=value;remember(wid,key,{revision,fields:values()});}}
    else {const next=await api('journal/patch',{collection:'party',id:selected.id,revision,fields:values()});revision=next.revision;}
    remember(wid,key,null);status.textContent='Saved';
  }catch(error){remember(wid,key,{revision,fields:values()});status.textContent=error.message;status.className='save-error';}};
}
