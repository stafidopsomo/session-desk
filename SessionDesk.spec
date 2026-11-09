# Explicit application assets only. No source libraries, tests or user workspaces.
from pathlib import Path

root = Path(SPECPATH)
static = root / "sessiondesk" / "static"
a = Analysis([str(root / "launcher.pyw")], pathex=[str(root)],
             binaries=[], datas=[(str(static / name), "sessiondesk/static")
                for name in ("index.html", "app.js", "book.js", "style.css", "icon.svg")],
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=["playwright", "pip", "setuptools", "unittest", "pydoc"],
             noarchive=False, optimize=1)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SessionDesk",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="SessionDesk")
