"""Read explicitly selected 5e.tools sources. Never search neighbouring libraries."""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
import uuid


class UserError(ValueError):
    pass


MAX_JSON = 48 * 1024 * 1024
MAX_IMAGE = 48 * 1024 * 1024
MAX_TOTAL = 1024 * 1024 * 1024
RASTER = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
          ".webp": "image/webp", ".gif": "image/gif"}


def stable(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, json.dumps(parts, ensure_ascii=False)))


def read_json(path):
    if path.stat().st_size > MAX_JSON:
        raise UserError("Source JSON is too large (48 MB maximum).")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise UserError("Invalid source JSON. Select an unmodified local library.") from exc


def confined(root, relative):
    relative = str(relative).replace("\\", "/")
    pieces = PurePosixPath(relative)
    if pieces.is_absolute() or ".." in pieces.parts or ":" in relative:
        raise UserError("Unsafe source path rejected.")
    root = Path(root).resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise UserError("Source symlink leaves the selected library.")
    return target


def plain(value):
    if not isinstance(value, str):
        return ""
    # 5e.tools inline tags: keep display text, never interpret HTML or scripts.
    def display(match):
        parts = match[1].split("|")
        return parts[2] if len(parts) >= 3 and parts[2] else parts[0]
    for _ in range(8):
        changed = re.sub(r"\{@\w+ ([^{}]*)}", display, value)
        if changed == value:
            break
        value = changed
    return value


def text_content(node):
    if isinstance(node, str):
        return plain(node)
    if isinstance(node, list):
        return "\n\n".join(filter(None, (text_content(x) for x in node)))
    if not isinstance(node, dict) or node.get("type") == "image":
        return ""
    values = []
    if node.get("name"):
        values.append(plain(node["name"]))
    for key in ("entry", "entries", "items", "rows", "row", "text", "caption"):
        if key in node:
            values.append(text_content(node[key]))
    return "\n\n".join(filter(None, values))


