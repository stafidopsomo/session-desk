const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data,shopId='all';
function render(){
  const query=$('search').value.trim().toLowerCase(),category=$('category').value;
  const rows=data.items.filter(item=>(shopId==='all'||item.shopId===shopId)&&(category==='all'||item.category===category)&&(`${item.name} ${item.note} ${item.category}`).toLowerCase().includes(query));
  $('items').innerHTML=rows.map(item=>{const shop=data.shops.find(s=>s.id===item.shopId);return `<tr><td><strong>${esc(item.name)}</strong><small>${esc(item.category)}</small></td><td class="price">${esc(item.price)}</td><td>${esc(shop.name)}</td><td>${esc(item.note)}</td><td><a target="_blank" rel="noopener" href="${esc(item.sourceLink)}">${esc(item.source)} p. ${item.page} ↗</a></td></tr>`;}).join('');
  $('count').textContent=`${rows.length} items · listed book prices`;$('empty').hidden=rows.length>0;
  document.querySelectorAll('[data-shop]').forEach(button=>{const selected=button.dataset.shop===shopId;button.classList.toggle('active',selected);button.setAttribute('aria-pressed',String(selected));});
  $('allShops').classList.toggle('active',shopId==='all');
}
try{
  const response=await fetch('/api/shop');if(!response.ok)throw Error();data=await response.json();
  $('intro').textContent=data.intro;$('coinage').textContent=data.coinage;$('stockNote').textContent=data.stockNote;
  $('book').href=data.sourceLink;$('priceSource').href=data.priceSourceUrl;
  $('shops').innerHTML=data.shops.map(shop=>`<article><button data-shop="${esc(shop.id)}"><strong>${esc(shop.name)}</strong><span>${esc(shop.location)}</span><p>${esc(shop.summary)}</p></button><a target="_blank" rel="noopener" href="${esc(shop.sourceUrl)}">Location reference ↗</a></article>`).join('');
  $('category').append(...[...new Set(data.items.map(item=>item.category))].map(name=>new Option(name,name)));
  document.querySelectorAll('[data-shop]').forEach(button=>button.onclick=()=>{shopId=button.dataset.shop;$('category').value='all';render();});
  $('allShops').onclick=()=>{shopId='all';$('category').value='all';render();};$('search').oninput=render;$('category').onchange=render;render();
}catch{$('intro').textContent='Could not load the price list. Refresh after checking the campaign server.';}
