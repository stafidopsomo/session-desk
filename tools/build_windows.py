"""Build only the reviewed product; create checksummed development artifacts."""
import hashlib
from importlib.metadata import distribution, version
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sessiondesk import __version__
from tools.release_gate import product_digest

BUILD_PACKAGES = ("pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "packaging",
                  "pefile", "pywin32-ctypes", "setuptools")


def main():
    if os.name != "nt" or platform.machine().lower() not in ("amd64", "x86_64") or sys.version_info[:2] != (3, 12):
        raise SystemExit("Build with Windows x64 Python 3.12 and requirements-build.lock.")
    subprocess.run([sys.executable, str(ROOT / "tools/check_product_boundary.py")], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "SessionDesk.spec"],
                   cwd=ROOT, env={**os.environ, "PYTHONHASHSEED": "0"}, check=True)
    folder = ROOT / "dist" / "SessionDesk"
    shutil.copyfile(ROOT / "docs/QUICKSTART.txt", folder / "READ-ME-FIRST.txt")
    notices = {name: {"version": version(name), "license": distribution(name).metadata.get("License-Expression")
                     or distribution(name).metadata.get("License", "See upstream distribution notices")} for name in BUILD_PACKAGES}
    notices["Python"] = {"version": platform.python_version(), "license": "PSF-2.0 and bundled third-party notices"}
    # Ship complete license texts, including the Python runtime's bundled notices.
    license_dir = folder / "LICENSES"
    license_dir.mkdir(exist_ok=True)
    runtime_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not runtime_license.is_file():
        raise SystemExit("Python runtime license was not found; refusing incomplete package.")
    shutil.copyfile(runtime_license, license_dir / "Python.txt")
    for name in BUILD_PACKAGES:
        dist = distribution(name)
        for entry in dist.files or []:
            path = str(entry).replace("\\", "/")
            if any(x in path.lower() for x in ("license", "copying", "notice")) and ".dist-info/" in path:
                source = dist.locate_file(entry)
                if source.is_file():
                    target = license_dir / (name + "-" + source.name)
                    shutil.copyfile(source, target)
    (folder / "DEPENDENCIES.json").write_text(json.dumps(notices, indent=2), encoding="utf-8")
    files = sorted(x for x in folder.rglob("*") if x.is_file())
    forbidden = (".git", "workspaces", "credentials", "imports", "tests", "playwright")
    records = []
    private_markers = [str(ROOT).encode(), str(ROOT).replace("\\", "/").encode(), Path.home().name.encode()]
    for file in files:
        relative = file.relative_to(folder).as_posix()
        if any(p.lower() in forbidden for p in file.relative_to(folder).parts) or file.is_symlink():
            raise SystemExit(f"Unexpected package entry: {relative}")
        data = file.read_bytes()
        if any(marker and marker.lower() in data.lower() for marker in private_markers):
            raise SystemExit(f"Developer path/name in package: {relative}")
        records.append({"path": relative, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip())
    manifest = {"version": __version__, "commit": commit, "dirty_source": dirty,
                "product_digest": product_digest(),
                "target": "windows-x64", "signing": "unsigned", "kind": "desktop-release" if "-" not in __version__ else "development-preview",
                "python": platform.python_version(), "ai": False, "files": records}
    (folder / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    archive = ROOT / "dist" / f"SessionDesk-{__version__}-windows-x64.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as out:
        for file in sorted(folder.rglob("*")):
            if file.is_file():
                out.write(file, file.relative_to(folder).as_posix())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"Windows package: {archive.name}; {len(records)} reviewed files; unsigned; AI Off")


if __name__ == "__main__":
    main()
