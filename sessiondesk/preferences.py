"""Small machine-local UI/source preferences; excluded from workspace exports."""
import json
from pathlib import Path
import threading
from .importer import UserError

class Preferences:
    def __init__(self, root):
        self.file = Path(root) / 'ui-settings.json'
        self.lock = threading.RLock()

    def read(self):
        if self.file.is_symlink():
            raise UserError('UI preferences cannot be linked.')
        if not self.file.is_file():
            return {}
        if self.file.stat().st_size > 256 * 1024:
            raise UserError('UI preferences exceed the supported size.')
        try:
            value = json.loads(self.file.read_text(encoding='utf-8'))
            return value if isinstance(value, dict) else {}
        except (ValueError, OSError):
            return {}

    def update(self, key, value):
        with self.lock:
            content = self.read()
            content[key] = value
            temp = self.file.with_suffix('.tmp')
            if temp.is_symlink():
                raise UserError('UI preferences cannot be linked.')
            text = json.dumps(content, ensure_ascii=False)
            if len(text.encode()) > 256 * 1024:
                raise UserError('UI preferences exceed the supported size.')
            temp.write_text(text, encoding='utf-8')
            temp.replace(self.file)

    def tutorial(self, workspace, phase, adventure, action):
        if phase not in ('workspace','adventure') or action not in ('get','complete'):
            raise UserError('Unknown tutorial action.')
        key = ':'.join((workspace, phase, adventure or ''))
        with self.lock:
            tours = self.read().get('tutorials', {})
            if action == 'complete':
                tours[key] = True
                self.update('tutorials', tours)
            return {'completed': tours.get(key) is True}
