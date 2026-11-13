import json
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from tests.test_core import WorkspaceCase
from sessiondesk.server import Application,make_server
from sessiondesk.importer import UserError

class ExperienceTests(WorkspaceCase):
    def test_adventure_removal_is_confirmed_scoped_and_keeps_shared_assets(self):
        import copy, uuid
        media=self.imported()
        other=copy.deepcopy(self.graph);other['id']=str(uuid.uuid4());other['source']='SECOND';other['fingerprint']='second'
        self.store.import_graph(self.wid,other,self.blobs)
        entry=self.graph['entries'][1]['id']
        self.store.prepare(self.wid,self.aid,entry,{'notes':'Remove this preparation','translation':'','status':'draft'})
        self.store.pin(self.wid,self.aid,'entry',entry,True)
        self.store.session_action(self.wid,self.aid,{'action':'present','media':media['id'],'with_fog':True})
        app=Application(self.store);body={'workspace':self.wid,'adventure':self.aid}
        with self.assertRaises(UserError):app.api('/api/adventure/remove',body,False,'POST')
        with self.assertRaises(PermissionError):app.api('/api/adventure/remove',body|{'confirm':True},True,'POST')
        app.api('/api/adventure/remove',body|{'confirm':True},False,'POST')
        self.assertEqual([a['id'] for a in self.store.overview(self.wid)['adventures']],[other['id']])
        with self.store.db(self.wid) as conn:
            for prefix in ('adventure:','prep:','session:','pins:'):self.assertIsNone(self.store.get(conn,prefix+self.aid))
        self.assertTrue(self.store.adventure(self.wid,other['id'])['maps'])
        self.assertTrue(all((self.store.folder(self.wid)/'assets'/digest).is_file() for digest in self.blobs))
        with self.assertRaises(UserError):self.store.session(self.wid,self.aid,True)
        self.assertTrue((self.lib/'data'/'adventures.json').is_file())

    def test_workspace_removal_retains_recovery_and_blocks_active_operations(self):
        self.imported();app=Application(self.store);body={'workspace':self.wid,'confirm':True}
        other=self.store.create('Keep this workspace')['id']
        with self.assertRaises(PermissionError):app.api('/api/workspace/remove',body,True,'POST')
        job=app.transfers._new_job('synthetic')
        with self.assertRaises(UserError):app.api('/api/workspace/remove',body,False,'POST')
        job['state']='complete'
        app.api('/api/workspace/remove',body,False,'POST')
        self.assertEqual([w['id'] for w in self.store.listing()],[other])
        copies=list((self.store.root/'removed-workspaces').iterdir())
        self.assertEqual(len(copies),1);self.assertTrue((copies[0]/'workspace.sqlite3').is_file())
        with self.assertRaises(UserError):self.store.overview(self.wid)
        with self.assertRaises(UserError):self.store.remove_workspace('../outside')

    def test_explicit_present_with_fog_keeps_map_covered_and_player_variant(self):
        media=self.imported()
        self.assertFalse(self.store.adventure(self.wid,self.aid)['maps'][0]['player_safe'])
        self.store.session_action(self.wid,self.aid,{'action':'present','media':media['id'],'with_fog':True})
        public=self.store.session(self.wid,self.aid,True)
        self.assertEqual(public['active'],media['id'])
        self.assertEqual(public['fog'].get(media['id'],[]),[])
        with self.assertRaises(UserError):
            self.store.session_action(self.wid,self.aid,{'action':'present','media':media['id'],'with_fog':True},True)

    def test_tutorial_is_per_workspace_and_phase_and_survives_restart(self):
        app=Application(self.store)
        body={'workspace':self.wid,'phase':'workspace','action':'get'}
        self.assertFalse(app.api('/api/tutorial',body,False,'POST')['completed'])
        app.api('/api/tutorial',body|{'action':'complete'},False,'POST')
        other=Application(self.store)
        self.assertTrue(other.api('/api/tutorial',body,False,'POST')['completed'])
        self.assertFalse(other.api('/api/tutorial',body|{'phase':'adventure'},False,'POST')['completed'])

    def test_validated_source_is_remembered_without_scanning_or_exporting_machine_paths(self):
        app=Application(self.store)
        app.api('/api/library',{'workspace':self.wid,'path':str(self.lib)},False,'POST')
        other=Application(self.store)
        self.assertEqual(Path(other.source_defaults()['path']),self.lib.resolve())
        self.assertTrue(other.source_defaults()['available'])
        import io,zipfile
        with zipfile.ZipFile(io.BytesIO(self.store.backup(self.wid))) as archive:
            self.assertNotIn(str(self.lib),archive.read('workspace.json').decode())
            self.assertNotIn('ui-settings.json',archive.namelist())
        self.assertFalse(Application(type(self.store)(self.root/'fresh')).source_defaults()['available'])

    def test_player_presence_is_scoped_and_closing_turns_it_off(self):
        app=Application(self.store);scope={'workspace':self.wid,'adventure':self.aid}
        import uuid
        ping=scope|{'client':str(uuid.uuid4())}
        app.api('/api/client/ping',ping,True,'POST')
        self.assertTrue(app.api('/api/player/presence',scope,False,'POST')['online'])
        self.assertFalse(app.api('/api/player/presence',scope|{'adventure':'other'},False,'POST')['online'])
        app.api('/api/client/close',ping,True,'POST')
        self.assertFalse(app.api('/api/player/presence',scope,False,'POST')['online'])

    def test_derived_page_and_caption_metadata_needs_no_reimport(self):
        self.graph['book'][0]['page']=12
        self.imported()
        loaded=self.store.adventure(self.wid,self.aid)
        self.assertEqual(loaded['entries'][0]['page'],12)

    def test_reference_routes_require_dm_and_remain_within_selected_library(self):
        self.imported();(self.lib/'bestiary.html').write_text('Original synthetic creature viewer')
        app=Application(self.store);app.remember_source(__import__('sessiondesk.importer',fromlist=['Library']).Library(self.lib),workspace=self.wid)
        server=make_server(app);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            origin='http://127.0.0.1:'+str(server.server_port)
            route='/reference/'+self.wid+'/'
            with urlopen(origin+route+app.dm_token+'/bestiary.html') as response:
                self.assertIn(b'Original synthetic',response.read())
            with self.assertRaises(HTTPError):urlopen(origin+route+app.player_token+'/bestiary.html')
            with self.assertRaises(HTTPError):urlopen(origin+route+app.dm_token+'/%2e%2e/secret.txt')
        finally:server.shutdown();server.server_close()


    def test_native_updater_waits_for_previous_process(self):
        import os,subprocess,sys
        from sessiondesk.__main__ import wait_for_process
        if os.name != 'nt':
            self.skipTest('Windows restart handshake')
        process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(.15)'],
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            wait_for_process(process.pid,5000)
            self.assertEqual(process.wait(timeout=2),0)
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=2)
        with self.assertRaises(ValueError):wait_for_process(os.getpid())

    def test_failed_restart_leaves_current_app_accepting_work(self):
        from unittest.mock import patch
        app=Application(self.store)
        exe=app.updater.applications/'0.9.0'/'SessionDesk.exe'
        exe.parent.mkdir(parents=True);exe.write_bytes(b'Original fake executable, never run')
        app.pending_update={'executable':str(exe)}
        with patch('sys.frozen',True,create=True),patch('sessiondesk.server.activate_application'),patch('sessiondesk.server.subprocess.Popen',side_effect=OSError('Original launch error')):
            with self.assertRaises(UserError):app.restart_update()
        self.assertTrue(app.transfers.accepting)


    def test_reference_reader_uses_the_explicit_separate_image_library(self):
        from sessiondesk.importer import Library
        images=self.root/'separate images';images.mkdir()
        (images/'example.png').write_bytes(b'Original image bytes for routing only')
        app=Application(self.store);app.remember_source(Library(self.lib),str(images),self.wid)
        file,mime=app.reference_file(self.wid,'img/example.png')
        self.assertEqual(file.resolve(),(images/'example.png').resolve())
