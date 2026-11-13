"""Loopback HTTP with per-instance DM/player capabilities and bounded routes."""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
import subprocess
import sys
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import parse_qs, urlsplit, unquote
import uuid

from . import __version__
from .importer import Library, MAX_IMAGE, UserError, confined
from .library_setup import LibrarySetup
from .updates import Updater, activate_application
from .preferences import Preferences
from .jobs import TransferJobs
from .transfers import CHUNK, MAX_BACKUP

STATIC = Path(__file__).parent / "static"


class Application:
    def __init__(self, store):
        self.store = store
        self.dm_token, self.player_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.ink = {}
        self.clients = {}
        self.no_clients_since = None
        self.started = time.monotonic()
        self.setup = LibrarySetup(store.root)
        self.preferences = Preferences(store.root)
        self.lock = threading.RLock()
        self.picker_lock = threading.Lock()
        self.server = None
        self.recovered = 0
        self.transfers = TransferJobs(store)
        self.prepared_cache = {}
        self.updater = Updater(store.root)
        self.update_candidate = None
        self.pending_update = None

    def recover(self):
        self.recovered = self.transfers.recover() + self.updater.recover()

    def close(self):
        self.transfers.close()


    def start_import(self, payload):
        library = Library(payload.get("path", ""), payload.get("images"))
        self.store.folder(payload["workspace"])
        def operation(event, job, progress):
            fetcher = self.setup.fetcher(library)
            progress("Reading chapters and downloading missing adventure images" if fetcher else "Reading chapters and local images")
            graph, blobs = library.load(payload["source"], event.is_set, fetcher)
            self.transfers.commit(event, job)
            self.remember_source(library, payload.get("images"), payload["workspace"])
            progress("Saving imported adventure")
            return self.store.import_graph(payload["workspace"], graph, blobs)
        return self.transfers.start_job("import", operation)

    def prepared(self, wid):
        from .prepared import Prepared
        settings = self.source_settings()
        path = settings.get(wid)
        with self.store.lock:
            cached = self.prepared_cache.get(wid)
            if cached is None or cached[0] != path:
                cached = (path, Prepared(self.store, wid, path))
                self.prepared_cache[wid] = cached
            return cached[1]

    def source_settings(self):
        file = self.store.root / 'local-sources.json'
        if file.is_symlink():
            raise UserError('Source preferences cannot be linked.')
        return json.loads(file.read_text(encoding='utf-8')) if file.is_file() else {}

    def connect_source(self, wid, path):
        self.store.folder(wid)
        library = Library(path)
        if library.root.name.lower() == 'data' and (library.root.parent / library.root.name) == library.data:
            library = Library(library.root.parent)
        info = library.validate()
        if not (library.data / 'book/book-phb.json').is_file():
            raise UserError('Choose a complete local 2014 library with the Player’s Handbook data.')
        if info['version'] and not str(info['version']).startswith('1.'):
            raise UserError('Choose the 2014 source copy for this campaign’s rules profile.')
        with self.store.lock:
            settings = self.source_settings()
            settings[wid] = str(library.root)
            file = self.store.root / 'local-sources.json'
            temp = file.with_suffix('.tmp')
            if temp.is_symlink():
                raise UserError('Source preference staging cannot be linked.')
            temp.write_text(json.dumps(settings), encoding='utf-8')
            temp.replace(file)
            self.prepared_cache.pop(wid, None)
            from .prepared_rules import database
            database.cache_clear()
        return {'connected': True, 'version': info['version']}

    def remember_source(self, library, images=None, workspace=None):
        # Preferences must never turn a completed import into a failed job.
        try:
            selection = {'path': str(library.root), 'images': str(images or '')}
            self.preferences.update('library', selection)
            if workspace:
                sources = self.preferences.read().get('sources', {})
                sources[workspace] = selection
                self.preferences.update('sources', sources)
        except (OSError, UserError):
            pass

    def source_defaults(self):
        saved = self.preferences.read().get('library', {})
        candidates = [saved] if saved.get('path') else []
        candidates += [{'path': p, 'images': ''} for p in reversed(list(self.setup.config()))]
        candidates += [{'path': p, 'images': ''} for p in self.source_settings().values()]
        for candidate in candidates:
            try:
                lib = Library(candidate['path'], candidate.get('images') or None)
                lib.validate()
                return {'path': str(lib.root), 'images': candidate.get('images',''), 'available': True}
            except (OSError, ValueError, UserError):
                continue
        return {'path': '', 'images': '', 'available': False}

    def reference_file(self, wid, name):
        self.store.folder(wid)
        selection = self.preferences.read().get('sources', {}).get(wid, {})
        path = selection.get('path') or self.source_settings().get(wid) or self.source_defaults()['path']
        if not path:
            raise UserError('Choose a local 5e.tools library through Add adventure first.')
        library = Library(path, selection.get('images') or None)
        if library.root.name.lower() == 'data':
            library = Library(library.root.parent, selection.get('images') or None)
        if name.startswith('img/'):
            file = confined(library.images.resolve(), name[4:])
        else:
            file = confined(library.root, name)
        if (not file.is_file() or '.git' in file.parts or file.suffix.lower() in
                ('.py','.exe','.bat','.cmd','.ps1','.dll','.sqlite3')):
            raise UserError('Reference resource not found in this library.')
        return file, mimetypes.guess_type(file.name)[0] or 'application/octet-stream'

    def restart_update(self):
        if not getattr(sys, 'frozen', False) or not self.pending_update:
            raise UserError('Install an update in the packaged app before restarting.')
        executable = Path(self.pending_update['executable']).resolve()
        if not executable.is_relative_to((self.store.root / 'applications').resolve()) or not executable.is_file():
            raise UserError('The staged update is unavailable. Download it again.')
        self.transfers.request_close()
        try:
            activate_application(self.store.root,executable)
            subprocess.Popen([str(executable), '--data-dir', str(self.store.root),
                '--wait-for-pid', str(os.getpid())], creationflags=subprocess.CREATE_NO_WINDOW)
        except (OSError, UserError) as exc:
            with self.transfers.lock:
                self.transfers.accepting = True
            raise UserError('Unable to open the update. Your current app is still running; try restarting again.') from exc
        threading.Thread(target=self.server.shutdown, daemon=True).start()
        return {'restarting': True}

    def should_exit(self, now=None):
        now = time.monotonic() if now is None else now
        with self.lock:
            if any(not c["closed"] and now - c["seen"] < 90 for c in self.clients.values()):
                self.no_clients_since = None
                return False
            if not self.clients and now - self.started < 120:
                return False
            if self.no_clients_since is None:
                self.no_clients_since = now
            if now - self.no_clients_since < 8:
                return False
            return self.transfers.cancel_and_idle()

    def api(self, path, body, player, method):
        store = self.store
        if path.startswith("/api/ai"):
            raise UserError("AI is unavailable in this build. No provider is connected or invoked.")
        if player and path not in ("/api/player", "/api/session/action", "/api/ink", "/api/heartbeat", "/api/client/ping", "/api/client/close"):
            raise PermissionError("This route is DM-only.")
        if path == "/api/heartbeat":
            return {"version": __version__, "ai": {"enabled": False, "available": False}}
        if path in ("/api/client/ping", "/api/client/close"):
            client = str(uuid.UUID(body["client"]))
            with self.lock:
                self.clients[client] = {"seen": time.monotonic(), "closed": path.endswith("close"),
                    "role": "player" if player else "dm", "workspace": body.get("workspace"),
                    "adventure": body.get("adventure")}
            return {"ok": True}
        if path == "/api/bootstrap":
            return {"version": __version__, "workspaces": store.listing(),
                    "ai": {"enabled": False, "available": False}, "player_token": self.player_token, 'recovered_operations': self.recovered}
        if path == "/api/player/presence":
            with self.lock:
                return {'online': any(c.get('role') == 'player' and not c['closed']
                    and c.get('workspace') == body.get('workspace')
                    and c.get('adventure') == body.get('adventure')
                    and time.monotonic() - c['seen'] < 20 for c in self.clients.values())}
        if path == '/api/tutorial':
            self.store.folder(body['workspace'])
            if body.get('adventure'):
                self.store.adventure(body['workspace'], body['adventure'])
            return self.preferences.tutorial(body['workspace'], body.get('phase'),
                body.get('adventure'), body.get('action','get'))
        if path == '/api/update/check':
            candidate = self.updater.check()
            self.update_candidate = candidate
            return candidate | {'supported': bool(getattr(sys,'frozen',False))}
        if path == '/api/update/install':
            if not getattr(sys,'frozen',False):
                raise UserError('In-app installation is available in the Windows EXE.')
            candidate = self.update_candidate or self.updater.check()
            if not candidate.get('available'):
                raise UserError('No newer release is available.')
            def install(event, job, progress):
                result = self.updater.install(candidate, event.is_set, progress,
                    lambda: self.transfers.commit(event,job))
                self.pending_update = result
                return result
            return self.transfers.start_job('update', install)
        if path == '/api/update/restart':
            return self.restart_update()
        if path == "/api/workspace/create":
            return store.create(body.get("name", ""), body.get("language", "English"), body.get("rules", "Unspecified"))
        if path == "/api/workspace":
            return store.overview(body["workspace"]) | {'rules_connected': body['workspace'] in self.source_settings()}
        if path == '/api/campaign/open':
            self.prepared(body['workspace'])
            return {'url': f"/campaign/{body['workspace']}/{self.dm_token}/"}
        if path == '/api/campaign/source':
            return self.connect_source(body['workspace'], body.get('path', ''))
        if path == '/api/module/files':
            from .workspace_modules import MODULE_ID, sync
            with store.lock, store.db(body['workspace']) as conn:
                sync(store, body['workspace'], conn)
                module = store.get(conn, 'module:' + MODULE_ID)
            if not module:
                raise UserError('No prepared files in this workspace.')
            return {'files': [{'path': name, **record} for name, record in module['files'].items()],
                    'original': module.get('original')}
        if path == "/api/adventure":
            graph = store.adventure(body["workspace"], body["adventure"])
            graph['reference_base'] = f"/reference/{body['workspace']}/{self.dm_token}/"
            return graph
        if path == "/api/library/defaults":
            return self.source_defaults()
        if path == "/api/library":
            result = self.setup.validate(body.get("path", ""), body.get("images"))
            self.remember_source(Library(body["path"]), body.get("images"), body.get("workspace"))
            return result
        if path == "/api/library/options":
            return self.setup.options()
        if path == "/api/library/install":
            return self.transfers.start_job("install", lambda event, job, progress: self.setup.install(
                body.get("location", ""), body.get("include_images") is True, event.is_set, progress,
                on_commit=lambda: self.transfers.commit(event, job)))
        if path == "/api/import/start":
            return self.start_import(body)
        if path == '/api/backup/export/start':
            return self.transfers.start_export(body['workspace'])
        if path == '/api/backup/restore/start':
            return self.transfers.prepare_restore(body.get('size'))
        if path == '/api/job/discard':
            return self.transfers.discard(body.get('job'))
        if path in ("/api/import/status", "/api/import/cancel", '/api/job/status', '/api/job/cancel'):
            return self.transfers.status(body.get('job'), cancel=path.endswith('cancel'))
        if path == "/api/prepare":
            return store.prepare(body["workspace"], body["adventure"], body["entry"], body)
        if path == "/api/pin":
            return {"pins": store.pin(body["workspace"], body["adventure"], body.get("kind"), body.get("id"), body.get("enabled"))}
        if path == "/api/media/review":
            return store.review_map(body["workspace"], body["adventure"], body["media"], body)
        if path == "/api/media/add":
            data = base64.b64decode(body["data"], validate=True)
            if len(data) > MAX_IMAGE:
                raise UserError("Image exceeds 48 MB.")
            return store.add_picture(body["workspace"], body["adventure"], body["name"], data)
        if path == "/api/session":
            return store.session(body["workspace"], body["adventure"])
        if path == "/api/player":
            return store.session(body["workspace"], body["adventure"], player=True)
        if path == "/api/session/action":
            result = store.session_action(body["workspace"], body["adventure"], body, player)
            return store.session(body["workspace"], body["adventure"], True) if player else result
        if path == "/api/ink":
            # Temporary drawing only: never stored in a database/backup. Shared by both windows.
            state = store.session(body["workspace"], body["adventure"], True)
            if body.get("media") not in {x["id"] for x in state["tabs"]}:
                raise UserError("Drawing tab is not open.")
            key = (body["workspace"], body["adventure"], body["media"])
            with self.lock:
                ink = self.ink.setdefault(key, [])
                if body.get("action") == "clear":
                    ink.clear()
                elif body.get("action") == "draw":
                    points, color = body.get("points"), body.get("color")
                    if color not in ("#f3c76a", "#e67070", "#69b8ff", "#8bd6b1"):
                        raise UserError("Invalid pen color.")
                    if not isinstance(points, list) or not 1 <= len(points) <= 1000:
                        raise UserError("Invalid pen stroke.")
                    media = next(x for x in state["tabs"] if x["id"] == body["media"])
                    for p in points:
                        if (not isinstance(p, list) or len(p) != 2 or any(type(n) not in (int, float) for n in p)
                                or not 0 <= p[0] <= media["width"] or not 0 <= p[1] <= media["height"]):
                            raise UserError("Pen stroke is outside the image.")
                    if len(ink) >= 2000:
                        raise UserError("Clear temporary drawings before adding more.")
                    ink.append({"points": points, "color": color})
                return {"strokes": list(ink)}
        if path == "/api/pick-folder":
            # Native dialog is invoked only by the user's Choose folder action.
            import tkinter as tk
            from tkinter import filedialog
            with self.picker_lock:
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                try:
                    title = "Choose parent folder for the new local copy" if body.get("purpose") == "install" else "Select your local source library"
                    return {"path": filedialog.askdirectory(parent=root, title=title)}
                finally:
                    root.destroy()
        if path == "/api/quit":
            self.transfers.request_close()
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return {"closed": True}
        raise UserError("Unknown API route.")