def image_size(data):
    """Read raster dimensions only; images are decoded by the browser, not executed."""
    try:
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return struct.unpack(">II", data[16:24]), "image/png"
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", data[6:10]), "image/gif"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            kind = data[12:16]
            if kind == b"VP8X":
                return (1 + int.from_bytes(data[24:27], "little"),
                        1 + int.from_bytes(data[27:30], "little")), "image/webp"
            if kind == b"VP8L" and data[20] == 0x2f:
                bits = int.from_bytes(data[21:25], "little")
                return ((bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1), "image/webp"
            if kind == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
                w, h = struct.unpack("<HH", data[26:30])
                return (w & 0x3fff, h & 0x3fff), "image/webp"
        if data[:2] == b"\xff\xd8":
            pos = 2
            while pos < len(data):
                if data[pos] != 255:
                    break
                while data[pos] == 255:
                    pos += 1
                marker = data[pos]
                pos += 1
                if marker in (0xd8, 0xd9) or 0xd0 <= marker <= 0xd7:
                    continue
                length = int.from_bytes(data[pos:pos + 2], "big")
                if length < 2:
                    break
                if marker in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7,
                              0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
                    h, w = struct.unpack(">HH", data[pos + 3:pos + 7])
                    return (w, h), "image/jpeg"
                pos += length
    except (IndexError, struct.error):
        pass
    raise UserError("Unsupported or damaged image. Use PNG, JPEG, WebP or GIF.")


def polygon(value, width, height):
    if not isinstance(value, list) or not 3 <= len(value) <= 2000:
        raise UserError("A region needs 3–2000 points.")
    out = []
    for point in value:
        if not isinstance(point, list) or len(point) != 2:
            raise UserError("Invalid region point.")
        x, y = point
        if (type(x) not in (int, float) or type(y) not in (int, float)
                or not math.isfinite(x) or not math.isfinite(y)
                or not 0 <= x <= width or not 0 <= y <= height):
            raise UserError("Region points must be inside this map's pixel dimensions.")
        out.append([x, y])
    area = abs(sum(out[i][0] * out[(i + 1) % len(out)][1]
                   - out[(i + 1) % len(out)][0] * out[i][1]
                   for i in range(len(out)))) / 2
    if area < 1:
        raise UserError("Region has no usable area.")
    return out


class Library:
    def __init__(self, path, images=None):
        self.root = Path(path).expanduser().resolve()
        self.images = Path(images).expanduser().resolve() if images else self.root / "img"
        self.data = self.root / "data" if (self.root / "data").is_dir() else self.root
        if not (self.data / "adventures.json").is_file():
            raise UserError("Select a library containing data/adventures.json (or its data folder).")
        if not self.data.resolve().is_relative_to(self.root) or (self.data / "adventures.json").is_symlink():
            raise UserError("Source index/data directory leaves the selected library.")
        if not images and self.data == self.root:
            self.images = self.root.parent / "img"  # exact conventional library location only

    def inventory(self):
        raw = read_json(self.data / "adventures.json")
        items = raw.get("adventure") if isinstance(raw, dict) else None
        if not isinstance(items, list):
            raise UserError("Unsupported index schema: expected an adventure list.")
        return [{"id": str(x["id"]), "name": plain(x.get("name", x["id"])),
                 "available": self.source_path(str(x["id"])).is_file()}
                for x in items if isinstance(x, dict) and x.get("id")]

    def source_path(self, source):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", source):
            raise UserError("Invalid adventure source ID.")
        return confined(self.data, f"adventure/adventure-{source.lower()}.json")

    def load(self, source, cancelled=lambda: False):
        meta = next((x for x in self.inventory() if x["id"].lower() == source.lower()), None)
        if not meta or not meta["available"]:
            raise UserError("Adventure data is missing from the selected library.")
        source = meta["id"]
        raw = read_json(self.source_path(source))
        chapters = raw.get("data") if isinstance(raw, dict) else None
        if not isinstance(chapters, list):
            wrapper = raw.get("adventureData", {}) if isinstance(raw, dict) else {}
            chapters = wrapper.get("data")
        if not isinstance(chapters, list) or not chapters:
            raise UserError("Unsupported adventure schema: expected data chapters.")
        aid = stable("5etools", source.lower())
        graph = {"id": aid, "name": meta["name"], "source": source,
                 "adapter": "5etools-local-v1", "entries": [], "maps": [], "pictures": [],
                 "warnings": [], "source_fingerprint": hashlib.sha256(
                     json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
        blobs, images, lookup = {}, [], {}
        count = 0

        def walk(node, trail, chapter, parent=None):
            nonlocal count
            count += 1
            if cancelled():
                raise UserError("Import cancelled; workspace unchanged.")
            if count > 250000 or len(trail) > 100:
                raise UserError("Adventure structure exceeds supported limits.")
            if isinstance(node, list):
                for i, child in enumerate(node):
                    walk(child, trail + [i], chapter, parent)
            elif isinstance(node, dict):
                if node.get("type") == "image":
                    images.append((node, trail, chapter, parent))
                    return
                entry_id = parent
                if node.get("name") or node.get("id"):
                    entry_id = stable(aid, "entry", trail)
                    title = plain(node.get("name", str(node.get("id", "Untitled"))))
                    entry = {"id": entry_id, "key": str(node.get("id", "")), "name": title,
                             "chapter": chapter, "parent": parent, "path": trail,
                             "text": text_content(node), "locator": {"source": source,
                             "chapter": chapter, "entry": node.get("id"), "path": trail}}
                    graph["entries"].append(entry)
                    if entry["key"]:
                        lookup.setdefault(entry["key"], []).append(entry)
                for key, value in node.items():
                    if key not in ("mapParent", "href", "mapRegions") and isinstance(value, (dict, list)):
                        walk(value, trail + [key], chapter, entry_id)

        for i, chapter in enumerate(chapters):
            walk(chapter, [i], i)
        for node, trail, chapter, parent in images:
            if cancelled():
                raise UserError("Import cancelled; workspace unchanged.")
            href = node.get("href", {})
            path = href.get("path") if isinstance(href, dict) else None
            if not path or href.get("type", "internal") != "internal":
                graph["warnings"].append("External image skipped; no downloads are performed.")
                continue
            try:
                image = confined(self.images, path.removeprefix("img/"))
                if image.suffix.lower() not in RASTER or not image.is_file():
                    raise UserError(f"Missing/unsupported local image: {path}")
                if image.stat().st_size > MAX_IMAGE:
                    raise UserError(f"Image exceeds 48 MB: {path}")
                data = image.read_bytes()
                (w, h), mime = image_size(data)
                if not 0 < w <= 30000 or not 0 < h <= 30000 or w * h > 100000000:
                    raise UserError(f"Image dimensions exceed supported limits: {path}")
                digest = hashlib.sha256(data).hexdigest()
                blobs[digest] = (mime, data)
                if sum(len(x[1]) for x in blobs.values()) > MAX_TOTAL:
                    raise UserError("Imported images exceed 1 GB; import a smaller adventure.")
                record = {"id": stable(aid, "image", trail), "name": plain(node.get("title") or
                          node.get("mapName") or image.stem), "asset": digest, "width": w,
                          "height": h, "chapter": chapter, "entry": parent,
                          "source_path": path, "regions": [], "player_safe": False}
                is_map = bool(node.get("mapRegions") or node.get("imageType") in ("map", "mapPlayer"))
                record["kind"] = "map" if is_map else "picture"
                record["safety_note"] = "Review for labels, secrets and spoilers before sharing."
                source_w, source_h = node.get("width"), node.get("height")
                dims_match = source_w == w and source_h == h
                for idx, region in enumerate(node.get("mapRegions", [])):
                    matches = lookup.get(str(region.get("area", "")), [])
                    nearby = [e for e in matches if e["chapter"] == chapter]
                    matches = nearby or matches
                    try:
                        points = polygon(region.get("points"), w, h) if dims_match else []
                    except UserError:
                        points = []
                    record["regions"].append({"id": stable(record["id"], "region", idx),
                        "key": str(region.get("area", "")), "name": matches[0]["name"]
                        if len(matches) == 1 else str(region.get("area", f"Region {idx + 1}")),
                        "entry": matches[0]["id"] if len(matches) == 1 else None,
                        "points": points, "source_points": region.get("points", []),
                        "role": "unknown", "verified": False,
                        "review_note": "Check extent/role against image; source polygons may mark a feature."
                        if points else "Dimensions/geometry uncertain; draw a boundary manually."})
                graph["maps" if is_map else "pictures"].append(record)
            except (OSError, UserError) as exc:
                graph["warnings"].append(str(exc) if isinstance(exc, UserError) else f"Cannot read image: {path}")
        if len(graph["warnings"]) > 500:
            graph["warnings"] = graph["warnings"][:500] + ["Further warnings omitted."]
        # Include asset hashes: a changed source image is a changed import, even with identical JSON.
        graph["fingerprint"] = hashlib.sha256((graph["source_fingerprint"] +
                            "".join(sorted(blobs))).encode()).hexdigest()
        return graph, blobs
