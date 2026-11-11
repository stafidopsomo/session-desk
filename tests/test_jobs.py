"""Operation results survive temporary Windows cleanup locks."""
import tempfile
import threading
import time
from pathlib import Path
import unittest
from unittest.mock import patch

from sessiondesk.importer import UserError
from sessiondesk.jobs import TransferJobs
from sessiondesk.store import Store
from sessiondesk.transfers import recover_staging, staging


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name));self.manager=TransferJobs(self.store)
        self.addCleanup(self.manager.close)

    def terminal(self, jid):
        limit=time.monotonic()+3
        while time.monotonic()<limit:
            state=self.manager.status(jid)
            if state['state'] not in ('running','uploading','committing'):
                return state
            time.sleep(.01)
        self.fail('Operation did not reach a terminal state')

    def run_locked_cleanup(self, operation):
        attempted=threading.Event()
        def locked(*_):
            attempted.set();raise PermissionError('Original synthetic Windows lock')
        with patch('sessiondesk.jobs.remove_staging',side_effect=locked):
            started=self.manager.start_job('restore',operation)
            self.assertTrue(attempted.wait(3))
            state=self.terminal(started['id'])
            self.assertTrue(self.manager.jobs[started['id']]['cleanup_pending'])
        return state,started['id']

    def test_failed_operation_cleanup_lock_does_not_block_next_job(self):
        def fail(event,job,progress):
            job['folder']=staging(self.manager.transfer_root,'_transfer-')
            raise UserError('Original source failure')
        result,jid=self.run_locked_cleanup(fail)
        self.assertEqual(result['state'],'failed')
        self.assertEqual(result['error'],'Original source failure')
        second=self.manager.start_job('import',lambda *_:{'ok':True})
        self.assertEqual(self.terminal(second['id'])['state'],'complete')
        self.manager.discard(jid)
        self.assertNotIn('folder',self.manager.jobs[jid])

    def test_committed_restore_stays_complete_when_cleanup_is_locked(self):
        def commit(event,job,progress):
            job['folder']=staging(self.manager.transfer_root,'_transfer-')
            result=self.store.create('Original committed workspace')
            self.manager.commit(event,job)
            return result
        state,jid=self.run_locked_cleanup(commit)
        self.assertEqual(state['state'],'complete')
        self.assertEqual(self.store.listing()[0]['id'],state['result']['id'])
        self.manager.close()
        self.assertFalse(list(self.manager.transfer_root.glob('_transfer-*')))

    def test_quit_refuses_active_work_and_prevents_new_jobs_after_acceptance(self):
        pending=self.manager.prepare_restore(30)
        with self.assertRaises(UserError):self.manager.request_close()
        self.manager.status(pending['id'],cancel=True)
        self.manager.request_close()
        with self.assertRaisesRegex(UserError,'closing'):
            self.manager.start_job('import',lambda *_:{})

    def test_startup_recovery_skips_locked_marked_folder_and_retries_later(self):
        folder=staging(self.manager.transfer_root,'_transfer-')
        with patch('sessiondesk.transfers.remove_staging',side_effect=PermissionError('Original lock')):
            self.assertEqual(recover_staging(self.manager.transfer_root,'_transfer-'),0)
        self.assertTrue(folder.is_dir())
        self.assertEqual(recover_staging(self.manager.transfer_root,'_transfer-'),1)