def make_server(app, port=0):
    class Handler(BaseHTTPRequestHandler):
        server_version = "SessionDesk"

        def log_message(self, *_):
            pass  # Never log URLs, tokens, private source text or local paths.

        def send(self, code, data, mime="application/json", attachment=False, csp=None, filename=None):
            # Drain small rejected POSTs before closing: Windows can otherwise reset
            # the socket before the client receives the authentication error.
            if code >= 400 and self.command == "POST":
                try:
                    length = getattr(self, 'body_remaining', None)
                    if length is None:
                        length = 0 if getattr(self, 'body_consumed', False) else int(self.headers.get('Content-Length', '0'))
                    if 0 < length <= 65536:
                        self.connection.settimeout(2)
                        self.rfile.read(length)
                except (OSError, ValueError):
                    pass
            file = data if isinstance(data, Path) else None
            if file is None and not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith(("text/", "application/json")) else ""))
            self.send_header("Content-Length", str(file.stat().st_size if file is not None else len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", csp or "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            if attachment:
                safe_name = ''.join(c for c in (filename or 'workspace-backup.zip') if c.isascii() and c.isalnum() or c in '.-_')[:100] or 'attachment.bin'
                self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"')
            self.end_headers()
            try:
                if file is None:
                    self.wfile.write(data)
                else:
                    with file.open('rb') as source:
                        while chunk := source.read(CHUNK):
                            self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def dispatch(self):
            self.body_consumed = False
            self.body_remaining = None
            try:
                origin = f"http://127.0.0.1:{self.server.server_port}"
                if self.headers.get("Host") != origin.removeprefix("http://"):
                    return self.send(403, {"error": "Invalid host."})
                parsed = urlsplit(self.path)
                path, query = parsed.path, parse_qs(parsed.query)
                if path.startswith('/reference/') and self.command == 'GET':
                    parts = path.split('/',4)
                    if len(parts) != 5 or not secrets.compare_digest(parts[3], app.dm_token):
                        raise PermissionError('Book references are DM-only.')
                    file, mime = app.reference_file(parts[2], unquote(parts[4]))
                    csp = "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'self'"
                    return self.send(200,file,mime,csp=csp)
                if path.startswith('/campaign/'):
                    return self.prepared_dispatch(path, query, origin)
                if self.command == "GET" and path in ("/", "/app.js", "/book.js", "/home.js", "/home.css", "/hero.svg", "/style.css", "/icon.svg"):
                    filename = "index.html" if path == "/" else path[1:]
                    mime = {"index.html": "text/html", "app.js": "text/javascript", "book.js": "text/javascript", "style.css": "text/css", "icon.svg": "image/svg+xml", "home.js":"text/javascript", "home.css":"text/css", "hero.svg":"image/svg+xml"}[filename]
                    return self.send(200, (STATIC / filename).read_bytes(), mime)
                token = self.headers.get("Authorization", "").removeprefix("Bearer ")
                if path.startswith(("/asset/", '/download/')):
                    token = query.get("token", [token])[0]
                dm = secrets.compare_digest(token, app.dm_token)
                player = secrets.compare_digest(token, app.player_token)
                if not dm and not player:
                    return self.send(401, {"error": "Open this window from the application launcher."})
                if self.command == 'GET' and path.startswith('/download/'):
                    if not dm:
                        raise PermissionError('Workspace backup downloads are DM-only.')
                    jid = str(uuid.UUID(path.removeprefix('/download/')))
                    with app.transfers.download(jid) as file:
                        return self.send(200, file, 'application/zip', attachment=True)
                if self.command == "GET" and path.startswith("/asset/"):
                    parts = path.split("/")
                    if len(parts) != 4:
                        raise UserError("Invalid asset route.")
                    _, _, wid, digest = parts
                    if player:
                        aid = query.get("adventure", [""])[0]
                        visible = app.store.session(wid, aid, True)
                        if digest not in {x["asset"] for x in visible["tabs"]}:
                            raise PermissionError("Image is not presented.")
                    file, mime = app.store.asset(wid, digest)
                    attachment = mime not in ('image/png','image/jpeg','image/webp','image/gif')
                    if attachment and not dm:
                        raise PermissionError('Workspace attachments are DM-only.')
                    return self.send(200, file, mime, attachment=attachment,
                                     filename=query.get('name',['attachment.bin'])[0])
                if self.command != "POST" or not path.startswith("/api/"):
                    return self.send(404, {"error": "Not found."})
                if self.headers.get("Origin") != origin:
                    return self.send(403, {"error": "Same-origin requests only."})
                if path.startswith('/api/backup/upload/'):
                    if not dm:
                        raise PermissionError("DM-only restore.")
                    length = int(self.headers.get("Content-Length", "0"))
                    if self.headers.get_content_type() != "application/zip" or not 0 < length <= MAX_BACKUP:
                        return self.send(413, {"error": "Expected a workspace ZIP up to 1 GB plus metadata."})
                    jid = str(uuid.UUID(path.removeprefix('/api/backup/upload/')))
                    self.connection.settimeout(15)
                    self.body_consumed = True
                    self.body_remaining = length
                    handler = self
                    class BodyReader:
                        def read(self, count):
                            chunk = handler.rfile.read(count)
                            handler.body_remaining -= len(chunk)
                            return chunk
                    return self.send(200, app.transfers.receive_restore(jid, BodyReader(), length))
                if self.headers.get_content_type() != "application/json":
                    raise UserError("Expected JSON.")
                length = int(self.headers.get("Content-Length", "0"))
                limit = 96 * 1024 * 1024 if path == "/api/media/add" else 2 * 1024 * 1024
                if not 0 < length <= limit:
                    return self.send(413, {"error": "Request exceeds size limit."})
                self.connection.settimeout(30)
                self.body_consumed = True
                body = json.loads(self.rfile.read(length), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite number")))
                if not isinstance(body, dict):
                    raise UserError("Expected a JSON object.")
                result = app.api(path, body, not dm, self.command)
                self.send(200, result)
            except PermissionError as exc:
                self.send(403, {"error": str(exc)})
            except (UserError, KeyError, TypeError, ValueError) as exc:
                self.send(400, {"error": str(exc) if isinstance(exc, UserError) else "Invalid request."})
            except Exception:
                self.send(500, {"error": "Operation failed. Check available disk space and source/workspace files. Existing data was not reset."})

        def prepared_dispatch(self, path, query, origin):
            from .prepared import static, rewrite, unmount
            parts = path.split('/', 4)
            if len(parts) != 5:
                raise UserError('Invalid prepared-campaign URL.')
            _, _, wid, token, tail = parts
            dm = secrets.compare_digest(token, app.dm_token)
            player = secrets.compare_digest(token, app.player_token)
            if not dm and not player:
                return self.send(401, {'error': 'Open this workspace from Session Desk.'})
            base = f'/campaign/{wid}/{token}'
            player_base = f'/campaign/{wid}/{app.player_token}'
            route = '/' + tail
            mount = app.prepared(wid)
            if self.command == 'POST':
                if self.headers.get('Origin') != origin or self.headers.get_content_type() != 'application/json':
                    raise PermissionError('Same-origin JSON requests only.')
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 2 * 1024 * 1024:
                    raise UserError('Invalid campaign action size.')
                self.connection.settimeout(30)
                self.body_consumed = True
                body = json.loads(self.rfile.read(length), parse_constant=lambda _: (_ for _ in ()).throw(UserError('Invalid number.')))
                if not isinstance(body, dict):
                    raise UserError('Expected a campaign action object.')
                result = mount.api(route, 'POST', unmount(body, base), query, not dm)
                return self.send(200, rewrite(result, base))
            if self.command != 'GET':
                raise PermissionError('Unsupported campaign request method.')
            if route.startswith('/api/'):
                return self.send(200, rewrite(mount.api(route,'GET',{},query,not dm),base))
            if route.startswith('/assets/'):
                file, mime, attachment = mount.file(route, not dm)
                return self.send(200,file,mime,attachment=attachment,filename=file.name)
            if route.startswith('/reference/'):
                file, mime = mount.reference(route, not dm)
                csp = "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'self'"
                return self.send(200,file,mime,csp=csp)
            pages = {'/':'index.html','/dm':'index.html','/player':'player.html','/shop':'shop.html'}
            if route in pages:
                if not dm and route in ('/','/dm'):
                    raise PermissionError('The campaign desk is DM-only.')
                name = pages[route]
            elif route.startswith('/static/'):
                name = unquote(route[len('/static/'):])
            else:
                raise UserError('Campaign page not found.')
            data, mime = static(name,base,player_base,wid,not dm)
            csp = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'"
            return self.send(200,data,mime,csp=csp)

        do_GET = dispatch
        do_POST = dispatch

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    app.server = server
    return server
