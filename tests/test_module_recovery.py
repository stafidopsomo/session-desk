"""Backup snapshots stay portable during edits, copy failures and cancellation."""
import copy
import hashlib
import json
import shutil
import threading
from unittest.mock import patch
import zipfile

from sessiondesk.importer import UserError
from sessiondesk import workspace_modules as modules
from tests.test_prepared import PreparedCase


class ModuleRecoveryTests(PreparedCase):
    def test_failed_materialization_publishes_nothing_and_retry_has_all_files(self):
        self.imported();manifest=self.module()
        root=self.store.folder(self.wid)/'module-files'/modules.MODULE_ID
        # Remove this synthetic editable copy only; the hashed source is intact.
        self.assertTrue(root.resolve().is_relative_to(self.root.resolve()))
        shutil.rmtree(root)
        original=shutil.copyfile;count=0
        def fail_second(*args,**kwargs):
            nonlocal count
            count+=1
            if count==2:raise OSError('Original synthetic full disk')
            return original(*args,**kwargs)
        with patch('sessiondesk.workspace_modules.shutil.copyfile',side_effect=fail_second):
            with self.assertRaises(OSError):modules.materialize(self.store.folder(self.wid),modules.MODULE_ID,manifest)
        self.assertFalse(root.exists())
        self.assertFalse(list(root.parent.glob('_materialize-*')))
        result=modules.materialize(self.store.folder(self.wid),modules.MODULE_ID,manifest)
        self.assertEqual({p.relative_to(result).as_posix() for p in result.rglob('*') if p.is_file()},set(manifest['files']))
        leftover=modules.staging(result.parent,'_materialize-')
        modules.materialize(self.store.folder(self.wid),modules.MODULE_ID,manifest)
        self.assertFalse(leftover.exists())

    def test_cancellation_during_module_snapshot_stops_immediately_and_rolls_back(self):
        self.imported();before=copy.deepcopy(self.module());stop=threading.Event()
        original=modules.capture_file;calls=[]
        def cancel(*args,**kwargs):
            calls.append(args[1]);stop.set();return original(*args,**kwargs)
        with patch('sessiondesk.workspace_modules.capture_file',side_effect=cancel):
            with self.assertRaisesRegex(UserError,'cancelled'):
                self.store.backup_file(self.wid,self.root/'cancelled.zip',stop.is_set)
        self.assertEqual(len(calls),1)
        self.assertEqual(self.module(),before)
        self.assertFalse((self.root/'cancelled.zip').exists())

    def test_repeated_edits_export_only_current_references_without_deleting_old_assets(self):
        self.imported();root=self.store.folder(self.wid)/'module-files'/modules.MODULE_ID
        old=[]
        for i in range(4):
            payload=('Original revised authoring note '+str(i)).encode()
            (root/'prep/same.txt').write_bytes(payload)
            old.append(hashlib.sha256(payload).hexdigest())
            self.store.backup_file(self.wid,self.root/'portable.zip')
        with zipfile.ZipFile(self.root/'portable.zip') as archive:
            data=json.loads(archive.read('workspace.json'))
            self.assertIn(old[-1],data['assets'])
            for digest in old[:-1]:self.assertNotIn(digest,data['assets'])
            original=self.module()['original']['asset'];self.assertIn(original,data['assets'])
        # Existing concurrent snapshots can still read old immutable objects.
        for digest in old:self.assertTrue((self.store.folder(self.wid)/'assets'/digest).is_file())
        restored=self.store.restore_file(self.root/'portable.zip')
        final=self.store.folder(restored['id'])/'module-files'/modules.MODULE_ID/'prep/same.txt'
        self.assertEqual(final.read_bytes(),payload)

    def test_unknown_module_keeps_unrecognized_attachment_references_conservatively(self):
        documents={'module:future':{'kind':'future','schema':7,'enabled':True,'files':{}}}
        assets={'original-future-hash':{'mime':'application/octet-stream','size':5}}
        self.assertEqual(modules.backup_assets(documents,assets),assets)
