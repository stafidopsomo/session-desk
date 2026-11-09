"""Loopback HTTP with per-instance DM/player capabilities and bounded routes."""
import base64
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import parse_qs, urlsplit
import uuid

from . import __version__
from .importer import Library, MAX_IMAGE, UserError
from .library_setup import LibrarySetup
from .transfers import ACTIVE, CHUNK, MAX_BACKUP, check_cancel, staging, remove_staging, recover_staging

STATIC = Path(__file__).parent / "static"


class Application:
    def __init__(self, store):
        self.store = store
        self.dm_token, self.player_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.jobs, self.ink = {}, {}
        self.clients = {}
        self.no_clients_since = None
        self.started = time.monotonic()
        self.setup = LibrarySetup(store.root)
        self.lock = threading.RLock()
        self.server = None
        self.active_downloads = 0
        self.recovered = 0
        self.transfer_root = store.root / 'transfers'

    def _new_job(self, kind, state='running'):
        with self.lock:
            if any(x['state'] in ACTIVE for x in self.jobs.values()):
                raise UserError('Another operation is running. Wait or cancel it first.')
            jid = str(uuid.uuid4())
            event = threading.Event()
            job = {"id": jid, "kind": kind, "state": state, "cancel": event,
                   "message": "Starting " + kind, "done": 0, "total": 0}
            self.jobs[jid] = job
            return job

    def public_job(self, job):
        keys = ('id', 'kind', 'state', 'message', 'done', 'total', 'result', 'error', 'error_code')
        return {k: job[k] for k in keys if k in job} | {'cancel_requested': job['cancel'].is_set()}

    def _clean_job(self, job):
        with self.lock:
            folder = job.pop('folder', None)
        if folder is not None:
            remove_staging(self.transfer_root, folder, '_transfer-')

    def _run_job(self, job, operation):
        event, kind = job['cancel'], job['kind']
        def progress(message, done=0, total=0):
            with self.lock:
                job.update(message=message, done=done, total=total)

        def run():
            try:
                result = operation(event, job, progress)
                if kind != 'export':
                    self._clean_job(job)
                with self.lock:
                    job.update(state="complete", result=result)
            except Exception as exc:
                self._clean_job(job)
                with self.lock:
                    job.update(state="cancelled" if event.is_set() else "failed",
                               error=str(exc) if isinstance(exc, UserError) else
                               "Operation stopped. Check source files, folder permissions and available space.",
                               error_code=kind.upper() + "_" + type(exc).__name__.upper())
        threading.Thread(target=run, daemon=True).start()
        return self.public_job(job)

    def start_job(self, kind, operation):
        return self._run_job(self._new_job(kind), operation)

    def _commit_job(self, event, job):
        with self.lock:
            check_cancel(event.is_set)
            job['state'] = 'committing'

    def cancel_job(self, job):
        with self.lock:
            if job['state'] in ('running', 'uploading'):
                job['cancel'].set()
                if job['state'] == 'uploading' and not job.get('upload_claimed'):
                    self._clean_job(job)
                    job['state'] = 'cancelled'
                    job['error'] = 'Backup upload cancelled.'
        return self.public_job(job)

    def start_export(self, wid):
        self.store.folder(wid)
        with self.lock:
            ready = [j for j in self.jobs.values() if j['kind'] == 'export' and j['state'] == 'complete'
                     and 'folder' in j and not j.get('downloads')]
            for old in ready[:-1]:
                self._clean_job(old)
        def operation(event, job, progress):
            job['folder'] = staging(self.transfer_root, '_transfer-')
            destination = job['folder'] / 'workspace.zip'
            self.store.backup_file(wid, destination, event.is_set, progress)
            check_cancel(event.is_set)
            return {'download': job['id'], 'filename': 'sessiondesk-workspace.zip', 'size': destination.stat().st_size}
        return self.start_job('export', operation)

    def prepare_restore(self, size):
        if type(size) is not int or not 0 < size <= MAX_BACKUP:
            raise UserError('Choose a workspace ZIP up to 1 GB plus metadata.')
        job = self._new_job('restore', 'uploading')
        try:
            job['folder'] = staging(self.transfer_root, '_transfer-')
            job.update(total=size, message='Uploading workspace backup')
            return self.public_job(job)
        except Exception:
            job['state'] = 'failed'
            raise

    def receive_restore(self, jid, input_stream, length):
        with self.lock:
            job = self.jobs.get(jid)
            if not job or job['kind'] != 'restore' or job['state'] != 'uploading' or job.get('upload_claimed'):
                raise UserError('Restore upload is not available. Start a new restore.')
            if length != job['total']:
                self.cancel_job(job)
                raise UserError('Backup upload size does not match the selected file.')
            job['upload_claimed'] = True
        try:
            path = job['folder'] / 'upload.zip'
            received = 0
            with path.open('xb') as output:
                while received < length:
                    check_cancel(job['cancel'].is_set)
                    chunk = input_stream.read(min(CHUNK, length - received))
                    if not chunk:
                        raise UserError('Backup upload was interrupted. Retry with the same ZIP.')
                    output.write(chunk)
                    received += len(chunk)
                    with self.lock:
                        job['done'] = received
            check_cancel(job['cancel'].is_set)
            with self.lock:
                job.update(state='running', message='Validating workspace backup', done=0)
            return self._run_job(job, lambda event, current, progress: self.store.restore_file(
                path, event.is_set, progress, lambda: self._commit_job(event, current)))
        except Exception as exc:
            self._clean_job(job)
            with self.lock:
                job.update(state='cancelled' if job['cancel'].is_set() else 'failed',
                           error=str(exc) if isinstance(exc, UserError) else 'Backup upload stopped. Retry the file.')
            raise

    @contextmanager
    def download(self, jid):
        with self.lock:
            job = self.jobs.get(jid)
            if not job or job['kind'] != 'export' or job['state'] != 'complete' or 'folder' not in job:
                raise UserError('Backup is no longer cached. Export it again.')
            job['downloads'] = job.get('downloads', 0) + 1
            self.active_downloads += 1
            file = job['folder'] / 'workspace.zip'
        try:
            yield file
        finally:
            with self.lock:
                self.active_downloads -= 1
                job['downloads'] -= 1
                if job.get('discard') and not job['downloads']:
                    self._clean_job(job)

    def recover(self):
        self.recovered = self.store.recover_interrupted_restores() + recover_staging(self.transfer_root, '_transfer-')

    def close(self):
        for job in list(self.jobs.values()):
            if job['state'] in ACTIVE:
                self.cancel_job(job)
            elif not job.get('downloads'):
                self._clean_job(job)

    def start_import(self, payload):
        library = Library(payload.get("path", ""), payload.get("images"))
        self.store.folder(payload["workspace"])
        def operation(event, job, progress):
            fetcher = self.setup.fetcher(library)
            progress("Reading chapters and downloading missing adventure images" if fetcher else "Reading chapters and local images")
            graph, blobs = library.load(payload["source"], event.is_set, fetcher)
            self._commit_job(event, job)
            progress("Saving imported adventure")
            return self.store.import_graph(payload["workspace"], graph, blobs)
        return self.start_job("import", operation)

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
            for job in self.jobs.values():
                self.cancel_job(job)
            return not self.active_downloads and not any(j['state'] in ACTIVE for j in self.jobs.values())

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
                self.clients[client] = {"seen": time.monotonic(), "closed": path.endswith("close")}
            return {"ok": True}
        if path == "/api/bootstrap":
            return {"version": __version__, "workspaces": store.listing(),
                    "ai": {"enabled": False, "available": False}, "player_token": self.player_token, 'recovered_operations': self.recovered}
        if path == "/api/workspace/create":
            return store.create(body.get("name", ""), body.get("language", "English"), body.get("rules", "Unspecified"))
        if path == "/api/workspace":
            return store.overview(body["workspace"])
        if path == "/api/adventure":
            return store.adventure(body["workspace"], body["adventure"])
        if path == "/api/library":
            return self.setup.validate(body.get("path", ""), body.get("images"))
        if path == "/api/library/options":
            return self.setup.options()
        if path == "/api/library/install":
            return self.start_job("install", lambda event, job, progress: self.setup.install(
                body.get("location", ""), body.get("include_images") is True, event.is_set, progress,
                on_commit=lambda: self._commit_job(event, job)))
        if path == "/api/import/start":
            return self.start_import(body)
        if path == '/api/backup/export/start':
            return self.start_export(body['workspace'])
        if path == '/api/backup/restore/start':
            return self.prepare_restore(body.get('size'))
        if path == '/api/job/discard':
            with self.lock:
                job = self.jobs.get(body.get('job'))
                if job and job['state'] not in ACTIVE:
                    job['discard'] = True
                    if not job.get('downloads'):
                        self._clean_job(job)
            return {'ok': True}
        if path in ("/api/import/status", "/api/import/cancel", '/api/job/status', '/api/job/cancel'):
            with self.lock:
                job = self.jobs.get(body.get("job"))
                if not job:
                    raise UserError("Import job not found. Re-import is safe after a restart.")
                if path.endswith('cancel'):
                    return self.cancel_job(job)
                return self.public_job(job)
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
            with self.lock:
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                try:
                    title = "Choose parent folder for the new local copy" if body.get("purpose") == "install" else "Select your local source library"
                    return {"path": filedialog.askdirectory(parent=root, title=title)}
                finally:
                    root.destroy()
        if path == "/api/quit":
            with self.lock:
                if self.active_downloads or any(j['state'] in ACTIVE for j in self.jobs.values()):
                    raise UserError('Wait for the current operation/download to finish, or cancel it before quitting.')
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return {"closed": True}
        raise UserError("Unknown API route.")


def make_server(app, port=0):
    class Handler(BaseHTTPRequestHandler):
        server_version = "SessionDesk"

        def log_message(self, *_):
            pass  # Never log URLs, tokens, private source text or local paths.

        def send(self, code, data, mime="application/json", attachment=False):
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
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            if attachment:
                self.send_header("Content-Disposition", 'attachment; filename="workspace-backup.zip"')
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
                if self.command == "GET" and path in ("/", "/app.js", "/book.js", "/style.css", "/icon.svg"):
                    filename = "index.html" if path == "/" else path[1:]
                    mime = {"index.html": "text/html", "app.js": "text/javascript", "book.js": "text/javascript", "style.css": "text/css", "icon.svg": "image/svg+xml"}[filename]
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
                    with app.download(jid) as file:
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
                    return self.send(200, file, mime)
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
                    return self.send(200, app.receive_restore(jid, BodyReader(), length))
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

        do_GET = dispatch
        do_POST = dispatch

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    app.server = server
    return server
