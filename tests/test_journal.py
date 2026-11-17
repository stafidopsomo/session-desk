"""Original synthetic campaign-book and local-navigation contracts."""
import copy
import hashlib
import json
from sessiondesk import journal
from sessiondesk.importer import UserError
from sessiondesk.prepared import Prepared
from sessiondesk.server import Application
from sessiondesk.store import Store
from sessiondesk.workspace_modules import MODULE_ID
from tests.test_prepared import PreparedCase

class JournalTests(PreparedCase):
    def create(self,collection='entries',**fields):
        return journal.patch(self.store,self.wid,{'collection':collection,'create':True,'fields':{'title':'Original synthetic record',**fields}})

    def test_fresh_and_restored_workspaces_share_the_book_contract(self):
        self.wid=self.store.create('Original empty campaign')['id']
        fresh=journal.get(self.store,self.wid)
        self.assertEqual(fresh['entries'],[])
        self.assertEqual(fresh['missions'],[])
        self.assertEqual(fresh['party'],[])
        entry=self.create(text='Original table note')
        self.assertEqual(entry['revision'],1)
        self.imported()
        root=self.store.folder(self.wid)/'module-files'/MODULE_ID
        original=(root/'state/table.json').read_bytes()
        seeded=journal.get(self.store,self.wid)
        self.assertEqual(seeded['migratedFrom'],'module:'+MODULE_ID)
        self.assertEqual((root/'state/table.json').read_bytes(),original)
        self.assertEqual(journal.get(self.store,self.wid),seeded)

    def test_authored_book_seeds_once_with_unknown_fields_and_provenance_preserved(self):
        self.imported();root=self.store.folder(self.wid)/'module-files'/MODULE_ID
        authored={'format':'original-planning-data','schemaVersion':1,'title':'Original authored book','chapters':[{'id':'now','title':'Now'}],
            'entries':[{'id':'reported','chapter':'now','title':'Original report','text':'Original report text','status':'confirmed','visibility':'dm','futureField':{'a':1}}],
            'missions':[{'id':'original-task','title':'Original task','status':'Offered','reward':{'offered':'50 gp','awarded':None,'provenance':'Original authored terms'}}]}
        (root/'data/campaign-book.json').write_text(json.dumps(authored))
        first=journal.get(self.store,self.wid)
        self.assertEqual(first['entries'][0]['futureField'],{'a':1})
        (root/'data/campaign-book.json').write_text('{}')
        self.assertEqual(journal.get(self.store,self.wid),first)
        updated=journal.patch(self.store,self.wid,{'collection':'missions','id':'original-task','revision':0,'fields':{'reward':{'offered':'60 gp','awarded':None}}})
        self.assertEqual(updated['reward']['provenance'],'Original authored terms')

    def test_record_revisions_protect_two_tabs_without_replacing_other_records(self):
        self.wid=self.store.create('Original concurrency case')['id']
        a,b=self.create(),self.create()
        journal.patch(self.store,self.wid,{'collection':'entries','id':a['id'],'revision':a['revision'],'fields':{'text':'Saved in tab one'}})
        with self.assertRaisesRegex(UserError,'another tab'):
            journal.patch(self.store,self.wid,{'collection':'entries','id':a['id'],'revision':a['revision'],'fields':{'text':'Stale tab draft'}})
        journal.patch(self.store,self.wid,{'collection':'entries','id':b['id'],'revision':b['revision'],'fields':{'text':'Independent tab two'}})
        entries=journal.get(self.store,self.wid)['entries']
        self.assertEqual([e['text'] for e in entries],['Saved in tab one','Independent tab two'])

    def test_resolving_mission_does_not_award_its_reward(self):
        self.wid=self.store.create('Original mission case')['id'];m=self.create('missions',status='Offered',reward={'offered':'50 gp','awarded':None})
        for status in ('Active','Resolved'):
            m=journal.patch(self.store,self.wid,{'collection':'missions','id':m['id'],'revision':m['revision'],'fields':{'status':status}})
        self.assertIsNone(m['reward']['awarded'])
        self.assertEqual(m['reward']['offered'],'50 gp')

    def test_book_and_party_roundtrip_with_unchanged_maps_characters_and_fog(self):
        self.imported();root=self.store.folder(self.wid)/'module-files'/MODULE_ID
        original={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
        self.create(text='Original journal for another machine')
        before=journal.get(self.store,self.wid)
        archive=self.root/'journal.zip';self.store.backup_file(self.wid,archive)
        other=Store(self.root/'restored-profile');meta=other.restore_file(archive)
        self.assertEqual(journal.get(other,meta['id']),before)
        output=other.folder(meta['id'])/'module-files'/MODULE_ID
        self.assertTrue(all((output/p).read_bytes()==data for p,data in original.items()))

    def test_inspection_of_another_map_does_not_present_or_change_saved_state(self):
        self.imported();prepared=Prepared(self.store,self.wid)
        before=copy.deepcopy(prepared.runtime.state)
        original=(prepared.workspace.path('state')/'table.json').read_bytes()
        maps=prepared.runtime.catalog()['maps']
        for m in maps:
            value=prepared.api('/api/map-state','GET',{}, {'mapId':[m['id']]},False)
            self.assertEqual(value['mapId'],m['id'])
            self.assertEqual(prepared.runtime.state,before)
        self.assertEqual((prepared.workspace.path('state')/'table.json').read_bytes(),original)
        with self.assertRaises(PermissionError):prepared.api('/api/map-state','GET',{}, {'mapId':[maps[0]['id']]},True)

    def test_party_notes_use_revision_guards_and_preserve_mechanics(self):
        self.imported();app=Application(self.store)
        self.addCleanup(app.close)
        original=journal.party(app,self.wid)['characters'][0]
        updated=journal.party(app,self.wid,{'id':original['id'],'revision':original['revision'],'field':'notes','value':'Original new note'})['characters'][0]
        for key in ('sheet','level','threads'):self.assertEqual(updated.get(key),original.get(key))
        with self.assertRaisesRegex(UserError,'another tab'):
            journal.party(app,self.wid,{'id':original['id'],'revision':original['revision'],'field':'notes','value':'Stale note'})

    def test_player_cannot_read_or_edit_book_and_malformed_module_is_rejected(self):
        self.wid=self.store.create('Original private case')['id'];app=Application(self.store);self.addCleanup(app.close)
        for path in ('/api/journal','/api/journal/patch','/api/party','/api/party/patch'):
            with self.assertRaises(PermissionError):app.api(path,{'workspace':self.wid},True,'POST')
        entry=self.create();book=journal.get(self.store,self.wid);book['entries'].append(book['entries'][0])
        with self.assertRaises(UserError):journal.validate(book)

    def test_workspace_mode_survives_restore_and_only_changes_starting_organisation(self):
        self.wid=self.store.create('Original single session',session_mode='oneshot')['id']
        book=journal.get(self.store,self.wid)
        self.assertEqual(book['sessionMode'],'oneshot')
        self.assertEqual([c['id'] for c in book['chapters']],['now','preparation','notes'])
        self.assertEqual(book['party'],[])
        restored=self.store.restore(self.store.backup(self.wid))
        self.assertEqual(restored['session_mode'],'oneshot')
        self.assertEqual(journal.get(self.store,restored['id']),book)
        with self.assertRaises(UserError):self.store.create('Original invalid case',session_mode='anything')
