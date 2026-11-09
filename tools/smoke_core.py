"""Synthetic source/frozen lifecycle test under an isolated application profile."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.fixtures import make_library


def call(ready, route, data=None, player=False, binary=False):
    headers = {"Authorization": "Bearer " + ready["player_token" if player else "token"],
               "Origin": ready["url"].rstrip("/"), "Content-Type": "application/json"}
    req = Request(ready["url"] + "api/" + route, json.dumps(data or {}).encode(), headers)
    with urlopen(req, timeout=30) as response:
        return response.read() if binary else json.load(response)


def wait_job(ready, jid):
    for _ in range(300):
        status = call(ready, 'job/status', {'job': jid})
        if status['state'] not in ('uploading', 'running', 'committing'):
            assert status['state'] == 'complete', status
            return status['result']
        time.sleep(.1)
    raise RuntimeError('Transfer did not complete within 30 seconds.')


@contextmanager
def launch(base, exe=None, data=None, auto_exit=False):
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    data = data or base / "profile" / "SessionDesk"
    ready_file = base / "ready.json"
    env = {k:v for k,v in os.environ.items() if k not in ("PYTHONPATH","PYTHONHOME")}
    env["LOCALAPPDATA"] = str(base / "profile")
    if exe:
        # The running account is unchanged. This tests a fresh app profile with
        # developer tools hidden, not a clean VM or a new Windows account.
        env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
    command = [str(Path(exe).resolve())] if exe else [sys.executable,"-m","sessiondesk"]
    command += ["--no-browser","--data-dir",str(data),"--ready-file",str(ready_file)]
    if auto_exit:
        command += ["--auto-exit"]
    process = subprocess.Popen(command, cwd=base if exe else ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    try:
        deadline = time.monotonic() + 40
        while not ready_file.is_file():
            if process.poll() is not None:
                raise RuntimeError(f"Application exited before readiness ({process.returncode}).")
            if time.monotonic() > deadline:
                raise RuntimeError("Application did not start within 40 seconds.")
            time.sleep(.1)
        ready = json.loads(ready_file.read_text())
        assert call(ready,"heartbeat")["ai"] == {"enabled":False,"available":False}
        yield ready
    finally:
        if process.poll() is None:
            try:
                call(ready,"quit")
                process.wait(timeout=10)
            except Exception:
                process.terminate()
                process.wait(timeout=10)


def run(exe=None):
    with tempfile.TemporaryDirectory(prefix="sessiondesk-smoke-") as temp:
        base = Path(temp)
        library = make_library(base / "original source Ω")
        data = base / "external user data"
        with launch(base / "first",exe,data) as ready:
            assert call(ready,"bootstrap")["workspaces"] == []
            wid = call(ready,"workspace/create",{"name":"Synthetic smoke","rules":"2014"})["id"]
            job = call(ready,"import/start",{"workspace":wid,"path":str(library),"source":"DEMO"})
            for _ in range(100):
                job = call(ready,"import/status",{"job":job["id"]})
                if job["state"] not in ("running","committing"): break
                time.sleep(.1)
            assert job["state"] == "complete", job
            aid = job["result"]["id"]
            scope = {"workspace":wid,"adventure":aid}
            graph = call(ready,"adventure",scope)
            entry,media = graph["entries"][1],graph["maps"][0]
            call(ready,"prepare",{**scope,"entry":entry["id"],"translation":"Αρχική δοκιμή","notes":"Private synthetic note","status":"approved"})
            call(ready,"media/review",{**scope,"media":media["id"],"player_safe":True})
            call(ready,"session/action",{**scope,"media":media["id"],"action":"present"})
            call(ready,"session/action",{**scope,"media":media["id"],"action":"note","text":"Shared synthetic note"})
            player = call(ready,"player",scope,True)
            assert player["tabs"][0]["id"] == media["id"]
            assert "Private synthetic note" not in json.dumps(player)
            assert "DM_ONLY_SYNTHETIC_SECRET" not in json.dumps(player)
            export = call(ready, 'backup/export/start', {'workspace': wid})
            wait_job(ready, export['id'])
            with urlopen(ready['url'] + 'download/' + export['id'] + '?token=' + ready['token']) as response:
                backup = response.read()
        with launch(base / "restart",exe,data) as ready:
            graph = call(ready,"adventure",scope)
            assert graph["preparation"][entry["id"]]["translation"] == "Αρχική δοκιμή"
            assert call(ready,"session",scope)["active"] == media["id"]
            job = call(ready, 'backup/restore/start', {'size': len(backup)})
            req = Request(ready["url"]+"api/backup/upload/"+job['id'],backup,{
                "Authorization":"Bearer "+ready["token"],"Origin":ready["url"].rstrip("/"),"Content-Type":"application/zip"})
            with urlopen(req,timeout=30) as response: json.load(response)
            restored = wait_job(ready, job['id'])
            assert restored["id"] != wid
            assert call(ready,"adventure",{"workspace":restored["id"],"adventure":aid})["maps"][0]["asset"] == media["asset"]
        with launch(base / "auto-close",exe,data,auto_exit=True) as ready:
            client=str(uuid.uuid4())
            call(ready,"client/ping",{"client":client})
            call(ready,"client/close",{"client":client})
            deadline=time.monotonic()+15
            while (base / "auto-close/ready.json").exists() and time.monotonic()<deadline:
                time.sleep(.1)
            assert not (base / "auto-close/ready.json").exists(), "Closing the last window did not stop the application"
        # Existing data can also be opened by a replacement app at another install path.
        print("Core smoke passed: import, prep, player allowlist, restart, restore and last-window shutdown; AI Off.")


def run_archive(archive):
    archive = Path(archive).resolve()
    expected = archive.with_suffix(".zip.sha256").read_text().split()[0]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise RuntimeError("ZIP checksum mismatch.")
    with tempfile.TemporaryDirectory(prefix="sessiondesk-extracted-") as temp:
        target = Path(temp) / "relocated application Ω"
        with zipfile.ZipFile(archive) as package:
            names = package.namelist()
            if len(names) != len(set(names)) or len(names) > 10000:
                raise RuntimeError("Invalid package entries.")
            for name in names:
                path = (target / name).resolve()
                if not path.is_relative_to(target.resolve()) or ":" in name or "\\" in name:
                    raise RuntimeError("Unsafe archive path.")
            manifest = json.loads(package.read("MANIFEST.json"))
            records = {r["path"]:r for r in manifest["files"]}
            if set(names) != set(records) | {"MANIFEST.json"}:
                raise RuntimeError("Archive and explicit manifest differ.")
            for name, record in records.items():
                data = package.read(name)
                if len(data) != record["size"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
                    raise RuntimeError("Package entry checksum mismatch: " + name)
            package.extractall(target)
        run(target / "SessionDesk.exe")
        # All mutable files must be outside the installation, including after restart.
        after = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
        if after != set(names):
            raise RuntimeError("Application wrote files into the installation.")
        for name, record in records.items():
            if hashlib.sha256((target / name).read_bytes()).hexdigest() != record["sha256"]:
                raise RuntimeError("Application changed an installation file.")
        print("Extracted ZIP verified: checksums, relocation, no install writes, bundled runtime; unsigned development preview.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe",type=Path)
    parser.add_argument("--archive",type=Path)
    args = parser.parse_args()
    run_archive(args.archive) if args.archive else run(args.exe)
