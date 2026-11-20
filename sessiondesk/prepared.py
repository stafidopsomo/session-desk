"""Optional, application-bundled prepared-campaign UI and authenticated routes."""
from dataclasses import dataclass
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from . import prepared_characters, prepared_rules
from .importer import Library, UserError
from .prepared_engine import make_runtime
from .workspace_modules import KIND, MODULE_ID, inspect_campaign, local, materialize, read, supported

STATIC = Path(__file__).parent / 'static' / 'prepared'
STATIC_NAMES = frozenset(('index.html','player.html','shop.html','app.js','player.js','shop.js',
    'after-citadel.js','map.js','tokens.js','characters.js','layout.js','appearance.js',
    'reference-storage.js','bootstrap.js','style.css','refinements.css','opening.css',
    'desk.css','slate.css','player.css','shop.css','tokens.css'))


@dataclass
class Workspace:
    root: Path
    manifest: dict
    reference: Path

    @property
    def data(self):
        return self.path('data')

    def path(self, key):
        return local(self.root, self.manifest.get('paths', {}).get(key, key))

    def data_file(self, name):
        return local(self.data, name)

    def resource(self, name):
        return local(self.root, name)

    def catalog(self, key, default):
        return self.manifest.get('catalogs', {}).get(key, default)

    def public(self):
        return {k: self.manifest[k] for k in ('id','title','rulesEdition','mapGroups') if k in self.manifest} | {
            'narrationMaps': self.catalog('narrationMaps', []),
            'archivedMapIds': self.catalog('archivedMapIds', []),
            'archivedAssetPrefixes': self.catalog('archivedAssetPrefixes', [])}


