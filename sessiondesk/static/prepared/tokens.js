import {assetUrl} from './map.js';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function setupTokens(root,{atlas,action,getState,player=false,onArm}){
  root.innerHTML=`<details class="token-controls"><summary>Tokens <span data-count>0</span></summary><div class="token-panel"><div class="token-party" aria-label="Character tokens"></div><div class="token-row"><button data-party>Place party</button>${player?'':'<select data-foe aria-label="Enemy token type"></select><button data-add-foe>Add foe</button>'}</div><p data-help>Choose a portrait, then click the map. Drag placed tokens to move them.</p><label class="token-size">Token size <input type="range" min="18" max="40" value="26" aria-label="Token size"></label><div class="token-row"><select data-selected aria-label="Selected map token"><option value="">Select token…</option></select><button data-remove disabled>Remove</button></div><div class="token-row">${player?'':'<button data-clear-foes>Clear foes</button>'}<button data-clear>${player?'Remove party':'Clear map tokens'}</button></div><small>Temporary · shared between screens · resets when the app stops${player?' · enemies are DM-controlled':''}</small></div></details>`;
  const q=s=>root.querySelector(s);let catalogKey='',tokenKey='',mapId;
  function arm(id){
    onArm?.();atlas.annotationMode='pan';atlas.tokenPlacement=id;atlas.canvas.style.cursor='crosshair';
    q('[data-help]').textContent='Click the map to place '+(id==='party'?'the party':'this token')+'. Esc cancels.';
    q('details').open=false;
  }
  atlas.onTokenPlace=async(p,id)=>{
    atlas.canvas.style.cursor='grab';q('[data-help]').textContent='Choose a portrait, then click the map. Drag placed tokens to move them.';
    await action({action:id==='party'?'token-party':'token-add',templateId:id,mapId:atlas.map.id,x:p.x,y:p.y,spacing:Math.max(1,Math.min(Math.max(atlas.map.width,atlas.map.height),85/atlas.scale))});
  };
  atlas.onTokenMove=t=>action({action:'token-move',mapId:atlas.map.id,id:t.id,x:t.x,y:t.y});
  atlas.onTokenSelect=id=>{q('[data-selected]').value=id;q('[data-remove]').disabled=false;};
  q('[data-party]').onclick=()=>arm('party');
  if(!player)q('[data-add-foe]').onclick=()=>arm(q('[data-foe]').value);
  q('[data-selected]').onchange=e=>{atlas.selectedTokenId=e.target.value;q('[data-remove]').disabled=!e.target.value;atlas.draw();};
  q('[data-remove]').onclick=()=>action({action:'token-remove',mapId:atlas.map.id,id:q('[data-selected]').value});
  q('[data-clear]').onclick=()=>action({action:'token-clear',mapId:atlas.map.id,scope:player?'pc':'all'});
  if(!player)q('[data-clear-foes]').onclick=()=>action({action:'token-clear',mapId:atlas.map.id,scope:'foe'});
  const size=q('input[type="range"]'),saved=Number(localStorage.getItem('campaign-token-size'));
  if(saved>=18&&saved<=40)size.value=saved;
  atlas.tokenRadius=Number(size.value);
  size.oninput=()=>{atlas.tokenRadius=Number(size.value);localStorage.setItem('campaign-token-size',size.value);atlas.draw();};
  window.addEventListener('keydown',e=>{if(e.key==='Escape'){atlas.tokenPlacement=null;atlas.canvas.style.cursor='grab';q('[data-help]').textContent='Choose a portrait, then click the map. Drag placed tokens to move them.';}});
  return {update(state=getState()){
    root.hidden=atlas.map?.kind!=='dungeon';
    if(mapId!==state.mapId){mapId=state.mapId;atlas.selectedTokenId=null;atlas.tokenPlacement=null;}
    const catalog=state.tokenCatalog||[],key=JSON.stringify(catalog);
    if(catalogKey!==key){
      catalogKey=key;q('.token-party').innerHTML=catalog.filter(t=>t.kind==='pc').map(t=>`<button data-template="${esc(t.id)}" title="Place ${esc(t.name)}"><img src="${assetUrl(t.image)}" alt=""><span>${esc(t.name)}</span></button>`).join('');
      root.querySelectorAll('[data-template]').forEach(b=>b.onclick=()=>arm(b.dataset.template));
      if(!player)q('[data-foe]').innerHTML=catalog.filter(t=>t.kind==='foe').map(t=>`<option value="${esc(t.id)}">${esc(t.name)}</option>`).join('');
    }
    const tokens=(state.tokens||[]).filter(t=>!player||t.kind==='pc');q('[data-count]').textContent=(state.tokens||[]).length;
    const next=JSON.stringify(tokens.map(t=>[t.id,t.name]));
    if(tokenKey!==next){tokenKey=next;q('[data-selected]').innerHTML='<option value="">Select token…</option>'+tokens.map(t=>`<option value="${esc(t.id)}">${esc(t.name)}</option>`).join('');}
    q('[data-selected]').value=atlas.selectedTokenId||'';q('[data-remove]').disabled=!q('[data-selected]').value;
  }};
}
