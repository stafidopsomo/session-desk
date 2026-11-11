export function setupAtlasSplitter(){
  const grid=document.querySelector('.atlas-grid'),handle=document.getElementById('atlasSplitter');
  if(!grid||!handle)return;const grip=document.getElementById('atlasGrip');
  let preferred=320;try{const saved=Number(localStorage.getItem('campaign-details-width'));if(saved>=220)preferred=saved;}catch{}
  function set(width,persist=false){
    const max=Math.max(220,grid.getBoundingClientRect().width-280),value=Math.round(Math.max(220,Math.min(max,width)));
    grid.style.setProperty('--details-width',value+'px');grip.setAttribute('aria-valuenow',String(value));grip.setAttribute('aria-valuemax',String(max));
    if(persist){preferred=value;try{localStorage.setItem('campaign-details-width',String(value));}catch{}}
  }
  handle.addEventListener('pointerdown',e=>{if(e.target.closest('button'))return;e.preventDefault();handle.setPointerCapture(e.pointerId);handle.classList.add('dragging');});
  handle.addEventListener('pointermove',e=>{if(handle.hasPointerCapture(e.pointerId)){set(grid.getBoundingClientRect().right-e.clientX,true);}});
  function stop(e){if(handle.hasPointerCapture(e.pointerId))handle.releasePointerCapture(e.pointerId);handle.classList.remove('dragging');}
  handle.addEventListener('pointerup',stop);handle.addEventListener('pointercancel',stop);
  handle.addEventListener('keydown',e=>{if(e.target!==grip)return;const width=Number(grip.getAttribute('aria-valuenow'));if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();set(width+(e.key==='ArrowLeft'?24:-24),true);}if(e.key==='Home'){e.preventDefault();set(320,true);}});
  handle.addEventListener('dblclick',()=>set(320,true));
  document.getElementById('widenDetails').onclick=()=>set(Number(grip.getAttribute('aria-valuenow'))+40,true);
  document.getElementById('widenMap').onclick=()=>set(Number(grip.getAttribute('aria-valuenow'))-40,true);
  new ResizeObserver(()=>{if(grid.getBoundingClientRect().width)set(preferred);}).observe(grid);
}

export function setupDisplaySettings(){
  const slider=document.getElementById('dmTextSize'),output=document.getElementById('dmTextSizeValue'),density=document.getElementById('placesDensity');
  let saved={scale:100,density:'comfortable'};
  try{saved={...saved,...JSON.parse(localStorage.getItem('campaign-dm-display')||'{}')};}catch{}
  function apply(persist=false){
    const value=Math.max(80,Math.min(160,Number(slider.value)||100));
    document.documentElement.style.setProperty('--dm-scale',String(value/100));output.textContent=value+'%';
    document.body.dataset.placesDensity=density.value==='compact'?'compact':'comfortable';
    if(persist)try{localStorage.setItem('campaign-dm-display',JSON.stringify({scale:value,density:density.value}));}catch{}
  }
  slider.value=String(saved.scale);density.value=saved.density==='compact'?'compact':'comfortable';apply();
  // Preview the value while dragging; apply the page reflow on release.
  // Otherwise changing topbar sizes moves the slider under the pointer.
  slider.oninput=()=>{output.textContent=slider.value+'%';};
  slider.onchange=()=>apply(true);density.onchange=()=>apply(true);
  document.getElementById('resetDisplay').onclick=()=>{slider.value='100';density.value='comfortable';apply(true);};
}
