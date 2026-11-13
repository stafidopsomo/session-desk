/** Offline Canvas2D cross treatment. Omit onAction to use document data-action routing. */
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const HOME_PRESET=Object.freeze({cellSize:11,coverage:24,density:24,invert:true,bgBlur:1,chromatic:15,animSpeed:80,animIntensity:30,toneCurve:[[0,0],[.28,.14],[.72,.86],[1,1]]});
const sceneURL=new URL('./hero.svg',import.meta.url).href;
function curve(v){const p=HOME_PRESET.toneCurve;for(let i=1;i<p.length;i++)if(v<=p[i][0])return p[i-1][1]+(v-p[i-1][0])/(p[i][0]-p[i-1][0])*(p[i][1]-p[i-1][1]);return 1;}
function hash(x,y){let n=Math.imul(x+17,374761393)^Math.imul(y+71,668265263);n=Math.imul(n^(n>>>13),1274126177);return((n^(n>>>16))>>>0)/4294967296;}
function backdrop(canvas,host){
  const ctx=canvas.getContext('2d',{alpha:false});if(!ctx)return()=>{};
  const base=document.createElement('canvas'),source=document.createElement('canvas');
  const bg=base.getContext('2d',{alpha:false}),sample=source.getContext('2d',{willReadFrequently:true});
  const motion=matchMedia('(prefers-reduced-motion: reduce)'),image=new Image();
  let alive=true,frame=0,timer=0,last=0,ready=false,width=1,height=1,ratio=1,cells=[];
  function draw(time=0){
    ctx.setTransform(ratio,0,0,ratio,0,0);ctx.globalAlpha=1;ctx.globalCompositeOperation='source-over';ctx.drawImage(base,0,0,width,height);
    ctx.globalCompositeOperation='screen';ctx.lineCap='square';
    const phase=time*.001*(.4+HOME_PRESET.animSpeed/100*1.5);
    for(const c of cells){
      const flicker=motion.matches?1:1-HOME_PRESET.animIntensity/100*.5+Math.sin(phase*Math.PI*2+c.phase)*HOME_PRESET.animIntensity/100*.5;
      const opacity=(.2+.62*c.tone)*flicker;
      ctx.globalAlpha=opacity;ctx.strokeStyle=c.color;ctx.lineWidth=1;
      ctx.beginPath();ctx.moveTo(c.x-c.arm,c.y);ctx.lineTo(c.x+c.arm,c.y);ctx.moveTo(c.x,c.y-c.arm);ctx.lineTo(c.x,c.y+c.arm);ctx.stroke();
      const shift=HOME_PRESET.chromatic/100*2.5;
      ctx.globalAlpha=opacity*.2;ctx.strokeStyle='#b0dfd3';ctx.beginPath();ctx.moveTo(c.x-c.arm-shift,c.y);ctx.lineTo(c.x+c.arm-shift,c.y);ctx.stroke();
      ctx.strokeStyle='#e6b89c';ctx.beginPath();ctx.moveTo(c.x+shift,c.y-c.arm);ctx.lineTo(c.x+shift,c.y+c.arm);ctx.stroke();
    }
    ctx.globalAlpha=1;ctx.globalCompositeOperation='source-over';
  }
  function tick(time){frame=0;if(!alive||!ready||document.hidden||motion.matches)return;if(time-last>=50){draw(time);last=time;}frame=requestAnimationFrame(tick);}
  function resume(){cancelAnimationFrame(frame);frame=0;if(!ready||!alive)return;draw(performance.now());if(!document.hidden&&!motion.matches)frame=requestAnimationFrame(tick);}
  function resize(){
    if(!alive||!image.naturalWidth)return;
    const r=host.getBoundingClientRect();width=Math.max(1,Math.round(r.width));height=Math.max(1,Math.round(r.height));ratio=Math.min(devicePixelRatio||1,1.5);
    canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);base.width=source.width=width;base.height=source.height=height;
    const cover=Math.max(width/image.naturalWidth,height/image.naturalHeight),w=image.naturalWidth*cover,h=image.naturalHeight*cover;
    sample.drawImage(image,(width-w)/2,(height-h)/2,w,h);bg.filter='blur(1px)';bg.drawImage(source,-2,-2,width+4,height+4);bg.filter='none';
    const pixels=sample.getImageData(0,0,width,height).data;
    const cell=HOME_PRESET.cellSize*Math.max(1,Math.sqrt(width*height/(22000*HOME_PRESET.cellSize**2)));cells=[];
    for(let y=0,row=0;y<height;y+=cell,row++)for(let x=0,col=0;x<width;x+=cell,col++){
      if(hash(col,row)>HOME_PRESET.coverage/100)continue;
      let red=0,green=0,blue=0;
      for(let sy=0;sy<4;sy++)for(let sx=0;sx<4;sx++){const px=Math.min(width-1,Math.floor(x+(sx+.5)*cell/4)),py=Math.min(height-1,Math.floor(y+(sy+.5)*cell/4)),i=(py*width+px)*4;red+=pixels[i];green+=pixels[i+1];blue+=pixels[i+2];}
      red/=16;green/=16;blue/=16;const lum=curve((.2126*red+.7152*green+.0722*blue)/255),tone=HOME_PRESET.invert?1-lum:lum;
      cells.push({x:x+cell/2,y:y+cell/2,arm:cell*(.18+.27*tone)*(.5+HOME_PRESET.density/100),tone,phase:hash(row+101,col+29)*Math.PI*2,color:'rgb('+Math.round(170+red*.32)+' '+Math.round(166+green*.34)+' '+Math.round(150+blue*.34)+')'});
    }
    ready=true;host.dataset.ready='true';resume();
  }
  const observer=new ResizeObserver(()=>{clearTimeout(timer);timer=setTimeout(resize,120);});observer.observe(host);
  image.onload=resize;image.onerror=()=>{host.dataset.ready='fallback';};image.decoding='async';image.src=sceneURL;
  document.addEventListener('visibilitychange',resume);motion.addEventListener('change',resume);
  return()=>{alive=false;cancelAnimationFrame(frame);clearTimeout(timer);observer.disconnect();document.removeEventListener('visibilitychange',resume);motion.removeEventListener('change',resume);image.onload=image.onerror=null;cells=[];canvas.width=canvas.height=base.width=base.height=source.width=source.height=1;};
}
export function mountHome(container,{workspaces=[],onAction}={}){
  const items=Array.isArray(workspaces)?workspaces:[];
  const cards=items.map((w,i)=>'<article class="home-workspace"><div class="home-workspace-symbol" aria-hidden="true">'+['◇','▱','✧','⊹'][i%4]+'</div><div class="home-workspace-copy"><h3>'+esc(w.name)+'</h3><p>'+esc([w.rules,w.language].filter(Boolean).join(' · ')||'Local workspace')+'</p>'+(w.unavailable?'<small>A compatible app version is required.</small>':'')+'</div><button type="button" data-action="workspace" data-id="'+esc(w.id)+'" '+(w.unavailable?'disabled':'')+' aria-label="Open workspace" title="Open '+esc(w.name)+'">Open<span aria-hidden="true">↗</span></button><button type="button" class="home-remove" data-action="remove-workspace" data-id="'+esc(w.id)+'" aria-label="Remove '+esc(w.name)+'">Remove</button></article>').join('');
  container.innerHTML=[
    '<main class="desk-home" aria-label="Session Desk home"><div class="home-landscape" aria-hidden="true"></div><canvas class="home-ascii" aria-hidden="true"></canvas><div class="home-shade" aria-hidden="true"></div><div class="home-scroll"><section class="home-window">',
    '<div class="home-window-top"><span class="home-mark" aria-hidden="true">✦</span><span>Session Desk</span><span class="home-local"><i></i>On this computer</span></div>',
    '<div class="home-intro"><h1>Adventures</h1>',
    '<div class="home-actions"><button type="button" class="home-create" data-action="new-workspace" aria-label="New workspace"><span aria-hidden="true">＋</span>New adventure<span class="home-arrow" aria-hidden="true">↗</span></button><button type="button" class="home-my" data-home-list>My adventures<span class="home-total">'+items.length+'</span></button></div><button type="button" class="home-restore" data-action="restore"><span aria-hidden="true">↥</span>Restore backup</button></div>',
    '<section class="home-adventures" id="home-adventures" aria-label="My adventures"><div class="home-list-title"><h2>My adventures</h2><span>'+items.length+' '+(items.length===1?'workspace':'workspaces')+'</span></div>',
    items.length?'<div class="home-workspaces">'+cards+'</div>':'<div class="home-empty"><span aria-hidden="true">◇</span><div><h3>No adventures yet</h3></div></div>',
    '</section><footer class="home-foot"><span>Saved on this computer</span></footer></section></div></main>'
  ].join('');
  const host=container.querySelector('.desk-home'),disposeBackdrop=backdrop(host.querySelector('canvas'),host);
  function click(e){if(e.target.closest('[data-home-list]')){host.querySelector('.home-adventures').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'nearest'});return;}const b=e.target.closest('button[data-action]');if(b&&onAction){e.stopPropagation();onAction(b.dataset.action,b.dataset.id,e);}}
  host.addEventListener('click',click);return()=>{disposeBackdrop();host.removeEventListener('click',click);};
}
