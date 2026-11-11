"""Temporary shared table tokens and reveal focus; never written to campaign saves."""
import json
import math
import uuid


def initial():
    return {'version': 0, 'tokens': {}, 'focus': {}, 'counters': {}}


def templates(character_root, art):
    party = []
    for item in art.get('party', []):
        path = character_root / item['characterId'] / 'character.json'
        if path.is_file():
            record = json.loads(path.read_text(encoding='utf-8-sig'))
            party.append({'id': 'pc:' + item['characterId'], 'kind': 'pc',
                          'name': record['name'], 'image': item['image'], 'color': item['color']})
    return party + art.get('foes', [])


def inside(x, y, polygon):
    hit = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            hit = not hit
    return hit


def distance(x, y, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = max(0, min(1, ((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.hypot(x-a[0]-t*dx, y-a[1]-t*dy)


def visible(m, fog, x, y):
    if not (0 <= x < m['width'] and 0 <= y < m['height']):
        return False
    if m['kind'] != 'dungeon':
        return True
    def room_hit(room, index, reveal):
        shape = room['shapes'][index]
        if inside(x, y, shape):
            return True
        if not reveal or not m.get('roomRevealPadding'):
            return False
        # Same calibrated wall collar as the canvas; neighboring room floors stay hidden.
        if any(inside(x, y, other) for r in m['locations'] for other in r['shapes'] if other is not shape):
            return False
        return any(distance(x, y, a, b) <= m['roomRevealPadding'] for a, b in zip(shape, shape[1:] + shape[:1]))
    shown = any(room_hit(r, i, True) for r in m['locations'] if r['id'] in m.get('initialRevealed', []) for i in range(len(r['shapes'])))
    for op in fog.get('operations', []):
        if op['kind'] in ('all', 'cover'):
            shown = op['kind'] == 'all'
        elif op['kind'] == 'room':
            room = next((r for r in m['locations'] if r['id'] == op['id']), None)
            if room and room_hit(room, op.get('shape', 0), op['reveal']):
                shown = op['reveal']
        elif op['kind'] == 'brush':
            points = op['points']
            segments = list(zip(points, points[1:])) or [(points[0], points[0])]
            if any(distance(x, y, a, b) <= op['radius'] for a, b in segments):
                shown = op['reveal']
    return shown


def point(body, m):
    x, y = float(body['x']), float(body['y'])
    if not math.isfinite(x) or not math.isfinite(y) or not (0 <= x < m['width'] and 0 <= y < m['height']):
        raise ValueError('Token point outside map')
    return round(x, 1), round(y, 1)


def apply(session, body, m, fog, catalog, player=False):
    if m['kind'] != 'dungeon':
        raise ValueError('Tokens are available on dungeon maps')
    kind = body['action']
    tokens = session['tokens'].setdefault(m['id'], [])
    by_id = {t['id']: t for t in catalog}
    if kind in ('token-add', 'token-party'):
        x, y = point(body, m)
        if kind == 'token-party' or player:
            if not visible(m, fog, x, y):
                raise ValueError('Place party tokens on revealed floor')
        choices = [t for t in catalog if t['kind'] == 'pc'] if kind == 'token-party' else [by_id.get(body.get('templateId'))]
        if not choices or any(t is None for t in choices):
            raise ValueError('Choose a token from the picker')
        if player and any(t['kind'] != 'pc' for t in choices):
            raise ValueError('Only the DM places enemies')
        if len(tokens) + len(choices) > 80:
            raise ValueError('Remove some tokens first (80 per map)')
        spacing = float(body.get('spacing', 45))
        if not math.isfinite(spacing) or not 1 <= spacing <= max(m['width'], m['height']):
            raise ValueError('Invalid party spacing')
        positions = [(x, y)]
        if kind == 'token-party':
            for size in (1, .65, .35):
                positions.extend((x+dx*spacing*size, y+dy*spacing*size) for dx, dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)) if visible(m, fog, x+dx*spacing*size, y+dy*spacing*size))
        for i, template in enumerate(choices):
            token = next((t for t in tokens if t['templateId'] == template['id']), None) if template['kind'] == 'pc' else None
            if token is None:
                counter = session['counters'].setdefault(m['id'], {})
                counter[template['id']] = counter.get(template['id'], 0) + 1
                label = template['name'] + (' ' + str(counter[template['id']]) if template['kind'] == 'foe' else '')
                token = {**template, 'id': uuid.uuid4().hex, 'templateId': template['id'], 'name': label}
                tokens.append(token)
            token['x'], token['y'] = positions[i % len(positions)]
    elif kind in ('token-move', 'token-remove'):
        token = next((t for t in tokens if t['id'] == body.get('id')), None)
        if not token:
            raise ValueError('Token no longer on this map')
        if player and token['kind'] != 'pc':
            raise ValueError('Only the DM moves or removes enemies')
        if kind == 'token-remove':
            tokens.remove(token)
        else:
            x, y = point(body, m)
            if player and not visible(m, fog, x, y):
                raise ValueError('Move party tokens on revealed floor')
            token.update(x=x, y=y)
    elif kind == 'token-clear':
        scope = body.get('scope', 'all')
        if scope not in ('all', 'pc', 'foe') or (player and scope != 'pc'):
            raise ValueError('Choose which tokens to remove')
        session['tokens'][m['id']] = [t for t in tokens if scope != 'all' and t['kind'] != scope]
    else:
        raise ValueError('Unknown token action')
    session['version'] += 1


def focus_reveal(session, m, points, radius=0):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    session['version'] += 1
    session['focus'][m['id']] = {'revision': session['version'], 'mapId': m['id'],
                               'x': min(xs)-radius, 'y': min(ys)-radius,
                               'w': max(xs)-min(xs)+radius*2, 'h': max(ys)-min(ys)+radius*2}
