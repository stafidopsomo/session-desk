const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export async function mountChapter(root,{data,action,setView,encounterPanel,toast}){
  const chapter=data.afterCitadel;
  if(!chapter?.scenes?.length){root.textContent='No chapter preparation available.';return;}
  const requested=root.dataset.scene||new URLSearchParams(location.search).get('scene')||localStorage.getItem('campaign-after-citadel-scene');
  root.dataset.scene='';
  let selected=chapter.scenes.find(s=>s.id===requested)||chapter.scenes[0];
  root.innerHTML=`<div class="page-heading"><div><div class="eyebrow">DM ONLY · PREPARATION</div><h1>${esc(chapter.title)}</h1><p>${esc(chapter.description)}</p></div><button class="button small" data-open-threads>Character threads →</button></div><p class="chapter-status">${esc(chapter.status)} Reading this guide never changes fog, character status, rewards or played events.</p><details class="chapter-checks"><summary>Continuity checks and open decisions</summary><ul>${(chapter.principles||[]).map(p=>`<li>${esc(p)}</li>`).join('')}</ul></details><div class="opening-layout"><nav class="opening-outline" aria-label="After the Citadel scenes"></nav><article class="opening-scene" data-chapter-scene></article></div><details class="chapter-assets"><summary>Preparation assets · ready, reusable and still optional</summary><table><thead><tr><th>Asset</th><th>Status</th><th>Use</th></tr></thead><tbody>${(chapter.assetPlan||[]).map(a=>`<tr><th>${esc(a.title)}</th><td>${esc(a.status)}</td><td>${esc(a.note)}</td></tr>`).join('')}</tbody></table></details>`;
  root.querySelector('[data-open-threads]').onclick=()=>setView('characters');
  const outline=root.querySelector('nav'),body=root.querySelector('[data-chapter-scene]');
  function render(){
    const index=chapter.scenes.indexOf(selected),s=selected;
    outline.innerHTML=chapter.scenes.map((scene,i)=>`<button class="opening-step ${scene.id===s.id?'active':''}" data-chapter-id="${esc(scene.id)}"><span>${i+1}</span><span>${esc(scene.title)}<small>${esc(scene.phase)}</small></span></button>`).join('');
    outline.querySelectorAll('button').forEach(b=>b.onclick=()=>choose(b.dataset.chapterId));
    const encounter=chapter.encounters?.[s.encounterId];
    body.innerHTML=`<div class="scene-heading"><span class="detail-kicker">${esc(s.kind)} · NOT A PLAY RECORD</span><h2>${esc(s.title)}</h2><p>${esc(s.goal)}</p></div>${s.trigger?`<p class="chapter-trigger"><strong>Trigger:</strong> ${esc(s.trigger)}</p>`:''}<section class="scene-readaloud"><h3>Read aloud · Greek</h3><p lang="el">${esc(s.readAloudGr)}</p></section>${s.npcLines?.length?`<section class="scene-dialogue"><h3>Optional lines · Greek</h3>${s.npcLines.map(n=>`<div><strong>${esc(n.speaker)}</strong><p lang="el">${esc(n.lineGr)}</p></div>`).join('')}</section>`:''}<section class="scene-run"><h3>Run this scene</h3><ol>${(s.run||[]).map(t=>`<li>${esc(t)}</li>`).join('')}</ol></section>${encounter?encounterPanel(encounter):''}<section class="scene-next"><h3>Move on when</h3><p>${esc(s.next)}</p></section><div class="scene-actions" data-chapter-actions></div><p class="detail-source">${esc(s.sourceNote)}</p><div class="scene-paging"><button class="button" data-previous ${index===0?'disabled':''}>← Previous scene</button><button class="button gold" data-next ${index===chapter.scenes.length-1?'disabled':''}>Next scene →</button></div>`;
    const actions=body.querySelector('[data-chapter-actions]');
    for(const id of s.handouts||[]){
      const h=chapter.handouts[id],button=document.createElement('button');button.className='button gold';button.textContent='Show '+h.title+' to players';
      button.onclick=async()=>{await action({action:'picture',path:h.path});toast('Handout sent to the player screen');};actions.append(button);
    }
    const mapIds=s.mapIds||(s.mapId?[s.mapId]:[]);
    for(const mapId of mapIds){
      const map=data.maps.find(m=>m.id===mapId);if(!map)continue;
      const button=document.createElement('button');button.className='button';button.textContent='Open '+map.title+' →';
      button.onclick=async()=>{await action({action:'map',mapId});if(s.locationId)await action({action:'location',id:s.locationId});setView('atlas');};actions.append(button);
    }
    if(mapIds.length){const note=document.createElement('small');note.className='chapter-map-hint';note.textContent='Map buttons switch the shared map; room fog is preserved. They do not reveal rooms.';actions.append(note);}
    for(const ref of s.references||[]){const a=document.createElement('a');a.className='button small';a.target='_blank';a.rel='noopener';a.href=ref.url;a.textContent=ref.title+' · DM ↗';actions.append(a);}
    body.querySelector('[data-previous]').onclick=()=>choose(chapter.scenes[Math.max(0,index-1)].id);
    body.querySelector('[data-next]').onclick=()=>choose(chapter.scenes[Math.min(chapter.scenes.length-1,index+1)].id);
  }
  function choose(id){selected=chapter.scenes.find(s=>s.id===id)||selected;localStorage.setItem('campaign-after-citadel-scene',selected.id);render();}
  render();
}
