"""Launch a local browser app. No external service or provider is contacted."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
import webbrowser

from .server import Application, make_server
from .store import Store


def instance_lock(root):
    """OS releases this lock after crashes; stale metadata never blocks a relaunch."""
    root.mkdir(parents=True, exist_ok=True)
    handle = (root / "instance.lock").open("a+b")
    handle.seek(0)
    if handle.read(1) == b"":
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return handle
    except OSError:
        handle.close()
        return None


def main():
    parser = argparse.ArgumentParser(description="Session Desk — local adventure preparation")
    parser.add_argument("--data-dir", type=Path, help="External user data directory")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--auto-exit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ready-file", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = args.data_dir or Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "SessionDesk"
    root = root.resolve()
    lock = instance_lock(root)
    if lock is None:
        for _ in range(20):
            try:
                ready = json.loads((root / "instance.json").read_text(encoding="utf-8"))
                if not args.no_browser:
                    webbrowser.open(ready["url"] + "#dm=" + ready["token"])
                return
            except (OSError, ValueError, KeyError):
                time.sleep(.1)
        raise RuntimeError("Session Desk is still starting. Try its launcher again shortly.")
    app = Application(Store(root))
    app.recover()
    server = make_server(app, args.port)
    if not args.no_browser or args.auto_exit:
        def monitor():
            while True:
                time.sleep(1)
                if app.should_exit():
                    server.shutdown()
                    return
        threading.Thread(target=monitor, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/"
    ready = {"url": url, "token": app.dm_token, "player_token": app.player_token}
    (root / "instance.json").write_text(json.dumps(ready), encoding="utf-8")
    if args.ready_file:
        args.ready_file.write_text(json.dumps(ready), encoding="utf-8")
    if not args.no_browser:
        webbrowser.open(url + "#dm=" + app.dm_token)
    elif sys.stdout:
        print("Session Desk is running on loopback.", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        app.close()
        (root / "instance.json").unlink(missing_ok=True)
        lock.close()
        if args.ready_file:
            args.ready_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
