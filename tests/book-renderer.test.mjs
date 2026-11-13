import test from 'node:test';
import assert from 'node:assert/strict';
import {bookContext,renderSource,inline,referenceHref} from '../sessiondesk/static/book.js';

const entry={id:'original-entry',key:'lens',chapter:0,path:[0],name:'Original section'};
const graph={entries:[entry],maps:[],pictures:[],book:[{name:'Original section',entries:[
  {type:'insetReadaloud',entries:['An original read-aloud.']},
  {type:'table',colLabels:['Roll','Observation'],rows:[['1','<script>bad()</script>']]},
  {type:'list',items:['A handle','A ribbon']}
]}]};
const context=bookContext(graph,()=>'/original.png');

test('structured book keeps boxes, table columns and lists while escaping source HTML',()=>{
  const html=renderSource(entry,context);
  assert.match(html,/book-box readaloud/);assert.match(html,/<table>/);assert.match(html,/<th>Observation<\/th>/);
  assert.match(html,/<ul>/);assert.doesNotMatch(html,/<script>/);assert.match(html,/&lt;script&gt;/);
});
test('area flags stay hidden and links resolve to an entry, including nested typography',()=>{
  assert.match(inline('{@area area 16|lens|x}',context),/data-id="original-entry">area 16<\/button>/);
  assert.equal(inline('{@b Look at {@i the lens}}',context),'<strong>Look at <em>the lens</em></strong>');
});


test('entity tags link to exact local 2014 pages and source-specific hashes',()=>{
  const ctx=bookContext({...graph,reference_base:'/reference/original-workspace/original-capability/'},()=>'/original.png');
  for(const [tag,page,source] of [['creature','bestiary','MM'],['spell','spells','PHB'],['item','items','DMG'],['background','backgrounds','PHB'],['race','races','PHB'],['class','classes','PHB'],['feat','feats','PHB']]) {
    const html=inline('{@'+tag+' Original Glass Guardian}',ctx);
    assert.ok(html.includes('href="/reference/original-workspace/original-capability/'+page+'.html#original%20glass%20guardian_'+source.toLowerCase()+'"'));
    assert.match(html,/target="_blank" rel="noopener noreferrer"/);
  }
  const html=inline('{@creature Original Guardian|SYNTH|the guardian}',ctx);
  assert.match(html,/bestiary.html#original%20guardian_synth/);
  assert.match(html,/>the guardian ↗<\/a>/);
});

test('book/adventure locators keep chapter and heading, class locators retain subclass state',()=>{
  assert.equal(referenceHref('book',['Original handbook','PHB','2','Original Hall','1'],context),'/reference/book.html#phb,2,original%20hall,1');
  assert.equal(referenceHref('adventure',['Original adventure','LAB-1','0','A & B'],context),'/reference/adventure.html#lab-1,0,a%20%26%20b');
  assert.equal(referenceHref('class',['Original Class','LAB','','Original Path','LAB'],context),'/reference/classes.html#original%20class_lab,state:sub_original%20path_lab=b1');
  assert.equal(referenceHref('book',['Original handbook','LAB','../../bad'],context),null);
});

test('structured creature and inline statblock references open their actual source entry',()=>{
  const synthetic={...graph,book:[{name:'Original references',entries:[
    {type:'statblock',tag:'creature',name:'Original Glass Guardian',source:'LAB'},
    {type:'statblock',prop:'background',name:'Original Traveler',source:'LAB'},
    {type:'statblockInline',statblockType:'monster',displayName:'Original display',statblockData:{name:'Original Guardian',source:'LAB'}}
  ]}]};
  const html=renderSource(entry,bookContext(synthetic,()=>'/original.png'));
  assert.match(html,/bestiary.html#original%20glass%20guardian_lab/);
  assert.match(html,/backgrounds.html#original%20traveler_lab/);
  assert.match(html,/bestiary.html#original%20guardian_lab/);
  assert.match(html,/>Original display ↗<\/a>/);
  assert.doesNotMatch(html,/<strong>Reference<\/strong>/);
});

test('reference labels and locators cannot inject HTML or external URLs',()=>{
  const html=inline('{@creature <img onerror=bad()>|LAB|<script>bad()</script>}',context);
  assert.doesNotMatch(html,/<script>|<img/);assert.match(html,/&lt;script&gt;/);
  assert.match(html,/bestiary.html#%3cimg%20onerror%3dbad\(\)%3e_lab/);
  for(const prefix of ['https://outside.invalid/','//outside.invalid/','/reference/../','/reference/?bad=1']) {
    assert.equal(referenceHref('creature',['Original Guardian','LAB'],{...context,referenceURL:prefix}),null);
  }
  assert.equal(referenceHref('creature',['Original\nGuardian','LAB'],context),null);
  assert.equal(inline('{@link Original label|https://outside.invalid/}',context),'Original label');
});

test('unsupported references preserve authored names without invented source destinations',()=>{
  const unknown={...graph,book:[{type:'statblock',tag:'unknownPlugin',name:'Original unsupported reference',source:'LAB'}]};
  const html=renderSource(entry,bookContext(unknown,()=>'/original.png'));
  assert.match(html,/Original unsupported reference/);
  assert.doesNotMatch(html,/href=/);
});
