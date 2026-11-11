"""Explicit product source allowlist, not a substitute for artifact/privacy review."""
from pathlib import Path
import subprocess


CLEAN_ROOT = '7cecbbc5062a1d7ed6b3b6a8d614352dac716c46'
ALLOWED_FILES = frozenset({
    '.gitignore', 'README.txt', 'ci.ps1', 'docs/AGENTS.md', 'docs/README.md',
    '.github/workflows/readiness.yml', '.github/README.md', '.github/ISSUE_TEMPLATE/bug_report.yml',
    'docs/ARCHITECTURE.md', 'docs/CODEX-PREFLIGHT.md',
    'docs/IMPLEMENTATION-GATES.md', 'docs/PROVIDERS.md', 'docs/MIGRATION.md',
    'docs/READINESS.md', 'docs/RELEASE-PIPELINE.md',
    'tools/check_product_boundary.py', 'tools/probe_codex.py',
    'tests/test_readiness.py',
    'SessionDesk.spec', 'launcher.pyw', 'requirements-build.lock', 'requirements-e2e.lock',
    'sessiondesk/__init__.py', 'sessiondesk/__main__.py', 'sessiondesk/importer.py',
    'sessiondesk/store.py', 'sessiondesk/server.py',
    'sessiondesk/library_setup.py',
    'sessiondesk/transfers.py',
    'sessiondesk/static/index.html', 'sessiondesk/static/app.js',
    'sessiondesk/static/book.js',
    'sessiondesk/static/style.css', 'sessiondesk/static/icon.svg',
    'tests/__init__.py', 'tests/fixtures.py', 'tests/test_core.py',
    'tests/test_setup.py',
    'tests/test_book.py', 'tests/book-renderer.test.mjs',
    'tests/test_transfers.py',
    'tools/build_windows.py', 'tools/smoke_core.py', 'tools/e2e_core.py',
    'docs/QUICKSTART.txt', 'docs/BUILD-STATUS.md',
    'tools/release_gate.py', 'release/acceptance.json', 'docs/RELEASE-NOTES.md',
    'sessiondesk/workspace_modules.py', 'sessiondesk/prepared.py',
    'sessiondesk/prepared_engine.py', 'sessiondesk/prepared_characters.py',
    'sessiondesk/prepared_rules.py', 'sessiondesk/prepared_tokens.py',
    'sessiondesk/static/prepared/index.html', 'sessiondesk/static/prepared/player.html',
    'sessiondesk/static/prepared/shop.html', 'sessiondesk/static/prepared/app.js',
    'sessiondesk/static/prepared/player.js', 'sessiondesk/static/prepared/shop.js',
    'sessiondesk/static/prepared/after-citadel.js', 'sessiondesk/static/prepared/map.js',
    'sessiondesk/static/prepared/tokens.js', 'sessiondesk/static/prepared/characters.js',
    'sessiondesk/static/prepared/layout.js', 'sessiondesk/static/prepared/appearance.js',
    'sessiondesk/static/prepared/reference-storage.js', 'sessiondesk/static/prepared/bootstrap.js',
    'sessiondesk/static/prepared/style.css', 'sessiondesk/static/prepared/refinements.css',
    'sessiondesk/static/prepared/opening.css', 'sessiondesk/static/prepared/desk.css',
    'sessiondesk/static/prepared/slate.css', 'sessiondesk/static/prepared/player.css',
    'sessiondesk/static/prepared/shop.css', 'sessiondesk/static/prepared/tokens.css',
    'tests/prepared_fixture.py', 'tests/test_prepared.py', 'tools/e2e_prepared.py',
    'tools/verify_library.py',
})


def inspect_boundary(roots, files):
    errors = []
    if roots != [CLEAN_ROOT]:
        errors.append('History does not have the sole approved product root')
    if not files:
        errors.append('No product files were found')
    for name, mode, data in files:
        if name not in ALLOWED_FILES or ('/' not in name and name.lower().endswith('.md')):
            errors.append(f'File is outside the product allowlist: {name}')
        if mode not in ('100644', '100755'):
            errors.append(f'Non-regular file is forbidden: {name}')
        if len(data) > 100_000 or b'\x00' in data:
            errors.append(f'Binary or oversized file is forbidden: {name}')
        try:
            data.decode('utf-8')
        except UnicodeDecodeError:
            errors.append(f'Non-UTF-8 file is forbidden: {name}')
    return errors


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def main():
    root = Path(__file__).resolve().parents[1]
    roots = git(root, 'rev-list', '--max-parents=0', 'HEAD').decode().splitlines()
    # Include new, non-ignored local files so the guard also helps before commit.
    names = git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')
    index = {}
    for row in git(root, 'ls-files', '-s', '-z').split(b'\x00'):
        if row:
            metadata, name = row.split(b'\t', 1)
            index[name.decode('utf-8')] = metadata.split()[0].decode()
    files = []
    for name in sorted(set(names.decode('utf-8').split('\x00')) - {''}):
        path = root / name
        mode = '120000' if path.is_symlink() else index.get(name, '100644')
        files.append((name, mode, path.read_bytes()))
    errors = inspect_boundary(roots, files)
    if errors:
        print('\n'.join(errors))
        return 1
    print(f'Product boundary passed: {len(files)} allowlisted text files; independent history')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
