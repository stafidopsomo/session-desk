"""Published source copies survive preference/cleanup failures without hidden downloads."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from sessiondesk.importer import Library
from sessiondesk.library_setup import IMAGES_DISABLED, LibrarySetup, RELEASE
from tests.fixtures import make_library


class InstallRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sessiondesk-install-recovery-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = make_library(self.root / 'original')
        self.profile = self.root / 'profile'
        self.profile.mkdir()
        self.setup = LibrarySetup(self.profile)
        self.destination = self.root / 'new library'
        self.original_files = {p.relative_to(source).as_posix(): p.read_bytes()
                               for p in source.rglob('*') if p.is_file()}
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            for name, body in self.original_files.items():
                archive.writestr(name, body)
        self.archive = data.getvalue()
        self.release = {**RELEASE, 'sha256': hashlib.sha256(self.archive).hexdigest()}

    def install(self):
        def fetch(url, target, *args):
            target.write_bytes(self.archive)
            return self.release['sha256']
        return self.setup.install(str(self.destination), True, lambda: False,
                                  lambda *_: None, fetch, self.release)

    def verify_installed_and_disabled(self, result):
        self.assertTrue(result['valid'])
        self.assertTrue(result['warnings'])
        self.assertFalse(result['download_images'])
        for name, body in self.original_files.items():
            self.assertEqual((self.destination / name).read_bytes(), body)
        self.assertTrue((self.destination / IMAGES_DISABLED).exists())
        restarted = LibrarySetup(self.profile)
        self.assertFalse(restarted.validate(self.destination)['download_images'])
        self.assertIsNone(restarted.fetcher(Library(self.destination)))

    def test_preference_write_failure_preserves_installed_copy_and_blocks_stale_consent(self):
        old_config = {str(self.destination.resolve()): {'images': True}, 'original-unrelated-copy': {'images': True}}
        self.setup.settings.write_text(json.dumps(old_config), encoding='utf-8')
        write = Path.write_text
        def fail_preferences(path, *args, **kwargs):
            if path == self.setup.settings.with_suffix('.tmp'):
                raise OSError('Synthetic app data disk full')
            return write(path, *args, **kwargs)
        with patch.object(Path, 'write_text', fail_preferences):
            result = self.install()
        self.verify_installed_and_disabled(result)
        self.assertEqual(self.setup.config(), old_config)

    def test_preference_publish_failure_preserves_copy_without_enabling_downloads(self):
        replace = Path.replace
        def fail_preferences(path, target):
            if path == self.setup.settings.with_suffix('.tmp'):
                raise OSError('Synthetic registry file lock')
            return replace(path, target)
        with patch.object(Path, 'replace', fail_preferences):
            result = self.install()
        self.verify_installed_and_disabled(result)
        self.assertFalse(self.setup.settings.with_suffix('.tmp').exists())

    def test_download_activation_failure_keeps_installed_copy_safely_off(self):
        unlink = Path.unlink
        def fail_activation(path, *args, **kwargs):
            if path == self.destination / IMAGES_DISABLED:
                raise OSError('Synthetic image setting file lock')
            return unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', fail_activation):
            result = self.install()
        self.verify_installed_and_disabled(result)
        self.assertTrue(self.setup.config()[str(self.destination.resolve())]['images'])

    def test_temporary_cleanup_failure_does_not_misreport_installed_copy_as_failed(self):
        with patch('sessiondesk.library_setup.shutil.rmtree', side_effect=OSError('Synthetic temporary file lock')):
            result = self.install()
        self.assertTrue(result['valid'])
        self.assertTrue(result['warnings'])
        self.assertTrue(result['download_images'])
        self.assertTrue((self.destination / 'data/adventures.json').is_file())
