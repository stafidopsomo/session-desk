import copy
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid
import zipfile

from sessiondesk.importer import UserError
from sessiondesk.prepared import Prepared
from sessiondesk.server import Application, make_server
from sessiondesk.store import SCHEMA, Store
from sessiondesk.workspace_modules import MODULE_ID, local
from tests.prepared_fixture import make_prepared, pack, rules_library


class PreparedCase(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='sessiondesk-prepared-synthetic-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.original=make_prepared(self.root/'original')
        self.archive=pack(self.original,self.root/'recovery.zip',recovery=True)
        self.store=Store(self.root/'app-data')

    def imported(self):
        self.meta=self.store.restore_file(self.archive)
        self.wid=self.meta['id']
        return self.wid

    def module(self, store=None, wid=None):
        store=store or self.store
        with store.db(wid or self.wid) as conn:
            return store.get(conn,'module:'+MODULE_ID)


class PreparedStorageTests(PreparedCase):
    def test_all_files_and_original_recovery_are_preserved_without_executing_code(self):
        self.imported()
        module=self.module()
        expected={p.relative_to(self.original).as_posix():p.read_bytes() for p in self.original.rglob('*') if p.is_file()}
        self.assertEqual(set(module['files']),set(expected))
        for name,data in expected.items():
            self.assertEqual((self.store.folder(self.wid)/'module-files'/MODULE_ID/name).read_bytes(),data)
            self.assertEqual(module['files'][name]['asset'],hashlib.sha256(data).hexdigest())
        self.assertEqual(module['original']['asset'],hashlib.sha256(self.archive.read_bytes()).hexdigest())
        self.assertEqual(module['files']['prep/same.txt']['asset'],module['files']['prep/same.md']['asset'])
        self.assertEqual(module['files']['prep/same.txt']['mime'],module['files']['prep/same.md']['mime'])
        self.assertEqual(module['summary']['characters'],1)
        self.assertEqual(module['summary']['maps'],2)

    def test_workspace_export_restore_preserves_edits_state_attachments_and_original_archive(self):
        self.imported()
        reference=rules_library(self.root/'rules')
        runtime=Prepared(self.store,self.wid,reference)
        runtime.api('/api/characters','POST',{'id':'explorer','field':'notes','value':'Changed original private note'},{},False)
        runtime.api('/api/action','POST',{'action':'room-note','mapId':'practice','id':'a','shape':0,'text':'The arrival is clear.'},{},False)
        runtime.api('/api/action','POST',{'action':'brush','mapId':'practice','points':[[100,100],[120,120]],'radius':10,'reveal':True},{},False)
        target=self.root/'workspace.zip'
        self.store.backup_file(self.wid,target)
        other=Store(self.root/'other-machine')
        restored=other.restore_file(target)
        module=self.module(other,restored['id'])
        self.assertEqual(len(module['files']),len(self.module()['files']))
        r=Prepared(other,restored['id'],reference)
        self.assertEqual(r.api('/api/characters','GET',{}, {},False)['characters'][0]['notes'],'Changed original private note')
        self.assertEqual(r.runtime.snapshot()['roomNotes']['a:0'],'The arrival is clear.')
        self.assertEqual(len(r.runtime.snapshot()['fogState']['operations']),3)
        self.assertEqual(module['original']['asset'],hashlib.sha256(self.archive.read_bytes()).hexdigest())
        for original in ('prep/do-not-run.py','prep/original.pdf','prep/same.md'):
            self.assertEqual(local(r.workspace.root,original).read_bytes(),local(self.original,original).read_bytes())

    def test_cancelled_conversion_has_no_visible_or_partial_workspace(self):
        stop=threading.Event()
        with self.assertRaises(UserError):
            self.store.restore_file(self.archive,stop.is_set,lambda *_:stop.set())
        self.assertEqual(self.store.listing(),[])
        self.assertFalse(list(self.store.workspaces.glob('_restore-*')))

    def test_invalid_map_dimensions_and_unsafe_paths_fail_without_publication(self):
        maps=json.loads((self.original/'data/maps.json').read_text())
        maps['maps'][0]['width']=450
        (self.original/'data/maps.json').write_text(json.dumps(maps))
        pack(self.original,self.archive,recovery=True)
        with self.assertRaisesRegex(UserError,'dimensions'):
            self.store.restore_file(self.archive)
        self.assertEqual(self.store.listing(),[])
        with zipfile.ZipFile(self.archive,'a') as out:out.writestr('../escape.txt','Not allowed')
        with self.assertRaises(UserError):self.store.restore_file(self.archive)
        self.assertEqual(self.store.listing(),[])

    def test_corrupt_recovery_manifest_fails_before_workspace_is_visible(self):
        self.archive=pack(self.original,self.root/'raw.zip')
        with zipfile.ZipFile(self.archive,'a') as out:
            out.writestr('backup-manifest.json',json.dumps({'format':'campaign-desk-full-snapshot','files':[{'path':'campaign.json','sha256':'0'*64,'size':1}]}))
        with self.assertRaisesRegex(UserError,'checksum'):self.store.restore_file(self.archive)
        self.assertEqual(self.store.listing(),[])

    def test_unknown_module_is_inert_and_roundtrips_unchanged(self):
        wid=self.store.create('Future module workspace')['id']
        digest=hashlib.sha256(b'Future data').hexdigest()
        record={'asset':digest,'size':11,'mime':'application/octet-stream'}
        value={'kind':'future-module','schema':17,'enabled':True,'title':'Future data',
               'files':{'original.bin':record},'future_fields':{'original':'preserve this'}}
        with self.store.db(wid) as conn:
            self.store.put(conn,'module:'+MODULE_ID,value)
            conn.execute('INSERT INTO assets VALUES (?,?,?)',(digest,record['mime'],11))
        (self.store.folder(wid)/'assets'/digest).write_bytes(b'Future data')
        restored=self.store.restore(self.store.backup(wid))
        self.assertEqual(self.module(wid=restored['id']),value)
        with self.assertRaises(UserError):Prepared(self.store,restored['id'])
        again=self.store.restore(self.store.backup(restored['id']))
        self.assertEqual(self.module(wid=again['id']),value)

    def test_old_database_upgrade_keeps_schema_one_recovery_copy(self):
        wid=self.store.create('Original profile')['id']
        file=self.store.folder(wid)/'workspace.sqlite3'
        conn=sqlite3.connect(file);conn.execute('PRAGMA user_version=1');conn.commit();conn.close()
        self.store.overview(wid)
        recovery=self.store.folder(wid)/'workspace-schema-1.sqlite3.bak'
        self.assertTrue(recovery.is_file())
        old=sqlite3.connect(recovery)
        try:self.assertEqual(old.execute('PRAGMA user_version').fetchone()[0],1)
        finally:old.close()
        with self.store.db(wid) as conn:self.assertEqual(conn.execute('PRAGMA user_version').fetchone()[0],SCHEMA)

    def test_fresh_workspace_has_no_optional_panels_or_personal_defaults(self):
        wid=self.store.create('Fresh workspace')['id']
        self.assertEqual(self.store.overview(wid)['modules'],[])
        with self.assertRaises(UserError):Prepared(self.store,wid)


class PreparedRuntimeTests(PreparedCase):
    def setUp(self):
        super().setUp();self.imported()
        self.reference=rules_library(self.root/'rules')
        self.app=Application(self.store)
        self.app.connect_source(self.wid,self.reference)
        self.server=make_server(self.app)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        self.origin=f'http://127.0.0.1:{self.server.server_port}'

    def call(self,path,body=None,player=False):
        token=self.app.player_token if player else self.app.dm_token
        url=self.origin+f'/campaign/{self.wid}/{token}'+path
        headers={'Origin':self.origin}
        if body is not None:headers['Content-Type']='application/json'
        req=Request(url,data=None if body is None else json.dumps(body).encode(),headers=headers)
        return urlopen(req,timeout=15)

    def test_player_snapshot_and_routes_never_expose_character_or_dm_state(self):
        with self.call('/api/player-state',player=True) as r:state=json.load(r)
        text=json.dumps(state)
        for marker in ('SYNTHETIC_PRIVATE','Original secret','backstory','encounter'):
            self.assertNotIn(marker,text)
        for route in ('/api/data','/api/characters','/api/character-rules','/'):
            with self.assertRaises(HTTPError) as error:self.call(route,player=True)
            self.assertEqual(error.exception.code,403)
        with self.call('/assets/maps/player.png',player=True) as r:self.assertEqual(r.status,200)
        for route in ('/assets/maps/dm.png','/assets/prep/do-not-run.py','/assets/adventures/practice/held.png'):
            with self.assertRaises(HTTPError) as error:self.call(route,player=True)
            self.assertEqual(error.exception.code,403)

    def test_actions_preserve_selection_fog_and_require_visible_room_for_player_notes(self):
        r=self.app.prepared(self.wid).runtime
        before=copy.deepcopy(r.state['fog'])
        with self.call('/api/action',{'action':'location','id':'b'}) as response:json.load(response)
        self.assertEqual(r.state['fog'],before)
        with self.assertRaises(HTTPError):self.call('/api/player-action',{'action':'room-note','mapId':'practice','id':'b','shape':0,'text':'Hidden'},True)
        with self.call('/api/player-action',{'action':'room-note','mapId':'practice','id':'a','shape':0,'text':'Shared'},True) as response:
            self.assertEqual(json.load(response)['roomNotes']['a:0'],'Shared')

    def test_characters_are_editable_and_rules_use_selected_classic_source(self):
        with self.call('/api/character-rules?id=explorer') as r:
            self.assertTrue(any(f['name']=='Original training' for f in json.load(r)['features']))
        with self.call('/api/characters',{'id':'explorer','field':'sheet','value':{'hpCurrent':17}}) as r:
            self.assertEqual(json.load(r)['characters'][0]['sheet']['hpCurrent'],17)

    def test_rules_connection_accepts_data_folder_and_rejects_new_edition(self):
        self.app.connect_source(self.wid,self.reference/'data')
        self.assertEqual(self.app.prepared(self.wid).workspace.reference,self.reference.resolve())
        package=self.reference/'package.json'
        package.write_text(json.dumps({'version':'2.0.0'}))
        with self.assertRaisesRegex(UserError,'2014'):
            self.app.connect_source(self.wid,self.reference)

    def test_invalid_saved_room_reference_prevents_restore_publication(self):
        state=json.loads((self.original/'state/table.json').read_text())
        state['fog']['practice']['operations'].append({'kind':'room','id':'missing','shape':0,'reveal':True})
        (self.original/'state/table.json').write_text(json.dumps(state))
        pack(self.original,self.archive,recovery=True)
        before=self.store.listing()
        with self.assertRaisesRegex(UserError,'reveal'):
            self.store.restore_file(self.archive)
        self.assertEqual(self.store.listing(),before)

    def test_static_mount_uses_player_capability_and_excludes_generation_controls(self):
        with self.call('/static/app.js') as r:text=r.read().decode()
        self.assertIn(f'/campaign/{self.wid}/{self.app.player_token}/player',text)
        self.assertNotIn("window.open('/player'",text)
        self.assertNotIn('pollRoomSceneProgress',text)
        with self.call('/') as r:page=r.read().decode()
        self.assertNotIn('Generate via',page)
        self.assertNotIn('Usage & quotas',page)
        with self.call('/static/bootstrap.js') as r:
            self.assertIn("['','api',path].join('/')",r.read().decode())

    def test_imported_source_files_are_downloads_not_executable_templates(self):
        with self.call('/assets/prep/do-not-run.py') as r:
            self.assertIn('attachment',r.headers['Content-Disposition'])
            self.assertIn(b'Backup code must never run',r.read())
        with self.assertRaises(HTTPError):self.call('/static/../../module-files/prep/do-not-run.py')

    def test_ai_and_cross_origin_writes_are_rejected(self):
        for endpoint in ('/api/usage','/api/room-scenes','/api/ai'):
            with self.assertRaises(HTTPError):self.call(endpoint)
        token=self.app.dm_token
        req=Request(self.origin+f'/campaign/{self.wid}/{token}/api/action',data=b'{"action":"blackout","value":true}',headers={'Origin':'https://example.invalid','Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as error:urlopen(req,timeout=10)
        self.assertEqual(error.exception.code,403)
