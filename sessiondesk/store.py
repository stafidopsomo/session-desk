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

from .importer import MAX_TOTAL, UserError, image_size, polygon

SCHEMA = 1
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
            if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA:
                raise UserError("Unsupported workspace version. Use its compatible app; data was not modified.")
            with conn:
                yield conn
        finally:
            conn.close()

    def create(self, name, language="English", rules="Unspecified"):
        name = string(name, 100).strip()
        if not name:
            raise UserError("Enter a workspace name.")
        wid = str(uuid.uuid4())
        folder = self.workspaces / wid
        folder.mkdir()
        (folder / "assets").mkdir()
        meta = {"id": wid, "name": name, "schema": SCHEMA,
                "language": string(language, 80), "rules": string(rules, 80)}
        conn = sqlite3.connect(folder / "workspace.sqlite3")
        try:
            with conn:
                conn.execute("CREATE TABLE documents (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                conn.execute("CREATE TABLE assets (hash TEXT PRIMARY KEY, mime TEXT NOT NULL, size INTEGER NOT NULL)")
                conn.execute(f"PRAGMA user_version={SCHEMA}")
                self.put(conn, "meta", meta)
        finally:
            conn.close()
        return meta

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
            return {"meta": self.get(conn, "meta"), "adventures": [
                {k: a[k] for k in ("id", "name", "source", "fingerprint")} |
                {"maps": len(a["maps"]), "pictures": len(a["pictures"]), "warnings": len(a["warnings"])}
                for a in adventures]}

    def adventure(self, wid, aid):
        with self.db(wid) as conn:
            graph = self.get(conn, "adventure:" + identifier(aid))
            if not graph:
                raise UserError("Adventure not found in this workspace.")
            graph["preparation"] = self.get(conn, "prep:" + aid, {})
            return graph

    def import_graph(self, wid, graph, blobs):
        with self.lock, self.db(wid) as conn:
            old = self.get(conn, "adventure:" + graph["id"])
            if old:
                if old["fingerprint"] == graph["fingerprint"]:
                    return {"id": graph["id"], "unchanged": True}
                raise UserError("This source changed. Import into a new workspace to preserve existing preparation/session state.")
            for digest, (mime, data) in blobs.items():
                if hashlib.sha256(data).hexdigest() != digest:
                    raise UserError("Image checksum mismatch.")
                target = self.folder(wid) / "assets" / digest
                if target.is_symlink():
                    raise UserError("Asset cannot be a symlink.")
                if not target.exists():
                    temp = target.with_suffix(".tmp")
                    temp.write_bytes(data)
                    temp.replace(target)
                conn.execute("INSERT OR IGNORE INTO assets VALUES (?,?,?)", (digest, mime, len(data)))
            self.put(conn, "adventure:" + graph["id"], graph)
        return {"id": graph["id"], "unchanged": False}

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
                              role=role, verified=change.get("verified") is True)
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
        # Player serialization has an explicit allowlist: no regions, locators, book text or DM prep.
        return {"tabs": [{k: media[mid][k] for k in ("id", "name", "asset", "width", "height", "kind")}
                         for mid in state["tabs"] if mid in media], "active": state["active"],
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
                if not media["player_safe"]:
                    raise UserError("Review this image for secrets and mark it safe before presenting.")
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
                    if not region or not region["verified"] or not region["points"]:
                        raise UserError("Review/verify this region's boundary before room reveal; brush is always available.")
                    operations.append({"mode": "reveal", "polygon": region["points"]})
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
        with self.lock, self.db(wid) as conn:
            documents = {k: json.loads(v) for k, v in conn.execute("SELECT key,value FROM documents")}
            assets = {h: {"mime": m, "size": s} for h, m, s in conn.execute("SELECT * FROM assets")}
            out = io.BytesIO()
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("workspace.json", json.dumps({"format": "sessiondesk-workspace", "version": SCHEMA,
                    "documents": documents, "assets": assets}, ensure_ascii=False))
                for digest in assets:
                    target, _ = self.asset(wid, digest)
                    data = target.read_bytes()
                    if hashlib.sha256(data).hexdigest() != digest:
                        raise UserError("Asset checksum failed; backup was not created.")
                    archive.writestr("assets/" + digest, data)
            return out.getvalue()

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
            if prefix not in ("adventure", "prep", "session") or not isinstance(value, dict):
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
            if prefix not in ("prep", "session"):
                continue
            if aid not in graphs:
                raise UserError("Orphan preparation/session in backup.")
            _, entries, media = graphs[aid]
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
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                files = archive.infolist()
                names = [x.filename for x in files]
                if (len(files) > 20000 or len(names) != len(set(names))
                        or sum(x.file_size for x in files) > MAX_TOTAL + 64 * 1024 * 1024
                        or any(x.flag_bits & 1 for x in files)):
                    raise UserError("Backup exceeds limits or has duplicate/encrypted entries.")
                info = archive.getinfo("workspace.json")
                if info.file_size > 64 * 1024 * 1024:
                    raise UserError("Backup metadata exceeds limits.")
                payload = json.loads(archive.read(info))
                if payload.get("format") != "sessiondesk-workspace" or payload.get("version") != SCHEMA:
                    raise UserError("Unsupported backup version.")
                documents, assets = payload["documents"], payload["assets"]
                if not isinstance(documents, dict) or not isinstance(assets, dict):
                    raise UserError("Invalid backup manifest.")
                if set(names) != {"workspace.json"} | {"assets/" + h for h in assets if HASH.fullmatch(h)}:
                    raise UserError("Backup contains unexpected paths.")
                # Restore declarative JSON, never an untrusted SQLite schema, trigger or extension.
                meta = documents["meta"]
                self.validate_backup(documents, assets)
                checked = {}
                for digest, details in assets.items():
                    if archive.getinfo("assets/" + digest).file_size > 48 * 1024 * 1024:
                        raise UserError("Backup image exceeds 48 MB.")
                    blob = archive.read("assets/" + digest)
                    if hashlib.sha256(blob).hexdigest() != digest or len(blob) != details["size"]:
                        raise UserError("Backup image checksum mismatch.")
                    _, mime = image_size(blob)
                    if mime != details["mime"]:
                        raise UserError("Backup image type mismatch.")
                    checked[digest] = (mime, blob)
        except (zipfile.BadZipFile, KeyError, TypeError, AttributeError, IndexError, json.JSONDecodeError, UnicodeError, OSError) as exc:
            raise UserError("Invalid or incomplete workspace backup.") from exc
        # All validation completes before a new workspace appears. Existing workspaces are untouched.
        new = self.create(string(meta["name"], 100)[:89] + " (restored)", meta.get("language", "English"), meta.get("rules", "Unspecified"))
        with self.lock, self.db(new["id"]) as conn:
            for key, value in documents.items():
                if key != "meta":
                    self.put(conn, key, value)
            for digest, (mime, blob) in checked.items():
                (self.folder(new["id"]) / "assets" / digest).write_bytes(blob)
                conn.execute("INSERT INTO assets VALUES (?,?,?)", (digest, mime, len(blob)))
        return new
