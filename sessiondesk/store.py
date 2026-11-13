"""Versioned, isolated SQLite workspaces and portable, verified backups."""
from contextlib import contextmanager
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import threading
import uuid
import zipfile

from .importer import MAX_IMAGE, UserError, image_size, polygon, enrich_book_metadata
from .transfers import CHUNK, MAX_BACKUP, MAX_METADATA, check_cancel, staging, remove_staging, recover_staging

SCHEMA = 2
ID = re.compile(r"^[a-f0-9-]{36}$")
HASH = re.compile(r"^[a-f0-9]{64}$")


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise UserError("Invalid workspace identifier.")
    return value


def string(value, maximum=100000):
    if not isinstance(value, str) or len(value) > maximum:
        raise UserError(f"Expected text up to {maximum} characters.")
    return value


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.workspaces = self.root / "workspaces"
        if self.workspaces.is_symlink():
            raise UserError("Workspace registry cannot be a symlink.")
        self.workspaces.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def folder(self, wid):
        path = self.workspaces / identifier(wid)
        if path.is_symlink() or not path.is_dir():
            raise UserError("Workspace not found.")
        if (path / "assets").is_symlink():
            raise UserError("Workspace asset directory cannot be a symlink.")
        return path

    @contextmanager
    def db(self, wid):
        folder = self.folder(wid)
        if (folder / "workspace.sqlite3").is_symlink():
            raise UserError("Workspace database cannot be a symlink.")
        conn = sqlite3.connect(folder / "workspace.sqlite3", timeout=15)
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version == 1:
                with self.lock:
                    recovery = folder / 'workspace-schema-1.sqlite3.bak'
                    if recovery.is_symlink():
                        raise UserError('Workspace recovery file cannot be linked.')
                    if not recovery.exists():
                        old = sqlite3.connect(recovery)
                        try:
                            conn.backup(old)
                        finally:
                            old.close()
                    conn.execute('BEGIN IMMEDIATE')
                    conn.execute(f'PRAGMA user_version={SCHEMA}')
                    meta = self.get(conn, 'meta', {})
                    meta['schema'] = SCHEMA
                    self.put(conn, 'meta', meta)
                    conn.commit()
                version = SCHEMA
            if version != SCHEMA:
                raise UserError("Unsupported workspace version. Use its compatible app; data was not modified.")
            with conn:
                yield conn
        finally:
            conn.close()

    def create(self, name, language="English", rules="Unspecified"):
        meta = self._metadata(name, language, rules)
        folder = staging(self.workspaces, '_restore-')
        try:
            (folder / 'assets').mkdir()
            self._initialize(folder, meta, {}, {})
            folder.replace(self.workspaces / meta['id'])
        finally:
            remove_staging(self.workspaces, folder, '_restore-')
        return meta

    @staticmethod
    def _metadata(name, language, rules):
        name = string(name, 100).strip()
        if not name:
            raise UserError("Enter a workspace name.")
        wid = str(uuid.uuid4())
        return {"id": wid, "name": name, "schema": SCHEMA,
                "language": string(language, 80), "rules": string(rules, 80)}

    def _initialize(self, folder, meta, documents, assets):
        conn = sqlite3.connect(folder / "workspace.sqlite3")
        try:
            with conn:
                conn.execute("CREATE TABLE documents (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                conn.execute("CREATE TABLE assets (hash TEXT PRIMARY KEY, mime TEXT NOT NULL, size INTEGER NOT NULL)")
                conn.execute(f"PRAGMA user_version={SCHEMA}")
                for key, value in documents.items():
                    if key != 'meta':
                        self.put(conn, key, value)
                self.put(conn, "meta", meta)
                for digest, record in assets.items():
                    conn.execute('INSERT INTO assets VALUES (?,?,?)', (digest, record['mime'], record['size']))
        finally:
            conn.close()

    @staticmethod
    def put(conn, key, value):
        conn.execute("INSERT OR REPLACE INTO documents VALUES (?,?)",
                     (key, json.dumps(value, ensure_ascii=False, allow_nan=False)))

    @staticmethod
    def get(conn, key, default=None):
        row = conn.execute("SELECT value FROM documents WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def listing(self):
        result = []
        for folder in sorted(self.workspaces.iterdir()):
            if not ID.fullmatch(folder.name) or not folder.is_dir() or folder.is_symlink():
                continue
            try:
                with self.db(folder.name) as conn:
                    result.append(self.get(conn, "meta"))
            except (UserError, sqlite3.Error):
                result.append({"id": folder.name, "name": "Workspace needs a compatible version", "unavailable": True})
        return result

    def overview(self, wid):
        with self.db(wid) as conn:
            adventures = [json.loads(row[0]) for row in conn.execute(
                "SELECT value FROM documents WHERE key LIKE 'adventure:%'")]
            modules = [{"id": key.split(':', 1)[1], **{k: value.get(k) for k in
                        ('kind', 'schema', 'enabled', 'title', 'summary')}}
                       for key, raw in conn.execute("SELECT key,value FROM documents WHERE key LIKE 'module:%'")
                       for value in [json.loads(raw)]]
            return {"meta": self.get(conn, "meta"), "modules": modules, "adventures": [
                {k: a[k] for k in ("id", "name", "source", "fingerprint")} |
                {"maps": sum(x.get("image_type") != "mapPlayer" for x in a["maps"]), "pictures": len(a["pictures"]), "warnings": len(a["warnings"])}
                for a in adventures]}

    def adventure(self, wid, aid):
        with self.db(wid) as conn:
            graph = self.get(conn, "adventure:" + identifier(aid))
            if not graph:
                raise UserError("Adventure not found in this workspace.")
            graph["preparation"] = self.get(conn, "prep:" + aid, {})
            graph["pins"] = self.get(conn, "pins:" + aid, {"items": []})["items"]
            return enrich_book_metadata(graph)

    def _write_assets(self, conn, wid, blobs):
        repaired = 0
        for digest, (mime, data) in blobs.items():
            if hashlib.sha256(data).hexdigest() != digest:
                raise UserError("Image checksum mismatch.")
            target = self.folder(wid) / "assets" / digest
            if target.is_symlink():
                raise UserError("Asset cannot be a symlink.")
            correct = False
            if target.is_file() and target.stat().st_size == len(data):
                with target.open('rb') as source:
                    checksum = hashlib.file_digest(source, 'sha256').hexdigest()
                correct = checksum == digest
            if not correct:
                temp = target.with_suffix('.tmp')
                if temp.is_symlink():
                    raise UserError('Asset temporary file cannot be a symlink.')
                try:
                    temp.write_bytes(data)
                    temp.replace(target)
                finally:
                    temp.unlink(missing_ok=True)
                repaired += 1
            conn.execute("INSERT OR REPLACE INTO assets VALUES (?,?,?)", (digest, mime, len(data)))
        return repaired

    def import_graph(self, wid, graph, blobs):
        with self.lock, self.db(wid) as conn:
            old = self.get(conn, "adventure:" + graph["id"])
            if old:
                if old["fingerprint"] == graph["fingerprint"]:
                    repaired = self._write_assets(conn, wid, blobs)
                    if old.get("book_schema", 0) >= graph.get("book_schema", 0):
                        if old.get('source_schema') != graph.get('source_schema'):
                            old['source_schema'] = graph.get('source_schema')
                            self.put(conn, 'adventure:' + graph['id'], old)
                        return {"id": graph["id"], "unchanged": True, "repaired_assets": repaired}
                    # Enrich the same snapshot without resetting manual material or session state.
                    previous = {m["id"]: m for m in old["maps"] + old["pictures"]}
                    for item in graph["maps"] + graph["pictures"]:
                        saved = previous.get(item["id"], {})
                        item["player_safe"] = saved.get("player_safe", False)
                        regions = {r["id"]: r for r in saved.get("regions", [])}
                        for region in item["regions"]:
                            if region["id"] in regions:
                                for field in ("points", "role", "verified", "boundary_origin"):
                                    if field in regions[region["id"]]:
                                        region[field] = regions[region["id"]][field]
                    graph["pictures"] += [m for m in old["pictures"] if m.get("origin") == "manual"]
                    self.put(conn, "adventure:" + graph["id"], graph)
                    return {"id": graph["id"], "unchanged": False, "enriched": True, "repaired_assets": repaired}
                raise UserError("This source changed. Import into a new workspace to preserve existing preparation/session state.")
            self._write_assets(conn, wid, blobs)
            self.put(conn, "adventure:" + graph["id"], graph)
        return {"id": graph["id"], "unchanged": False}

    def pin(self, wid, aid, kind, resource, enabled):
        with self.lock, self.db(wid) as conn:
            graph = self.get(conn, "adventure:" + identifier(aid))
            if not graph or kind not in ("entry", "media") or type(enabled) is not bool:
                raise UserError("Invalid pinned resource.")
            candidates = graph["entries"] if kind == "entry" else graph["maps"] + graph["pictures"]
            if resource not in {x["id"] for x in candidates}:
                raise UserError("Resource not found in this adventure.")
            saved = self.get(conn, "pins:" + aid, {"items": []})
            item = {"kind": kind, "id": resource}
            saved["items"] = [x for x in saved["items"] if x != item]
            if enabled:
                if len(saved["items"]) >= 64:
                    raise UserError("Unpin a resource before adding another (64 maximum).")
                saved["items"].append(item)
            self.put(conn, "pins:" + aid, saved)
            return saved["items"]

    def prepare(self, wid, aid, entry, payload):
        with self.lock, self.db(wid) as conn:
            graph = self.get(conn, "adventure:" + identifier(aid))
            if not graph or entry not in {x["id"] for x in graph["entries"]}:
                raise UserError("Source entry not found.")
            prep = self.get(conn, "prep:" + aid, {})
            status = payload.get("status", "draft")
            if status not in ("draft", "approved"):
                raise UserError("Choose draft or approved.")
            prep[entry] = {"translation": string(payload.get("translation", "")),
                           "notes": string(payload.get("notes", "")), "status": status,
                           "origin": "manual"}
            self.put(conn, "prep:" + aid, prep)
            return prep[entry]

    def review_map(self, wid, aid, mid, payload):
        with self.lock, self.db(wid) as conn:
            graph = self.get(conn, "adventure:" + identifier(aid))
            if not graph:
                raise UserError("Adventure not found.")
            item = next((x for x in graph["maps"] + graph["pictures"] if x["id"] == mid), None)
            if not item:
                raise UserError("Map/picture not found.")
            if "player_safe" in payload:
                if type(payload["player_safe"]) is not bool:
                    raise UserError("Invalid sharing review.")
                item["player_safe"] = payload["player_safe"]
            if "region" in payload:
                change = payload["region"]
                region = next((r for r in item["regions"] if r["id"] == change.get("id")), None)
                if not region:
                    raise UserError("Region not found.")
                role = change.get("role", "unknown")
                if role not in ("room", "feature", "landing", "area", "unknown"):
                    raise UserError("Unknown region role.")
                region.update(points=polygon(change.get("points"), item["width"], item["height"]),
                              role=role, verified=change.get("verified") is True,
                              boundary_origin="manual")
            # Revoking safety immediately removes that media from the player screen.
            session = self.get(conn, "session:" + aid, self.empty_session())
            if not item["player_safe"]:
                session["tabs"] = [x for x in session["tabs"] if x != mid]
                if session["active"] == mid:
                    session["active"] = next(iter(session["tabs"]), None)
                self.put(conn, "session:" + aid, session)
            self.put(conn, "adventure:" + aid, graph)
            return item

    def add_picture(self, wid, aid, name, data):
        (w, h), mime = image_size(data)
        if w * h > 100000000 or not 0 < min(w, h) or max(w, h) > 30000:
            raise UserError("Image dimensions exceed supported limits.")
        digest = hashlib.sha256(data).hexdigest()
        with self.lock, self.db(wid) as conn:
            graph = self.get(conn, "adventure:" + identifier(aid))
            if not graph:
                raise UserError("Adventure not found.")
            target = self.folder(wid) / "assets" / digest
            if target.is_symlink():
                raise UserError("Asset cannot be a symlink.")
            if not target.exists():
                temp = target.with_suffix(".tmp")
                temp.write_bytes(data)
                temp.replace(target)
            conn.execute("INSERT OR IGNORE INTO assets VALUES (?,?,?)", (digest, mime, len(data)))
            record = {"id": str(uuid.uuid4()), "name": string(name, 200), "asset": digest,
                      "width": w, "height": h, "kind": "picture", "chapter": -1,
                      "entry": None, "regions": [], "player_safe": False,
                      "source_path": "Manual import", "origin": "manual"}
            graph["pictures"].append(record)
            self.put(conn, "adventure:" + aid, graph)
            return record

    @staticmethod
    def empty_session():
        return {"tabs": [], "active": None, "fog": {}, "notes": {}, "revision": 0}

    def session(self, wid, aid, player=False):
        graph = self.adventure(wid, aid)
        with self.db(wid) as conn:
            state = self.get(conn, "session:" + aid, self.empty_session())
        if not player:
            return state
        media = {x["id"]: x for x in graph["maps"] + graph["pictures"] if x["player_safe"]}
        all_maps = {x["id"]: x for x in graph["maps"]}
        tabs = []
        for mid in state["tabs"]:
            if mid not in media:
                continue
            record = {k: media[mid][k] for k in ("id", "name", "asset", "width", "height", "kind")}
            player_map = all_maps.get(media[mid].get("player_map"))
            if player_map:
                record["asset"] = player_map["asset"]
            tabs.append(record)
        # Player serialization has an explicit allowlist: no regions, locators, book text or DM prep.
        return {"tabs": tabs, "active": state["active"],
                "fog": {k: v for k, v in state["fog"].items() if k in state["tabs"]},
                "notes": {k: v for k, v in state["notes"].items() if k in state["tabs"]},
                "revision": state["revision"]}

    def session_action(self, wid, aid, payload, player=False):
        with self.lock, self.db(wid) as conn:
            graph = self.get(conn, "adventure:" + identifier(aid))
            if not graph:
                raise UserError("Adventure not found.")
            state = self.get(conn, "session:" + aid, self.empty_session())
            action, mid = payload.get("action"), payload.get("media")
            if player and action not in ("activate", "close", "close_all"):
                raise UserError("Only the DM controls visibility and shared notes.")
            media = next((x for x in graph["maps"] + graph["pictures"] if x["id"] == mid), None)
            if action not in ("close_all",) and not media:
                raise UserError("Map/picture not found.")
            if action == "present":
                if media["kind"] == "picture" or payload.get('with_fog') is True:
                    media['player_safe'] = True
                    self.put(conn, 'adventure:' + aid, graph)
                if not media["player_safe"]:
                    raise UserError("Use Present with fog to open this map covered.")
                if mid not in state["tabs"]:
                    state["tabs"].append(mid)
                state["active"] = mid
            elif action == "activate":
                if mid not in state["tabs"]:
                    raise UserError("Tab is not open.")
                state["active"] = mid
            elif action == "close":
                state["tabs"] = [x for x in state["tabs"] if x != mid]
                if state["active"] == mid:
                    state["active"] = next(iter(state["tabs"]), None)
            elif action == "close_all":
                state["tabs"], state["active"] = [], None
            elif action == "note":
                state["notes"][mid] = string(payload.get("text", ""), 20000)
            elif action in ("fog", "reveal_region", "reset_fog", "show_map"):
                if media["kind"] != "map":
                    raise UserError("Fog only applies to maps.")
                operations = state["fog"].setdefault(mid, [])
                if action == "reset_fog":
                    state["fog"][mid] = []
                elif action == "show_map":
                    state["fog"][mid] = [{"mode": "reveal", "polygon": [[0, 0], [media["width"], 0],
                        [media["width"], media["height"]], [0, media["height"]]]}]
                elif action == "reveal_region":
                    region = next((r for r in media["regions"] if r["id"] == payload.get("region")), None)
                    if not region or not region["points"]:
                        raise UserError("Draw this room's boundary first, or use the reveal brush.")
                    operations.append({"mode": "reveal", "polygon": polygon(region["points"], media["width"], media["height"])})
                else:
                    mode = payload.get("mode")
                    if mode not in ("reveal", "hide"):
                        raise UserError("Choose reveal or hide.")
                    points = payload.get("points")
                    radius = payload.get("radius")
                    if not isinstance(points, list) or not 1 <= len(points) <= 1000:
                        raise UserError("Invalid brush stroke.")
                    if type(radius) not in (int, float) or not 1 <= radius <= 3000:
                        raise UserError("Invalid brush size.")
                    for point in points:
                        if (not isinstance(point, list) or len(point) != 2 or
                                any(type(n) not in (int, float) for n in point) or
                                not 0 <= point[0] <= media["width"] or not 0 <= point[1] <= media["height"]):
                            raise UserError("Brush stroke is outside the map.")
                    operations.append({"mode": mode, "points": points, "radius": radius})
                if len(state["fog"][mid]) > 10000:
                    raise UserError("Fog history limit reached. Back up before resetting fog.")
            else:
                raise UserError("Unknown session action.")
            state["revision"] += 1
            self.put(conn, "session:" + aid, state)
            return state

    def asset(self, wid, digest):
        if not HASH.fullmatch(digest):
            raise UserError("Invalid asset ID.")
        with self.db(wid) as conn:
            row = conn.execute("SELECT mime FROM assets WHERE hash=?", (digest,)).fetchone()
        target = self.folder(wid) / "assets" / digest
        if not row or target.is_symlink() or not target.is_file():
            raise UserError("Asset missing. Restore an asset-complete workspace backup.")
        return target, row[0]

    def backup(self, wid):
        """Byte-oriented compatibility helper for small tests; UI uses backup_file."""
        out = io.BytesIO()
        self.backup_file(wid, out)
        return out.getvalue()

    def backup_file(self, wid, destination, cancelled=lambda: False, progress=lambda *_: None):
        if not isinstance(destination, (str, Path)):
            return self._backup_archive(wid, destination, cancelled, progress)
        destination = Path(destination)
        partial = destination.with_name(destination.name + '.partial')
        if destination.is_symlink() or partial.is_symlink():
            raise UserError('Backup destination cannot be a symlink.')
        try:
            self._backup_archive(wid, partial, cancelled, progress)
            check_cancel(cancelled)
            partial.replace(destination)
        finally:
            partial.unlink(missing_ok=True)

    def _backup_archive(self, wid, destination, cancelled, progress):
        # Snapshot metadata briefly; immutable hashed assets can be read without
        # holding the write lock, so a backup doesn't freeze live fog/notes.
        with self.lock, self.db(wid) as conn:
            from .workspace_modules import sync, backup_assets
            sync(self, wid, conn, cancelled)
            raw_size = conn.execute('SELECT COALESCE(SUM(length(CAST(value AS BLOB))),0) FROM documents').fetchone()[0]
            if raw_size > MAX_METADATA:
                raise UserError('Workspace metadata exceeds the supported backup size (64 MB).')
            documents = {k: json.loads(v) for k, v in conn.execute("SELECT key,value FROM documents")}
            assets = {h: {"mime": m, "size": s} for h, m, s in conn.execute("SELECT * FROM assets")}
            assets = backup_assets(documents, assets)
        metadata = json.dumps({"format": "sessiondesk-workspace", "version": SCHEMA,
            "documents": documents, "assets": assets}, ensure_ascii=False).encode('utf-8')
        total = sum(x['size'] for x in assets.values()) + len(metadata)
        if total > MAX_BACKUP or len(metadata) > MAX_METADATA:
            raise UserError('Workspace exceeds the supported backup size (1 GB of images plus metadata).')
        check_cancel(cancelled)
        done = len(metadata)
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('workspace.json', metadata)
            progress('Backing up workspace', done, total)
            for digest in assets:
                check_cancel(cancelled)
                target, _ = self.asset(wid, digest)
                checksum, count = hashlib.sha256(), 0
                with target.open('rb') as source, archive.open('assets/' + digest, 'w') as output:
                    while chunk := source.read(CHUNK):
                        check_cancel(cancelled)
                        checksum.update(chunk)
                        output.write(chunk)
                        done += len(chunk)
                        count += len(chunk)
                        progress('Backing up images', done, total)
                if checksum.hexdigest() != digest or count != assets[digest]['size']:
                    raise UserError('An image is missing or damaged. Re-import its original adventure to repair it, then retry the backup.')
            check_cancel(cancelled)

    def recover_interrupted_restores(self):
        return recover_staging(self.workspaces, '_restore-')

    @staticmethod
    def validate_backup(documents, assets):
        """Treat backups as untrusted typed data, including every UI-facing ID."""
        graphs = {}
        for key, value in documents.items():
            if key == "meta":
                if not isinstance(value, dict):
                    raise UserError("Invalid workspace metadata.")
                string(value.get("name"), 100)
                continue
            prefix, _, suffix = key.partition(":")
            identifier(suffix)
            if prefix == 'module':
                from .workspace_modules import validate
                validate(value, assets)
                continue
            if prefix not in ("adventure", "prep", "session", "pins") or not isinstance(value, dict):
                raise UserError("Unknown backup document.")
            if prefix != "adventure":
                continue
            if identifier(value["id"]) != suffix:
                raise UserError("Adventure identity mismatch.")
            for field in ("name", "source", "adapter", "fingerprint"):
                string(value[field], 1000)
            entries, media = value["entries"], value["maps"] + value["pictures"]
            if not isinstance(entries, list) or len(entries) > 50000 or len(media) > 10000:
                raise UserError("Adventure exceeds backup limits.")
            entry_ids = {identifier(e["id"]) for e in entries}
            media_ids = {identifier(m["id"]) for m in media}
            if len(entry_ids) != len(entries) or len(media_ids) != len(media):
                raise UserError("Duplicate source/media identity.")
            if entry_ids & media_ids:
                raise UserError("Source/media identities overlap.")
            parents = {entry['id']: entry.get('parent') for entry in entries}
            for eid in entry_ids:
                current, seen = eid, set()
                while current is not None:
                    if current not in parents or current in seen or len(seen) > 100:
                        raise UserError("Invalid or cyclic book hierarchy.")
                    seen.add(current)
                    current = parents[current]
            for entry in entries:
                string(entry["name"], 2000)
                string(entry["text"], 10000000)
                string(entry["key"], 1000)
                if type(entry["chapter"]) is not int or not isinstance(entry["path"], list):
                    raise UserError("Invalid source locator.")
            for item in media:
                string(item["name"], 2000)
                if (type(item["width"]) is not int or type(item["height"]) is not int
                        or not 0 < min(item["width"], item["height"])
                        or max(item["width"], item["height"]) > 30000
                        or item["width"] * item["height"] > 100000000
                        or item["kind"] not in ("map", "picture")
                        or type(item["player_safe"]) is not bool or item["asset"] not in assets):
                    raise UserError("Invalid map/picture in backup.")
                for region in item["regions"]:
                    identifier(region["id"])
                    string(region["name"], 2000)
                    if region["points"]:
                        polygon(region["points"], item["width"], item["height"])
                    elif region["verified"]:
                        raise UserError("Verified region has no boundary.")
            graphs[suffix] = (value, entry_ids, {m["id"]: m for m in media})
        for key, value in documents.items():
            prefix, _, aid = key.partition(":")
            if prefix not in ("prep", "session", "pins"):
                continue
            if aid not in graphs:
                raise UserError("Orphan preparation/session in backup.")
            _, entries, media = graphs[aid]
            if prefix == "pins":
                if not isinstance(value.get("items"), list) or len(value["items"]) > 64:
                    raise UserError("Invalid pinned resources.")
                for pin in value["items"]:
                    candidates = entries if pin.get("kind") == "entry" else media if pin.get("kind") == "media" else {}
                    if pin.get("id") not in candidates:
                        raise UserError("Invalid pinned resource reference.")
                continue
            if prefix == "prep":
                for eid, prep in value.items():
                    if eid not in entries or prep["status"] not in ("draft", "approved"):
                        raise UserError("Invalid preparation reference.")
                    string(prep["notes"])
                    string(prep["translation"])
                continue
            if (not isinstance(value["tabs"], list) or len(set(value["tabs"])) != len(value["tabs"])
                    or any(mid not in media or not media[mid]["player_safe"] for mid in value["tabs"])
                    or value["active"] not in [None, *value["tabs"]]
                    or type(value["revision"]) is not int):
                raise UserError("Invalid presentation tabs.")
            for mid, note in value["notes"].items():
                if mid not in media:
                    raise UserError("Unknown shared-note image.")
                string(note, 20000)
            for mid, ops in value["fog"].items():
                if mid not in media or not isinstance(ops, list) or len(ops) > 10000:
                    raise UserError("Invalid fog reference.")
                for op in ops:
                    if op["mode"] not in ("reveal", "hide"):
                        raise UserError("Invalid fog operation.")
                    item = media[mid]
                    if "polygon" in op:
                        polygon(op["polygon"], item["width"], item["height"])
                    else:
                        if (type(op["radius"]) not in (int, float) or not 1 <= op["radius"] <= 3000
                                or not 1 <= len(op["points"]) <= 1000):
                            raise UserError("Invalid fog stroke.")
                        for point in op["points"]:
                            if (len(point) != 2 or any(type(n) not in (int, float) for n in point)
                                    or not 0 <= point[0] <= item["width"] or not 0 <= point[1] <= item["height"]):
                                raise UserError("Fog point outside map.")

    def restore(self, data):
        """Byte-oriented compatibility helper; normal restore uses a staged file."""
        return self.restore_file(io.BytesIO(data))

    def restore_file(self, source, cancelled=lambda: False, progress=lambda *_: None, on_commit=lambda: None):
        folder = None
        try:
            check_cancel(cancelled)
            with zipfile.ZipFile(source) as archive:
                files = archive.infolist()
                names = [x.filename for x in files]
                if 'workspace.json' not in names:
                    from .workspace_modules import import_campaign
                    return import_campaign(self, source, cancelled, progress, on_commit)
                if (len(files) > 20000 or len(names) != len(set(names))
                        or sum(x.file_size for x in files) > MAX_BACKUP
                        or any(x.flag_bits & 1 or (x.external_attr >> 16) & 0o170000 == 0o120000 for x in files)):
                    raise UserError("Backup exceeds limits or has duplicate/encrypted entries.")
                info = archive.getinfo("workspace.json")
                if info.file_size > MAX_METADATA:
                    raise UserError("Backup metadata exceeds limits.")
                def invalid_constant(_):
                    raise UserError('Backup contains an invalid JSON number.')
                payload = json.loads(archive.read(info), parse_constant=invalid_constant)
                if (payload.get("format") != "sessiondesk-workspace" or type(payload.get('version')) is not int
                        or payload['version'] not in (1, SCHEMA)):
                    raise UserError("Unsupported backup version.")
                documents, assets = payload["documents"], payload["assets"]
                if not isinstance(documents, dict) or not isinstance(assets, dict):
                    raise UserError("Invalid backup manifest.")
                if set(names) != {"workspace.json"} | {"assets/" + h for h in assets if HASH.fullmatch(h)}:
                    raise UserError("Backup contains unexpected paths.")
                # Restore declarative JSON, never an untrusted SQLite schema, trigger or extension.
                meta = documents["meta"]
                self.validate_backup(documents, assets)
                new = self._metadata(string(meta['name'], 100)[:89] + ' (restored)',
                                     meta.get('language', 'English'), meta.get('rules', 'Unspecified'))
                check_cancel(cancelled)
                folder = staging(self.workspaces, '_restore-')
                (folder / 'assets').mkdir()
                total = sum(x['size'] for x in assets.values())
                done = 0
                media = [m for key, doc in documents.items() if key.startswith('adventure:')
                         for m in doc['maps'] + doc['pictures']]
                raster_assets = {m['asset'] for m in media}
                for digest, details in assets.items():
                    check_cancel(cancelled)
                    asset_info = archive.getinfo('assets/' + digest)
                    from .workspace_modules import MAX_ATTACHMENT
                    if (not HASH.fullmatch(digest) or type(details.get('size')) is not int
                            or details['size'] < 0 or asset_info.file_size != details['size']
                            or asset_info.file_size > (MAX_IMAGE if digest in raster_assets else MAX_ATTACHMENT)):
                        raise UserError('Backup asset exceeds its supported size or has invalid metadata.')
                    target = folder / 'assets' / digest
                    checksum, count = hashlib.sha256(), 0
                    with archive.open(asset_info) as input_file, target.open('xb') as output:
                        while chunk := input_file.read(CHUNK):
                            check_cancel(cancelled)
                            checksum.update(chunk)
                            output.write(chunk)
                            count += len(chunk)
                            done += len(chunk)
                            progress('Checking and restoring images', done, total)
                    if checksum.hexdigest() != digest or count != details['size']:
                        raise UserError("Backup image checksum mismatch.")
                    # At most one bounded image is in memory, never the whole ZIP.
                    if digest in raster_assets or details['mime'].startswith('image/'):
                        if asset_info.file_size > MAX_IMAGE:
                            raise UserError('Backup image exceeds 48 MB.')
                        dimensions, mime = image_size(target.read_bytes())
                        if mime != details["mime"]:
                            raise UserError("Backup image type mismatch.")
                        if any(m['asset'] == digest and (m['width'], m['height']) != dimensions for m in media):
                            raise UserError('Backup image dimensions do not match the map/picture metadata.')
                    elif details['mime'] not in ('application/octet-stream', 'application/json',
                                                 'application/pdf', 'application/zip', 'text/plain', 'text/markdown'):
                        raise UserError('Unsupported attachment type in workspace backup.')
                check_cancel(cancelled)
                progress('Saving restored workspace', total, total)
                self._initialize(folder, new, documents, assets)
                from .workspace_modules import materialize_all
                materialize_all(folder, documents)
                check_cancel(cancelled)
                on_commit()
                # Publishing is one same-volume rename, after all files and the
                # closed SQLite transaction are valid. Existing folders never move.
                folder.replace(self.workspaces / new['id'])
                return new
        except (zipfile.BadZipFile, KeyError, TypeError, AttributeError, IndexError, RecursionError,
                json.JSONDecodeError, UnicodeError, OSError) as exc:
            raise UserError("Invalid or incomplete workspace backup.") from exc
        finally:
            if folder is not None:
                remove_staging(self.workspaces, folder, '_restore-')
