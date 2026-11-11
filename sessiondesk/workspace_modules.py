"""Data-only optional workspace modules and prepared-campaign recovery import.

Only application-bundled renderers run. Files carried by a backup are never
imported as Python/JavaScript or used as application templates.
"""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import uuid
import zipfile

from .importer import MAX_IMAGE, MAX_TOTAL, UserError, image_size, polygon, stable
from .transfers import CHUNK, MAX_BACKUP, check_cancel, staging, remove_staging, recover_staging

KIND = 'campaign-desk-v1'
MODULE_ID = stable('sessiondesk-module', KIND)
HASH = re.compile(r'^[a-f0-9]{64}$')
MAX_FILES = 10000
MAX_ATTACHMENT = 512 * 1024 * 1024


def relative(value):
    if not isinstance(value, str) or not value or len(value) > 600 or '\\' in value:
        raise UserError('Invalid module file path.')
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ('', '.', '..') for x in value.split('/')):
        raise UserError('Module files must stay inside their workspace.')
    for part in p.parts:
        if (any(c in part for c in ':<>"|?*\x00\r\n') or part.endswith(('.', ' '))
                or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part)):
            raise UserError('Module file path is not portable on Windows.')
    return p.as_posix()


def local(root, name):
    name = relative(name)
    root = Path(root).resolve()
    target = root / name
    if not target.resolve().is_relative_to(root):
        raise UserError('Module path leaves its selected folder.')
    current = target
    while current != root:
        if current.is_symlink() or current.is_junction():
            raise UserError('Linked module files/directories are not supported.')
        current = current.parent
    return target


def read(path, default=None):
    path = Path(path)
    if not path.is_file():
        return default
    if path.stat().st_size > MAX_IMAGE:
        raise UserError('Campaign JSON exceeds 48 MB.')
    return json.loads(path.read_text(encoding='utf-8-sig'),
                      parse_constant=lambda _: (_ for _ in ()).throw(UserError('Invalid campaign number.')))


def validate(module, assets):
    if (not isinstance(module, dict) or not isinstance(module.get('kind'), str)
            or not re.fullmatch(r'[a-z0-9-]{1,80}', module['kind'])
            or type(module.get('schema')) is not int or module['schema'] < 1
            or type(module.get('enabled')) is not bool or not isinstance(module.get('files'), dict)
            or len(module['files']) > MAX_FILES or not isinstance(module.get('title'), str)
            or len(module['title']) > 200):
        raise UserError('Invalid workspace module manifest.')
    seen = set()
    for name, record in module['files'].items():
        path = relative(name)
        if path.casefold() in seen:
            raise UserError('Case-colliding module paths are not portable.')
        seen.add(path.casefold())
        validate_record(record, assets)
    if module.get('original'):
        validate_record(module['original'], assets)


def validate_record(record, assets):
    if (not isinstance(record, dict) or not isinstance(record.get('asset'), str)
            or not HASH.fullmatch(record['asset']) or record['asset'] not in assets
            or type(record.get('size')) is not int or not 0 <= record['size'] <= MAX_ATTACHMENT
            or record['size'] != assets[record['asset']]['size']
            or record.get('mime') != assets[record['asset']]['mime']):
        raise UserError('Invalid module attachment reference.')


def supported(module):
    return module.get('kind') == KIND and module.get('schema') == 1 and module.get('enabled') is True


