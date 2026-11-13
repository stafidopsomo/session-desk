"""Launch a local browser app. No external service or provider is contacted."""
import argparse
import json
import os
from pathlib import Path
import sys
import subprocess
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


def wait_for_process(pid, timeout_ms=90000):
    """A staged Windows build waits for the old build to release its workspace lock."""
    if os.name != 'nt' or type(pid) is not int or pid <= 0 or pid == os.getpid():
        raise ValueError('Invalid update process.')
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x00100000, False, pid)
    if not handle:
        if ctypes.get_last_error() not in (0,87,1168):
            raise OSError('Unable to wait for the previous Session Desk process.')
        return
    try:
        if kernel.WaitForSingleObject(handle, timeout_ms) != 0:
            raise RuntimeError('The previous app has not closed. Close it before opening the update.')
    finally:
        kernel.CloseHandle(handle)


def main():
    parser = argparse.ArgumentParser(description="Session Desk — local adventure preparation")
    parser.add_argument("--data-dir", type=Path, help="External user data directory")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--auto-exit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ready-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--wait-for-pid', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.wait_for_pid:
        wait_for_process(args.wait_for_pid)
    root = args.data_dir or Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "SessionDesk"
    root = root.resolve()
    if getattr(sys,'frozen',False):
        from .updates import preferred_application
        from . import __version__
        preferred=preferred_application(root,__version__)
        if preferred:
            command=[str(preferred),'--data-dir',str(root),'--wait-for-pid',str(os.getpid())]
            if args.no_browser:command.append('--no-browser')
            if args.auto_exit:command.append('--auto-exit')
            if args.port:command+=['--port',str(args.port)]
            if args.ready_file:command+=['--ready-file',str(args.ready_file)]
            try:
                subprocess.Popen(command,creationflags=subprocess.CREATE_NO_WINDOW)
                return
            except OSError:
                pass  # Retain the original working application as fallback.
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
