#!/usr/bin/env python3
"""Pull one CC-licensed species photo from Wikimedia Commons.

    python tools/fetch_species_image.py sugar-glider.jpg "Petaurus breviceps"
    python tools/fetch_species_image.py bearded-dragon.jpg "Pogona vitticeps" \
        --query "Pogona vitticeps head"

Why this exists: the topic queue refuses to publish an article without artwork
(`grow()` gates on the image file existing), and hot-linking a stock photo is
not an option — the site ships every image locally and records the licence in
`static/images/credits.json`.

Search is by the Latin binomial because common names collide badly on Commons
("sugar glider" returns toys and logos). The first hit whose licence is
redistributable wins; anything non-free is skipped rather than guessed at.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "static" / "images"
CREDITS = IMAGES / "credits.json"
API = "https://commons.wikimedia.org/w/api.php"
UA = "exotic-pet-blog/1.0 (image sourcing for a static site)"

# 3:2 at the size the article figure is rendered at, matching every other photo.
TARGET_W, TARGET_H = 1536, 1024

OK_LICENCES = ("cc0", "cc by", "cc-by", "public domain", "pd")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read()


def _api(params: dict) -> dict:
    params = {**params, "format": "json", "formatversion": "2"}
    return json.loads(_get(API + "?" + urllib.parse.urlencode(params)))


def search(query: str, limit: int = 12) -> list[dict]:
    """File candidates for a query, with licence metadata and a download URL."""
    data = _api({
        "action": "query",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size",
        "iiurlwidth": str(TARGET_W),
    })
    out = []
    for page in data.get("query", {}).get("pages", []):
        info = (page.get("imageinfo") or [{}])[0]
        if not info.get("thumburl"):
            continue
        meta = info.get("extmetadata", {})
        lic = (meta.get("LicenseShortName", {}).get("value") or "").strip()
        out.append({
            "title": page["title"].removeprefix("File:"),
            "url": info["thumburl"],
            "width": info.get("width", 0),
            "height": info.get("height", 0),
            "license": lic,
            "license_url": meta.get("LicenseUrl", {}).get("value", ""),
            "artist": meta.get("Artist", {}).get("value", ""),
            "page": info.get("descriptionurl", ""),
        })
    return out


def _clean_artist(html: str) -> str:
    """extmetadata returns HTML; strip tags and entities for a plain credit line."""
    import html as _html
    import re
    text = re.sub(r"<[^>]+>", "", _html.unescape(html or ""))
    return re.sub(r"\s+", " ", text).strip()[:80] or "Unknown"


def crop_to_ratio(data: bytes) -> Image.Image:
    """Centre-crop to 3:2 and resize, so every figure in the grid lines up."""
    im = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = im.size
    want = TARGET_W / TARGET_H
    if w / h > want:
        new_w = int(h * want)
        im = im.crop(((w - new_w) // 2, 0, (w + new_w) // 2, h))
    else:
        new_h = int(w / want)
        im = im.crop((0, (h - new_h) // 2, w, (h + new_h) // 2))
    return im.resize((TARGET_W, TARGET_H), Image.LANCZOS)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("filename", help="target file name, e.g. sugar-glider.jpg")
    ap.add_argument("query", help="search query — use the Latin binomial")
    ap.add_argument("--pick", type=int, default=0,
                    help="skip N accepted candidates (when the first is unusable)")
    args = ap.parse_args()

    free = [c for c in search(args.query)
            if any(k in c["license"].lower() for k in OK_LICENCES)]
    if not free:
        print(f"no redistributable image for {args.query!r}", file=sys.stderr)
        return 1

    for cand in free[args.pick:]:
        try:
            data = _get(cand["url"])
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {cand['title'][:50]}: {exc}")
            continue
        try:
            im = crop_to_ratio(data)
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {cand['title'][:50]}: {exc}")
            continue

        dest = IMAGES / args.filename
        im.save(dest, "JPEG", quality=86, optimize=True, progressive=True)

        credits = json.loads(CREDITS.read_text(encoding="utf-8")) \
            if CREDITS.exists() else {}
        credits[args.filename] = {
            "title": cand["title"],
            "artist": _clean_artist(cand["artist"]),
            "license": cand["license"],
            "license_url": cand["license_url"],
            "page": cand["page"],
        }
        CREDITS.write_text(json.dumps(credits, indent=1, ensure_ascii=False) + "\n",
                           encoding="utf-8")

        print(f"✓ {dest.relative_to(ROOT)}  {im.size[0]}×{im.size[1]}  "
              f"{dest.stat().st_size // 1024} KB")
        print(f"  {cand['title']} — {_clean_artist(cand['artist'])} ({cand['license']})")
        print(f"  {cand['page']}")
        return 0

    print("every candidate failed to download", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
