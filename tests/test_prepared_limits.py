"""Prepared actions cannot save states that their own backup contract rejects."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from sessiondesk.prepared import Prepared
from sessiondesk.prepared_engine import MAX_FOG_OPERATIONS, MAX_TABS
from sessiondesk.store import Store
from tests.prepared_fixture import make_prepared, pack


class PreparedSessionLimitTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='sessiondesk-prepared-limits-')
        self.addCleanup(self.temp.cleanup)
        base=Path(self.temp.name)
        original=make_prepared(base/'original')
        self.store=Store(base/'data')
        self.wid=self.store.restore_file(pack(original,base/'original.zip'))['id']
        self.prepared=Prepared(self.store,self.wid)
        self.runtime=self.prepared.runtime
        self.file=self.prepared.workspace.path('state')/'table.json'

    def action(self, **body):
        return self.prepared.api('/api/action','POST',body,{},False)

    def full_tabs(self):
        tabs=[{'id':'existing-'+str(i),'kind':'guide','cardId':'world'} for i in range(MAX_TABS)]
        self.runtime.state.update(tabs=tabs,activeTabId=tabs[0]['id'])

    def assert_rejected_without_change(self, body, message):
        state=copy.deepcopy(self.runtime.state)
        table=copy.deepcopy(self.runtime.table)
        saved=self.file.read_bytes()
        with self.assertRaisesRegex(ValueError,message):self.action(**body)
        self.assertEqual(self.runtime.state,state)
        self.assertEqual(self.runtime.table,table)
        self.assertEqual(self.file.read_bytes(),saved)

    def test_generic_book_card_uses_its_local_source_and_title(self):
        self.action(action='book-section',cardId='world')
        tab=next(t for t in self.runtime.state['tabs'] if t['id']=='book:world')
        self.assertEqual(tab['url'],'/reference/book.html#phb,0')
        self.assertEqual(tab['title'],'Our example world')
        shared=self.runtime.snapshot(player=True)['bookSection']
        self.assertEqual(shared,{'url':tab['url'],'title':tab['title']})

    def test_book_card_rejects_external_malformed_or_nonbook_sources(self):
        path=self.prepared.workspace.data/'world-guide.json'
        source=json.loads(path.read_text())
        for link in ('https://example.invalid/book.html#phb','//example.invalid/book.html#phb',
                '/reference/adventure.html#demo,0','/reference/book.html?source=elsewhere#phb',
                '/reference/book.html#../../private','/reference/book.html#phb%2fsecret',
                '/reference/book.html#phb\n','/reference/book.html#phb\\file','/reference/book.html#'):
            with self.subTest(link=link):
                source['cards'][0]['sourceLink']=link;path.write_text(json.dumps(source))
                self.assert_rejected_without_change({'action':'book-section','cardId':'world'},'local book source')

    def test_fog_cap_rejects_every_append_before_state_or_camera_mutation(self):
        op={'kind':'room','id':'a','shape':0,'reveal':True}
        self.runtime.state['fog']['practice']['operations']=[op.copy() for _ in range(MAX_FOG_OPERATIONS-1)]
        self.action(action='room',id='a',shape=0,reveal=True)
        self.assertEqual(len(self.runtime.state['fog']['practice']['operations']),MAX_FOG_OPERATIONS)
        for body in ({'action':'room','id':'a','shape':0,'reveal':True},
                     {'action':'brush','points':[[100,100]],'radius':10,'reveal':True},
                     {'action':'all'},{'action':'cover'}):
            with self.subTest(body=body):self.assert_rejected_without_change(body,'Fog history is full')

    def test_undo_and_reset_remain_available_at_fog_cap(self):
        op={'kind':'room','id':'a','shape':0,'reveal':True}
        self.runtime.state['fog']['practice']['operations']=[op.copy() for _ in range(MAX_FOG_OPERATIONS)]
        self.action(action='undo')
        self.assertEqual(len(self.runtime.state['fog']['practice']['operations']),MAX_FOG_OPERATIONS-1)
        self.action(action='reset')
        self.assertEqual(self.runtime.state['fog']['practice']['operations'],[])

    def test_all_new_tab_actions_are_rejected_without_mutation_at_cap(self):
        self.full_tabs()
        for body in ({'action':'map','mapId':'realm'},
                     {'action':'location','mapId':'realm','id':'village'},
                     {'action':'guide','cardId':'world'},
                     {'action':'book-section','cardId':'world'},
                     {'action':'shop-catalog'},
                     {'action':'room-scene','id':'a','shape':0},
                     {'action':'picture','path':'adventures/practice/a.png'},
                     {'action':'map-view'}):
            with self.subTest(body=body):self.assert_rejected_without_change(body,'100 maximum')
        self.runtime.state['tabs'][0]={'id':'scene:a','kind':'picture','path':'adventures/practice/a.png',
            'title':'Original scene','scene':{'mapId':'practice','roomId':'a','shape':0}}
        self.runtime.state.update(mapId='realm',locationId='village',activeTabId='scene:a')
        self.assert_rejected_without_change({'action':'room-scene-map'},'100 maximum')

    def test_existing_tab_and_close_actions_remain_usable_at_cap(self):
        self.full_tabs()
        self.runtime.state['tabs'][0]={'id':'map:practice','kind':'map','mapId':'practice','locationId':None}
        self.runtime.state['activeTabId']='map:practice'
        self.action(action='map',mapId='practice')
        self.assertEqual(len(self.runtime.state['tabs']),MAX_TABS)
        self.action(action='tab-close',id='map:practice')
        self.assertEqual(len(self.runtime.state['tabs']),MAX_TABS-1)
        self.action(action='guide',cardId='world')
        self.assertEqual(len(self.runtime.state['tabs']),MAX_TABS)
        self.action(action='tab-close-all')
        self.assertEqual(self.runtime.state['tabs'],[])
