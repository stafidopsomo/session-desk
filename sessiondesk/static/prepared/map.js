export const assetUrl = path => '/assets/' + path.split('/').map(encodeURIComponent).join('/');

function inside(point, polygon) {
  let yes = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i], [xj, yj] = polygon[j];
    if (((yi > point.y) !== (yj > point.y)) && point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi) yes = !yes;
  }
  return yes;
}

export class AtlasMap {
  constructor(canvas, {player = false, onSelect, onStroke, onPing, onZoom, onLoad, onAnnotationChange, onTokenMove, onTokenSelect, onTokenPlace} = {}) {
    Object.assign(this, {canvas, player, onSelect, onStroke, onPing, onZoom, onLoad, onAnnotationChange, onTokenMove, onTokenSelect, onTokenPlace});
    this.ctx = canvas.getContext('2d'); this.tool = 'rooms'; this.radius = 48;
    this.scale = 1; this.tx = 0; this.ty = 0; this.space = false; this.images = new Map();
    this.fog = document.createElement('canvas'); this.selected = null;
    this.ink = document.createElement('canvas'); this.annotations = new Map();
    this.annotationMode='pan'; this.penColor='#e7b94f'; this.penSize=4;
    this.tokenImages=new Map(); this.focusSeen=new Map(); this.tokenRadius=26;
    this.observer = new ResizeObserver(() => this.resize()); this.observer.observe(canvas);
    canvas.addEventListener('wheel', e => { e.preventDefault(); const r = canvas.getBoundingClientRect(); this.zoom(Math.exp(-e.deltaY * .0015), e.clientX - r.left, e.clientY - r.top); }, {passive: false});
    canvas.addEventListener('pointerdown', e => this.pointerDown(e));
    canvas.addEventListener('pointermove', e => this.pointerMove(e));
    canvas.addEventListener('pointerleave', () => {this.hover=null;this.draw();});
    canvas.addEventListener('pointerup', e => this.pointerUp(e));
    canvas.addEventListener('pointercancel', () => { this.drag = null; this.preview = null; this.inkPreview=null; this.draw(); });
    canvas.addEventListener('contextmenu', e => { e.preventDefault(); if (!player) this.pick(e, true); });
    // Track Space before the canvas receives focus, without stealing typing
    // from notes, narration, sliders or other controls.
    const editable = target => target?.closest?.('input,textarea,select,[contenteditable="true"]');
    window.addEventListener('keydown', e => {
      if(e.code==='Space'){this.space=true;if(!editable(e.target))e.preventDefault();}
    });
    window.addEventListener('keyup', e => {if(e.code==='Space')this.space=false;});
    window.addEventListener('blur', () => {this.space=false;this.drag=null;this.preview=null;this.inkPreview=null;this.draw();});
    canvas.addEventListener('keydown', e => {if (e.key === '+' || e.key === '=') this.zoom(1.3); if (e.key === '-') this.zoom(1 / 1.3);});
  }
  resize() {
    const r = this.canvas.getBoundingClientRect();
    if (this.w && Math.abs(this.w-r.width)<.5 && Math.abs(this.h-r.height)<.5) return;
    const ratio=this.hasFit?this.scale/(this.baseScale||this.scale):1;
    const center=this.w?{x:(this.w/2-this.tx)/this.scale,y:(this.h/2-this.ty)/this.scale}:null;
    this.w = r.width; this.h = r.height;
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.round(r.width * dpr); this.canvas.height = Math.round(r.height * dpr); this.dpr = dpr;
    if (this.map) { this.fit(); if(center&&ratio>1.05){this.scale=this.baseScale*ratio;this.tx=this.w/2-center.x*this.scale;this.ty=this.h/2-center.y*this.scale;this.draw();} } else this.draw();
  }
  async set(map, state) {
    const changed = this.map?.id !== map.id;
    this.map = map; this.state = state;
    this.loadTokenImages();
    const key = JSON.stringify([map.id, map.roomRevealPadding, state.fogState]);
    if (key !== this.fogKey) { this.fogKey = key; this.buildFog(); }
    this.selected = state.locationId;
    if (changed) {
      this.hasFit = false; this.image = null;
      this.onLoad?.(false);
      try {
        let image = this.images.get(map.image);
        if (!image) {
          image = new Image(); image.src = assetUrl(map.image); await image.decode(); this.cacheImage(map.image, image);
        }
        if (this.map.id !== map.id) return;
        this.image = image; this.fit();
        const selected=this.map.locations.find(p=>p.id===this.state.locationId);
        if(selected&&!this.player)this.focus(selected);
        this.onLoad?.(true);
      } catch (e) { this.onLoad?.(false, 'Map image could not be loaded. Open the image library to check the file.'); }
    } else this.draw();
  }
  cacheImage(path,image){this.images.delete(path);this.images.set(path,image);while(this.images.size>3)this.images.delete(this.images.keys().next().value);}
  buildFog() {
    if (this.map.kind !== 'dungeon') return;
    this.fog.width = this.map.width; this.fog.height = this.map.height;
    const c = this.fog.getContext('2d'); c.fillStyle = '#000'; c.fillRect(0, 0, this.fog.width, this.fog.height);
    for (const p of this.map.locations) if ((this.map.initialRevealed || []).includes(p.id)) for (const shape of p.shapes) this.punch(c, shape, true);
    for (const op of this.state.fogState?.operations || []) {
      if (op.kind === 'room') {
        const p = this.map.locations.find(p => p.id === op.id); const shape = p?.shapes[op.shape || 0]; if (shape) this.punch(c, shape, op.reveal);
      } else if (op.kind === 'all') c.clearRect(0, 0, this.fog.width, this.fog.height);
      else if (op.kind === 'cover') { c.globalCompositeOperation = 'source-over'; c.fillRect(0, 0, this.fog.width, this.fog.height); }
      else if (op.kind === 'brush') this.brush(c, op);
    }
  }
  polygon(c, shape) { c.beginPath(); shape.forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y)); c.closePath(); }
  punch(c, shape, reveal) {
    const padding=this.map.roomRevealPadding||0;
    c.globalCompositeOperation = reveal ? 'destination-out' : 'source-over';
    if(padding){
      // A small collar exposes printed walls and the near half of thresholds.
      // Never extend this collar into another keyed room's interior.
      const mask=this.roomMask||=document.createElement('canvas');
      if(mask.width!==this.map.width||mask.height!==this.map.height){mask.width=this.map.width;mask.height=this.map.height;}
      const m=mask.getContext('2d');m.clearRect(0,0,mask.width,mask.height);m.globalCompositeOperation='source-over';this.polygon(m,shape);m.fill();m.lineWidth=padding*2;m.lineJoin='round';m.stroke();
      m.globalCompositeOperation='destination-out';
      for(const room of this.map.locations)for(const other of room.shapes)if(other!==shape){this.polygon(m,other);m.fill();}
      c.drawImage(mask,0,0);
    }else{this.polygon(c,shape);c.fillStyle='#000';c.fill();}
    c.globalCompositeOperation='source-over';
  }
  brush(c, op) {
    c.globalCompositeOperation = op.reveal ? 'destination-out' : 'source-over'; c.fillStyle = c.strokeStyle = '#000'; c.lineCap = c.lineJoin = 'round'; c.lineWidth = op.radius * 2;
    c.beginPath(); op.points.forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y)); c.stroke();
    for (const [x, y] of [op.points[0], op.points.at(-1)]) { c.beginPath(); c.arc(x, y, op.radius, 0, Math.PI * 2); c.fill(); }
    c.globalCompositeOperation = 'source-over';
  }
  fit() {
    if (!this.map || !this.w || !this.h) return;
    let box = {x: 0, y: 0, w: this.map.width, h: this.map.height};
    if (this.player && this.map.kind === 'dungeon') {
      const points = [];
      for (const room of this.map.locations) room.shapes?.forEach((shape, i) => { if (this.state.revealed?.includes(`${room.id}:${i}`)) points.push(...shape); });
      for (const op of this.state.fogState?.operations || []) if (op.kind === 'brush' && op.reveal) for (const [x,y] of op.points) points.push([x-op.radius,y-op.radius],[x+op.radius,y+op.radius]);
      if (points.length) { const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]); const edge=this.map.roomRevealPadding||0,x=Math.min(...xs)-edge,y=Math.min(...ys)-edge; box={x,y,w:Math.max(150,Math.max(...xs)-x+edge),h:Math.max(150,Math.max(...ys)-y+edge)}; }
      if ((this.state.fogState?.operations || []).some(op=>op.kind === 'all')) box={x:0,y:0,w:this.map.width,h:this.map.height};
    }
    const preferredPad = this.player ? (this.map.kind==='picture'?8:this.map.kind==='dungeon'?80:45) : 48;
    const pad = Math.min(preferredPad, Math.min(this.w,this.h)*.12);
    this.baseScale = Math.min((this.w-pad*2)/box.w,(this.h-pad*2)/box.h);
    this.scale = Math.max(.015, this.baseScale); this.tx=(this.w-box.w*this.scale)/2-box.x*this.scale; this.ty=(this.h-box.h*this.scale)/2-box.y*this.scale; this.hasFit=true; this.draw();
  }
  focus(location) {
    const shape = location.shapes?.[this.selectedShape || 0];
    if (shape) {
      const xs=shape.map(p=>p[0]),ys=shape.map(p=>p[1]),w=Math.max(...xs)-Math.min(...xs),h=Math.max(...ys)-Math.min(...ys);
      this.scale=Math.min(this.w/(w*2.7),this.h/(h*2.7),2.5);
    } else this.scale=Math.max(this.scale,this.baseScale*2.8);
    this.tx=this.w/2-location.x*this.map.width*this.scale;this.ty=this.h/2-location.y*this.map.height*this.scale;this.draw();
  }
  followReveal(focus) {
    if(!focus||focus.mapId!==this.map?.id||this.focusSeen.get(focus.mapId)===focus.revision)return;
    const width=Math.max(180,focus.w),height=Math.max(180,focus.h);
    this.scale=Math.min(this.w/(width*1.5),this.h/(height*1.5),2.5);
    this.tx=this.w/2-(focus.x+focus.w/2)*this.scale;
    this.ty=this.h/2-(focus.y+focus.h/2)*this.scale;
    this.focusSeen.set(focus.mapId,focus.revision);this.draw();
  }
  zoom(factor, x=this.w/2, y=this.h/2) { if (!this.map) return; const next=Math.max((this.baseScale||.1)*.5,Math.min(5,this.scale*factor)); const ratio=next/this.scale;this.tx=x-(x-this.tx)*ratio;this.ty=y-(y-this.ty)*ratio;this.scale=next;this.draw(); }
  point(e) { const r=this.canvas.getBoundingClientRect();return {x:(e.clientX-r.left-this.tx)/this.scale,y:(e.clientY-r.top-this.ty)/this.scale}; }
  valid(p) { return p.x>=0&&p.y>=0&&p.x<=this.map.width&&p.y<=this.map.height; }
  pointerDown(e) {
    if (e.button===2 || !this.map) return;
    this.canvas.focus({preventScroll:true}); this.canvas.setPointerCapture(e.pointerId);
    const p=this.point(e), drawing=this.player&&['pen','eraser'].includes(this.annotationMode)&&!this.space&&e.button===0;
    if(this.map.kind==='dungeon'&&!this.space&&e.button===0&&!drawing){
      if(this.tokenPlacement){
        if(this.valid(p)&&(!this.player||this.visiblePoint(p))){const placement=this.tokenPlacement;this.tokenPlacement=null;this.onTokenPlace?.(p,placement);}
        return;
      }
      if(this.player?this.annotationMode==='pan':this.tool==='rooms'){
        const token=[...(this.state.tokens||[])].reverse().find(t=>(!this.player||(t.kind==='pc'&&this.visiblePoint(t)))&&Math.hypot(t.x-p.x,t.y-p.y)*this.scale<this.tokenRadius+4);
        if(token){this.selectedTokenId=token.id;this.drag={token:{...token}};this.onTokenSelect?.(token.id);this.draw();return;}
      }
    }
    this.drag={x:e.clientX,y:e.clientY,tx:this.tx,ty:this.ty,moved:false,suppressPick:this.space||e.button===1,pan:!drawing&&(this.player||this.map.kind!=='dungeon'||this.tool==='rooms'||this.space||e.button===1)};
    if(drawing){if(this.valid(p))this.inkPreview={points:[[p.x,p.y]],color:this.penColor,width:this.penSize/this.scale,erase:this.annotationMode==='eraser'};return;}
    if (e.altKey&&!this.player) { this.drag=null;if(this.valid(p))this.onPing?.(p);return; }
    if (!this.player&&!this.drag.pan&&this.valid(p)) this.preview={points:[[p.x,p.y]],radius:this.radius,reveal:e.shiftKey?this.tool==='hide':this.tool==='reveal'};
  }
  pointerMove(e) {
    this.hover=this.point(e);
    if(!this.drag){this.draw();return;}
    if(this.drag.token){const p=this.point(e);if(this.valid(p)&&(!this.player||this.visiblePoint(p))){Object.assign(this.drag.token,p);this.draw();}return;}
    const dx=e.clientX-this.drag.x,dy=e.clientY-this.drag.y;if(Math.hypot(dx,dy)>4)this.drag.moved=true;
    if(this.inkPreview){const p=this.point(e),last=this.inkPreview.points.at(-1);if(this.valid(p)&&Math.hypot(p.x-last[0],p.y-last[1])*this.scale>2)this.inkPreview.points.push([p.x,p.y]);this.draw();}
    else if (this.drag.pan) {this.tx=this.drag.tx+dx;this.ty=this.drag.ty+dy;this.draw();}
    else if(this.preview) {const p=this.point(e);if(this.valid(p)){const last=this.preview.points.at(-1);if(Math.hypot(p.x-last[0],p.y-last[1])>this.radius/4)this.preview.points.push([p.x,p.y]);}this.draw();}
  }
  pointerUp(e) {
    if(!this.drag)return;const drag=this.drag;this.drag=null;
    if(drag.token){this.onTokenMove?.(drag.token);this.draw();return;}
    if(this.inkPreview){this.inkHistory().push(this.inkPreview);this.inkPreview=null;this.draw();this.onAnnotationChange?.();}
    else if(this.preview){const stroke=this.preview;this.preview=null;this.onStroke?.(stroke);this.draw();}
    else if(!drag.moved&&!drag.suppressPick)this.pick(e,false);
  }
  pick(e,hide) {
    if(!this.map)return;const point=this.point(e);
    if(this.map.kind==='dungeon') {
      for(const p of [...this.map.locations].reverse()) for(let i=0;i<p.shapes.length;i++)if((!this.player||this.state.revealed?.includes(`${p.id}:${i}`))&&inside(point,p.shapes[i])){this.selectedShape=i;this.onSelect?.(p,i,hide);return;}
    }else if(!this.player){
      let closest=null,distance=26/this.scale;
      for(const p of this.map.locations){const d=Math.hypot(point.x-p.x*this.map.width,point.y-p.y*this.map.height);if(d<distance){distance=d;closest=p;}}
      if(closest)this.onSelect?.(closest,0,false);
    }
  }
  inkHistory(){if(!this.map)return [];if(!this.annotations.has(this.map.id))this.annotations.set(this.map.id,[]);return this.annotations.get(this.map.id);}
  visiblePoint(p){return this.valid(p)&&p.x<this.map.width&&p.y<this.map.height&&this.fog.getContext('2d').getImageData(Math.floor(p.x),Math.floor(p.y),1,1).data[3]<128;}
  loadTokenImages(){
    for(const token of this.state.tokens||[]){
      if(!token.image||this.tokenImages.has(token.image))continue;
      this.tokenImages.set(token.image,null);
      const image=new Image();image.src=assetUrl(token.image);
      image.decode().then(()=>{this.tokenImages.set(token.image,image);this.draw();}).catch(()=>{});
    }
  }
  drawTokens(){
    if(this.map.kind!=='dungeon')return;
    const c=this.ctx,r=this.tokenRadius;
    for(const saved of this.state.tokens||[]){
      const t=this.drag?.token?.id===saved.id?this.drag.token:saved;
      const visible=this.visiblePoint(t);if(this.player&&!visible)continue;
      const x=this.tx+t.x*this.scale,y=this.ty+t.y*this.scale;
      if(x+r<0||x-r>this.w||y+r<0||y-r>this.h)continue;
      c.save();c.globalAlpha=visible?1:.55;
      c.beginPath();c.arc(x,y,r+3,0,Math.PI*2);c.fillStyle='#0b120e';c.fill();
      c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.fillStyle=t.kind==='pc'?'#31485a':'#693a32';c.fill();
      const image=this.tokenImages.get(t.image);
      if(image){c.save();c.clip();const side=Math.min(image.naturalWidth,image.naturalHeight);c.drawImage(image,(image.naturalWidth-side)/2,(image.naturalHeight-side)/2,side,side,x-r,y-r,r*2,r*2);c.restore();}
      else{c.fillStyle='#fff';c.font='bold 18px Segoe UI';c.textAlign='center';c.fillText(t.name.slice(0,1),x,y+6);}
      c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.strokeStyle=t.color||'#e9c982';c.lineWidth=3;c.stroke();
      if(t.id===this.selectedTokenId){c.beginPath();c.arc(x,y,r+6,0,Math.PI*2);c.strokeStyle='#fff';c.lineWidth=2;c.stroke();}
      c.font='600 12px Segoe UI, sans-serif';c.textAlign='center';
      const name=t.name,labelW=c.measureText(name).width+14,labelY=y-r-25;
      const labelX=Math.max(labelW/2+3,Math.min(this.w-labelW/2-3,x));
      c.fillStyle='#101812ed';c.fillRect(labelX-labelW/2,labelY,labelW,20);
      c.fillStyle='#fff5df';c.fillText(name,labelX,labelY+14);c.restore();
    }
  }
  undoAnnotation(){this.inkHistory().pop();this.draw();this.onAnnotationChange?.();}
  clearAnnotations(){if(this.inkHistory().length)this.inkHistory().push({clear:true});this.draw();this.onAnnotationChange?.();}
  drawAnnotations(){
    const history=[...this.inkHistory(),...(this.inkPreview?[this.inkPreview]:[])];if(!history.length)return;
    const width=this.canvas.width,height=this.canvas.height;if(this.ink.width!==width||this.ink.height!==height){this.ink.width=width;this.ink.height=height;}
    const c=this.ink.getContext('2d');c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,width,height);
    for(const stroke of history){
      if(stroke.clear){c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,width,height);continue;}
      c.save();c.setTransform(this.dpr*this.scale,0,0,this.dpr*this.scale,this.tx*this.dpr,this.ty*this.dpr);c.beginPath();c.rect(0,0,this.map.width,this.map.height);c.clip();
      c.globalCompositeOperation=stroke.erase?'destination-out':'source-over';c.strokeStyle=c.fillStyle=stroke.color;c.lineWidth=stroke.width;c.lineCap=c.lineJoin='round';
      c.beginPath();stroke.points.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.stroke();
      for(const [x,y] of [stroke.points[0],stroke.points.at(-1)]){c.beginPath();c.arc(x,y,stroke.width/2,0,Math.PI*2);c.fill();}c.restore();
    }
    this.ctx.drawImage(this.ink,0,0,this.w,this.h);
  }
  draw() {
    const c=this.ctx,d=this.dpr||1;c.setTransform(d,0,0,d,0,0);c.clearRect(0,0,this.w||0,this.h||0);
    if(!this.image||!this.map)return;
    c.save();c.translate(this.tx,this.ty);c.scale(this.scale,this.scale);c.drawImage(this.image,0,0,this.map.width,this.map.height);
    if(this.map.kind==='dungeon'){
      c.globalAlpha=this.player?1:.54;c.drawImage(this.fog,0,0);c.globalAlpha=1;
      if(!this.player){const room=this.map.locations.find(p=>p.id===this.selected);if(room){const shape=room.shapes[this.selectedShape||0];this.polygon(c,shape);c.strokeStyle='#e9ca85';c.lineWidth=2/this.scale;c.stroke();}}
      if(this.preview){c.globalAlpha=.35;c.strokeStyle=c.fillStyle=this.preview.reveal?'#a7cf7d':'#e38671';c.lineWidth=this.preview.radius*2;c.lineCap='round';c.beginPath();this.preview.points.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.stroke();const p=this.preview.points.at(-1);c.beginPath();c.arc(p[0],p[1],this.preview.radius,0,Math.PI*2);c.fill();c.globalAlpha=1;}
    }
    c.restore();
    if(this.map.kind!=='dungeon'){
      const locations=this.player?(this.state.location?[this.state.location]:[]):this.map.locations;
      const pins=locations.map(p=>({p,x:this.tx+p.x*this.map.width*this.scale,y:this.ty+p.y*this.map.height*this.scale,active:p.id===this.selected||this.player})).filter(p=>p.x>0&&p.y>0&&p.x<this.w&&p.y<this.h);
      const occupied=[];
      for(const {p,x,y,active} of pins){c.beginPath();c.arc(x,y,active?8:5,0,Math.PI*2);c.fillStyle=active?'#e8c785':'#bca56d';c.fill();c.strokeStyle='#182118';c.lineWidth=2;c.stroke();if(active){c.beginPath();c.arc(x,y,13,0,Math.PI*2);c.strokeStyle='#ead49b88';c.lineWidth=1;c.stroke();}}
      for(const {p,x,y,active} of [...pins].sort((a,b)=>Number(b.active)-Number(a.active))){
        c.font=`${active?'600 ':''}${this.player?13:11}px 'Segoe UI',sans-serif`;let label=p.name;while(c.measureText(label).width>175&&label.length>5)label=label.slice(0,-2)+'…';const width=c.measureText(label).width+10,height=22;
        const overlap=(a,b)=>a.x<b.x+b.w&&a.x+a.w>b.x&&a.y<b.y+b.h&&a.y+a.h>b.y;
        const candidates=[{x:x+17,y:y-11},{x:x-width-17,y:y-11},{x:x-width/2,y:y-36},{x:x-width/2,y:y+18}].map(a=>({...a,w:width,h:height}));
        const box=candidates.find(a=>a.x>=3&&a.y>=3&&a.x+a.w<=this.w-3&&a.y+a.h<=this.h-3&&!occupied.some(b=>overlap(a,b))&&!pins.some(other=>overlap(a,{x:other.x-12,y:other.y-12,w:24,h:24})));
        if(!box)continue;occupied.push(box);c.fillStyle='#142017ed';c.fillRect(box.x,box.y,box.w,box.h);c.fillStyle=active?'#f5e1b1':'#e5e2cc';c.fillText(label,box.x+5,box.y+15);
      }
    }
    this.drawAnnotations();
    this.drawTokens();
    this.drawBrushCursor();
    const ping=this.state.ping;if(ping&&Date.now()/1000-ping.at<3){const age=Date.now()/1000-ping.at,x=this.tx+ping.x*this.map.width*this.scale,y=this.ty+ping.y*this.map.height*this.scale;c.beginPath();c.arc(x,y,12+age*15,0,Math.PI*2);c.strokeStyle=`rgba(255,214,132,${1-age/3})`;c.lineWidth=3;c.stroke();requestAnimationFrame(()=>this.draw());}
    this.onZoom?.(Math.round(this.scale/(this.baseScale||this.scale)*100));
  }
  drawBrushCursor(){
    if(!this.hover||this.space||!this.valid(this.hover))return;
    const ink=this.player&&['pen','eraser'].includes(this.annotationMode);
    const fog=!this.player&&this.map.kind==='dungeon'&&['reveal','hide'].includes(this.tool);
    if(!ink&&!fog)return;
    const c=this.ctx,x=this.tx+this.hover.x*this.scale,y=this.ty+this.hover.y*this.scale;
    const radius=ink?this.penSize/2:this.radius*this.scale;
    c.save();c.beginPath();c.arc(x,y,Math.max(.5,radius),0,Math.PI*2);c.strokeStyle='#000';c.lineWidth=3;c.stroke();c.strokeStyle=ink&&this.annotationMode==='pen'?this.penColor:'#fff';c.lineWidth=1;c.stroke();c.restore();
  }
}
