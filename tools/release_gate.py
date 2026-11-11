"""Require exact-tree evidence and an explicit, channel-specific release decision."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sessiondesk import __version__

REQUIRED = {"owned_library_import", "clean_standard_user", "laptop_compatibility",
            "backup_restore", "privacy_audit", "frozen_browser_e2e"}
FIRST_PREVIEW = '0.1.0-preview.1'


def product_digest(root=ROOT):
    paths = [*sorted((root / "sessiondesk").rglob("*.py")),
             *sorted(p for p in (root / "sessiondesk/static").rglob('*') if p.is_file()),
             *(root / x for x in ("SessionDesk.spec", "launcher.pyw", "requirements-build.lock",
                 'requirements-e2e.lock', 'ci.ps1', '.github/workflows/readiness.yml',
                 'tools/build_windows.py', 'tools/check_product_boundary.py', 'tools/release_gate.py',
                 'docs/RELEASE-NOTES.md', "docs/QUICKSTART.txt"))]
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_text(encoding="utf-8").encode() + b"\0")
    return digest.hexdigest()


def evaluate(record, version, digest, tag):
    errors = []
    required = REQUIRED
    preview = version == FIRST_PREVIEW
    if preview:
        # The owner explicitly requested this first preview while away from the
        # laptop. This decision is limited to this tag; alpha acceptance is intact.
        decision = record.get('publication', {})
        decision = decision if isinstance(decision, dict) else {}
        deferred = decision.get('deferred', {})
        deferred = deferred if isinstance(deferred, dict) else {}
        if (record.get('preview_ready') is not True or record.get('alpha_ready') is not False
                or decision.get('channel') != 'preview' or decision.get('kind') != 'prerelease'
                or decision.get('basis') != 'owner_request'
                or decision.get('scope') != 'first_windows_preview'
                or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(decision.get('date', '')))
                or not decision.get('reason')
                or set(deferred) != {'laptop_compatibility', 'full_visual_geometry'}
                or not all(deferred.values())):
            errors.append('The first preview needs its explicit scoped publication decision and completed automated checks.')
        laptop = record.get('checks', {}).get('laptop_compatibility', {})
        if laptop.get('passed') is not False or laptop.get('status') != 'deferred':
            errors.append('The preview must retain laptop compatibility as deferred, not claim it passed.')
        required = REQUIRED - {'laptop_compatibility'}
    else:
        if record.get("alpha_ready") is not True:
            errors.append("Alpha acceptance has not been completed.")
        if not re.fullmatch(r'\d+\.\d+\.\d+-alpha\.\d+', version):
            errors.append('Only the explicitly authorized first preview or an accepted alpha can be published.')
    if record.get("version") != version or tag != "product-v" + version:
        errors.append("Tag/version must identify the accepted release exactly.")
    if record.get("product_digest") != digest:
        errors.append("Acceptance does not cover this product tree.")
    for check in sorted(required):
        proof = record.get("checks", {}).get(check, {})
        if not isinstance(proof, dict) or proof.get("passed") is not True or not proof.get("evidence"):
            errors.append("Missing acceptance evidence: " + check)
    return errors


def verify_package(archive, version, digest, commit):
    """Check the downloaded CI artifact, not just the checkout's acceptance file."""
    archive = Path(archive)
    checksum = archive.with_suffix('.zip.sha256').read_text(encoding='utf-8').split()
    if checksum != [hashlib.sha256(archive.read_bytes()).hexdigest(), archive.name]:
        raise ValueError('Release ZIP checksum does not match its companion file.')
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        if (len(names) != len(set(names)) or len(names) > 10000
                or any(n.startswith(('/', '\\')) or '\\' in n or ':' in n or '..' in n.split('/') for n in names)):
            raise ValueError('Release ZIP has invalid or unsafe entries.')
        manifest = json.loads(package.read('MANIFEST.json'))
        expected = {'version': version, 'product_digest': digest, 'commit': commit,
                    'dirty_source': False, 'target': 'windows-x64', 'signing': 'unsigned', 'ai': False}
        if any(type(manifest.get(k)) is not type(v) or manifest[k] != v for k, v in expected.items()):
            raise ValueError('Release ZIP provenance differs from the accepted commit/tree/version.')
        records = {r['path']: r for r in manifest['files']}
        if len(records) != len(manifest['files']) or set(names) != set(records) | {'MANIFEST.json'}:
            raise ValueError('Release ZIP differs from its explicit file manifest.')
        for name, record in records.items():
            data = package.read(name)
            if len(data) != record['size'] or hashlib.sha256(data).hexdigest() != record['sha256']:
                raise ValueError('Release file checksum mismatch: ' + name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag",required=True)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--commit')
    args = parser.parse_args()
    record = json.loads((ROOT / "release/acceptance.json").read_text())
    errors = evaluate(record,__version__,product_digest(),args.tag)
    if errors:
        raise SystemExit("\n".join(errors))
    if bool(args.archive) != bool(args.commit):
        parser.error('--archive and --commit must be supplied together.')
    if args.archive:
        verify_package(args.archive, __version__, product_digest(), args.commit)
    print('Publication gate passed for the accepted ' + ('first preview' if __version__ == FIRST_PREVIEW else 'alpha') + ' product tree.')


if __name__ == "__main__":
    main()