def materialize(folder, module_id, module):
    root = local(folder, 'module-files/' + module_id)
    parent = root.parent
    if parent.exists():
        recover_staging(parent, '_materialize-')
    if root.exists():
        if root.is_symlink() or root.is_junction():
            raise UserError('Module folder cannot be linked.')
        return root
    parent.mkdir(parents=True, exist_ok=True)
    # The marker stays outside content: only complete authored data is published.
    pending = staging(parent, '_materialize-')
    content = pending / 'content'
    content.mkdir()
    try:
        for name, record in module['files'].items():
            target = local(content, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            source = local(folder, 'assets/' + record['asset'])
            shutil.copyfile(source, target)
        content.replace(root)
    finally:
        try:
            remove_staging(parent, pending, '_materialize-')
        except OSError:
            pass  # Marked staging is recoverable; published data is complete.
    return root


def materialize_all(folder, documents):
    for key, value in documents.items():
        if key.startswith('module:'):
            root = materialize(folder, key.split(':', 1)[1], value)
            if supported(value):
                inspect_campaign(root)


def inspect_campaign(root):
    """Validate the supported authored format; do not execute its prep scripts."""
    root = Path(root)
    manifest = read(local(root, 'campaign.json'))
    if not isinstance(manifest, dict) or manifest.get('schemaVersion') != 1:
        raise UserError('Unsupported prepared-campaign format.')
    if manifest.get('rulesEdition') != '2014':
        raise UserError('Prepared campaigns currently require the 2014 rules profile.')
    paths = manifest.get('paths', {})
    for key in ('data', 'state', 'characters', 'prep'):
        local(root, paths.get(key, key))
    data = local(root, paths.get('data', 'data'))
    maps = []
    for name in manifest.get('catalogs', {}).get('maps', []):
        content = read(local(data, name))
        if not isinstance(content, dict) or not isinstance(content.get('maps'), list):
            raise UserError('Prepared map catalog is missing or invalid.')
        maps.extend(content['maps'])
    if not maps or len(maps) > 200:
        raise UserError('A prepared campaign needs 1–200 maps.')
    ids = set()
    for m in maps:
        if not isinstance(m.get('id'), str) or m['id'] in ids:
            raise UserError('Prepared map identities must be unique.')
        ids.add(m['id'])
        w, h = m.get('width'), m.get('height')
        if type(w) is not int or type(h) is not int or not 0 < w * h <= 100000000 or min(w, h) < 1:
            raise UserError('Prepared map dimensions exceed supported limits.')
        for field in ('image', 'playerImage'):
            if m.get(field):
                image = local(root, m[field])
                if not image.is_file() or image.stat().st_size > MAX_IMAGE:
                    raise UserError('Prepared map image is missing or too large.')
                dimensions, _ = image_size(image.read_bytes())
                if dimensions != (w, h):
                    raise UserError('Prepared map image dimensions do not match its coordinates.')
        for location in m.get('locations', []):
            for shape in location.get('shapes', []):
                polygon(shape, w, h)
    characters = local(root, paths.get('characters', 'characters'))
    records = list(characters.glob('*/character.json')) if characters.is_dir() else []
    for file in records:
        record = read(file)
        if record.get('id') != file.parent.name or not re.fullmatch(r'[a-z0-9-]+', record['id']):
            raise UserError('Prepared character identities do not match their folders.')
    state = read(local(root, paths.get('state','state') + '/table.json'))
    if state is not None:
        validate_state(state, maps)
    return {'maps': len(maps), 'characters': len(records),
            'locations': sum(len(m.get('locations', [])) for m in maps),
            'files': sum(p.is_file() for p in root.rglob('*'))}


def validate_state(state, maps):
    by_id = {m['id']:m for m in maps}
    if not isinstance(state, dict) or state.get('mapId') not in by_id or not isinstance(state.get('fog',{}),dict):
        raise UserError('Saved campaign state refers to an unknown map.')
    for mid, fog in state.get('fog',{}).items():
        if mid not in by_id or not isinstance(fog,dict) or not isinstance(fog.get('operations'),list) or len(fog['operations'])>10000:
            raise UserError('Invalid saved campaign fog.')
        m=by_id[mid]
        rooms={r['id']:r for r in m.get('locations',[])}
        for op in fog['operations']:
            if not isinstance(op,dict) or op.get('kind') not in ('room','brush','all','cover'):
                raise UserError('Unsupported saved fog operation.')
            if op['kind']=='room':
                room=rooms.get(op.get('id'))
                section=op.get('shape',0)
                if (not room or type(section) is not int or not 0<=section<len(room.get('shapes',[]))
                        or type(op.get('reveal')) is not bool):
                    raise UserError('Saved room reveal no longer matches the map.')
            if op['kind']=='brush':
                radius=op.get('radius')
                if (type(radius) not in (int,float) or not math.isfinite(radius)
                        or not 1<=radius<=max(m['width'],m['height'])
                        or not isinstance(op.get('points'),list) or not 1<=len(op['points'])<=2000
                        or type(op.get('reveal')) is not bool):
                    raise UserError('Invalid saved campaign brush.')
                for point in op['points']:
                    if (not isinstance(point,list) or len(point)!=2
                            or any(type(v) not in (int,float) or not math.isfinite(v) for v in point)
                            or not 0<=point[0]<=m['width'] or not 0<=point[1]<=m['height']):
                        raise UserError('Saved brush point is outside its original map.')
    tabs=state.get('tabs',[])
    if not isinstance(tabs,list) or len(tabs)>100:
        raise UserError('Invalid saved presentation tabs.')
    for tab in tabs:
        if not isinstance(tab,dict) or not isinstance(tab.get('id'),str) or tab.get('kind') not in ('map','picture','guide','book'):
            raise UserError('Unsupported saved presentation tab.')
        if tab['kind']=='map' and tab.get('mapId') not in by_id:
            raise UserError('Saved tab refers to an unknown map.')
        if tab['kind']=='picture':
            relative(tab.get('path'))
        if tab['kind']=='book' and not (str(tab.get('url','')).startswith('/reference/book.html#') or tab.get('url')=='/shop'):
            raise UserError('Saved book tab must refer to a local shared reference.')


def capture_file(folder, file, cancelled=lambda: False):
    """Hash/copy one bounded file, preserving immutable asset storage."""
    if file.stat().st_size > MAX_ATTACHMENT:
        raise UserError('A workspace attachment exceeds 512 MB.')
    before = (file.stat().st_size, file.stat().st_mtime_ns)
    temp = folder / 'assets' / ('_capture-' + uuid.uuid4().hex)
    digest, size = hashlib.sha256(), 0
    try:
        with file.open('rb') as source, temp.open('xb') as output:
            while chunk := source.read(CHUNK):
                check_cancel(cancelled)
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        if (file.stat().st_size, file.stat().st_mtime_ns) != before:
            raise UserError('A campaign file changed during backup. Retry after saving the edit.')
        mime = 'application/octet-stream'
        with temp.open('rb') as probe:
            header = probe.read(32)
        raster = header.startswith((b'\x89PNG\r\n\x1a\n', b'GIF87a', b'GIF89a', b'\xff\xd8')) or header[:4] == b'RIFF' and header[8:12] == b'WEBP'
        if raster:
            if size > MAX_IMAGE:
                raise UserError('Campaign image exceeds 48 MB.')
            _, mime = image_size(temp.read_bytes())
        value = digest.hexdigest()
        target = folder / 'assets' / value
        if not target.exists():
            temp.replace(target)
        else:
            with target.open('rb') as existing:
                if hashlib.file_digest(existing, 'sha256').hexdigest() != value:
                    temp.replace(target)
        return {'asset': value, 'mime': mime, 'size': size}
    finally:
        temp.unlink(missing_ok=True)


def sync(store, wid, conn, cancelled=lambda: False):
    """Snapshot edited module files under the same lock as runtime writers."""
    folder = store.folder(wid)
    modules = [(key, json.loads(value)) for key, value in conn.execute(
        "SELECT key,value FROM documents WHERE key LIKE 'module:%'")]
    for key, module in modules:
        check_cancel(cancelled)
        if not supported(module):
            continue  # Unknown module schemas round-trip unchanged and stay inert.
        root = local(folder, 'module-files/' + key.split(':', 1)[1])
        if not root.exists():
            continue
        files = {}
        for file in sorted(root.rglob('*')):
            check_cancel(cancelled)
            if file.is_symlink() or file.is_junction():
                raise UserError('Linked module files cannot be backed up.')
            if file.is_file() and file.suffix != '.tmp':
                name = relative(file.relative_to(root).as_posix())
                files[name] = capture_file(folder, file, cancelled)
                record = files[name]
                conn.execute('INSERT OR REPLACE INTO assets VALUES (?,?,?)',
                             (record['asset'], record['mime'], record['size']))
        if len(files) > MAX_FILES:
            raise UserError('Prepared campaign exceeds the 10,000-file limit.')
        module['files'] = files
        if supported(module):
            module['summary'] = inspect_campaign(root)
        store.put(conn, key, module)


def backup_assets(documents, assets):
    """Export current references, retaining immutable historical files locally.

    An in-flight backup may still need old hashes, so this is not garbage
    collection. Unknown modules conservatively retain all attachments.
    """
    needed = set()
    for key, value in documents.items():
        if key.startswith('adventure:'):
            needed.update(m['asset'] for m in value['maps'] + value['pictures'])
        elif key.startswith('module:'):
            if not supported(value):
                return assets
            needed.update(record['asset'] for record in value['files'].values())
            if value.get('original'):
                needed.add(value['original']['asset'])
    return {digest: assets[digest] for digest in needed}


def import_campaign(store, source, cancelled, progress, on_commit):
    """Convert a selected legacy data archive into a new ordinary workspace."""
    folder = None
    try:
        with zipfile.ZipFile(source) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            if (len(infos) > 20000 or len(set(names)) != len(names)
                    or sum(i.file_size for i in infos) > MAX_BACKUP
                    or any(i.flag_bits & 1 or (i.external_attr >> 16) & 0o170000 == 0o120000 for i in infos)):
                raise UserError('Campaign archive exceeds limits or contains duplicate/encrypted/linked files.')
            for name in names:
                if name.endswith('/'):
                    name = name[:-1]
                relative(name)
            candidates = [name for name in names if name == 'campaign.json' or
                          (name.startswith('project/campaigns/') and name.endswith('/campaign.json')
                           and len(PurePosixPath(name).parts) == 4)]
            if len(candidates) != 1:
                raise UserError('Choose a prepared-campaign ZIP containing exactly one campaign.json.')
            config = read_archive_json(archive, candidates[0])
            prefix = candidates[0][:-len('campaign.json')]
            selected = [i for i in infos if i.filename.startswith(prefix) and not i.is_dir()]
            if len(selected) > MAX_FILES:
                raise UserError('Prepared campaign exceeds the 10,000-file limit.')
            name = str(config.get('title') or config.get('id') or 'Imported campaign')[:100]
            meta = store._metadata(name, 'Greek' if any('narration-gr' in i.filename for i in selected) else 'English',
                                   str(config.get('rulesEdition', 'Unspecified')))
            folder = staging(store.workspaces, '_restore-')
            (folder / 'assets').mkdir()
            root = folder / 'module-files' / MODULE_ID
            root.mkdir(parents=True)
            files, assets, seen = {}, {}, set()
            total = sum(i.file_size for i in selected)
            done = 0
            # A recovery manifest, when present, must match the captured bytes.
            expected = {}
            if 'backup-manifest.json' in names:
                manifest = read_archive_json(archive, 'backup-manifest.json')
                if manifest.get('format') != 'campaign-desk-full-snapshot':
                    raise UserError('Unrecognized campaign recovery manifest.')
                expected = {r['path']: r for r in manifest.get('files', [])}
            for info in selected:
                check_cancel(cancelled)
                rel = relative(info.filename[len(prefix):])
                if rel.casefold() in seen:
                    raise UserError('Case-colliding campaign files are not supported.')
                seen.add(rel.casefold())
                if info.file_size > MAX_ATTACHMENT:
                    raise UserError('Campaign attachment exceeds 512 MB.')
                target = local(root, rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                checksum = hashlib.sha256()
                with archive.open(info) as inp, target.open('xb') as out:
                    while chunk := inp.read(CHUNK):
                        check_cancel(cancelled)
                        checksum.update(chunk)
                        out.write(chunk)
                        done += len(chunk)
                        progress('Importing prepared campaign files', done, total)
                if expected:
                    record = expected.get(info.filename)
                    if not record or record.get('sha256') != checksum.hexdigest() or record.get('size') != info.file_size:
                        raise UserError('Campaign recovery file checksum mismatch.')
                record = capture_file(folder, target, cancelled)
                files[rel] = record
                assets[record['asset']] = {'mime': record['mime'], 'size': record['size']}
            summary = inspect_campaign(root)
            module = {'kind': KIND, 'schema': 1, 'enabled': True, 'title': name,
                      'files': files, 'summary': summary}
            # Preserve the original full recovery archive too, including source,
            # history and authoring files which are never executed by this app.
            if isinstance(source, (str, Path)):
                progress('Preserving original recovery archive', 0, Path(source).stat().st_size)
                original = capture_file(folder, Path(source), cancelled)
                module['original'] = original
                assets[original['asset']] = {'mime': original['mime'], 'size': original['size']}
            if sum(a['size'] for a in assets.values()) > MAX_TOTAL:
                raise UserError('Prepared workspace exceeds 1 GB; original campaign was not changed.')
            documents = {'module:' + MODULE_ID: module}
            validate(module, assets)
            store._initialize(folder, meta, documents, assets)
            check_cancel(cancelled)
            on_commit()
            folder.replace(store.workspaces / meta['id'])
            return meta
    finally:
        if folder is not None:
            remove_staging(store.workspaces, folder, '_restore-')


def read_archive_json(archive, name):
    info = archive.getinfo(name)
    if info.file_size > 48 * 1024 * 1024:
        raise UserError('Campaign manifest exceeds supported limits.')
    return json.loads(archive.read(info).decode('utf-8-sig'),
                      parse_constant=lambda _: (_ for _ in ()).throw(UserError('Invalid campaign JSON.')))
