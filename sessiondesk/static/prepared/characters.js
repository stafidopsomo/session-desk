const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const signed=n=>n==null?'—':n>=0?'+'+n:String(n);
const abilities=['str','dex','con','int','wis','cha'];
const skills={'Acrobatics':'dex','Animal Handling':'wis','Arcana':'int','Athletics':'str','Deception':'cha','History':'int','Insight':'wis','Intimidation':'cha','Investigation':'int','Medicine':'wis','Nature':'int','Perception':'wis','Performance':'cha','Persuasion':'cha','Religion':'int','Sleight of Hand':'dex','Stealth':'dex','Survival':'wis'};
const threadStatuses=[['Idea','only in your head'],['Seeded','the player has seen it'],['Active','being pursued'],['Done','finished'],['Dropped','set aside']];
const headerLine=c=>[c.race,c.class,'Level '+c.level,c.faction].filter(Boolean).join(' · ');
const statusPill=s=>`<span class="thread-pill" data-status="${esc(s)}">${esc(s)}</span>`;
function overviewRows(characters,showIdeas){
  const wanted=showIdeas?['Active','Seeded','Idea']:['Active','Seeded'];
  return characters.map(c=>{
    const threads=wanted.flatMap(status=>(c.threads||[]).filter(t=>t.status===status));
    const name=`<button type="button" class="thread-open" data-open-character="${esc(c.id)}">${esc(c.name)}</button>`;
    if(!threads.length)return `<tr><th>${name}</th><td colspan="3" class="thread-none">Nothing in play</td></tr>`;
    return threads.map((t,i)=>`<tr><th>${i?'':name}</th><td>${esc(t.title)}</td><td>${statusPill(t.status)}</td><td>${esc(t.next)}</td></tr>`).join('');
  }).join('');
}
let optionsPromise;
async function json(url,init){const r=await fetch(url,init);const d=await r.json();if(!r.ok)throw Error(d.error||'Could not load character data');return d;}
function text(value){
  let out=esc(value);
  for(let i=0;i<8&&out.includes('{@');i++)out=out.replace(/\{@(\w+) ([^{}]*)\}/g,(_,tag,body)=>{
    const p=body.split('|'),label=p[2]||p[0];
    if(['b','bold'].includes(tag))return '<b>'+body+'</b>';
    if(['i','italic'].includes(tag))return '<i>'+body+'</i>';
    if(tag==='dc')return 'DC '+p[0];
    if(tag==='hit')return signed(Number(p[0]));
    const page={spell:'spells',condition:'conditionsdiseases',action:'actions',item:'items',optfeature:'optionalfeatures',sense:'senses'}[tag];
    return page?`<a href="/reference/${page}.html#${encodeURIComponent(p[0].toLowerCase())}_${encodeURIComponent((p[1]||'phb').toLowerCase())}" target="_blank" rel="noopener">${label}</a>`:label;
  });
  return out;
}
function entry(e){
  if(e==null)return '';
  if(typeof e==='string'||typeof e==='number')return '<p>'+text(e)+'</p>';
  if(Array.isArray(e))return e.map(entry).join('');
  if(e.type==='table')return `<div class="sheet-table"><table>${e.caption?'<caption>'+text(e.caption)+'</caption>':''}<thead><tr>${(e.colLabels||[]).map(x=>'<th>'+text(x)+'</th>').join('')}</tr></thead><tbody>${(e.rows||[]).map(row=>'<tr>'+(row.row||row).map(cell=>'<td>'+cellText(cell)+'</td>').join('')+'</tr>').join('')}</tbody></table></div>`;
  if(e.type==='list')return '<ul>'+ (e.items||[]).map(x=>'<li>'+entry(x)+'</li>').join('')+'</ul>';
  return (e.name?'<h5>'+text(e.name)+'</h5>':'')+entry(e.entries||e.entry||e.items||e.text|| (e.type==='options'?'Choose an option from the source.':''));
}
function cellText(x){if(typeof x==='object'&&x!==null){if(x.roll)return x.roll.exact??`${x.roll.min}–${x.roll.max}`;if(x.toRoll)return x.toRoll.map(d=>(d.number||1)+'d'+d.faces).join(' + ');if(x.amount!=null)return esc(x.amount);return entry(x);}return text(x);}
function select(label,field,list,value){return `<label>${esc(label)}<select data-sheet="${field}"><option value="">Not set</option>${list.map(x=>`<option value="${esc(x.key)}" ${x.key===value?'selected':''}>${esc(x.name)} · ${esc(x.source)}</option>`).join('')}</select></label>`;}
function num(label,field,value,min=0,max=9999){return `<label>${esc(label)}<input type="number" data-${field.startsWith('scores.')?'score':'sheet'}="${field.replace('scores.','')}" min="${min}" max="${max}" value="${esc(value)}" placeholder="—"></label>`;}
function textarea(label,field,value,sheet=false){return `<label class="character-field">${esc(label)}<textarea rows="4" maxlength="20000" data-${sheet?'sheet':'field'}="${field}">${esc(value)}</textarea></label>`;}
function calc(c,card){
  const s=c.sheet||{},level=c.level,pb=2+Math.floor((level-1)/4),mods={};abilities.forEach(a=>mods[a]=s.scores?.[a]==null?null:Math.floor((s.scores[a]-10)/2));
  card.querySelectorAll('[data-mod]').forEach(e=>e.textContent=signed(mods[e.dataset.mod]));
  card.querySelectorAll('[data-save-bonus]').forEach(e=>{const a=e.dataset.saveBonus;e.textContent=signed(mods[a]==null?null:mods[a]+(s.saves?.[a]?pb:0));});
  card.querySelectorAll('[data-skill-bonus]').forEach(e=>{const key=e.dataset.skillBonus,a=skills[key];e.textContent=signed(mods[a]==null?null:mods[a]+(s.skills?.[key]||0)*pb);});
  card.querySelector('[data-pb]').textContent=signed(pb);card.querySelector('[data-initiative]').textContent=signed(mods.dex);
  card.querySelector('[data-passive]').textContent=mods.wis==null?'—':10+mods.wis+(s.skills?.Perception||0)*pb;
  const a=s.castingAbility||card.dataset.casting,mod=mods[a];card.querySelector('[data-dc]').textContent=mod==null?'—':8+pb+mod;card.querySelector('[data-spell-attack]').textContent=signed(mod==null?null:pb+mod);
}
export async function mountCharacters(root){
  if(root.dataset.loading==='true')return;root.dataset.loading='true';root.textContent='Loading private character sheets…';
  try{
    const [roster,opts]=await Promise.all([json('/api/characters'),optionsPromise||=(json('/api/character-options').catch(e=>{optionsPromise=null;throw e;}))]);
    root.innerHTML=`<section class="thread-overview"><div class="thread-overview-head"><h2>In play</h2><label><input type="checkbox" data-show-ideas> Show ideas</label></div><div class="sheet-table"><table><thead><tr><th>Character</th><th>Thread</th><th>Status</th><th>Next step</th></tr></thead><tbody data-overview></tbody></table></div></section>`+roster.characters.map(c=>`<details class="character-sheet" data-character="${esc(c.id)}"><summary><span><strong>${esc(c.name)}</strong><small>${esc(headerLine(c))}</small></span><span class="sheet-expand">Open sheet</span></summary><div class="sheet-body"></div></details>`).join('');
    const ideasToggle=root.querySelector('[data-show-ideas]');
    const refreshOverview=()=>{root.querySelector('[data-overview]').innerHTML=overviewRows(roster.characters,ideasToggle.checked);};
    ideasToggle.onchange=refreshOverview;
    root.querySelector('[data-overview]').onclick=e=>{const id=e.target.closest('[data-open-character]')?.dataset.openCharacter;if(!id)return;const card=[...root.querySelectorAll('.character-sheet')].find(x=>x.dataset.character===id);card.open=true;card.scrollIntoView({block:'start'});};
    refreshOverview();
    root.querySelectorAll('.character-sheet').forEach(card=>{
      let c=roster.characters.find(x=>x.id===card.dataset.character),loaded=false,queue=Promise.resolve(),lastFailure=null,rulesOpen=false;
      const updateHeader=()=>{const line=card.querySelector('summary small');line.textContent=headerLine(c);};
      const status=()=>card.querySelector('.character-save');
      const pending=[];
      function flush(){
        queue=queue.catch(()=>{}).then(async()=>{
          while(pending.length){try{await json('/api/characters',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(pending[0])});pending.shift();}catch(e){lastFailure=true;status().textContent='Not saved: '+e.message;status().classList.add('save-error');card.querySelector('[data-retry]').hidden=false;return;}}
          lastFailure=null;status().textContent='Saved · private DM record';status().classList.remove('save-error');card.querySelector('[data-retry]').hidden=true;
        });return queue;
      }
      function save(field,value){
        pending.push(JSON.parse(JSON.stringify({id:c.id,field,value})));status().textContent='Saving…';return flush();
      }
      function threadsHtml(){
        c.threads||=[];
        if(!c.threads.length)return '<p class="thread-none">No threads yet.</p>';
        return c.threads.map((t,i)=>`<div class="thread" data-thread="${i}" data-status="${esc(t.status)}"><div class="thread-head"><label>Thread<input data-thread-field="title" value="${esc(t.title)}"></label><label>Status<select data-thread-field="status">${threadStatuses.map(([name,hint])=>`<option value="${name}" ${t.status===name?'selected':''}>${name} · ${hint}</option>`).join('')}</select></label></div><div class="thread-head"><label>Next step<input data-thread-field="next" value="${esc(t.next)}"></label><label>Where it can come up<input data-thread-field="where" value="${esc(t.where)}"></label></div><details class="thread-more"><summary>Notes and source</summary><label class="character-field">Notes<textarea rows="5" maxlength="20000" data-thread-field="notes">${esc(t.notes)}</textarea></label>${t.source||t.link?`<p class="thread-source">${esc(t.source)}${t.link?` <a href="${esc(t.link)}" target="_blank" rel="noopener">Open source ↗</a>`:''}</p>`:''}<button type="button" class="button small" data-thread-remove>Remove thread</button></details></div>`).join('');
      }
      function storyHtml(){
        const factionFields=c.faction||c.patron||c.contact?`<details class="sheet-section"><summary>Faction contact</summary>${textarea('Patron / contact','patron',c.patron)}${textarea('Contact location','contact',c.contact)}</details>`:'';
        return `<section class="character-story"><div class="sheet-config"><label>Name<input data-field="name" value="${esc(c.name)}"></label><label>Player<input data-field="player" value="${esc(c.player)}" placeholder="Not set"></label><label>Race<input data-field="race" value="${esc(c.race)}" placeholder="Not set"></label><label>Background<input data-field="background" value="${esc(c.background)}" placeholder="Not set"></label><label>Home<input data-field="home" value="${esc(c.home)}" placeholder="Not set"></label><label>Faction<input data-field="faction" value="${esc(c.faction)}" placeholder="None"></label><label>Renown<input type="number" min="0" max="9999" data-field="renown" value="${esc(c.renown)}" placeholder="—"></label></div>${c.rank?`<p>${esc(c.rank)}</p>`:''}${textarea('Who they are','concept',c.concept)}<h3>Threads</h3><div data-thread-list>${threadsHtml()}</div><button type="button" class="button small" data-thread-add>+ Add thread</button>${textarea('Private notes','notes',c.notes)}${factionFields}${c.backstory?'<details class="sheet-section"><summary>Read backstory</summary><div class="backstory-text">'+esc(c.backstory)+'</div></details>':''}${c.hooks?'<details class="sheet-section"><summary>Read DM hooks (proposals, not events)</summary><div class="backstory-text">'+esc(c.hooks)+'</div></details>':''}${c.source||c.sourceLink?`<p class="thread-source">${esc(c.source)}${c.sourceLink?` <a href="${esc(c.sourceLink)}" target="_blank" rel="noopener">Open source ↗</a>`:''}</p>`:''}</section>`;
      }
      function bindThreads(){
        const list=card.querySelector('[data-thread-list]');
        const saveThreads=()=>{refreshOverview();return save('threads',c.threads);};
        const edit=e=>{const field=e.target.dataset.threadField;if(!field)return;const row=e.target.closest('[data-thread]');c.threads[row.dataset.thread][field]=e.target.value;if(field==='status')row.dataset.status=e.target.value;saveThreads();};
        list.addEventListener('input',e=>{if(e.target.tagName!=='SELECT')edit(e);});
        list.addEventListener('change',e=>{if(e.target.tagName==='SELECT')edit(e);});
        list.addEventListener('click',e=>{if(!e.target.matches('[data-thread-remove]'))return;const row=e.target.closest('[data-thread]'),t=c.threads[row.dataset.thread];if(!confirm('Remove "'+t.title+'"?'))return;c.threads.splice(Number(row.dataset.thread),1);list.innerHTML=threadsHtml();saveThreads();});
        card.querySelector('[data-thread-add]').onclick=()=>{c.threads.push({title:'New thread',status:'Idea',next:'',where:'',notes:'',source:'',link:''});list.innerHTML=threadsHtml();saveThreads();list.querySelector('.thread:last-child [data-thread-field="title"]').select();};
        card.querySelector('.rules-sheet').addEventListener('toggle',e=>{rulesOpen=e.target.open;});
      }
      function controls(){
        const s=c.sheet||={};const cls=opts.classes.find(x=>x.key===s.classKey),race=opts.races.find(x=>x.key===s.raceKey);
        card.querySelector('.sheet-body').innerHTML=`${storyHtml()}<details class="sheet-section rules-sheet" ${rulesOpen?'open':''}><summary>Stats, rules, and spells</summary><p class="sheet-privacy">Private DM sheet · scores are final totals, including any racial or level bonuses.</p><div class="sheet-config">${select('Class / rules source','classKey',opts.classes,s.classKey)}${select('Subclass','subclassKey',opts.subclasses.filter(x=>x.className===cls?.name&&(x.classSource||'PHB')===cls?.source),s.subclassKey)}<label>Level<input type="number" data-field="level" min="1" max="20" required value="${c.level}"></label>${select('Race','raceKey',opts.races,s.raceKey)}${select('Subrace / lineage','subraceKey',opts.subraces.filter(x=>x.raceName===race?.name&&(x.raceSource||'PHB')===race?.source),s.subraceKey)}${select('Spellcasting ability override','castingAbility',abilities.map(a=>({key:a,name:a.toUpperCase(),source:'manual'})),s.castingAbility)}</div><div class="ability-grid">${abilities.map(a=>`<div>${num(a.toUpperCase(),'scores.'+a,s.scores?.[a],1,30)}<output data-mod="${a}">—</output></div>`).join('')}</div><div class="sheet-vitals">${num('Armor class','ac',s.ac)}${num('Max HP','hpMax',s.hpMax)}${num('Current HP','hpCurrent',s.hpCurrent)}${num('Temporary HP','hpTemp',s.hpTemp)}${num('Speed (ft)','speed',s.speed)}<div>Proficiency<strong data-pb></strong></div><div>Initiative<strong data-initiative></strong></div><div>Passive Perception<strong data-passive></strong></div><div>Spell save DC<strong data-dc></strong></div><div>Spell attack<strong data-spell-attack></strong></div></div><details class="sheet-section"><summary>Saves and skills</summary><div class="sheet-saves">${abilities.map(a=>`<label><input type="checkbox" data-save="${a}" ${s.saves?.[a]?'checked':''}> ${a.toUpperCase()} <b data-save-bonus="${a}"></b></label>`).join('')}</div><div class="sheet-skills">${Object.entries(skills).map(([key,a])=>`<label>${key} <small>${a.toUpperCase()}</small><select data-skill="${key}">${[[0,'No proficiency'],[1,'Proficient'],[2,'Expertise']].map(([v,t])=>`<option value="${v}" ${(s.skills?.[key]||0)===v?'selected':''}>${t}</option>`).join('')}</select><b data-skill-bonus="${key}"></b></label>`).join('')}</div><small>Class saving throw proficiencies are seeded in each record. Set background, racial, and chosen proficiencies manually; half proficiency and other situational bonuses are not inferred.</small></details><section class="sheet-section"><h3>Abilities and rules reference</h3><p>Available features follow the selected class, subclass, race, and level. Choices and prerequisites remain subject to your ruling.</p><label>Find an ability<input type="search" data-feature-search placeholder="Action Surge, Echo, spell name…"></label><div class="character-rules">Loading source features…</div></section><details class="sheet-section"><summary>Choices, spells, and table rulings</summary>${cls?.name==='Artificer'?`<label>Armor model<select data-sheet="armorModel">${['','Guardian','Infiltrator'].map(x=>`<option ${s.armorModel===x?'selected':''}>${x}</option>`).join('')}</select></label>`:''}<div class="reference-picker"><label>Choose an optional feature<input data-option-search type="search" placeholder="Search styles, infusions, invocations, feats…"></label><div data-option-results></div><div data-option-selected></div></div><div class="reference-picker"><label>Choose a spell<input data-spell-search type="search" placeholder="Search a spell to add its reference…"></label><div data-spell-results></div><div data-spell-selected></div></div>${textarea('Feature choices, prerequisites, custom abilities, and DM rulings','featureNotes',s.featureNotes,true)}${textarea('Resource tracking · enter uses, remaining charges, and recovery','resources',s.resources,true)}</details></details><div class="sheet-save"><span class="character-save" role="status">Saved · private DM record</span><button class="button" data-retry hidden>Retry save</button></div>`;
        bind();bindThreads();calc(c,card);loadRules();
      }
      let rulesRequest=0;
      async function loadRules(){const request=++rulesRequest;try{const r=await json('/api/character-rules?id='+encodeURIComponent(c.id));if(request!==rulesRequest)return;card.dataset.casting=r.classInfo?.spellcastingAbility||'';const disabled=c.sheet.disabledFeatures||[];card.querySelector('.character-rules').innerHTML=(r.warnings||[]).map(w=>'<p class="sheet-warning">'+esc(w)+'</p>').join('')+(r.classInfo?'<p>Hit die: d'+esc(r.classInfo.hd?.faces)+' · Source: '+esc(r.classInfo.source)+(r.raceInfo?' · '+esc(r.raceInfo.name)+(r.raceInfo.subrace?' ('+esc(r.raceInfo.subrace)+')':''):'')+'</p>':'')+r.features.map(f=>`<details class="source-feature" data-feature-name="${esc((f.name+' '+JSON.stringify(f.content)).toLowerCase())}"><summary>${esc(f.name)} <small>${esc(f.kind)}${f.level?' · level '+f.level:''} · ${esc(f.source)}</small>${disabled.includes(f.key)?' · excluded':''}</summary><label class="feature-toggle"><input type="checkbox" data-feature="${esc(f.key)}" ${disabled.includes(f.key)?'':'checked'}> Use at this table</label>${entry(f.content)}<a class="detail-source" href="/reference/${f.kind==='Race'?'races':['Selected spell','Racial spell'].includes(f.kind)?'spells':f.kind==='Chosen option'?(f.referencePage||'optionalfeatures'):'classes'}.html#${encodeURIComponent((f.kind==='Race'?c.sheet.raceKey:['Selected spell','Racial spell','Chosen option'].includes(f.kind)?f.key:c.sheet.classKey).toLowerCase().replaceAll('|','_'))}" target="_blank" rel="noopener">Open source in 5e.tools ↗</a></details>`).join('')+r.tables.map(t=>`<details class="source-feature"><summary>${text(t.title)} · progression table</summary><div class="sheet-table"><table><thead><tr><th>Level</th>${t.colLabels.map(x=>'<th>'+text(x)+'</th>').join('')}</tr></thead><tbody>${t.rows.map((row,i)=>`<tr ${i+1===c.level?'class="current-level"':''}><th>${i+1}</th>${row.map(x=>'<td>'+cellText(x)+'</td>').join('')}</tr>`).join('')}</tbody></table></div></details>`).join('');card.querySelectorAll('[data-feature]').forEach(el=>el.onchange=()=>{const keys=new Set(c.sheet.disabledFeatures||[]);if(el.checked)keys.delete(el.dataset.feature);else keys.add(el.dataset.feature);c.sheet.disabledFeatures=[...keys];save('sheet',{disabledFeatures:c.sheet.disabledFeatures});});calc(c,card);}catch(e){card.querySelector('.character-rules').textContent='Rules unavailable: '+e.message;}}
      function pickers(){
        for(const [kind,group,field] of [['option','optional','selectedFeatures'],['spell','spells','selectedSpells']]){
          const chosen=c.sheet[field]||=[];const selected=card.querySelector('[data-'+kind+'-selected]');
          selected.innerHTML=chosen.map(key=>`<button type="button" class="button small" data-remove="${esc(key)}">${esc(opts[group].find(x=>x.key===key)?.name||key)} ×</button>`).join('');
          selected.querySelectorAll('[data-remove]').forEach(b=>b.onclick=async()=>{c.sheet[field]=c.sheet[field].filter(x=>x!==b.dataset.remove);await save('sheet',{[field]:c.sheet[field]});pickers();loadRules();});
          const search=card.querySelector('[data-'+kind+'-search]');search.oninput=()=>{const q=search.value.trim().toLowerCase();const results=card.querySelector('[data-'+kind+'-results]');const found=q.length>=2?opts[group].filter(x=>!c.sheet[field].includes(x.key)&&x.name.toLowerCase().includes(q)).slice(0,15):[];results.innerHTML=found.map(x=>`<button type="button" class="button small" data-add="${esc(x.key)}">+ ${esc(x.name)} · ${esc(x.source)}</button>`).join('');results.querySelectorAll('[data-add]').forEach(b=>b.onclick=async()=>{if(!c.sheet[field].includes(b.dataset.add))c.sheet[field].push(b.dataset.add);await save('sheet',{[field]:c.sheet[field]});search.value='';results.innerHTML='';pickers();loadRules();});};
        }
      }
      function bind(){
        card.querySelector('[data-retry]').onclick=()=>{if(lastFailure)flush();};
        card.querySelector('[data-feature-search]').oninput=e=>{const q=e.target.value.toLowerCase();card.querySelectorAll('[data-feature-name]').forEach(el=>el.hidden=!el.dataset.featureName.includes(q));};
        // Every edit is queued immediately. No debounce can discard an earlier failed edit.
        card.querySelectorAll('[data-field],[data-sheet],[data-score],[data-skill],[data-save]').forEach(el=>{const event=el.tagName==='SELECT'||el.type==='checkbox'?'change':'input';el.addEventListener(event,async()=>{
          let refresh=false;if(el.type==='number'&&!el.checkValidity()){status().textContent='Enter a number within the allowed range.';return;}
          if(el.dataset.field){const field=el.dataset.field,value=el.type==='number'?(el.value===''?null:Number(el.value)):el.value;c[field]=value;if(field==='name'){card.querySelector('summary strong').textContent=value;refreshOverview();}updateHeader();await save(field,value);refresh=field==='level';}
          else{const patch={};if(el.dataset.score){c.sheet.scores||={};c.sheet.scores[el.dataset.score]=el.value===''?null:Number(el.value);patch.scores=c.sheet.scores;}else if(el.dataset.skill){c.sheet.skills||={};c.sheet.skills[el.dataset.skill]=Number(el.value);patch.skills=c.sheet.skills;}else if(el.dataset.save){c.sheet.saves||={};c.sheet.saves[el.dataset.save]=el.checked;patch.saves=c.sheet.saves;}else{const field=el.dataset.sheet;patch[field]=el.type==='number'?(el.value===''?null:Number(el.value)):el.value;if(field==='classKey')patch.subclassKey='';if(field==='raceKey')patch.subraceKey='';Object.assign(c.sheet,patch);refresh=['classKey','subclassKey','raceKey','subraceKey'].includes(field);}
            calc(c,card);await save('sheet',patch);
          }
          calc(c,card);if(refresh&&!lastFailure){await queue;if(el.dataset.field==='level')loadRules();else controls();const cls=opts.classes.find(x=>x.key===c.sheet.classKey),sub=opts.subclasses.find(x=>x.key===c.sheet.subclassKey);c.class=(cls?.name||'Class not set')+(sub?' · '+sub.name:'');updateHeader();}
        });});pickers();
      }
      card.ontoggle=()=>{if(card.open&&!loaded){loaded=true;controls();}};
    });
  }catch(e){root.textContent=e.message;}finally{delete root.dataset.loading;}
}
