// Render imported structured source as book content. Source strings never become HTML.
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pathKey = path => JSON.stringify(path);

export function bookContext(graph, assetURL) {
  return {
    graph, assetURL, referenceURL: graph.reference_base || '/reference/',
    entries: new Map(graph.entries.map(e => [pathKey(e.path),e])),
    media: new Map([...graph.maps,...graph.pictures].filter(m=>m.path).map(m=>[pathKey(m.path),m]))
  };
}

// The local 2014 reader uses lower-case URI components joined with underscores.
// Only fixed local pages are allowed; source names never become URL paths/HTML.
const referenceKinds = Object.freeze({
  creature:['bestiary.html','MM','Creature'], monster:['bestiary.html','MM','Creature'],
  spell:['spells.html','PHB','Spell'], item:['items.html','DMG','Item'],
  background:['backgrounds.html','PHB','Background'], race:['races.html','PHB','Race'],
  class:['classes.html','PHB','Class'], feat:['feats.html','PHB','Feat'],
  condition:['conditionsdiseases.html','PHB','Condition'], status:['conditionsdiseases.html','PHB','Status'],
  disease:['conditionsdiseases.html','DMG','Disease'], optfeature:['optionalfeatures.html','PHB','Optional feature'],
  optionalfeature:['optionalfeatures.html','PHB','Optional feature'],
  action:['actions.html','PHB','Action'], language:['languages.html','PHB','Language'],
  reward:['rewards.html','DMG','Reward'], object:['objects.html','DMG','Object'],
  trap:['trapshazards.html','DMG','Trap'], hazard:['trapshazards.html','DMG','Hazard'],
  variantrule:['variantrules.html','DMG','Variant rule'], table:['tables.html','DMG','Table'],
  vehicle:['vehicles.html','GoS','Vehicle'], boon:['cultsboons.html','MTF','Boon'],
  cult:['cultsboons.html','MTF','Cult']
});
const hashPart = value => encodeURIComponent(String(value).toLowerCase()).toLowerCase();
const validReferencePart = value => typeof value==='string' && value.trim().length>0 && value.length<=500 && !/[\x00-\x1f\x7f]/.test(value);
function localReference(ctx,page,hash) {
  const base=ctx.referenceURL ?? ctx.graph?.reference_base ?? '/reference/';
  if(typeof base!=='string'||!/^\/reference\/(?:[a-zA-Z0-9_-]{1,100}\/)*$/.test(base))return null;
  return base+page+'#'+hash;
}
export function referenceHref(tag,parts,ctx) {
  if(tag==='book'||tag==='adventure') {
    if(!validReferencePart(parts[1]))return null;
    let hash=hashPart(parts[1]);
    if(parts[2]) {
      if(!/^\d{1,4}$/.test(parts[2]))return null;
      hash+=','+parts[2];
      if(parts[3]){if(!validReferencePart(parts[3]))return null;hash+=','+hashPart(parts[3]);}
      if(parts[4]){if(!/^\d{1,4}$/.test(parts[4]))return null;hash+=','+parts[4];}
    }
    return localReference(ctx,tag==='book'?'book.html':'adventure.html',hash);
  }
  const kind=referenceKinds[tag];
  if(!kind||!validReferencePart(parts[0])||!validReferencePart(parts[1]||kind[1]))return null;
  let hash=hashPart(parts[0])+'_'+hashPart(parts[1]||kind[1]);
  if(tag==='class'&&parts[3]) {
    if(!validReferencePart(parts[3])||!validReferencePart(parts[4]||parts[1]||kind[1]))return null;
    hash+=',state:sub_'+hashPart(parts[3])+'_'+hashPart(parts[4]||parts[1]||kind[1])+'=b1';
  }
  return localReference(ctx,kind[0],hash);
}
function referenceAnchor(href,label) {
  return `<a class="book-link reference-link" href="${escape(href)}" target="_blank" rel="noopener noreferrer" title="Open this reference in local 5e.tools">${label} ↗</a>`;
}
function statblock(node,ctx,chapter,depth) {
  const data=node.type==='statblockInline'?(node.statblockData||{}):node;
  const tag=node.tag||node.prop||node.statblockType;
  const kind=referenceKinds[tag];
  const name=data.name||node.name;
  const label=inline(node.displayName||name||'Unnamed reference',ctx,chapter,depth+1);
  const source=data.source||node.source||(kind?.[1]||'');
  const href=name?referenceHref(tag,[name,source],ctx):null;
  return `<aside class="book-reference"><strong>${href?referenceAnchor(href,label):label}</strong><small>${escape(kind?.[2]||'Reference')}${source?' · '+escape(source):''}</small>${href?'':'<p>This reference has no supported local source locator.</p>'}</aside>`;
}

export function sourceNode(entry, graph) {
  if(!graph.book)return null;
  let node=graph.book;
  for(const segment of entry.path) {if(node==null)return null;node=node[segment];}
  return node;
}

