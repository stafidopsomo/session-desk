"""Fail closed on alpha publication until evidence covers this exact product tree."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sessiondesk import __version__

REQUIRED = {"owned_library_import", "clean_standard_user", "laptop_compatibility",
            "backup_restore", "privacy_audit", "frozen_browser_e2e"}


def product_digest(root=ROOT):
    paths = [*sorted((root / "sessiondesk").rglob("*.py")),
             *sorted((root / "sessiondesk/static").iterdir()),
             *(root / x for x in ("SessionDesk.spec", "launcher.pyw", "requirements-build.lock", "docs/QUICKSTART.txt"))]
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_text(encoding="utf-8").encode() + b"\0")
    return digest.hexdigest()


def evaluate(record, version, digest, tag):
    errors = []
    if record.get("alpha_ready") is not True:
        errors.append("Alpha acceptance has not been completed.")
    if record.get("version") != version or tag != "product-v" + version or "alpha" not in version:
        errors.append("Tag/version must identify the accepted alpha; development previews cannot be published as alpha.")
    if record.get("product_digest") != digest:
        errors.append("Acceptance does not cover this product tree.")
    for check in sorted(REQUIRED):
        proof = record.get("checks", {}).get(check, {})
        if not isinstance(proof, dict) or proof.get("passed") is not True or not proof.get("evidence"):
            errors.append("Missing acceptance evidence: " + check)
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag",required=True)
    args = parser.parse_args()
    record = json.loads((ROOT / "release/acceptance.json").read_text())
    errors = evaluate(record,__version__,product_digest(),args.tag)
    if errors:
        raise SystemExit("\n".join(errors))
    print("Alpha publication gate passed for the accepted product tree.")


if __name__ == "__main__":
    main()
