"""Accidental-leakage guard for the readiness tree, not a content/privacy audit."""
from pathlib import Path
import subprocess


CLEAN_ROOT = '7cecbbc5062a1d7ed6b3b6a8d614352dac716c46'
ALLOWED_FILES = frozenset({
    '.gitignore', 'AGENTS.md', 'README.md',
    '.github/workflows/readiness.yml',
    'docs/ARCHITECTURE.md', 'docs/CODEX-PREFLIGHT.md',
    'docs/IMPLEMENTATION-GATES.md', 'docs/PROVIDERS.md',
    'docs/READINESS.md', 'docs/RELEASE-PIPELINE.md',
    'tools/check_product_boundary.py', 'tools/probe_codex.py',
    'tests/test_readiness.py',
})


def inspect_boundary(roots, files):
    errors = []
    if roots != [CLEAN_ROOT]:
        errors.append('History does not have the sole approved product root')
    if not files:
        errors.append('No product files were found')
    for name, mode, data in files:
        if name not in ALLOWED_FILES:
            errors.append(f'File is outside the readiness allowlist: {name}')
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
    print(f'Readiness boundary passed: {len(files)} allowlisted text files; independent history')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