export function inline(value, ctx, chapter=0, depth=0) {
  if(depth>10)return escape(value);
  const text=String(value??'');let result='',position=0;
  while(position<text.length) {
    const start=text.indexOf('{@',position);
    if(start<0){result+=escape(text.slice(position));break;}
    result+=escape(text.slice(position,start));let end=start+2,nesting=1;
    for(;end<text.length;end++){if(text[end]==='{')nesting++;if(text[end]==='}'&&--nesting===0)break;}
    if(end===text.length){result+=escape(text.slice(start));break;}
    const match=/^([\w]+)(?:\s+([\s\S]*))?$/.exec(text.slice(start+2,end));
    if(!match){result+=escape(text.slice(start,end+1));position=end+1;continue;}
    const tag=match[1],parts=(match[2]||'').split('|');
    const display=['b','bold','i','italic','u','s','sup','sub'].includes(tag)?match[2]||'':
      ['area','link','filter','book','adventure'].includes(tag)?parts[0]:parts[2]||parts[0];
    const formatted=inline(display,ctx,chapter,depth+1);
    if(['b','bold'].includes(tag))result+=`<strong>${formatted}</strong>`;
    else if(['i','italic'].includes(tag))result+=`<em>${formatted}</em>`;
    else if(['u','s','sup','sub'].includes(tag))result+=`<${tag}>${formatted}</${tag}>`;
    else if(tag==='h')result+='<strong>Hit: </strong>';
    else if(tag==='dc')result+=`DC ${formatted}`;
    else if(tag==='area'){
      const matches=ctx.graph.entries.filter(e=>e.key===parts[1]);
      const local=matches.filter(e=>e.chapter===chapter);const candidates=local.length?local:matches;
      result+=candidates.length===1?`<button type="button" class="book-link" data-action="entry" data-id="${candidates[0].id}">${formatted}</button>`:formatted;
    } else {const href=referenceHref(tag,parts,ctx);result+=href?referenceAnchor(href,formatted):formatted;}
    position=end+1;
  }
  return result;
}

function children(node,key,ctx,path,level) {
  const value=node[key];
  if(Array.isArray(value))return value.map((v,i)=>render(v,ctx,[...path,key,i],level+1)).join('');
  return value==null?'':render(value,ctx,[...path,key],level+1);
}

function render(node,ctx,path,level=0) {
  if(level>80)return '';
  const chapter=typeof path[0]==='number'?path[0]:0;
  if(typeof node==='string'||typeof node==='number')return `<p>${inline(node,ctx,chapter)}</p>`;
  if(Array.isArray(node))return node.map((v,i)=>render(v,ctx,[...path,i],level+1)).join('');
  if(!node||typeof node!=='object')return '';
  const title=node.name?inline(node.name,ctx,chapter):'';
  const heading=title?`<h${Math.min(5,Math.max(2,level+2))}>${title}</h${Math.min(5,Math.max(2,level+2))}>`:'';
  const content=()=>children(node,'entries',ctx,path,level)+children(node,'entry',ctx,path,level);
  if(node.type==='image'){
    const media=ctx.media.get(pathKey(path));
    if(!media||media.image_type==='mapPlayer')return '';
    return `<figure><button type="button" class="book-image" data-action="media" data-id="${media.id}"><img loading="lazy" src="${escape(ctx.assetURL(media))}" alt="${escape(media.name)}"></button><figcaption>${escape(media.name)}</figcaption></figure>`;
  }
  if(node.type==='gallery')return `<div class="book-gallery">${children(node,'images',ctx,path,level)}</div>`;
  if(['insetReadaloud','inset','quote'].includes(node.type))return `<aside class="book-box ${node.type==='insetReadaloud'?'readaloud':node.type==='quote'?'quotation':''}">${heading}${content()}${node.by?`<footer>${inline(node.by,ctx,chapter)}</footer>`:''}</aside>`;
  if(node.type==='list'){
    const ordered=String(node.style||'').startsWith('list-decimal');const tag=ordered?'ol':'ul';
    return heading+`<${tag}>${(node.items||[]).map((v,i)=>`<li>${render(v,ctx,[...path,'items',i],level+1)}</li>`).join('')}</${tag}>`;
  }
  if(['item','itemSub','itemSpell'].includes(node.type))return `${title?`<strong>${title}</strong> `:''}${content()}`;
  if(node.type==='table'){
    const cell=(value)=>{
      if(typeof value==='object'&&value?.roll){const r=value.roll;return escape(r.exact??`${r.min??''}–${r.max??''}`);}
      return typeof value==='object'?render(value,ctx,path,level+1):inline(value,ctx,chapter);
    };
    return `<div class="book-table"><table>${node.caption?`<caption>${inline(node.caption,ctx,chapter)}</caption>`:''}
      ${node.colLabels?`<thead><tr>${node.colLabels.map(x=>`<th>${cell(x)}</th>`).join('')}</tr></thead>`:''}<tbody>${(node.rows||[]).map(row=>`<tr>${(Array.isArray(row)?row:row.row||[]).map(x=>`<td>${cell(x)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }
  if(node.type==='statblock'||node.type==='statblockInline')return statblock(node,ctx,chapter,level);
  const entry=ctx.entries.get(pathKey(path));
  return `<section ${entry?`data-source-entry="${entry.id}"`:''}>${heading}${content()}${children(node,'items',ctx,path,level)}${children(node,'blocks',ctx,path,level)}${children(node,'text',ctx,path,level)}</section>`;
}

export function renderSource(entry,ctx) {
  if(!entry)return '';
  const node=sourceNode(entry,ctx.graph);
  return node?render(node,ctx,entry.path):`<div class="legacy-source">${escape(entry.text)}</div>`;
}
