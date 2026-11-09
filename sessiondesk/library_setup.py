"""Explicit, cancellable local source setup; no Git/Node or downloaded code runs."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
import uuid
import zipfile

from .importer import Library, MAX_IMAGE, UserError, confined, image_size

RELEASE = {"version": "1.221.6", "rules": "2014",
           "url": "https://github.com/5etools-mirror-3/5etools-2014-src/releases/download/v1.221.6/5etools-v1.221.6.zip",
           "sha256": "415a07ce01e09c3d5c1b9746f497b2038a082e5811a85f48981c3d22e8824591"}
IMAGE_BASE = "https://2014.5e.tools/img/"
DOWNLOAD_HOSTS = {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com", "2014.5e.tools"}


def download(url, destination, limit, cancelled, progress, opener=urlopen):
    if urlsplit(url).scheme != "https" or urlsplit(url).hostname not in DOWNLOAD_HOSTS:
        raise UserError("Unsupported download source.")
    try:
        with opener(Request(url, headers={"User-Agent": "SessionDesk-local-setup/0.1"}), timeout=25) as response:
            final = urlsplit(response.geturl())
            if final.scheme != "https" or final.hostname not in DOWNLOAD_HOSTS:
                raise UserError("Unexpected download redirect.")
            total = int(response.headers.get("Content-Length", "0"))
            if total > limit:
                raise UserError("Download exceeds the supported size.")
            count, digest = 0, hashlib.sha256()
            with Path(destination).open("wb") as out:
                while True:
                    if cancelled():
                        raise UserError("Operation cancelled.")
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > limit:
                        raise UserError("Download exceeds the supported size.")
                    out.write(chunk)
                    digest.update(chunk)
                    progress(count, total)
            if total and count != total:
                raise UserError("Download was interrupted. Retry when the connection is available.")
            return digest.hexdigest()
    except HTTPError as exc:
        raise UserError(f"Source download returned HTTP {exc.code}. Retry or select an existing local copy.") from exc
    except (URLError, TimeoutError) as exc:
        raise UserError("Source download failed. Check your connection or select an existing local copy.") from exc


def extract_source(archive, destination, cancelled):
    """No extractall: reject traversal, links, case collisions and archive bombs."""
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive) as package:
        files = package.infolist()
        names = [x.filename for x in files]
        if len(files) > 50000 or sum(x.file_size for x in files) > 1024 ** 3:
            raise UserError("Source archive exceeds supported limits.")
        indices = [n for n in names if n.endswith("data/adventures.json")]
        if len(indices) != 1:
            raise UserError("Downloaded archive is not a supported source library.")
        prefix = indices[0][:-len("data/adventures.json")]
        seen = set()
        for entry in files:
            if cancelled():
                raise UserError("Installation cancelled; destination unchanged.")
            if prefix and not entry.filename.startswith(prefix):
                if entry.is_dir():
                    continue
                raise UserError("Unexpected source archive layout.")
            name = entry.filename[len(prefix):]
            if not name:
                continue
            if "\\" in name or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise UserError("Archive links/unsafe paths are not supported.")
            target = confined(destination, name)
            key = str(PurePosixPath(name)).casefold()
            if key in seen:
                raise UserError("Source archive contains duplicate/colliding paths.")
            seen.add(key)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.open(entry) as source, target.open("xb") as out:
                    while chunk := source.read(256 * 1024):
                        if cancelled():
                            raise UserError("Installation cancelled; destination unchanged.")
                        out.write(chunk)


class LibrarySetup:
    def __init__(self, data_root):
        self.settings = Path(data_root) / "libraries.json"

    def options(self):
        return {"version": RELEASE["version"], "rules": "2014", "download_mb": 45,
                "image_mode": "Adventure images download when you import; this is not the complete image archive."}

    def config(self):
        if not self.settings.exists():
            return {}
        try:
            value = json.loads(self.settings.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def install(self, location, include_images, cancelled, progress, fetch=download, release=RELEASE, on_commit=lambda: None):
        if not isinstance(location, str) or not location.strip():
            raise UserError("Choose an installation folder.")
        destination = Path(location).expanduser().absolute()
        if destination.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
            raise UserError("Choose a source-library location outside the application folder.")
        if destination.is_symlink() or (destination.exists() and (not destination.is_dir() or any(destination.iterdir()))):
            raise UserError("Choose a new or empty folder. Existing local copies are never overwritten.")
        parent = destination.parent.resolve()
        parent.mkdir(parents=True, exist_ok=True)
        stage = parent / (".sessiondesk-install-" + str(uuid.uuid4()))
        stage.mkdir()
        try:
            archive = stage / "source.zip"
            progress("Downloading verified 2014 source copy", 0, 0)
            digest = fetch(release["url"], archive, 128 * 1024 * 1024, cancelled,
                           lambda done, total: progress("Downloading source copy", done, total))
            if digest != release["sha256"]:
                raise UserError("Source checksum failed. Nothing was installed; retry the download.")
            content = stage / "library"
            content.mkdir()
            progress("Extracting and validating local copy", 0, 0)
            extract_source(archive, content, cancelled)
            Library(content).validate()
            if cancelled():
                raise UserError("Installation cancelled; destination unchanged.")
            on_commit()
            # Do not replace a folder that became non-empty while downloading.
            if destination.exists():
                if any(destination.iterdir()):
                    raise UserError("Destination changed during installation; choose another folder.")
                destination.rmdir()
            content.replace(destination)
            config = self.config()
            config[str(destination.resolve())] = {"images": bool(include_images), "version": release["version"]}
            temp = self.settings.with_suffix(".tmp")
            temp.write_text(json.dumps(config), encoding="utf-8")
            temp.replace(self.settings)
            return self.validate(destination)
        finally:
            # Only this newly-created staging directory may be removed recursively.
            if stage.resolve().is_relative_to(parent) and stage.name.startswith(".sessiondesk-install-"):
                shutil.rmtree(stage)

    def validate(self, location, images=None):
        library = Library(location, images)
        result = library.validate()
        managed = self.config().get(str(library.root), {})
        result["download_images"] = managed.get("images") is True and not images
        return result

    def fetcher(self, library):
        if self.config().get(str(library.root), {}).get("images") is not True:
            return None
        # The registry is app-owned consent, not instructions read from a source book.
        expected_root = (library.root / "img").resolve()
        if library.images.resolve() != expected_root or not expected_root.is_relative_to(library.root):
            return None
        def fetch_image(relative, destination, cancelled):
            destination = confined(expected_root, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            temp = destination.with_name(destination.name + ".sessiondesk-download")
            try:
                download(IMAGE_BASE + quote(relative, safe="/"), temp, MAX_IMAGE, cancelled, lambda *_: None)
                image_size(temp.read_bytes())
                if cancelled():
                    raise UserError("Import cancelled.")
                temp.replace(destination)
            finally:
                temp.unlink(missing_ok=True)
        return fetch_image
