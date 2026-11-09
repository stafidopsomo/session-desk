import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from sessiondesk.importer import Library,UserError,plain
from sessiondesk.store import Store
from tests.fixtures import make_library


class BookTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='sessiondesk-book-test-')
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.graph,self.blobs=Library(make_library(root/'library',rich=True)).load('DEMO')
        self.store=Store(root/'profile');self.wid=self.store.create('Original book test')['id'];self.aid=self.graph['id']

    def test_structured_book_keeps_box_context_and_player_pair(self):
        box=next(e for e in self.graph['entries'] if e['key']=='16b')
        self.assertEqual(box['name'],'Read-aloud')
        self.assertFalse(box['has_heading'])
        self.assertEqual(next(e for e in self.graph['entries'] if e['id']==box['parent'])['name'],'Arrival platform')
        self.assertEqual(self.graph['book'][0]['entries'][0]['entries'][2]['type'],'insetReadaloud')
        player=next(m for m in self.graph['maps'] if m['image_type']=='mapPlayer')
        self.assertEqual(self.graph['maps'][0]['player_map'],player['id'])
        self.assertEqual(plain('{@area area 16|085|x}'),'area 16')

    def test_pins_are_persistent_scoped_backed_up_and_never_player_data(self):
        self.store.import_graph(self.wid,self.graph,self.blobs)
        entry=self.graph['entries'][1]['id']
        expected=[{'kind':'entry','id':entry}]
        self.assertEqual(self.store.pin(self.wid,self.aid,'entry',entry,True),expected)
        self.assertEqual(Store(self.store.root).adventure(self.wid,self.aid)['pins'],expected)
        self.assertNotIn('pins',self.store.session(self.wid,self.aid,True))
        other=self.store.create('Independent')['id']
        with self.assertRaises(UserError):self.store.pin(other,self.aid,'entry',entry,True)
        restored=self.store.restore(self.store.backup(self.wid))['id']
        self.assertEqual(self.store.adventure(restored,self.aid)['pins'],expected)
        self.assertEqual(self.store.pin(self.wid,self.aid,'entry',entry,False),[])

    def test_player_variant_is_behind_dm_map_and_uses_shared_fog_coordinates(self):
        self.store.import_graph(self.wid,self.graph,self.blobs)
        dm=self.graph['maps'][0]
        player=next(m for m in self.graph['maps'] if m['id']==dm['player_map'])
        self.assertNotEqual(player['asset'],dm['asset'])
        self.store.review_map(self.wid,self.aid,dm['id'],{'player_safe':True})
        self.store.session_action(self.wid,self.aid,{'action':'present','media':dm['id']})
        state=self.store.session(self.wid,self.aid,True)
        tab=state['tabs'][0]
        self.assertEqual(tab['id'],dm['id']);self.assertEqual(tab['asset'],player['asset'])
        self.assertEqual((tab['width'],tab['height']),(dm['width'],dm['height']))
        self.assertNotIn('player_map',tab)

    def test_backup_rejects_cyclic_book_hierarchy_before_restore(self):
        self.store.import_graph(self.wid,self.graph,self.blobs)
        out=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(self.store.backup(self.wid))) as source,zipfile.ZipFile(out,'w') as target:
            for name in source.namelist():
                content=source.read(name)
                if name=='workspace.json':
                    data=json.loads(content)
                    entries=data['documents']['adventure:'+self.aid]['entries']
                    entries[0]['parent']=entries[1]['id']
                    content=json.dumps(data).encode()
                target.writestr(name,content)
        with self.assertRaisesRegex(UserError,'cyclic'):self.store.restore(out.getvalue())
        self.assertEqual(len(self.store.listing()),1)

    def test_same_snapshot_enrichment_preserves_prep_session_pins_and_manual_boundary(self):
        legacy=copy.deepcopy(self.graph);legacy.pop('book');legacy.pop('book_schema')
        for item in legacy['maps']+legacy['pictures']:
            for field in ('image_type','player_map','map_parent','source_id','path','order'):
                item.pop(field,None)
        self.store.import_graph(self.wid,legacy,self.blobs)
        media=legacy['maps'][0];entry=legacy['entries'][1]['id'];region=media['regions'][0]
        points=[[10,10],[100,10],[100,100],[10,100]]
        self.store.prepare(self.wid,self.aid,entry,{'notes':'Keep my note','translation':'Keep my narration'})
        self.store.pin(self.wid,self.aid,'entry',entry,True)
        manual=self.store.add_picture(self.wid,self.aid,'My local illustration',next(iter(self.blobs.values()))[1])
        self.store.review_map(self.wid,self.aid,media['id'],{'player_safe':True,'region':{**region,'points':points,'verified':True}})
        self.store.session_action(self.wid,self.aid,{'action':'present','media':media['id']})
        before=self.store.session(self.wid,self.aid)
        result=self.store.import_graph(self.wid,copy.deepcopy(self.graph),self.blobs)
        self.assertTrue(result['enriched'])
        saved=self.store.adventure(self.wid,self.aid)
        self.assertIn('book',saved)
        self.assertEqual(saved['preparation'][entry]['notes'],'Keep my note')
        self.assertEqual(saved['maps'][0]['regions'][0]['points'],points)
        self.assertEqual(len(saved['pins']),1)
        self.assertIn(manual['id'],{p['id'] for p in saved['pictures']})
        self.assertEqual(self.store.session(self.wid,self.aid),before)


if __name__=='__main__':unittest.main()
