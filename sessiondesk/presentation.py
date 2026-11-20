"""Workspace-wide tab selection across existing, independent media sessions."""
import json

from .importer import UserError
from .workspace_modules import MODULE_ID, supported


PREPARED = 'prepared'
PREPARED_PRESENT = frozenset(('map', 'map-view', 'location', 'room-scene',
                              'room-scene-map', 'guide', 'book-section',
                              'shop-catalog', 'picture', 'tab-select'))


class Presentation:
    def __init__(self, application):
        self.app = application
        self.store = application.store
        self.active = {}
        self.order = {}

    def activate(self, wid, source, tab):
        if tab:
            self.active[wid] = (source, tab)

    def _tabs(self, wid):
        # Ignore unopened sources. Some workspaces include several large
        # reference books whose graphs need not be loaded to list player tabs.
        with self.store.db(wid) as conn:
            prepared = self.store.get(conn, 'module:' + MODULE_ID)
            imports = [key.split(':', 1)[1] for key, raw in conn.execute(
                "SELECT key,value FROM documents WHERE key LIKE 'session:%' ORDER BY key")
                if json.loads(raw)['tabs']]
        tabs, selected = [], {}
        if prepared and supported(prepared):
            try:
                state = self.app.prepared(wid).runtime.snapshot(player=True)
            except (OSError, ValueError):
                # Unavailable local prepared files must not block independent imports.
                state = None
            if state is not None:
                selected[PREPARED] = state.get('activeTabId')
                tabs.extend({'source': PREPARED, 'id': tab['id'], 'title': tab['title']}
                            for tab in state['tabs'])
        for aid in imports:
            state = self.store.session(wid, aid, player=True)
            selected[aid] = state['active']
            tabs.extend({'source': aid, 'id': tab['id'], 'title': tab['name']}
                        for tab in state['tabs'])
        return tabs, selected

    def _snapshot(self, wid):
        tabs, selected = self._tabs(wid)
        items = {(tab['source'], tab['id']): tab for tab in tabs}
        order = [key for key in self.order.get(wid, ()) if key in items]
        order.extend(key for key in items if key not in order)
        self.order[wid] = order
        active = self.active.get(wid)
        if active not in items and order:
            candidate = (order[0][0], selected.get(order[0][0]))
            active = candidate if candidate in items else order[0]
        if not order:
            active = None
        return {'tabs': [items[key] for key in order],
                'active': dict(source=active[0], id=active[1]) if active else None}

    def snapshot(self, wid):
        with self.store.lock:
            return self._snapshot(wid)

    def action(self, wid, body):
        with self.store.lock:
            state = self._snapshot(wid)
            action = body.get('action')
            if action == 'close_all':
                for source in dict.fromkeys(tab['source'] for tab in state['tabs']):
                    self._apply(wid, source, 'close_all')
                self.active.pop(wid, None)
                return self._snapshot(wid)
            source, media = body.get('source'), body.get('id')
            if action not in ('activate', 'close') or not any(
                    tab['source'] == source and tab['id'] == media for tab in state['tabs']):
                raise UserError('Choose an open presentation tab.')
            self._apply(wid, source, action, media)
            if action == 'activate':
                self.activate(wid, source, media)
            elif state['active'] == {'source': source, 'id': media}:
                after = self._snapshot(wid)
                if active := after['active']:
                    self._apply(wid, active['source'], 'activate', active['id'])
                    self.activate(wid, active['source'], active['id'])
            return self._snapshot(wid)

    def _apply(self, wid, source, action, media=None):
        if source == PREPARED:
            kind = {'activate': 'tab-select', 'close': 'tab-close', 'close_all': 'tab-close-all'}[action]
            self.app.prepared(wid).api('/api/player-action', 'POST', {'action': kind, 'id': media}, {}, True)
        else:
            self.store.session_action(wid, source, {'action': action, 'media': media}, player=True)
