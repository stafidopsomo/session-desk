import test from 'node:test';
import assert from 'node:assert/strict';
import {bookContext,renderSource,inline} from '../sessiondesk/static/book.js';

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