class Prepared:
    def __init__(self, store, wid, reference=None):
        self.store, self.wid = store, wid
        with store.lock, store.db(wid) as conn:
            module = store.get(conn, 'module:' + MODULE_ID)
            if not module or not supported(module):
                raise UserError('This workspace has no enabled prepared campaign.')
            root = materialize(store.folder(wid), MODULE_ID, module)
            inspect_campaign(root)
            self.workspace = Workspace(root, read(root / 'campaign.json'),
                Path(reference) if reference else root / '_unconfigured-rules')
            self.runtime = make_runtime(self.workspace, store.lock)

    def capabilities(self):
        data = self.runtime.catalog()
        return {'characters': bool(prepared_characters.records(self.workspace.path('characters'))['characters']),
                'aftermath': bool(data['afterCitadel'].get('scenes')),
                'opening': bool(data['opening'].get('scenes')),
                'shopping': bool(data['shopping'].get('items')),
                'sessions': bool(data['sessions'] or data['guide'].get('cards')), 'rules': (self.workspace.reference / 'data/book/book-phb.json').is_file()}

    def room_source(self, map_id, room_id):
        """Resolve a saved room against its exact entry in the local source library."""
        map_data = self.runtime.map_by_id(map_id)
        room = next((room for room in (map_data or {}).get('locations', [])
                     if room.get('id') == room_id), None)
        if not room:
            raise UserError('Room not found.')

        source_link = urlsplit(room.get('sourceLink') or '')
        kind = {'/reference/adventure.html': 'adventure',
                '/reference/book.html': 'book'}.get(source_link.path)
        locator = source_link.fragment.split(',')
        if not kind or source_link.netloc or source_link.scheme or len(locator) < 2:
            return {'entry': None}
        source_id, chapter_index = locator[:2]
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', source_id) or not re.fullmatch(r'[0-9]{1,4}', chapter_index):
            return {'entry': None}
        source_id = ('book:' if kind == 'book' else '') + source_id
        try:
            _, _, chapters, _ = Library(self.workspace.reference).read_source(source_id)
            section = chapters[int(chapter_index)]
        except (OSError, ValueError, IndexError):
            return {'entry': None}

        area = room.get('sourceAreaId')
        heading = unquote(locator[2]).casefold() if len(locator) > 2 else ''
        # Prefer the stable area key. Some source data has unkeyed headings,
        # so accept the title only when it uniquely identifies one entry.
        stack = [section]
        keyed, titled = [], []
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(reversed(node))
            elif isinstance(node, dict):
                if area and node.get('id') == area:
                    keyed.append(node)
                if heading and str(node.get('name', '')).casefold() == heading:
                    titled.append(node)
                for field in ('entries', 'items', 'rows', 'entry'):
                    if isinstance(node.get(field), (dict, list)):
                        stack.append(node[field])
        if len(keyed) == 1:
            return {'entry': keyed[0]}
        if len(titled) == 1:
            return {'entry': titled[0]}
        return {'entry': None}

    def api(self, path, method, body, query, player):
        r = self.runtime
        if player and path not in ('/api/player-state','/api/player-action','/api/shop'):
            raise PermissionError('This campaign resource is DM-only.')
        with self.store.lock:
            if method == 'GET':
                if path == '/api/data':
                    data = r.catalog()
                    cue = self.workspace.catalog('shoppingCue', None)
                    # The earlier authored format had this implicit location.
                    # Retain it only when those actual records are present.
                    city = next((m for m in data['maps'] if m['id'] == 'waterdeep'), None)
                    if cue is None and city and any(p['id'] == 'castle-ward' for p in city['locations']):
                        cue = {'mapId':'waterdeep','locationId':'castle-ward'}
                    data['campaign']['shoppingCue'] = cue
                    return data | {'capabilities': self.capabilities()}
                if path in ('/api/state','/api/player-state'):
                    return r.snapshot(player=path.endswith('player-state'))
                if path == '/api/room-source':
                    return self.room_source(query.get('mapId', [''])[0], query.get('roomId', [''])[0])
                if path == '/api/map-state':
                    import copy
                    m = r.map_by_id(query.get('mapId',[''])[0])
                    if not m: raise UserError('Map not found.')
                    state = r.snapshot()
                    fog = copy.deepcopy(r.state['fog'].get(m['id'], {'operations':[]}))
                    return state | {'mapId':m['id'], 'locationId':None, 'fogState':fog,
                        'revealed':r.revealed(m,fog), 'tokens':[], 'playerFocus':None,
                        'roomNotes':read(self.workspace.path('state')/'room-notes.json',{}).get(m['id'],{})}
                if path == '/api/shop':
                    return read(self.workspace.data / 'shopping.json', {'shops': [], 'items': []})
                if path == '/api/characters':
                    return prepared_characters.records(self.workspace.path('characters'))
                if path == '/api/character-options':
                    return prepared_rules.options(self.workspace.reference)
                if path == '/api/character-rules':
                    ident = query.get('id', [''])[0]
                    c = next((c for c in prepared_characters.records(self.workspace.path('characters'))['characters']
                              if c['id'] == ident), None)
                    if not c:
                        raise UserError('Character not found in this workspace.')
                    return prepared_rules.rules(c, self.workspace.reference)
            if method == 'POST':
                if path == '/api/characters':
                    return prepared_characters.update(self.workspace.path('characters'), body, self.workspace.reference)
                if path == '/api/narration':
                    return r.narration(body)
                if path == '/api/action':
                    return r.action(body)
                if path == '/api/player-action':
                    action = body.get('action', '')
                    if isinstance(action, str) and action.startswith('token-'):
                        r.action(body, player=True)
                    elif action in ('tab-select','tab-close','tab-close-all','room-scene','room-scene-map'):
                        # Scene selection is validated against revealed, approved art.
                        r.action(body)
                    elif action == 'room-note':
                        m = r.map_by_id(body.get('mapId'))
                        key = f"{body.get('id')}:{int(body.get('shape',0))}"
                        if not m or key not in r.revealed(m, r.state['fog'].get(m['id'], {'operations': []})):
                            raise UserError('Shared notes are available only for revealed rooms.')
                        r.action(body)
                    else:
                        raise PermissionError('Only the DM controls campaign visibility.')
                    return r.snapshot(player=True)
        raise UserError('Unsupported prepared-campaign action. AI/generation routes are unavailable.')

    def player_files(self):
        r = self.runtime
        state = r.snapshot(player=True)
        result = set()
        if state.get('emptyState'):
            return result
        data = r.catalog()
        for tab in r.state.get('tabs', []):
            if tab.get('kind') == 'map':
                m = r.map_by_id(tab['mapId'], data)
                if m:
                    result.add(m.get('playerImage', m['image']))
        if state.get('map'):
            result.add(state['map']['image'])
        if state.get('overlay'):
            result.add(state['overlay']['path'])
        if (state.get('guideCard') or {}).get('picture'):
            result.add(state['guideCard']['picture'])
        result.update(t['image'] for t in state.get('tokens', []) if t.get('image'))
        result.update(t['image'] for t in state.get('tokenCatalog', []) if t.get('image'))
        return result

    def file(self, path, player):
        name = unquote(path.removeprefix('/assets/'))
        if player and name not in self.player_files():
            raise PermissionError('This campaign file is not presented.')
        file = local(self.workspace.root, name)
        if not file.is_file():
            raise UserError('Campaign file not found.')
        mime = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
        if player and file.suffix.lower() not in ('.png','.jpg','.jpeg','.gif','.webp'):
            raise PermissionError('Players receive only presented raster images.')
        return file, mime, not mime.startswith('image/') or file.suffix.lower() == '.svg'

    def reference(self, path, player):
        if not (self.workspace.reference / 'data/book/book-phb.json').is_file():
            raise UserError('Connect a local 2014 rules library from the Workspace screen first.')
        name = unquote(path.removeprefix('/reference/'))
        if player:
            state = self.runtime.snapshot(player=True)
            section = state.get('bookSection') or {}
            source = section.get('url', '')
            if not source.startswith('/reference/book.html#'):
                raise PermissionError('No source book has been shared.')
            book = source.split('#', 1)[1].split(',', 1)[0].lower()
            if name.startswith('data/') and name not in ('data/books.json', f'data/book/book-{book}.json'):
                raise PermissionError('Only the explicitly shared source book is available.')
            if name.endswith('.html') and name != 'book.html':
                raise PermissionError('Only the shared book reader is available.')
        root = self.workspace.reference
        if name.startswith('img/'):
            file = local((root / 'img').resolve(), name[4:])
        else:
            file = local(root, name)
        if (not file.is_file() or '.git' in file.parts or
                file.suffix.lower() in ('.py','.exe','.bat','.ps1','.cmd','.dll','.sqlite3')):
            raise UserError('Reference resource not found.')
        mime = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
        if name == 'js/utils.js':
            shim = (STATIC / 'reference-storage.js').read_text(encoding='utf-8')
            shim = shim.replace('campaign-desk:reference-2014:', 'sessiondesk:' + self.wid + ':reference-2014:')
            return file.read_bytes() + b'\n' + shim.encode(), 'text/javascript'
        return file, mime


