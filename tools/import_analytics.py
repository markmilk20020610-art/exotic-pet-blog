#!/usr/bin/env python3
"""Turn a traffic export into `analytics.json`, which drives homepage ordering.

    python tools/import_analytics.py path/to/export.csv
    python tools/import_analytics.py export.csv --merge   # add to existing counts

Accepts the CSV shape you get from Cloudflare Web Analytics, GA4 or Plausible:
a header row, a column of page paths (or full URLs) and a column of counts. The
column is found by name rather than by position, because every one of those
products names it differently — `Page`, `page`, `URL`, `Path`, `Landing Page`,
`Pageviews`, `Views`, `Sessions`, `Visitors`, `Count`.

Output is keyed by page filename, e.g. {"pet-007.html": 412}, which is what
`generate.py:load_analytics()` expects. Anything that is not an article page is
dropped, so index pages and 404s never skew the ranking.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analytics.json"

PATH_COLS = ("page", "url", "path", "landing page", "page path", "pagepath")
COUNT_COLS = ("pageviews", "views", "sessions", "visitors", "count",
              "page views", "unique visitors", "visits")

# pet-007.html, /pet-007.html, /pet-007, and a full URL all mean the same page.
ARTICLE_RE = re.compile(r"(pet-\d+)(?:\.html)?/?$")


def _pick(header: list[str], candidates: tuple[str, ...]) -> int | None:
    low = [h.strip().lower() for h in header]
    for want in candidates:
        if want in low:
            return low.index(want)
    # Fall back to a substring match, so "Pageviews (last 28 days)" still works.
    for i, h in enumerate(low):
        if any(want in h for want in candidates):
            return i
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="traffic export with a header row")
    ap.add_argument("--merge", action="store_true",
                    help="add to the existing analytics.json instead of replacing it")
    args = ap.parse_args()

    src = Path(args.csv)
    if not src.exists():
        print(f"no such file: {src}", file=sys.stderr)
        return 1

    with src.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    if len(rows) < 2:
        print("export has no data rows", file=sys.stderr)
        return 1

    header = rows[0]
    path_i = _pick(header, PATH_COLS)
    count_i = _pick(header, COUNT_COLS)
    if path_i is None or count_i is None:
        print(f"could not find a path and a count column in: {header}", file=sys.stderr)
        print(f"  looked for path in {PATH_COLS}", file=sys.stderr)
        print(f"  looked for count in {COUNT_COLS}", file=sys.stderr)
        return 1

    counts: dict[str, int] = {}
    if args.merge and OUT.exists():
        try:
            counts = json.loads(OUT.read_text(encoding="utf-8"))
        except ValueError:
            counts = {}

    skipped = 0
    for row in rows[1:]:
        if len(row) <= max(path_i, count_i):
            continue
        m = ARTICLE_RE.search(row[path_i].strip())
        if not m:
            skipped += 1
            continue
        raw = re.sub(r"[^\d]", "", row[count_i])
        if not raw:
            continue
        key = f"{m.group(1)}.html"
        counts[key] = counts.get(key, 0) + int(raw)

    if not counts:
        print("no article pages matched — check that the path column holds "
              "pet-00N.html style paths", file=sys.stderr)
        return 1

    OUT.write_text(json.dumps(dict(sorted(counts.items())), indent=1) + "\n",
                   encoding="utf-8")
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    print(f"✓ {OUT.relative_to(ROOT)} — {len(counts)} pages, {skipped} non-article rows skipped")
    for name, n in top:
        print(f"  {n:>6,}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
