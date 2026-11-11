import copy
import hashlib
import io
import json
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

from sessiondesk.importer import Library, UserError
from sessiondesk.server import Application, make_server
from sessiondesk.store import Store
from sessiondesk.transfers import staging
from tests.test_core import WorkspaceCase


class TransferStorageTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.media = self.imported()

    def test_cancelled_export_preserves_old_backup_and_removes_partial(self):
        target = self.root / 'previous.zip'
        target.write_bytes(b'Previous backup file')
        stop = threading.Event()
        with self.assertRaisesRegex(UserError, 'cancelled'):
            self.store.backup_file(self.wid, target, stop.is_set, lambda *_: stop.set())
        self.assertEqual(target.read_bytes(), b'Previous backup file')
        self.assertFalse(target.with_name(target.name + '.partial').exists())

    def test_cancelled_restore_is_never_listed_or_published(self):
        stop = threading.Event()
        def progress(*_):
            self.assertEqual(len(self.store.listing()), 1)
            stop.set()
        with self.assertRaisesRegex(UserError, 'cancelled'):
            self.store.restore_file(io.BytesIO(self.store.backup(self.wid)), stop.is_set, progress)
        self.assertEqual(len(self.store.listing()), 1)
        self.assertFalse(list(self.store.workspaces.glob('_restore-*')))

    def test_disk_failure_before_publish_leaves_no_partial_workspace(self):
        backup = self.store.backup(self.wid)
        for method in ('initialize', 'rename'):
            scope = patch.object(self.store, '_initialize', side_effect=OSError('Synthetic disk full')) if method == 'initialize' else patch.object(Path, 'replace', side_effect=OSError('Synthetic publish failure'))
            with scope, self.assertRaises(UserError):
                self.store.restore(backup)
            self.assertEqual(len(self.store.listing()), 1)
            self.assertFalse(list(self.store.workspaces.glob('_restore-*')))

    def test_create_failure_does_not_expose_an_empty_workspace(self):
        with patch.object(self.store, '_initialize', side_effect=OSError('Synthetic disk full')):
            with self.assertRaises(OSError):
                self.store.create('Must not appear')
        self.assertEqual(len(self.store.listing()), 1)
        self.assertFalse(list(self.store.workspaces.glob('_restore-*')))

    def test_same_snapshot_repairs_missing_and_corrupt_assets_without_resetting_prep(self):
        eid = self.graph['entries'][1]['id']
        self.store.prepare(self.wid, self.aid, eid, {'notes': 'Keep this preparation'})
        self.store.pin(self.wid, self.aid, 'entry', eid, True)
        self.store.session_action(self.wid, self.aid, {'action': 'note', 'media': self.media['id'], 'text': 'Keep shared notes'})
        state = self.store.session(self.wid, self.aid)
        target, _ = self.store.asset(self.wid, self.media['asset'])
        for corrupt in (False, True):
            if corrupt:
                target.write_bytes(b'Synthetic damage')
            else:
                target.unlink()
            result = self.store.import_graph(self.wid, copy.deepcopy(self.graph), self.blobs)
            self.assertTrue(result['unchanged'])
            self.assertEqual(result['repaired_assets'], 1)
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), self.media['asset'])
            self.assertEqual(self.store.session(self.wid, self.aid), state)
            saved = self.store.adventure(self.wid, self.aid)
            self.assertEqual(saved['preparation'][eid]['notes'], 'Keep this preparation')
            self.assertEqual(len(saved['pins']), 1)

    def test_backup_detects_corruption_and_never_replaces_a_good_target(self):
        target, _ = self.store.asset(self.wid, self.media['asset'])
        target.write_bytes(b'Synthetic damage')
        backup = self.root / 'good.zip'
        backup.write_bytes(b'Previous valid file')
        with self.assertRaisesRegex(UserError, 'damaged'):
            self.store.backup_file(self.wid, backup)
        self.assertEqual(backup.read_bytes(), b'Previous valid file')

    def test_oversized_metadata_is_rejected_before_replacing_backup(self):
        target = self.root / 'keep.zip'
        target.write_bytes(b'Existing backup')
        with patch('sessiondesk.store.MAX_METADATA', 1):
            with self.assertRaisesRegex(UserError, 'metadata'):
                self.store.backup_file(self.wid, target)
        self.assertEqual(target.read_bytes(), b'Existing backup')

    def test_backup_snapshot_does_not_block_session_edits(self):
        mid = self.media['id']
        self.store.session_action(self.wid, self.aid, {'action': 'note', 'media': mid, 'text': 'Before snapshot'})
        updated = []
        def progress(*_):
            if updated:
                return
            updated.append(True)
            thread = threading.Thread(target=lambda: self.store.session_action(self.wid, self.aid,
                {'action': 'note', 'media': mid, 'text': 'After snapshot'}))
            thread.start()
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive(), 'Backup held the live session write lock')
        path = self.root / 'snapshot.zip'
        self.store.backup_file(self.wid, path, progress=progress)
        restored = self.store.restore_file(path)['id']
        self.assertEqual(self.store.session(restored, self.aid)['notes'][mid], 'Before snapshot')
        self.assertEqual(self.store.session(self.wid, self.aid)['notes'][mid], 'After snapshot')

    def test_restore_rejects_image_geometry_mismatch(self):
        original = self.store.backup(self.wid)
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(output, 'w') as target:
            for name in source.namelist():
                data = source.read(name)
                if name == 'workspace.json':
                    metadata = json.loads(data)
                    metadata['documents']['adventure:' + self.aid]['maps'][0]['width'] = 899
                    data = json.dumps(metadata).encode()
                target.writestr(name, data)
        with self.assertRaisesRegex(UserError, 'dimensions'):
            self.store.restore(output.getvalue())
        self.assertEqual(len(self.store.listing()), 1)

    def test_restart_recovery_only_removes_marked_private_staging(self):
        interrupted = staging(self.store.workspaces, '_restore-')
        (interrupted / 'partial').write_bytes(b'Synthetic partial data')
        unknown = self.store.workspaces / '_restore-unmarked'
        unknown.mkdir()
        (unknown / 'keep.txt').write_text('User data must remain', encoding='utf-8')
        self.assertEqual(self.store.recover_interrupted_restores(), 1)
        self.assertFalse(interrupted.exists())
        self.assertTrue((unknown / 'keep.txt').exists())
        self.assertEqual(len(self.store.listing()), 1)

    def test_supported_schema_variants_are_recorded_and_mismatched_source_is_refused(self):
        path = self.lib / 'data/adventure/adventure-demo.json'
        original = json.loads(path.read_text(encoding='utf-8'))
        variants = [(original, 'data-list'),
            ({'adventureData': {'id': 'DEMO', 'data': original['data']}}, 'adventureData-object'),
            ({'adventureData': [{'id': 'DEMO', 'data': original['data']}]}, 'adventureData-list')]
        for payload, expected in variants:
            path.write_text(json.dumps(payload), encoding='utf-8')
            graph, _ = Library(self.lib).load('DEMO')
            self.assertEqual(graph['source_schema'], expected)
        path.write_text(json.dumps({'adventureData': {'id': 'WRONG', 'data': original['data']}}), encoding='utf-8')
        with self.assertRaisesRegex(UserError, 'does not match'):
            Library(self.lib).load('DEMO')
        path.write_text(json.dumps({'data': ['not a chapter object']}), encoding='utf-8')
        with self.assertRaisesRegex(UserError, 'data chapters'):
            Library(self.lib).load('DEMO')

    def test_index_without_data_is_not_reported_as_a_valid_library(self):
        (self.lib / 'data/adventure/adventure-demo.json').unlink()
        with self.assertRaisesRegex(UserError, 'data files are missing'):
            Library(self.lib).validate()

    def test_backup_survives_source_removal_and_imports_into_another_root(self):
        source = self.lib / 'img/original/map.png'
        source.unlink()
        backup = self.root / 'portable.zip'
        self.store.backup_file(self.wid, backup)
        second = Store(self.root / 'different install and profile')
        restored = second.restore_file(backup)['id']
        path, _ = second.asset(restored, self.media['asset'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), self.media['asset'])


class TransferHttpTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.imported()
        self.app = Application(self.store)
        self.server = make_server(self.app)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.origin = f'http://127.0.0.1:{self.server.server_port}'
        self.addCleanup(self.app.close)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def call(self, route, payload=None, player=False):
        request = Request(self.origin + '/api/' + route,
            json.dumps({'workspace': self.wid, **(payload or {})}).encode(),
            {'Content-Type': 'application/json', 'Authorization': 'Bearer ' +
             (self.app.player_token if player else self.app.dm_token), 'Origin': self.origin})
        with urlopen(request, timeout=10) as response:
            return json.load(response)

    def wait(self, jid):
        for _ in range(500):
            result = self.call('job/status', {'job': jid})
            if result['state'] not in ('uploading', 'running', 'committing'):
                return result
            time.sleep(.01)
        self.fail('Transfer did not reach a terminal state')

    def upload(self, jid, data):
        request = Request(self.origin + '/api/backup/upload/' + jid, data,
            {'Content-Type': 'application/zip', 'Authorization': 'Bearer ' + self.app.dm_token, 'Origin': self.origin})
        with urlopen(request, timeout=10) as response:
            return json.load(response)

    def test_background_export_download_and_restore_round_trip(self):
        eid = self.graph['entries'][1]['id']
        self.store.prepare(self.wid, self.aid, eid, {'notes': 'Synthetic private note'})
        job = self.call('backup/export/start')
        result = self.wait(job['id'])
        self.assertEqual(result['state'], 'complete')
        self.assertNotIn(str(self.root), json.dumps(result))
        for token, expected in ((self.app.player_token, 403), ('wrong', 401)):
            with self.assertRaises(HTTPError) as caught:
                urlopen(self.origin + '/download/' + job['id'] + '?token=' + token)
            self.assertEqual(caught.exception.code, expected)
        with urlopen(self.origin + '/download/' + job['id'] + '?token=' + self.app.dm_token) as response:
            backup = response.read()
            self.assertIn('attachment', response.headers['Content-Disposition'])
        restore = self.call('backup/restore/start', {'size': len(backup)})
        self.upload(restore['id'], backup)
        completed = self.wait(restore['id'])
        self.assertEqual(completed['state'], 'complete')
        restored = completed['result']['id']
        self.assertNotEqual(restored, self.wid)
        self.assertEqual(self.store.adventure(restored, self.aid)['preparation'][eid]['notes'], 'Synthetic private note')

    def test_cancelled_upload_frees_slot_and_keeps_workspaces(self):
        job = self.call('backup/restore/start', {'size': 100})
        self.assertEqual(self.call('job/cancel', {'job': job['id']})['state'], 'cancelled')
        with self.assertRaises(HTTPError):
            self.upload(job['id'], b'not uploaded')
        self.assertEqual(len(self.store.listing()), 1)
        self.assertFalse(list(self.app.transfers.transfer_root.glob('_transfer-*')))
        self.assertEqual(self.wait(self.call('backup/export/start')['id'])['state'], 'complete')

    def test_short_upload_fails_cleanly_and_retry_can_complete(self):
        data = self.store.backup(self.wid)
        job = self.call('backup/restore/start', {'size': len(data)})
        with self.assertRaises(UserError):
            self.app.transfers.receive_restore(job['id'], io.BytesIO(data[:10]), len(data))
        self.assertEqual(self.call('job/status', {'job': job['id']})['state'], 'failed')
        self.assertEqual(len(self.store.listing()), 1)
        retry = self.call('backup/restore/start', {'size': len(data)})
        self.upload(retry['id'], data)
        self.assertEqual(self.wait(retry['id'])['state'], 'complete')

    def test_restore_worker_cancellation_acknowledges_and_cleans_upload(self):
        data = self.store.backup(self.wid)
        def blocked(source, cancelled, *_):
            for _ in range(200):
                if cancelled():
                    raise UserError('Cancelled synthetic restore')
                time.sleep(.01)
            raise AssertionError('Cancellation was not delivered')
        with patch.object(self.store, 'restore_file', blocked):
            job = self.call('backup/restore/start', {'size': len(data)})
            self.upload(job['id'], data)
            self.call('job/cancel', {'job': job['id']})
            self.assertEqual(self.wait(job['id'])['state'], 'cancelled')
        self.assertFalse(list(self.app.transfers.transfer_root.glob('_transfer-*')))
        self.assertEqual(len(self.store.listing()), 1)

    def test_transfers_are_dm_only_and_pending_upload_prevents_quit(self):
        for path in ('backup/export/start', 'backup/restore/start', 'job/status'):
            with self.assertRaises(HTTPError) as caught:
                self.call(path, {'size': 20}, player=True)
            self.assertEqual(caught.exception.code, 403)
        job = self.call('backup/restore/start', {'size': 20})
        with self.assertRaises(HTTPError):
            self.call('quit')
        self.call('job/cancel', {'job': job['id']})


if __name__ == '__main__':
    unittest.main()
