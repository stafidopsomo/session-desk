import copy
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

from sessiondesk.importer import Library, UserError, confined, image_size, polygon
from sessiondesk.server import Application, make_server
from sessiondesk.store import Store
from tests.fixtures import make_library
from tools.release_gate import REQUIRED, evaluate


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sessiondesk-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lib = make_library(self.root / "source")
        self.store = Store(self.root / "user data Ω")
        self.wid = self.store.create("Synthetic table", "Greek", "2014")["id"]
        self.graph, self.blobs = Library(self.lib).load("DEMO")
        self.aid = self.graph["id"]

    def imported(self):
        self.store.import_graph(self.wid, self.graph, self.blobs)
        return self.graph["maps"][0]


class CoreTests(WorkspaceCase):
    def test_import_generic_ids_geometry_and_chapter_reference_resolution(self):
        self.assertEqual(len(self.graph["maps"]), 4)
        self.assertEqual(len(self.graph["pictures"]), 1)
        first, second, no_regions, uncertain = self.graph["maps"]
        self.assertNotEqual(first["regions"][0]["id"], second["regions"][0]["id"])
        self.assertNotEqual(first["regions"][0]["entry"], second["regions"][0]["entry"])
        self.assertEqual(no_regions["regions"], [])
        self.assertFalse(uncertain["regions"][0]["points"])
        self.assertFalse(first["regions"][1]["verified"])
        self.assertEqual(first["regions"][1]["role"], "unknown")
        self.assertTrue(all(not m["player_safe"] for m in self.graph["maps"]))
        entry = self.graph["entries"][1]
        self.assertEqual(entry["locator"]["chapter"], 0)
        self.assertEqual(entry["locator"]["entry"], "platform-A")

    def test_import_is_idempotent_and_preserves_manual_work(self):
        self.imported()
        entry = self.graph["entries"][1]["id"]
        self.store.prepare(self.wid,self.aid,entry,{"notes":"Original manual note", "translation":"Ελληνικά", "status":"approved"})
        self.assertTrue(self.store.import_graph(self.wid,self.graph,self.blobs)["unchanged"])
        self.assertEqual(self.store.adventure(self.wid,self.aid)["preparation"][entry]["notes"],"Original manual note")
        changed = copy.deepcopy(self.graph)
        changed["fingerprint"] = "different"
        with self.assertRaises(UserError):
            self.store.import_graph(self.wid,changed,self.blobs)

    def test_source_removed_after_import_assets_remain_self_contained(self):
        media = self.imported()
        (self.lib / "img" / "original" / "map.png").unlink()
        path, mime = self.store.asset(self.wid,media["asset"])
        self.assertEqual(mime,"image/png")
        self.assertEqual(image_size(path.read_bytes())[0],(900,600))

    def test_workspaces_cannot_read_or_modify_each_other(self):
        self.imported()
        other = self.store.create("Separate table")["id"]
        self.assertEqual(self.store.overview(other)["adventures"],[])
        with self.assertRaises(UserError): self.store.adventure(other,self.aid)
        with self.assertRaises(UserError): self.store.asset(other,self.graph["maps"][0]["asset"])
        with self.assertRaises(UserError): self.store.prepare(other,self.aid,self.graph["entries"][1]["id"],{})

    def test_unverified_regions_cannot_be_revealed_and_reveal_is_additive(self):
        media = self.imported()
        with self.assertRaises(UserError):
            self.store.session_action(self.wid,self.aid,{"action":"reveal_region","media":media["id"],"region":media["regions"][0]["id"]})
        r = media["regions"][0]
        self.store.review_map(self.wid,self.aid,media["id"],{"region":{**r,"verified":True,"role":"room"}})
        self.store.session_action(self.wid,self.aid,{"action":"fog","media":media["id"],"mode":"reveal","points":[[30,40]],"radius":20})
        state = self.store.session_action(self.wid,self.aid,{"action":"reveal_region","media":media["id"],"region":r["id"]})
        self.assertEqual(len(state["fog"][media["id"]]),2)
        self.assertIn("points",state["fog"][media["id"]][0])

    def test_player_safe_serialization_and_revoking_media(self):
        media = self.imported()
        with self.assertRaises(UserError): self.store.session_action(self.wid,self.aid,{"action":"present","media":media["id"]})
        self.store.review_map(self.wid,self.aid,media["id"],{"player_safe":True})
        self.store.session_action(self.wid,self.aid,{"action":"present","media":media["id"]})
        player = self.store.session(self.wid,self.aid,True)
        self.assertEqual(len(player["tabs"]),1)
        self.assertNotIn("regions",player["tabs"][0])
        self.assertNotIn("DM_ONLY",json.dumps(player))
        self.store.review_map(self.wid,self.aid,media["id"],{"player_safe":False})
        self.assertEqual(self.store.session(self.wid,self.aid,True)["tabs"],[])

    def test_players_may_switch_and_close_tabs_but_cannot_change_fog(self):
        self.imported()
        for m in self.graph["maps"][:2]:
            self.store.review_map(self.wid,self.aid,m["id"],{"player_safe":True})
            self.store.session_action(self.wid,self.aid,{"action":"present","media":m["id"]})
        mid = self.graph["maps"][0]["id"]
        state = self.store.session_action(self.wid,self.aid,{"action":"activate","media":mid},True)
        self.assertEqual(state["active"],mid)
        with self.assertRaises(UserError): self.store.session_action(self.wid,self.aid,{"action":"show_map","media":mid},True)
        self.store.session_action(self.wid,self.aid,{"action":"close_all"},True)
        self.assertEqual(self.store.session(self.wid,self.aid)["tabs"],[])

    def test_backup_restores_into_different_root_with_images_and_state(self):
        media = self.imported()
        self.store.prepare(self.wid,self.aid,self.graph["entries"][1]["id"],{"translation":"Καλημέρα", "notes":"private"})
        self.store.session_action(self.wid,self.aid,{"action":"note","media":media["id"],"text":"shared"})
        backup = self.store.backup(self.wid)
        other = Store(self.root / "another computer")
        new = other.restore(backup)["id"]
        self.assertNotEqual(new,self.wid)
        self.assertEqual(other.adventure(new,self.aid)["preparation"],self.store.adventure(self.wid,self.aid)["preparation"])
        self.assertEqual(other.session(new,self.aid)["notes"][media["id"]],"shared")
        self.assertTrue(other.asset(new,media["asset"])[0].is_file())

    def test_backup_rejects_path_injection_and_corruption_before_creating_workspace(self):
        self.imported()
        original = self.store.backup(self.wid)
        for corrupt in (False,True):
            out = io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(original)) as src, zipfile.ZipFile(out,"w") as dst:
                for name in src.namelist():
                    data = src.read(name)
                    dst.writestr(name,b"corrupt" if corrupt and name.startswith("assets/") else data)
                if not corrupt: dst.writestr("../escape.txt","no")
            with self.assertRaises(UserError): self.store.restore(out.getvalue())
            self.assertEqual(len(self.store.listing()),1)

    def test_future_schema_fails_without_resetting_or_migrating_data(self):
        path = self.store.folder(self.wid) / "workspace.sqlite3"
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA user_version=999")
        conn.close()
        before = path.read_bytes()
        with self.assertRaises(UserError): self.store.overview(self.wid)
        self.assertEqual(path.read_bytes(),before)

    def test_paths_polygons_and_cancelled_import_are_bounded(self):
        for path in ("../outside.png","C:/outside.png","/etc/passwd"):
            with self.assertRaises(UserError): confined(self.lib,path)
        with self.assertRaises(UserError): polygon([[0,0],[1,1],[2,2]],900,600)
        with self.assertRaises(UserError): Library(self.lib).load("DEMO",lambda:True)
        self.assertEqual(self.store.overview(self.wid)["adventures"],[])

    def test_missing_and_external_assets_report_errors_without_downloading(self):
        path = self.lib / "data/adventure/adventure-demo.json"
        source = json.loads(path.read_text())
        source["data"][0]["entries"] += [
            {"type":"image","href":{"type":"external","url":"https://example.invalid/private"}},
            {"type":"image","href":{"type":"internal","path":"../outside.png"}}]
        path.write_text(json.dumps(source))
        graph,_ = Library(self.lib).load("DEMO")
        self.assertEqual(len(graph["warnings"]),2)

    def test_alpha_gate_requires_matching_version_tree_and_evidence(self):
        self.assertTrue(evaluate({},"0.1.0-dev.1","synthetic-digest","product-v0.1.0-dev.1"))
        record = {"alpha_ready":True,"version":"0.1.0-alpha.1","product_digest":"synthetic-digest",
                  "checks":{k:{"passed":True,"evidence":"Synthetic conformance record"} for k in REQUIRED}}
        self.assertEqual(evaluate(record,"0.1.0-alpha.1","synthetic-digest","product-v0.1.0-alpha.1"),[])
        self.assertTrue(evaluate(record,"0.1.0-alpha.1","changed-tree","product-v0.1.0-alpha.1"))

    def test_backup_rejects_invalid_ui_identity(self):
        self.imported()
        original = self.store.backup(self.wid)
        out = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original)) as src, zipfile.ZipFile(out,"w") as dst:
            for name in src.namelist():
                data = src.read(name)
                if name == "workspace.json":
                    payload = json.loads(data)
                    payload["documents"]["adventure:"+self.aid]["maps"][0]["id"] = '"<invalid-id>'
                    data = json.dumps(payload).encode()
                dst.writestr(name,data)
        with self.assertRaises(UserError): self.store.restore(out.getvalue())
        self.assertEqual(len(self.store.listing()),1)


class HttpTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.imported()
        self.app = Application(self.store)
        self.server = make_server(self.app)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def call(self,path,body=None,token=None,origin=None):
        data = {"workspace":self.wid,"adventure":self.aid,**(body or {})}
        req = Request(self.origin + path,data=json.dumps(data).encode(),headers={
            "Content-Type":"application/json","Authorization":"Bearer " + (token or self.app.dm_token),
            "Origin":origin or self.origin})
        return json.load(urlopen(req,timeout=10))

    def test_dm_authentication_and_same_origin_are_required(self):
        for token,origin in (("wrong",self.origin),(self.app.dm_token,"https://example.invalid")):
            with self.assertRaises(HTTPError) as e: self.call("/api/bootstrap",token=token,origin=origin)
            self.assertIn(e.exception.code,(401,403))
        self.assertEqual(self.call("/api/bootstrap")["ai"],{"enabled":False,"available":False})

    def test_player_cannot_get_dm_data_or_unpresented_assets(self):
        with self.assertRaises(HTTPError) as e: self.call("/api/adventure",token=self.app.player_token)
        self.assertEqual(e.exception.code,403)
        digest = self.graph["maps"][0]["asset"]
        with self.assertRaises(HTTPError):
            urlopen(self.origin+f"/asset/{self.wid}/{digest}?token={self.app.player_token}&adventure={self.aid}")
        self.assertNotIn("DM_ONLY",json.dumps(self.call("/api/player",token=self.app.player_token)))

    def test_ai_routes_cannot_be_enabled_or_submitted(self):
        for path in ("/api/ai/enable","/api/ai/jobs","/api/ai"):
            with self.assertRaises(HTTPError) as e: self.call(path,{"enabled":True})
            self.assertEqual(e.exception.code,400)
        self.assertFalse(self.call("/api/heartbeat")["ai"]["enabled"])

    def test_temporary_ink_is_not_in_backup_or_restarted_app(self):
        media = self.graph["pictures"][0]
        self.store.review_map(self.wid,self.aid,media["id"],{"player_safe":True})
        self.store.session_action(self.wid,self.aid,{"action":"present","media":media["id"]})
        self.call("/api/ink",{"media":media["id"],"action":"draw","points":[[3,4]],"color":"#69b8ff"},self.app.player_token)
        self.assertEqual(len(self.app.ink),1)
        with zipfile.ZipFile(io.BytesIO(self.store.backup(self.wid))) as archive:
            self.assertNotIn('"strokes"',archive.read("workspace.json").decode())
        self.assertEqual(Application(Store(self.store.root)).ink,{})


if __name__ == "__main__":
    unittest.main()
