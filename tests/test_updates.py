"""Original synthetic release transport; tests never contact GitHub or execute files."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from unittest.mock import patch
import zipfile

from sessiondesk.importer import UserError
from sessiondesk.updates import LATEST, ORIGIN, Updater, version_key


class Response(io.BytesIO):
    def __init__(self,data,url):
        super().__init__(data);self.url=url;self.headers={'Content-Length':str(len(data))}
    def geturl(self):return self.url


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='sessiondesk-update-original-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()/'app data';self.root.mkdir()
        (self.root/'workspaces').mkdir();(self.root/'workspaces/keep.txt').write_bytes(b'Original workspace save')
        (self.root/'local-sources.json').write_bytes(b'Original selected source setting')
        (self.root/'current.exe').write_bytes(b'Original running app stand-in')
        self.version='0.2.0';self.filename='SessionDesk-'+self.version+'-windows-x64.zip'
        self.url=ORIGIN+'/releases/download/product-v'+self.version+'/'+self.filename
        self.contents={'SessionDesk.exe':b'Original synthetic application, never executed',
                       '_internal/original.txt':b'Original synthetic runtime attachment'}
        self.manifest={'version':self.version,'target':'windows-x64','dirty_source':False,'ai':False,
            'commit':'a'*40,'product_digest':'b'*64,
            'files':[{'path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in self.contents.items()]}
        self.calls=[];self.set_package()
        self.updater=Updater(self.root,'0.1.0-preview.2',frozen=True,opener=self.open)

    def set_package(self,contents=None,manifest=None):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as z:
            for name,body in (contents or self.contents).items():z.writestr(name,body)
            z.writestr('MANIFEST.json',json.dumps(manifest or self.manifest))
        self.archive=data.getvalue();digest=hashlib.sha256(self.archive).hexdigest()
        self.checksum=(digest+'  '+self.filename+'\n').encode()
        self.release={'tag_name':'product-v'+self.version,'draft':False,'prerelease':False,'assets':[
            {'name':self.filename,'browser_download_url':self.url,'size':len(self.archive),'digest':'sha256:'+digest},
            {'name':self.filename+'.sha256','browser_download_url':self.url+'.sha256','size':len(self.checksum)}]}

    def open(self,request,timeout):
        self.calls.append(request.full_url)
        self.assertEqual(timeout,25)
        payload={LATEST:json.dumps(self.release).encode(),self.url:self.archive,self.url+'.sha256':self.checksum}
        if request.full_url not in payload:self.fail('Unexpected synthetic update URL')
        return Response(payload[request.full_url],request.full_url)

    def unchanged(self):
        self.assertEqual((self.root/'workspaces/keep.txt').read_bytes(),b'Original workspace save')
        self.assertEqual((self.root/'local-sources.json').read_bytes(),b'Original selected source setting')
        self.assertEqual((self.root/'current.exe').read_bytes(),b'Original running app stand-in')
        self.assertFalse(list((self.root/'applications').glob('_update-*')))

    def test_numeric_versions_and_stable_release_comparison(self):
        self.assertGreater(version_key('0.10.0'),version_key('0.2.9'))
        self.assertGreater(version_key('0.1.0'),version_key('0.1.0-preview.20'))
        self.assertGreater(version_key('0.1.0-preview.10'),version_key('0.1.0-preview.2'))
        state=self.updater.check();self.assertTrue(state['available']);self.assertTrue(state['supported'])
        self.assertEqual(state['current'],'0.1.0-preview.2');self.assertEqual(state['latest'],'0.2.0')
        current=Updater(self.root,'0.3.0',frozen=True,opener=self.open)
        self.assertFalse(current.check()['available'])

    def test_update_is_side_by_side_and_preserves_current_app_workspaces_and_settings(self):
        candidate=self.updater.check();committed=[]
        result=self.updater.install(candidate,on_commit=lambda:committed.append(True))
        self.assertTrue(result['restart_required']);self.assertEqual(committed,[True])
        self.assertEqual(Path(result['executable']).read_bytes(),self.contents['SessionDesk.exe'])
        self.assertEqual(Path(result['path']),self.root/'applications/0.2.0')
        self.unchanged()
        retry=self.updater.install(candidate)
        self.assertEqual(retry['path'],result['path']);self.unchanged()

    def test_no_regular_release_is_a_normal_result_and_rate_limit_is_actionable(self):
        for status in (404,403):
            def error(request,timeout):raise HTTPError(request.full_url,status,'Original synthetic HTTP error',{},None)
            updater=Updater(self.root,frozen=True,opener=error)
            if status==404:self.assertFalse(updater.check()['available'])
            else:
                with self.assertRaisesRegex(UserError,'limiting'):updater.check()
        self.assertFalse((self.root/'applications').exists())

    def test_source_mode_and_unchecked_or_changed_candidate_cannot_install(self):
        with self.assertRaisesRegex(UserError,'Check for updates'):self.updater.install()
        candidate=self.updater.check();candidate['version']='8.0.0'
        with self.assertRaisesRegex(UserError,'Check for updates'):self.updater.install(candidate)
        source=Updater(self.root,frozen=False,opener=self.open);self.assertFalse(source.check()['supported'])
        with self.assertRaisesRegex(UserError,'Windows EXE'):source.install()
        self.assertFalse((self.root/'applications').exists())

    def test_external_assets_redirects_and_prereleases_are_rejected(self):
        for modification in ('asset','prerelease','redirect'):
            release=copy.deepcopy(self.release)
            if modification=='asset':release['assets'][0]['browser_download_url']='https://outside.invalid/app.zip'
            if modification=='prerelease':release['prerelease']=True
            def fake(request,timeout):
                return Response(json.dumps(release).encode(),'https://outside.invalid/metadata' if modification=='redirect' else LATEST)
            with self.assertRaises(UserError):Updater(self.root,frozen=True,opener=fake).check()
        self.assertFalse((self.root/'applications').exists())

    def test_archive_checksum_file_tamper_and_wrong_version_never_publish(self):
        for case in ('checksum','file','version'):
            self.set_package()
            if case=='file':
                changed={**self.contents,'_internal/original.txt':b'Tampered original entry'}
                self.set_package(contents=changed)
            if case=='version':
                self.set_package(manifest={**self.manifest,'version':'9.0.0'})
            self.updater.check()
            if case=='checksum':self.checksum=('0'*64+'  '+self.filename).encode()
            with self.assertRaises(UserError):self.updater.install()
            self.assertFalse((self.root/'applications/0.2.0').exists());self.unchanged()

    def test_traversal_and_case_collisions_are_rejected_without_external_writes(self):
        for extra in ('../escaped.exe','_internal/../escaped.exe','sessiondesk.exe'):
            contents={**self.contents,extra:b'Original malicious-path fixture'}
            self.set_package(contents=contents);self.updater.check()
            with self.assertRaises(UserError):self.updater.install()
            self.assertFalse((self.root/'applications/0.2.0').exists())
            self.assertFalse((self.root/'escaped.exe').exists());self.unchanged()

    def test_cancel_and_failure_before_commit_leave_existing_data_and_no_new_version(self):
        self.updater.check();stop=threading.Event()
        def progress(*args):stop.set()
        with self.assertRaisesRegex(UserError,'cancelled'):
            self.updater.install(cancelled=stop.is_set,progress=progress)
        self.unchanged();self.assertFalse((self.root/'applications/0.2.0').exists())
        def failed_commit():raise UserError('Original synthetic commit cancellation')
        with self.assertRaisesRegex(UserError,'commit cancellation'):self.updater.install(on_commit=failed_commit)
        self.unchanged();self.assertFalse((self.root/'applications/0.2.0').exists())

    def test_cleanup_lock_does_not_report_published_update_as_failed(self):
        candidate=self.updater.check()
        with patch('sessiondesk.updates.remove_staging',side_effect=PermissionError('Original Windows cleanup lock')):
            result=self.updater.install(candidate)
        self.assertTrue(Path(result['executable']).is_file())
        self.assertTrue(list((self.root/'applications').glob('_update-*')))
        self.updater.recover();self.unchanged()


    def test_restart_response_lost_after_commit_can_resume_verified_existing_install(self):
        self.updater.check();first=self.updater.install()
        restarted=Updater(self.root,'0.1.0-preview.2',frozen=True,opener=self.open)
        restarted.check();before=len(self.calls)
        resumed=restarted.install()
        self.assertEqual(resumed,first)
        self.assertGreater(len(self.calls),before,'Existing files must be compared to a fresh download')
        self.unchanged()

    def test_changed_existing_install_is_never_overwritten_or_reused(self):
        self.updater.check();first=self.updater.install()
        executable=Path(first['executable']);executable.write_bytes(b'Original user modification')
        with self.assertRaisesRegex(UserError,'differs'):self.updater.install()
        self.assertEqual(executable.read_bytes(),b'Original user modification')
        self.unchanged()


class LaunchPointerTests(unittest.TestCase):
    def test_verified_update_is_used_only_by_older_launchers_and_tampering_falls_back(self):
        from sessiondesk.updates import activate_application,preferred_application
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'applications'/'0.2.0';folder.mkdir(parents=True)
            exe=folder/'SessionDesk.exe';data=b'Original synthetic executable, not run';exe.write_bytes(data)
            manifest={'version':'0.2.0','target':'windows-x64','dirty_source':False,
                'files':[{'path':'SessionDesk.exe','size':len(data),'sha256':hashlib.sha256(data).hexdigest()}]}
            (folder/'MANIFEST.json').write_text(json.dumps(manifest),encoding='utf-8')
            activate_application(root,exe)
            self.assertEqual(preferred_application(root,'0.1.1'),exe)
            self.assertIsNone(preferred_application(root,'0.2.0'))
            self.assertIsNone(preferred_application(root,'0.3.0'))
            exe.write_bytes(b'Changed file')
            self.assertIsNone(preferred_application(root,'0.1.1'))

    def test_launch_pointer_cannot_escape_application_folder(self):
        from sessiondesk.updates import activate_application,preferred_application
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);exe=root/'outside.exe';exe.write_bytes(b'Original synthetic file')
            with self.assertRaises(UserError):activate_application(root,exe)
            (root/'active-application.json').write_text(json.dumps({'version':'9.0.0','executable':str(exe),'manifest_sha256':'0'*64}))
            self.assertIsNone(preferred_application(root,'0.1.1'))
