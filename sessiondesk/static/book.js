// Render imported structured source as book content. Source strings never become HTML.
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pathKey = path => JSON.stringify(path);

export function bookContext(graph, assetURL) {
  return {
    graph, assetURL,
    entries: new Map(graph.entries.map(e => [pathKey(e.path),e])),
    media: new Map([...graph.maps,...graph.pictures].filter(m=>m.path).map(m=>[pathKey(m.path),m]))
  };
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
    } else result+=formatted;
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
  if(node.type==='statblock')return `<aside class="book-reference"><strong>${title||'Reference'}</strong><small>${escape(node.tag||node.prop||'')} ${escape(node.source||'')}</small></aside>`;
  const entry=ctx.entries.get(pathKey(path));
  return `<section ${entry?`data-source-entry="${entry.id}"`:''}>${heading}${content()}${children(node,'items',ctx,path,level)}${children(node,'blocks',ctx,path,level)}${children(node,'text',ctx,path,level)}</section>`;
}

export function renderSource(entry,ctx) {
  if(!entry)return '';
  const node=sourceNode(entry,ctx.graph);
  return node?render(node,ctx,entry.path):`<div class="legacy-source">${escape(entry.text)}</div>`;
}
