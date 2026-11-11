/* Only trusted application code runs; imported files remain workspace data. */
(() => {
  const parts = new URL(document.currentScript.src).pathname.split('/');
  const workspace = parts[2], token = parts[3], player = document.currentScript.dataset.player === '1';
  const client = crypto.randomUUID();
  const api = (path, body) => fetch(new URL(['','api',path].join('/'),location.origin), {method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify(body)});
  api('client/ping',{client}).catch(()=>{});
  setInterval(()=>api('client/ping',{client}).catch(()=>{}),10000);
  window.addEventListener('pagehide',()=>fetch(new URL(['','api','client/close'].join('/'),location.origin),{method:'POST',keepalive:true,headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({client})}));
  if(player)sessionStorage.removeItem('dmToken');
  else sessionStorage.setItem('dmToken',token);
  window.preparedCapabilities = data => {
    for(const name of ['characters','aftermath','opening','shopping','sessions']) {
      const button=document.getElementById(name+'Nav');if(button)button.hidden=!data.capabilities?.[name];
    }
    const archive=document.querySelector('.archive-group');if(archive)archive.hidden=!data.capabilities?.opening;
    const count=document.querySelector('#sessionsNav .nav-count');if(count)count.textContent=data.sessions.length;
    for(const [name,title] of [['aftermath',data.afterCitadel.title],['opening',data.opening.title]]) {
      const button=document.getElementById(name+'Nav');if(button&&title)for(const child of [...button.childNodes])if(child.nodeType===Node.TEXT_NODE)child.textContent=' '+title;
    }
    document.title=(data.campaign.title||'Prepared campaign')+' · Session Desk';
    const shop=document.getElementById('shoppingView');if(shop){shop.querySelector('h1').textContent=data.shopping.title||'Shops & supplies';shop.querySelector('.eyebrow').textContent='LISTED SUPPLIES';}
    const shopMap=document.getElementById('shopMap');if(shopMap)shopMap.hidden=!data.campaign.shoppingCue;
    const ai=document.getElementById('roomSceneProgress');if(ai)ai.hidden=true;
  };
  window.addEventListener('DOMContentLoaded',()=>{
    const quit=document.getElementById('preparedQuit');
    if(quit)quit.onclick=async()=>{const response=await api('quit',{});const result=await response.json();if(!response.ok){alert(result.error);return;}document.body.textContent='Session Desk closed. You can close this window.';};
  });
})();
