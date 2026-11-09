import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid
import zipfile

from sessiondesk.importer import Library, UserError
from sessiondesk.library_setup import LibrarySetup, RELEASE, download, extract_source
from sessiondesk.server import Application
from sessiondesk.store import Store
from tests.fixtures import make_library


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='sessiondesk-setup-test-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.library=make_library(self.root/'original',wrapped=True)
        self.store=Store(self.root/'profile')
        self.setup=LibrarySetup(self.store.root)

    def archive(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as archive:
            for file in self.library.rglob('*'):
                if file.is_file():archive.write(file,'synthetic-root/'+file.relative_to(self.library).as_posix())
        return out.getvalue()

    def test_real_2014_list_wrapper_and_unsupported_wrapper(self):
        graph,_=Library(self.library).load('DEMO')
        self.assertEqual(len(graph['maps']),4)
        path=self.library/'data/adventure/adventure-demo.json'
        source=json.loads(path.read_text(encoding='utf-8'))
        source['adventureData'].append({'id':'OTHER','data':[]})
        path.write_text(json.dumps(source),encoding='utf-8')
        self.assertEqual(len(Library(self.library).load('DEMO')[0]['maps']),4)
        source['adventureData'][0]['id']='MISSING'
        path.write_text(json.dumps(source),encoding='utf-8')
        with self.assertRaisesRegex(UserError,'matching source ID'):Library(self.library).load('DEMO')

    def test_validation_reports_found_library_and_image_status(self):
        result=self.setup.validate(self.library)
        self.assertTrue(result['valid'])
        self.assertEqual(result['available'],1)
        self.assertTrue(result['images_found'])
        self.assertFalse(result['download_images'])

    def test_import_size_limit_stops_instead_of_retaining_oversized_blobs(self):
        with patch('sessiondesk.importer.MAX_TOTAL',1):
            with self.assertRaisesRegex(UserError,'exceed'):Library(self.library).load('DEMO')

    def install(self,destination,images=False,cancelled=lambda:False,bad_hash=False):
        data=self.archive()
        release={**RELEASE,'sha256':'bad' if bad_hash else hashlib.sha256(data).hexdigest()}
        def fetch(url,target,*args):
            target.write_bytes(data)
            return hashlib.sha256(data).hexdigest()
        return self.setup.install(str(destination),images,cancelled,lambda *_:None,fetch,release)

    def test_install_is_atomic_validated_and_records_image_opt_in(self):
        target=self.root/'new library'
        result=self.install(target,True)
        self.assertTrue(result['valid'])
        self.assertTrue(result['download_images'])
        self.assertIsNotNone(self.setup.fetcher(Library(target)))
        self.assertIsNone(self.setup.fetcher(Library(self.library)))
        self.assertFalse(list(self.root.glob('.sessiondesk-install-*')))
        with self.assertRaisesRegex(UserError,'never overwritten'):self.install(target)

    def test_failed_or_cancelled_install_cleans_staging_and_preserves_destination(self):
        for kind in ('checksum','cancelled'):
            target=self.root/kind
            target.mkdir()
            with self.assertRaises(UserError):self.install(target,cancelled=lambda:kind=='cancelled',bad_hash=kind=='checksum')
            self.assertEqual(list(target.iterdir()),[])
            self.assertFalse(list(self.root.glob('.sessiondesk-install-*')))

    def test_zip_slip_and_links_are_rejected(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as archive:
            archive.writestr('data/adventures.json','{"adventure":[]}')
            archive.writestr('../escape.txt','not allowed')
        with self.assertRaises(UserError):extract_source(io.BytesIO(out.getvalue()),self.root/'extract',lambda:False)
        self.assertFalse((self.root/'escape.txt').exists())

    def test_download_rejects_untrusted_sources_without_opening_network(self):
        def never(*args,**kwargs):self.fail('Unexpected network access')
        with self.assertRaises(UserError):download('http://example.invalid/file',self.root/'out',100,lambda:False,lambda *_:None,never)

    def test_failed_job_is_terminal_and_next_job_can_run(self):
        app=Application(self.store)
        wid=self.store.create('Synthetic failure test')['id']
        path=self.library/'data/adventure/adventure-demo.json'
        original=path.read_bytes()
        path.write_text('{"adventureData": []}',encoding='utf-8')
        first=app.start_import({'workspace':wid,'path':str(self.library),'source':'DEMO'})
        for _ in range(100):
            if app.jobs[first['id']]['state']=='failed':break
            time.sleep(.01)
        self.assertEqual(app.jobs[first['id']]['state'],'failed')
        self.assertEqual(self.store.overview(wid)['adventures'],[])
        path.write_bytes(original)
        second=app.start_import({'workspace':wid,'path':str(self.library),'source':'DEMO'})
        for _ in range(100):
            if app.jobs[second['id']]['state']=='complete':break
            time.sleep(.01)
        self.assertEqual(app.jobs[second['id']]['state'],'complete')

    def test_window_lifetime_keeps_players_and_reload_alive_then_exits(self):
        app=Application(self.store)
        dm,player=str(uuid.uuid4()),str(uuid.uuid4())
        app.clients={dm:{'seen':0,'closed':True},player:{'seen':5,'closed':False}}
        self.assertFalse(app.should_exit(10))
        app.clients[player]['closed']=True
        self.assertFalse(app.should_exit(11))
        app.clients['reload']={'seen':12,'closed':False}
        self.assertFalse(app.should_exit(18))
        app.clients['reload']['closed']=True
        self.assertFalse(app.should_exit(19))
        self.assertTrue(app.should_exit(28))

    def test_last_window_close_cancels_worker_and_waits_for_atomic_commit(self):
        app=Application(self.store)
        app.clients={'closed':{'seen':1,'closed':True}}
        event=threading.Event()
        app.jobs={'job':{'state':'running','cancel':event}}
        self.assertFalse(app.should_exit(1))
        self.assertFalse(app.should_exit(10))
        self.assertTrue(event.is_set())
        app.jobs['job']['state']='committing'
        self.assertFalse(app.should_exit(11))
        app.jobs['job']['state']='complete'
        self.assertTrue(app.should_exit(12))

    def test_cancelled_job_acknowledges_stop_and_releases_operation_slot(self):
        app=Application(self.store)
        def work(event,job,progress):
            if not event.wait(2):raise AssertionError('Cancellation was not delivered')
            raise UserError('Cancelled synthetic operation')
        first=app.start_job('install',work)
        response=app.api('/api/import/cancel',{'job':first['id']},False,'POST')
        self.assertTrue(response['cancel_requested'])
        for _ in range(100):
            if app.jobs[first['id']]['state']=='cancelled':break
            time.sleep(.01)
        self.assertEqual(app.jobs[first['id']]['state'],'cancelled')
        second=app.start_job('install',lambda *args:{'synthetic':True})
        for _ in range(100):
            if app.jobs[second['id']]['state']=='complete':break
            time.sleep(.01)
        self.assertEqual(app.jobs[second['id']]['state'],'complete')


if __name__=='__main__':unittest.main()
