"""Trusted prepared-campaign engine, isolated per imported workspace.

The renderer implements the declared campaign-desk data format. It does not
load modules, run generators or execute source files from an imported archive.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
from . import prepared_tokens as table_tools

MAX_TABS = 100
MAX_FOG_OPERATIONS = 10000


def local_book_link(value):
    """Only a local book reader and a bounded, explicit book locator may be shared."""
    if (not isinstance(value, str) or len(value) > 2000
            or any(ord(c) < 32 or ord(c) == 127 or c == '\\' for c in value)):
        return False
    parts = urlsplit(value)
    return (not parts.scheme and not parts.netloc and not parts.query
            and parts.path == '/reference/book.html'
            and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', parts.fragment.split(',', 1)[0]) is not None)


def make_runtime(workspace, lock):
    WORKSPACE = workspace
    REPO = workspace.root
    DATA = workspace.data
    STATE_FILE = workspace.path('state') / 'table.json'
    NOTES_FILE = workspace.path('state') / 'room-notes.json'
    NARRATION_FILE = DATA / 'narration-gr.json'
    CHARACTER_ROOT = workspace.path('characters')
    REFERENCE = workspace.reference
    LOCK = lock
    TABLE = table_tools.initial()
    def read_json(path, default=None):
        if not path.exists():
            return copy.deepcopy(default)
        return json.loads(path.read_text(encoding='utf-8-sig'))

    def catalog():
        maps = []
        for name in WORKSPACE.catalog('maps', ['world.json','dungeon.json']):
            maps.extend(read_json(WORKSPACE.data_file(name), {'maps': []})['maps'])
        narration = read_json(NARRATION_FILE, {'rooms': {}})
        dialogue = read_json(DATA / 'npc-dialogue-gr.json', {'rooms': {}})
        encounters = read_json(DATA / 'encounters.json', {'partyLevel': 3, 'partySize': 5, 'rooms': {}, 'opening': {}})
        chapter = read_json(DATA / 'after-citadel.json', {'scenes': [], 'roomCues': []})
        chapter_scenes = {s['id']: s for s in chapter['scenes']}
        chapter['encounters'] = {key:read_json(WORKSPACE.resource(path), {}) for key,path in WORKSPACE.catalog('chapterEncounters', {}).items()}
        for map_data in maps:
            if map_data.get('kind') == 'dungeon':
                map_data.setdefault('sourceLink', next((p['sourceLink'].rsplit(',', 1)[0] for p in map_data.get('locations', []) if p.get('sourceLink', '').startswith('/reference/')), '/reference/index.html'))
                for room in map_data['locations']:
                    # Forge uses namespaced IDs and carries its own preparation.
                    if room['id'] in encounters['rooms']:
                        room['encounter'] = encounters['rooms'][room['id']]
                    room['npcDialogueGr'] = dialogue['rooms'].get(room['id'], []) if map_data['id'] in WORKSPACE.catalog('narrationMaps', []) else []
                    text = narration['rooms'].get(room['id'], {})
                    room.update({k: text[k] for k in ('readAloudGr', 'additionalPassages', 'narrationType') if k in text})
                    if text:
                        room['narrationKind'] = text.get('kind', '')
                        room['deliveryNote'] = text.get('deliveryNote', '')
                    approach = WORKSPACE.catalog('approachCue', {})
                    if map_data['id'] == approach.get('mapId') and room['id'] == approach.get('areaId') and narration.get('approach'):
                        room['additionalPassages'] = [{'trigger': 'Before descending: the ravine approach', 'readAloudGr': narration['approach']['readAloudGr']}] + room.get('additionalPassages', [])
                    room['privateCues'] = []
                    for cue in chapter.get('roomCues', []):
                        if cue['mapId'] != map_data['id'] or cue['areaId'] != room['id'] or cue['sceneId'] not in chapter_scenes:
                            continue
                        detail = copy.deepcopy(chapter_scenes[cue['sceneId']])
                        if cue.get('note'):
                            detail.update(title=cue['title'], trigger=cue['note'], readAloudGr='', npcLines=[])
                        room['privateCues'].append(detail)
        assets = {}
        for root in ('maps', 'adventures', 'sessions'):
            folder = REPO / root
            for manifest in sorted(folder.rglob('manifest.json')):
                for asset in read_json(manifest, {'assets': []})['assets']:
                    if (REPO / asset['path']).is_file():
                        if asset['path'].startswith('maps/sunless-citadel/'):
                            asset['spoiler'] = True
                        path = asset['path']
                        asset.setdefault('collection', ('session-00' if path.startswith('sessions/session-00/') else
                                               'session-01' if path.startswith('sessions/session-01/') else
                                               'sunless-citadel' if 'sunless-citadel' in path else
                                               'forge-of-fury' if 'forge-of-fury' in path else
                                               'waterdeep' if '/waterdeep/' in path else 'sword-coast'))
                        assets[asset['path']] = asset
        for map_data in maps:
            for room in map_data['locations']:
                room['scenes'] = [{'path': a['path'], 'shape': a.get('sectionIndex', 0), 'title': 'Room ' + room['id']}
                                  for a in assets.values() if a.get('mapId') == map_data['id'] and a.get('areaId') == room['id']
                                  and a.get('category') == 'room-scene' and not a.get('spoiler', True) and not room.get('sceneDisabled')]
        sessions = read_json(DATA / 'sessions.json', {'sessions': []})['sessions']
        opening = read_json(DATA / 'opening.json', {'title': 'Start the adventure', 'scenes': []})
        for scene in opening['scenes']:
            scene['encounter'] = encounters.get('opening', {}).get(scene['id'])
        return {'maps': maps, 'assets': list(assets.values()), 'sessions': sessions,
                'guide': read_json(DATA / 'world-guide.json', {'cards': []}),
                'opening': opening, 'encounters': encounters,
                'shopping': read_json(DATA / 'shopping.json', {'shops': [], 'items': []}),
                'afterCitadel': chapter,
                'tokenCatalog': table_tools.templates(CHARACTER_ROOT, read_json(DATA / 'token-art.json', {})),
                'campaign': WORKSPACE.public()}

    def initial_state():
        first_map=next(iter(catalog()['maps']), {'id':'sword-coast'})['id']
        return {'version': 1, 'mapId': first_map, 'locationId': None,
                'overlay': None, 'blackout': False, 'ping': None, 'fog': {}, 'mapSplitVersion': 1,
                'tabs': [{'id': 'map:'+first_map, 'kind': 'map', 'mapId': first_map, 'locationId': None}],
                'activeTabId': 'map:'+first_map}

    def ensure_tabs():
        if 'tabs' not in STATE:
            tab = {'id': 'map:' + STATE['mapId'], 'kind': 'map', 'mapId': STATE['mapId'], 'locationId': STATE.get('locationId')}
            STATE.update(tabs=[tab], activeTabId=tab['id'])

    def open_tab(tab):
        ensure_tabs()
        old = next((t for t in STATE['tabs'] if t['id'] == tab['id']), None)
        if old is None and len(STATE['tabs']) >= MAX_TABS:
            raise ValueError('Close a player tab before opening another (100 maximum).')
        if old:
            old.update(tab)
        else:
            STATE['tabs'].append(tab)
        STATE['activeTabId'] = tab['id']
        STATE['overlay'] = {'path': tab['path'], 'title': tab.get('title', '')} if tab['kind'] == 'picture' else None

    def map_by_id(map_id, data=None):
        return next((m for m in (data or catalog())['maps'] if m['id'] == map_id), None)

    def fog_for(map_data):
        return STATE['fog'].setdefault(map_data['id'], {'operations': []})

    def revealed(map_data, fog):
        ids = {f"{p['id']}:{i}" for p in map_data['locations'] if p['id'] in map_data.get('initialRevealed', []) for i in range(len(p.get('shapes', [])))}
        for op in fog['operations']:
            if op['kind'] == 'room':
                if op['reveal']:
                    ids.add(f"{op['id']}:{op.get('shape', 0)}")
                else:
                    ids.discard(f"{op['id']}:{op.get('shape', 0)}")
            elif op['kind'] == 'all':
                ids = {f"{p['id']}:{i}" for p in map_data['locations'] for i in range(len(p.get('shapes', [])))}
            elif op['kind'] == 'cover':
                ids.clear()
        return sorted(ids)

    def snapshot(player=False):
        with LOCK:
            state = copy.deepcopy(STATE)
            table = copy.deepcopy(TABLE)
        data = catalog()
        # Withdraw rejected room art from existing presentation tabs in snapshots,
        # without rewriting the live table save or its fog history.
        approved_scenes = {s['path'] for m in data['maps'] for r in m['locations'] for s in r.get('scenes', [])}
        approved_pictures = {a['path'] for a in data['assets'] if not a.get('spoiler',True)}
        state['tabs'] = [t for t in state.get('tabs', []) if
                         (not t.get('scene') or t.get('path') in approved_scenes) and
                         (t.get('kind') != 'picture' or t.get('path') in approved_pictures)]
        if state.get('activeTabId') not in {t['id'] for t in state['tabs']}:
            state['activeTabId'] = state['tabs'][0]['id'] if state['tabs'] else None
        active = next((t for t in state.get('tabs', []) if t['id'] == state.get('activeTabId')), None)
        visible_map_id = (active['mapId'] if active and active['kind'] == 'map' else (active or {}).get('scene', {}).get('mapId', state['mapId'])) if player else state['mapId']
        m = map_by_id(visible_map_id, data)
        if not m:
            if player:
                return {'version':state.get('version',0),'emptyState':True,'tabs':[],'map':None}
            return state
        state['fogState'] = state['fog'].get(m['id'], {'operations': []})
        state['revealed'] = revealed(m, state['fogState'])
        state['tableVersion'] = table['version']
        state['tokens'] = [t for t in table['tokens'].get(m['id'], []) if not player or table_tools.visible(m, state['fogState'], t['x'], t['y'])]
        state['tokenCatalog'] = [t for t in data['tokenCatalog'] if not player or t['kind'] == 'pc']
        state['playerFocus'] = table['focus'].get(m['id'])
        notes = read_json(NOTES_FILE, {}).get(m['id'], {})
        state['roomNotes'] = {k: v for k, v in notes.items() if not player or k in state['revealed']}
        state['tabs'] = [public_tab(t, data) for t in state.get('tabs', [])]
        if player:
            state.pop('openingSceneId', None)
            state['emptyState'] = not state['tabs']
            state['mapId'] = visible_map_id
            state['locationId'] = active.get('locationId') if active and active['kind'] == 'map' else None
            state.pop('fog', None)
            state['map'] = {k: m[k] for k in ('id', 'title', 'width', 'height', 'kind', 'initialRevealed', 'roomRevealPadding') if k in m}
            state['map']['image'] = m.get('playerImage', m['image'])
            # Geometry is needed to draw fog. Room names and notes never reach this endpoint.
            state['map']['locations'] = [{'id': p['id'], 'shapes': p.get('shapes', []), 'scenes': [s for s in p.get('scenes', []) if f"{p['id']}:{s['shape']}" in state['revealed']]} for p in m['locations']] if m.get('kind') == 'dungeon' else []
            p = next((p for p in m['locations'] if p['id'] == state['locationId']), None)
            state['location'] = ({'name': p['name'], 'summary': p.get('summary', ''),
                                  'x': p['x'], 'y': p['y']} if p and m.get('kind') != 'dungeon' else None)
            state['overlay'] = {'path': active['path'], 'title': active.get('title', '')} if active and active['kind'] == 'picture' else None
            if state['overlay'] and active.get('scene'):
                state['overlay']['scene'] = active['scene']
            card = next((c for c in data['guide']['cards'] if active and c['id'] == active.get('cardId')), None)
            state['guideCard'] = ({k: card[k] for k in ('title', 'summary', 'prompt', 'picture') if k in card} if card else None)
            state['bookSection'] = {'url': active['url'], 'title': active['title']} if active and active['kind'] == 'book' else None
        if player:
            allowed = ('version','mapId','locationId','tabs','activeTabId','overlay','blackout','ping',
                       'fogState','revealed','tableVersion','tokens','tokenCatalog','playerFocus',
                       'roomNotes','emptyState','map','location','guideCard','bookSection')
            return {key:state[key] for key in allowed if key in state}
        return state

    def public_tab(tab, data):
        result = {'id': tab['id'], 'kind': tab['kind']}
        if tab['kind'] == 'map':
            result['mapId'] = tab['mapId']
            result['title'] = (map_by_id(tab['mapId'], data) or {}).get('title', 'Map')
        elif tab['kind'] == 'picture':
            result['title'] = tab.get('title', 'Picture')
        elif tab['kind'] == 'book':
            result['title'] = tab['title']
        else:
            card = next((c for c in data['guide']['cards'] if c['id'] == tab.get('cardId')), {})
            result['title'] = card.get('title', 'World guide')
        return result

    def save_state():
        STATE['version'] += 1
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = STATE_FILE.with_suffix('.tmp')
        temporary.write_text(json.dumps(STATE, indent=2, ensure_ascii=False), encoding='utf-8')
        temporary.replace(STATE_FILE)

    def action(body, player=False):
        with LOCK:
            data = catalog()
            kind = body.get('action')
            ensure_tabs()
            m = map_by_id(body.get('mapId', STATE['mapId']), data)
            if not m:
                raise ValueError('Unknown map')
            if isinstance(kind, str) and kind.startswith('token-'):
                table_tools.apply(TABLE, body, m, STATE['fog'].get(m['id'], {'operations': []}), data['tokenCatalog'], player=player)
                return snapshot(player=player)
            if kind == 'map':
                open_tab({'id': 'map:' + m['id'], 'kind': 'map', 'mapId': m['id'], 'locationId': None})
                STATE.update(mapId=m['id'], locationId=None, overlay=None)
            elif kind == 'opening-scene':
                if not any(s['id'] == body.get('id') for s in data['opening']['scenes']):
                    raise ValueError('Unknown opening scene')
                STATE['openingSceneId'] = body['id']
            elif kind == 'location':
                target = body.get('id')
                if target is not None and not any(p['id'] == target for p in m['locations']):
                    raise ValueError('Unknown location')
                if m.get('kind') != 'dungeon':
                    open_tab({'id': 'map:' + m['id'], 'kind': 'map', 'mapId': m['id'], 'locationId': target})
                STATE['locationId'] = target
            elif kind == 'room-note':
                room = next((p for p in m['locations'] if p['id'] == body.get('id')), None)
                shape = int(body.get('shape', 0)); text = body.get('text', '')
                if not room or not 0 <= shape < len(room.get('shapes', [])) or not isinstance(text, str) or len(text) > 20000:
                    raise ValueError('Invalid room note')
                notes = read_json(NOTES_FILE, {})
                notes.setdefault(m['id'], {})[f"{room['id']}:{shape}"] = text
                NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
                temp = NOTES_FILE.with_suffix('.tmp')
                temp.write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding='utf-8')
                temp.replace(NOTES_FILE)
            elif kind == 'tab-close-all':
                STATE.update(tabs=[], activeTabId=None, overlay=None)
            elif kind in ('tab-select', 'tab-close'):
                tab = next((t for t in STATE['tabs'] if t['id'] == body.get('id')), None)
                if not tab:
                    raise ValueError('Unknown player tab')
                if kind == 'tab-close':
                    STATE['tabs'].remove(tab)
                    if not STATE['tabs']:
                        STATE.update(activeTabId=None, overlay=None)
                        save_state()
                        return snapshot()
                    if STATE['activeTabId'] == tab['id']:
                        tab = STATE['tabs'][-1]
                    else:
                        tab = next(t for t in STATE['tabs'] if t['id'] == STATE['activeTabId'])
                STATE['activeTabId'] = tab['id']
                if tab['kind'] == 'map':
                    STATE.update(mapId=tab['mapId'], locationId=tab.get('locationId'))
                STATE['overlay'] = {'path': tab['path'], 'title': tab.get('title', '')} if tab['kind'] == 'picture' else None
            elif kind == 'guide':
                card = next((c for c in data['guide']['cards'] if c['id'] == body.get('cardId')), None)
                if not card:
                    raise ValueError('Unknown guide card')
                open_tab({'id': 'guide:' + card['id'], 'kind': 'guide', 'cardId': card['id']})
            elif kind == 'book-section':
                card = next((c for c in data['guide']['cards'] if c['id'] == body.get('cardId')), None)
                if not card or not local_book_link(card.get('sourceLink')):
                    raise ValueError('Choose a guide card with a local book source.')
                open_tab({'id': 'book:' + card['id'], 'kind': 'book', 'url': card['sourceLink'], 'title': card.get('title') or 'Book source'})
            elif kind == 'shop-catalog':
                open_tab({'id': 'shop:catalog', 'kind': 'book', 'url': '/shop', 'title': data['shopping'].get('title', 'Shops & supplies')})
            elif kind in ('room', 'brush', 'undo', 'reset', 'all', 'cover'):
                if m.get('kind') != 'dungeon':
                    raise ValueError('Fog is available on dungeon maps')
                if (kind in ('room', 'brush', 'all', 'cover')
                        and len(STATE['fog'].get(m['id'], {'operations': []})['operations']) >= MAX_FOG_OPERATIONS):
                    raise ValueError('Fog history is full. Export a backup, then undo or reset fog before revealing more.')
                fog = fog_for(m)
                if kind == 'room':
                    room = next((p for p in m['locations'] if p['id'] == body.get('id')), None)
                    shape = int(body.get('shape', 0))
                    if room is None or not 0 <= shape < len(room.get('shapes', [])):
                        raise ValueError('Unknown room')
                    fog['operations'].append({'kind': 'room', 'id': body['id'], 'shape': shape, 'reveal': bool(body['reveal'])})
                    if body['reveal']:
                        table_tools.focus_reveal(TABLE, m, room['shapes'][shape], m.get('roomRevealPadding', 0))
                elif kind == 'brush':
                    points = body.get('points', [])
                    radius = float(body.get('radius', 35))
                    if not 1 <= radius <= max(m['width'], m['height']) or not 1 <= len(points) <= 2000:
                        raise ValueError('Invalid brush stroke')
                    checked = []
                    for p in points:
                        x, y = float(p[0]), float(p[1])
                        if not (0 <= x <= m['width'] and 0 <= y <= m['height']):
                            raise ValueError('Brush point outside map')
                        checked.append([round(x, 1), round(y, 1)])
                    fog['operations'].append({'kind': 'brush', 'points': checked, 'radius': radius, 'reveal': bool(body.get('reveal', True))})
                    if body.get('reveal', True):
                        table_tools.focus_reveal(TABLE, m, checked, radius)
                elif kind == 'undo':
                    if fog['operations']:
                        fog['operations'].pop()
                elif kind == 'reset':
                    fog['operations'] = []
                else:
                    fog['operations'].append({'kind': kind})
            elif kind == 'room-scene':
                room = next((r for r in m['locations'] if r['id'] == body.get('id')), None)
                shape = int(body.get('shape', 0))
                scene = next((s for s in (room or {}).get('scenes', []) if s['shape'] == shape), None)
                if not scene or f"{body.get('id')}:{shape}" not in revealed(m, STATE['fog'].get(m['id'], {'operations': []})):
                    raise ValueError('Reveal this room before showing its prepared scene')
                open_tab({'id': f"room-scene:{m['id']}:{room['id']}:{shape}", 'kind': 'picture', 'path': scene['path'], 'title': scene['title'],
                          'scene': {'mapId': m['id'], 'roomId': room['id'], 'shape': shape}})
            elif kind == 'room-scene-map':
                active = next((t for t in STATE.get('tabs', []) if t['id'] == STATE.get('activeTabId')), {})
                context = active.get('scene')
                if not context or not map_by_id(context['mapId'], data):
                    raise ValueError('No room scene is active')
                open_tab({'id': 'map:' + context['mapId'], 'kind': 'map', 'mapId': context['mapId'], 'locationId': context['roomId']})
                STATE.update(mapId=context['mapId'], locationId=context['roomId'])
            elif kind == 'picture':
                asset = next((a for a in data['assets'] if a['path'] == body.get('path')), None)
                if not asset or asset.get('spoiler', True) or Path(asset['path']).suffix.lower() == '.pdf':
                    raise ValueError('This asset is for DM reference only')
                open_tab({'id': 'picture:' + asset['path'], 'kind': 'picture', 'path': asset['path'], 'title': asset['title']})
            elif kind == 'map-view':
                open_tab({'id': 'map:' + m['id'], 'kind': 'map', 'mapId': m['id'], 'locationId': STATE['locationId']})
            elif kind == 'blackout':
                STATE['blackout'] = bool(body.get('value'))
            elif kind == 'ping':
                x, y = float(body['x']), float(body['y'])
                if not (0 <= x <= 1 and 0 <= y <= 1):
                    raise ValueError('Ping outside map')
                STATE['ping'] = {'x': x, 'y': y, 'at': time.time()}
            else:
                raise ValueError('Unknown action')
            save_state()
        return snapshot()

    def safe_file(root, relative):
        path = (root / relative).resolve()
        return path if path.is_relative_to(root.resolve()) and path.is_file() else None

    def update_narration(body):
        """Explicit DM edits to first-level preparation, never the live game save."""
        m = map_by_id(body.get('mapId'))
        ident = body.get('id')
        if not m or m['id'] not in WORKSPACE.catalog('narrationMaps', []) or not any(r['id'] == ident for r in m['locations']):
            raise ValueError('Choose a room configured for narration editing')
        text = body.get('readAloudGr')
        if not isinstance(text, str) or not text.strip() or len(text) > 20000:
            raise ValueError('Enter narration of 1–20000 characters')
        with LOCK:
            narration = read_json(NARRATION_FILE, {'rooms': {}})
            narration['rooms'].setdefault(ident, {})['readAloudGr'] = text.strip()
            temp = NARRATION_FILE.with_suffix('.tmp')
            temp.write_text(json.dumps(narration, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            temp.replace(NARRATION_FILE)
        return {'id': ident, 'readAloudGr': text.strip()}
    STATE = read_json(STATE_FILE, initial_state())
    return SimpleNamespace(catalog=catalog, snapshot=snapshot, action=action,
        narration=update_narration, state=STATE, table=TABLE, workspace=workspace,
        map_by_id=map_by_id, revealed=revealed, lock=LOCK)
