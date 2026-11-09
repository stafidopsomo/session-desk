"""Private, bounded staging folders for user-requested backup transfers."""
import shutil
from pathlib import Path
import uuid

from .importer import MAX_TOTAL, UserError

CHUNK = 64 * 1024
MAX_METADATA = 64 * 1024 * 1024
MAX_BACKUP = MAX_TOTAL + MAX_METADATA
MARKER = '.sessiondesk-staging'
MARKER_TEXT = 'SessionDesk private staging v1'
ACTIVE = ('uploading', 'running', 'committing')


def check_cancel(cancelled):
    if cancelled():
        raise UserError('Operation cancelled; saved workspaces were not changed.')


def staging(parent, prefix):
    if Path(parent).is_symlink():
        raise UserError('Staging root cannot be a symlink.')
    parent = Path(parent).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    folder = parent / (prefix + str(uuid.uuid4()))
    folder.mkdir()
    (folder / MARKER).write_text(MARKER_TEXT, encoding='utf-8')
    return folder


def remove_staging(parent, folder, prefix):
    """Only marked directories created by this app, strictly inside the named root."""
    parent, folder = Path(parent).resolve(), Path(folder)
    if not folder.exists():
        return
    if (folder.is_symlink() or folder.resolve().parent != parent or not folder.name.startswith(prefix)
            or not (folder / MARKER).is_file() or (folder / MARKER).is_symlink()
            or (folder / MARKER).read_text(encoding='utf-8') != MARKER_TEXT):
        raise UserError('Unrecognized staging directory; it was not removed.')
    # The resolved absolute target has been checked before recursive removal.
    shutil.rmtree(folder)


def recover_staging(parent, prefix):
    parent = Path(parent)
    if parent.is_symlink():
        raise UserError('Staging root cannot be a symlink.')
    if not parent.exists():
        return 0
    removed = 0
    for folder in parent.iterdir():
        if folder.is_dir() and not folder.is_symlink() and folder.name.startswith(prefix):
            marker = folder / MARKER
            if marker.is_file() and not marker.is_symlink() and marker.read_text(encoding='utf-8') == MARKER_TEXT:
                remove_staging(parent, folder, prefix)
                removed += 1
    return removed
