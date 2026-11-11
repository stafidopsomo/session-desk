"""Publication is narrower than a successful development build."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.release_gate import FIRST_PREVIEW, REQUIRED, evaluate, verify_package


def record():
    return {'version': FIRST_PREVIEW, 'preview_ready': True, 'alpha_ready': False,
            'product_digest': 'original-test-digest',
            'checks': {k: {'passed': True, 'evidence': 'Original synthetic evidence'} for k in REQUIRED} | {
                'laptop_compatibility': {'passed': False, 'status': 'deferred', 'evidence': None}},
            'publication': {'channel': 'preview', 'kind': 'prerelease', 'basis': 'owner_request',
                'scope': 'first_windows_preview', 'date': '2026-11-11', 'reason': 'Original test decision',
                'deferred': {'laptop_compatibility': 'Hardware unavailable',
                             'full_visual_geometry': 'Review individual source maps'}}}


class ReleaseGateTests(unittest.TestCase):
    def check(self, r, version=FIRST_PREVIEW, digest='original-test-digest', tag=None):
        return evaluate(r, version, digest, tag or 'product-v' + version)

    def test_first_preview_keeps_laptop_deferred_and_alpha_incomplete(self):
        r=record()
        self.assertEqual(self.check(r), [])
        self.assertFalse(r['alpha_ready'])
        self.assertFalse(r['checks']['laptop_compatibility']['passed'])

    def test_preview_requires_scoped_decision_and_all_other_evidence(self):
        for key in ('preview_ready','publication'):
            r=record();r.pop(key)
            self.assertTrue(self.check(r),key)
        for key,value in (('scope','future_releases'),('kind','stable'),('basis','automatic'),('reason',''),('deferred',None)):
            r=record();r['publication'][key]=value
            self.assertTrue(self.check(r),key)
        for key in REQUIRED-{'laptop_compatibility'}:
            r=record();r['checks'][key]['passed']=False
            self.assertTrue(self.check(r),key)
        r=record();r['checks']['laptop_compatibility']['passed']=True
        self.assertTrue(self.check(r))

    def test_preview_permission_does_not_cover_another_tag_version_or_tree(self):
        r=record()
        self.assertTrue(self.check(r,tag='product-v0.1.0-preview.2'))
        r['version']='0.1.0-preview.2'
        self.assertTrue(self.check(r,version=r['version']))
        self.assertTrue(self.check(record(),digest='changed-tree'))

    def test_alpha_cannot_use_preview_hardware_deferral(self):
        r=record();r.update(version='0.1.0-alpha.1',alpha_ready=True)
        self.assertTrue(self.check(r,version=r['version']))
        r['checks']['laptop_compatibility']={'passed':True,'evidence':'Original synthetic hardware result'}
        self.assertEqual(self.check(r,version=r['version']), [])

    def test_package_requires_clean_matching_provenance_and_every_file_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            archive=Path(temp)/'original-test-package.zip'
            content=b'Original synthetic package entry, not executable code.'
            manifest={'version':FIRST_PREVIEW,'product_digest':'original-test-digest','commit':'a'*40,
                'dirty_source':False,'target':'windows-x64','signing':'unsigned','ai':False,
                'files':[{'path':'SessionDesk.exe','size':len(content),'sha256':hashlib.sha256(content).hexdigest()}]}
            def pack(m, data=content):
                with zipfile.ZipFile(archive,'w') as z:
                    z.writestr('SessionDesk.exe',data);z.writestr('MANIFEST.json',json.dumps(m))
                archive.with_suffix('.zip.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
            pack(manifest)
            verify_package(archive,FIRST_PREVIEW,'original-test-digest','a'*40)
            for key,value in (('dirty_source',True),('commit','b'*40),('ai',True),('product_digest','changed'),('version','0.1.0-preview.2')):
                changed=copy.deepcopy(manifest);changed[key]=value;pack(changed)
                with self.assertRaisesRegex(ValueError,'provenance'):
                    verify_package(archive,FIRST_PREVIEW,'original-test-digest','a'*40)
            pack(manifest,b'Tampered entry')
            with self.assertRaisesRegex(ValueError,'checksum'):
                verify_package(archive,FIRST_PREVIEW,'original-test-digest','a'*40)
            pack(manifest);archive.with_suffix('.zip.sha256').write_text('0'*64+'  '+archive.name)
            with self.assertRaisesRegex(ValueError,'checksum'):
                verify_package(archive,FIRST_PREVIEW,'original-test-digest','a'*40)
