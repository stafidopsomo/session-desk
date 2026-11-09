"""Generate an original miniature library at runtime, without bundled book data."""
import json
from pathlib import Path
import struct
import zlib


def png(width=900, height=600):
    rows = []
    for y in range(height):
        row = bytearray(b"\0")
        for x in range(width):
            room = (80 < x < 390 and 100 < y < 450) or (510 < x < 820 and 100 < y < 450)
            wall = room and (x % 40 < 2 or y % 40 < 2)
            row.extend((64, 76, 88) if wall else (182, 174, 154) if room else (28, 34, 42))
        rows.append(row)
    def chunk(kind, content):
        return struct.pack(">I", len(content)) + kind + content + struct.pack(">I", zlib.crc32(kind + content))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b"")


def make_library(root, wrapped=False):
    root = Path(root)
    (root / "data" / "adventure").mkdir(parents=True)
    (root / "img" / "original").mkdir(parents=True)
    (root / "img" / "original" / "map.png").write_bytes(png())
    image = {"type": "image", "imageType": "map", "title": "Observatory floor",
             "href": {"type": "internal", "path": "original/map.png"}, "width": 900, "height": 600,
             "mapRegions": [{"area": "platform-A", "points": [[85,105],[385,105],[385,445],[85,445]]},
                            {"area": "lens", "points": [[600,200],[650,200],[650,250],[600,250]]}]}
    source = {"data": [
        {"type": "section", "name": "The observatory", "entries": [
            {"name": "Arrival platform", "id": "platform-A", "entries": ["A quiet platform under a glass roof.", "DM_ONLY_SYNTHETIC_SECRET"]},
            {"name": "The suspended lens", "id": "lens", "entries": ["A brass lens hangs from a chain."]}, image,
            {"type": "image", "title": "Evening sky", "href": {"type": "internal", "path": "original/map.png"}}]},
        {"name": "The lower gallery", "entries": [
            {"name": "Lower platform", "id": "platform-A", "entries": ["A second, different platform."]},
            {**image, "title": "Gallery floor", "mapRegions": [image["mapRegions"][0]]},
            {**image, "title": "Unkeyed roof", "mapRegions": []},
            {**image, "title": "Uncertain scale", "width": 450}]}]}
    (root / "data" / "adventures.json").write_text(json.dumps({"adventure": [
        {"id": "DEMO", "name": "The Glass Observatory"}]}), encoding="utf-8")
    path = root / "data" / "adventure" / "adventure-demo.json"
    if wrapped:
        source = {"adventureData": [{"id": "DEMO", "source": "DEMO", "data": source["data"]}]}
    path.write_text(json.dumps(source), encoding="utf-8")
    return root