def rewrite(value, base):
    """URLs are namespaced only in responses; canonical files stay portable."""
    if isinstance(value, str) and value.startswith(('/reference/','/assets/','/shop')):
        return base + value
    if isinstance(value, list):
        return [rewrite(v, base) for v in value]
    if isinstance(value, dict):
        return {k: rewrite(v, base) for k, v in value.items()}
    return value


def unmount(value, base):
    if isinstance(value, str) and value.startswith(base + '/'):
        return value[len(base):]
    if isinstance(value, list):
        return [unmount(v, base) for v in value]
    if isinstance(value, dict):
        return {k: unmount(v, base) for k, v in value.items()}
    return value


def static(name, base, player_base, wid, player):
    if name not in STATIC_NAMES:
        raise UserError('Application resource not found.')
    text = (STATIC / name).read_text(encoding='utf-8')
    text = text.replace('__PLAYER__', '1' if player else '0').replace('__WORKSPACE_URL__', '/?workspace=' + wid)
    # Rewrite trusted bundled templates only. Never serve templates from a ZIP.
    for quote in ('"', "'", '`'):
        text = text.replace(quote + '/player' + quote, quote + player_base + '/player' + quote)
        for prefix in ('/static/', '/assets/', '/reference/', '/api/'):
            text = text.replace(quote + prefix, quote + base + prefix)
        text = text.replace(quote + '/shop' + quote, quote + base + '/shop' + quote)
    mime = 'text/html' if name.endswith('.html') else 'text/javascript' if name.endswith('.js') else 'text/css'
    return text.encode('utf-8'), mime
