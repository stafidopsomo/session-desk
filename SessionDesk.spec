# Explicit application assets only. No source libraries, tests or user workspaces.
from pathlib import Path

root = Path(SPECPATH)
static = root / "sessiondesk" / "static"
a = Analysis([str(root / "launcher.pyw")], pathex=[str(root)],
             binaries=[], datas=[(str(static / name), "sessiondesk/static")
                for name in ("index.html", "app.js", "book.js", "style.css", "icon.svg", "home.js", "home.css", "hero.svg")] +
                [(str(static / 'prepared' / name), "sessiondesk/static/prepared") for name in (
                    'index.html', 'player.html', 'shop.html', 'app.js', 'player.js', 'shop.js',
                    'after-citadel.js', 'map.js', 'tokens.js', 'characters.js', 'layout.js',
                    'appearance.js', 'reference-storage.js', 'bootstrap.js', 'style.css',
                    'refinements.css', 'opening.css', 'desk.css', 'slate.css', 'player.css',
                    'shop.css', 'tokens.css')],
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=["playwright", "pip", "setuptools", "unittest", "pydoc"],
             noarchive=False, optimize=1)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SessionDesk",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="SessionDesk")
