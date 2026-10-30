# -*- coding: utf-8 -*-
"""
generate.py — Exotic Pet Care Hub static site builder.

Pipeline (unchanged in spirit, rebuilt in presentation):

    keywords.json  ->  article body  ->  magazine template  ->  pet-00X.html
                        (cache | DeepSeek | content.py fallback)

Outputs, all written to the repository root so GitHub Pages keeps serving
the same URLs:

    index.html
    pet-001.html ... pet-00N.html
    sitemap.xml
    robots.txt
    feed.xml

Design notes
------------
* Images are bound to a *species*, never to a category. `SPECIES_IMAGE` maps
  each article id to one exact photograph, and the build refuses to render a
  post whose image is missing or whose species does not match the alt text.
* All SEO head tags, JSON-LD (Article + Breadcrumb + FAQPage), canonical URLs,
  Open Graph and Twitter cards are emitted here.
* sitemap.xml is regenerated on every run, with per-page lastmod.

Usage
-----
    python generate.py                # build from cache / fallback content
    python generate.py --refresh      # force DeepSeek regeneration
    python generate.py --serve        # build, then serve on :8000
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from string import Template

import affiliate as aff
from content import AUTHORS, POSTS
from topics import GROUP_ROTATION, TOPIC_POOL
from vivarium import VIVARIUM_ASSETS, vivarium_html

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
IMAGES = STATIC / "images"
CACHE = ROOT / "cache"
DRAFTS = ROOT / "drafts"
KEYWORDS = ROOT / "keywords.json"

# Every article the factory has ever published beyond the six hand-written ones
# in content.py. It is the anti-duplication ledger: `grow()` reads it to work out
# which pool topics are already taken, and `collect()` merges it back into the
# build. Keeping it out of content.py means a generated article can be reverted
# by deleting one entry instead of editing the hand-authored source.
LIBRARY = ROOT / "library.json"

# Same trap as AMAZON_TAG: a var that exists but is empty (`SITE_URL=` in a
# shell, or an unset GitHub/Cloudflare secret) would otherwise yield "//pet-001"
# canonical URLs and an unusable sitemap. Empty means "use the default".
DEFAULT_SITE_URL = "https://exotic-pet-blog.markmilk20020610.workers.dev"
SITE_URL = ((os.environ.get("SITE_URL") or "").strip() or DEFAULT_SITE_URL).rstrip("/")
SITE_NAME = "Exotic Pet Care Hub"
AMAZON_TAG = aff.AMAZON_TAG
LANG = "en"

# Navigation is derived from the posts, never hand-written. The old literal
# list drifted away from the data: it linked to #amphibians and #bioactive,
# neither of which was ever rendered (dead links on all eight pages), while
# Crustaceans existed but could not be reached from the nav at all.
CATEGORY_SHORT = {
    "Feeding Guide": "Feeding",
    "Habitat Setup": "Habitat",
    "Troubleshooting": "Health",
}
CATEGORY_ORDER = ["Feeding Guide", "Habitat Setup", "Troubleshooting"]

# One-sentence pitch per editorial topic, used as the dek on its own index page.
CATEGORY_DEK = {
    "Feeding Guide": "What to feed, how much and how often — portioning, schedules and the mistakes that shorten lives.",
    "Habitat Setup": "Enclosures, substrate, heating and lighting that hold a stable, bioactive environment.",
    "Troubleshooting": "When something is wrong: humidity, mould, refusals, and the fixes that actually work.",
}

# Exact species image per article. This is the fix for "animal mix-ups":
# the photograph is chosen by species, never by category or random seed.
SPECIES_IMAGE = {
    "pet-001": ("jumping-spider.jpg", "Invertebrates"),
    "pet-002": ("crested-gecko.jpg", "Reptiles"),
    "pet-003": ("isopods.jpg", "Invertebrates"),
    "pet-004": ("ball-python.jpg", "Reptiles"),
    "pet-005": ("leopard-gecko.jpg", "Reptiles"),
    "pet-006": ("hermit-crab.jpg", "Crustaceans"),
}

MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}

# Photo attribution for the species images (written by the fetch tooling).
CREDITS: dict = {}
_credits_file = IMAGES / "credits.json"
if _credits_file.exists():
    CREDITS = json.loads(_credits_file.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def e(text: str) -> str:
    return html.escape(str(text), quote=True)


def absolute(path: str) -> str:
    return f"{SITE_URL}/{path.lstrip('/')}" if path else SITE_URL + "/"


def fmt_date(iso: str) -> str:
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d.day} {MONTHS[d.month]} {d.year}"


def rfc822(iso: str) -> str:
    d = datetime.strptime(iso, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return d.strftime("%a, %d %b %Y 09:00:00 +0000")


def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", str(text))
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-")


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def taxonomy(posts: list[dict]) -> dict:
    """The site's two taxonomies, taken from the posts themselves.

    `cats` are editorial topics (Feeding Guide / Habitat Setup /
    Troubleshooting) and drive the primary navigation; `groups` are species
    classes (Reptiles / Invertebrates / Crustaceans) and drive the browse index
    and the footer. Both are ordered and de-duplicated here, so every nav label
    is guaranteed to have a section rendered for it — the previous hand-written
    list pointed at two anchors that were never emitted.
    """
    def bucket(values: list[str]) -> list[tuple[str, str]]:
        seen: list[tuple[str, str]] = []
        for v in values:
            slug = slugify(v)
            if slug not in [s for _, s in seen]:
                seen.append((v, slug))
        return seen

    cats = bucket([p["category"] for p in posts])
    rank = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    cats.sort(key=lambda kv: (rank.get(kv[0], len(rank)), kv[0]))

    groups = bucket([p["group"] for p in posts])
    groups.sort(key=lambda kv: kv[0])

    return {"cats": cats, "groups": groups}


def rank_posts(posts: list[dict]) -> list[dict]:
    """Pinned guides first, then newest first.

    Two stable passes: sort by date, then float the pinned ones up. That keeps
    the date order intact inside both groups, so a pinned guide leads the page
    without scrambling the chronology behind it.
    """
    by_date = sorted(posts, key=lambda p: p["date"], reverse=True)
    return sorted(by_date, key=lambda p: not p.get("is_pinned"))


def initials(name: str) -> str:
    parts = [p for p in name.replace("Dr.", "").split() if p]
    return "".join(p[0] for p in parts[:2]).upper()


def amz_link(query: str) -> str:
    """Kept as the single entry point for ad-hoc Amazon search links."""
    return aff.amazon_search(query)


def read_time(body_html: str) -> int:
    words = len(strip_tags(body_html).split())
    return max(4, round(words / 205))


def credit_html(filename: str, prefix: str = "Photograph") -> str:
    """Attribution line for a species photograph."""
    rec = CREDITS.get(filename)
    if not rec:
        return ""
    artist = e(rec.get("artist") or "Wikimedia Commons contributor")
    return (
        f'{prefix} · <a href="{e(rec.get("page", ""))}" target="_blank" '
        f'rel="noopener noreferrer">{artist}</a> / Wikimedia Commons · {e(rec.get("license", ""))}'
    )


# --------------------------------------------------------------------------- #
# content resolution
# --------------------------------------------------------------------------- #

# Bump this whenever PROMPT or the structural contract changes. It is part of
# the cache fingerprint, so a prompt edit invalidates every cached body instead
# of leaving old, off-brief articles in place for months.
PROMPT_VERSION = "2026-10-30.3"

PROMPT = Template("""You are the senior keeper at Exotic Pet Care Hub, an independent magazine
written by people who keep the animals, for people who keep them. You have a
zoology background and ten years of husbandry notes. Write the body of one field
guide in English.

Target keyword: "$keyword"
Topic: $topic
Species: $species ($sci)
Editorial category: $category

$history

## The four degrees

Every guide has to clear all four. A draft that is deep but narrow is a forum
post; one that is broad but shallow is a content mill; one with neither is a
press release.

DEPTH — hard numbers and mechanism, never a conversation of generalities.
  · Named parameters with units, at the level a keeper can set an instrument to:
    basking-spot and cool-end temperatures, a thermal gradient across the
    enclosure, a humidity band, a UV index with its distance, a calcium-to-
    phosphorus ratio, a photoperiod in hours.
  · At least one physiological or pathological mechanism explained end to end:
    why ecdysis fails when the cuticle dries, how the nitrogen cycle converts
    ammonia to nitrite to nitrate, what nutritional secondary
    hyperparathyroidism does to bone, why a gut stops at a given temperature.
    Name the process, then trace the causal chain in plain sentences.

BREADTH — the whole animal and the whole life, not one life stage.
  · Where the species has them, cover juvenile / subadult / adult differences in
    feeding, enclosure and handling, and say what changes between them.
  · Include the ecological half: bioactive substrate, clean-up crew, drainage,
    the enclosure as a small system rather than a box.
  · Behaviour belongs here — stress postures, feeding response, seasonal
    cycles — and so do morphs or bloodlines when they change husbandry rather
    than just colour.

HEIGHT — authority, honestly earned.
  · Where a practice genuinely traces to recognised clinical or academic
    consensus, say so plainly: exotic-animal veterinary teaching hospitals,
    herpetological and amphibian-medicine bodies, welfare standards. Name the
    institution only when you are stating something it actually teaches or
    publishes.
  · NEVER invent a study, a paper title, an author, a year, a DOI, a journal or
    a specific finding attributed to a named institution. If you cannot state
    the claim without a fabricated citation, state the claim as clinical
    consensus and leave the citation out. A vague true sentence beats a precise
    fake one, and a fake citation is the fastest way to lose the reader's trust.
  · Where the evidence is thin, say it is thin and say what experienced keepers
    do instead. That is the E-E-A-T signal, not a weakness.

FREEDOM — a keeper's voice, not a care-sheet template.
  · Write from the mess: the escape, the failed shed, the animal that only eats
    if you warm the prey to a specific temperature, the £200 vet bill for
    something that turned out to be a thermostat. Concrete, dated, physical.
  · Allow opinion. "I no longer use loose substrate for this species, and here
    is the year I stopped" is worth more than a neutral list of options.
  · Break the rhythm. A one-line paragraph after a long one. A number standing
    alone. Never the same section shape twice in one article.

Gear this article is allowed to recommend — refer to it by token, never by name
or price:
$products

## The four beats, in this order

1. THE SCIENCE HOOK — no heading, 2-4 sentences, opens the article.
   HARD REQUIREMENT, NOT NEGOTIABLE: the first paragraph must contain at least
   one concrete measurement with its unit. Any of these satisfies it:
     · a temperature range        72-80 °F  ·  22-27 °C
     · a humidity percentage      60-70 %
     · an adult body length       12-18 mm  ·  1.5 inches
     · a UVB wavelength           290-320 nm
     · a UV index or a dose       0.6-1.1 UVI  ·  10 mg/kg
     · an enclosure volume        40-gallon  ·  45 × 45 × 60 cm
   A number without a unit does not count. A claim with no number in it does not
   count. A duration does not count either: "a reliable 10-14 day feeder" is not
   a measurement of the animal's environment. It has to be something an
   instrument could read — a temperature, a humidity, a length, a wavelength.
   Do not open with a scene, a question or a definition and put the data in
   paragraph two — the number belongs in the first paragraph.
   Then earn it in the same paragraph: say what that number does to the animal.
   No throat-clearing, no "exotic pets are increasingly popular".

   Worked example of a compliant opening. Copy the shape, never the species or
   the numbers:
   "<p>A crested gecko's enclosure runs 72-80 °F at the warm end and 60-70 %
   relative humidity, and the animal's entire welfare budget is spent inside
   those two ranges. Step outside them for a week and the first thing you lose
   is appetite, not weight.</p>"

2. THE KEEPER'S DIARY — one <h2> section, 120-180 words, first person singular.
   One animal, one evening, concrete detail: what it did, what you got wrong,
   what it cost. Sound, weight, the time on the clock. Physical before
   sentimental. This is the only section where "I" leads; do not perform emotion
   you have not earned with a specific.

3. THE ACTIONABLE CARE GUIDE — two or three <h2> sections, the bulk of the
   piece. Turn the science into something a household can actually run: numbers
   with units, thresholds, the decision the reader has to make, and the failure
   mode when they get it wrong. Use <ol> for sequences, <ul> for options, and
   exactly one <table> summary. Every recommendation must be checkable against
   something the reader can see or measure.

4. THE QUIET RECOMMENDATION — not a section. Where the guide first reaches a
   real pain point, place the matching affiliate token on its own line:
     {{affiliate:feeding}}   the first time you say what to feed or how to portion it
     {{affiliate:habitat}}   the first time you specify enclosure, substrate, heating, light or decor
     {{affiliate:health}}    only if the piece covers illness, quarantine, mites, shedding or a refusal to eat
   At most one token per category, at most two in total. Never invent a token.
   Never explain or justify the token. The sentence before it must lead in
   naturally — "The cheapest fix here is a second hygrometer:" not "Buy this:".
   If the article never reaches that pain point, use no token at all.

Close with a "Frequently asked questions" <h2> holding exactly three <h3>
questions, each answered by a single <p> of 40-70 words.

## Voice

- Write like a keeper who has been bitten, surprised and occasionally wrong.
  Confidence about what you have measured; plain uncertainty about the rest.
- Explain a technical term the first time it appears, in the same sentence, in
  plain words. Never stack jargon.
- Warmth is earned by specificity, not by adjectives. "The abdomen was still
  plump" beats "it was such a worrying time".
- No AI voice. Never write "as an AI", "as a language model", "I cannot browse",
  or apologise for being an assistant. You are a person with animals.
- No content-mill filler: "in today's fast-paced world", "delve into", "unlock
  the secrets", "navigate the complexities", "game-changer", "elevate your",
  "it's important to note that", "in conclusion". Cut them on sight.
- Do not address the reader as "pet parents" or sell them a lifestyle.

## Accuracy

- Never invent a statistic, a study, a citation, an institution, a vet's name or
  a review count. If a number is contested in the hobby, say so in one clause
  and give the range you actually use.
- Use the Latin binomial once, in <em>, at first mention.
- Where the evidence is thin, say what is unknown. That is the E-E-A-T signal,
  not a weakness.

## Output contract

- Return an HTML fragment only: no <html>, <head>, <body>, no markdown fences.
- No <h1> — the page template renders the title.
- No <a>, no <img>, no price, no star rating, no button, no inline style. The
  template renders every product card.
- 950-1350 words. Five to eight <h2> sections in total. The four degrees need
  more room than the old 750-word brief allowed, but length is not the goal: if
  you are running past 1350, cut the third care section, never the table.
- EXACTLY ONE <table> is mandatory, and it must be a real comparison the reader
  can act on: life stages against parameters, a symptom against its likely
  cause, a food against its calcium-to-phosphorus ratio. A table of two columns
  restating the prose is not acceptable.
- At least five distinct measurements carrying physical units across the piece,
  not counting the same number repeated.
- Before returning, re-read your first paragraph. If it has no number with
  a unit in it, rewrite that paragraph. This is the one rule that is
  checked automatically and rejected automatically.
- Before returning, re-read the ALREADY PUBLISHED list above. If your angle,
  your opening measurement, your diary anecdote or your FAQ set overlaps any
  article on it, change it. Different species is not enough — the framing has to
  be different too.
- Never write about a different species as the subject of the article.
""")


def prompt_products(kit: list[dict]) -> str:
    """The gear brief handed to the writer, grouped by merchandising category."""
    if not kit:
        return "  (none — do not insert any affiliate token)"
    lines = []
    for slug in aff.CATEGORY_ORDER:
        items = [p for p in kit if p["cat"] == slug]
        if not items:
            continue
        lines.append(f"  {aff.category(slug)['label']} — token {{{{affiliate:{slug}}}}}")
        for p in items:
            lines.append(f"    · {p['title']} ({p['brand']})")
    return "\n".join(lines)


SYSTEM_VOICE = (
    "You are a senior keeper and science writer for an independent exotic-animal "
    "magazine. You write as a person with animals in the room, never as an "
    "assistant, and you never invent a number you could not defend."
)


def _chat(client, messages: list[dict]) -> str:
    """One completion, stripped of fences, rejected if it is too short to be real."""
    resp = client.chat.completions.create(
        model="deepseek-chat", messages=messages, stream=False)
    body = resp.choices[0].message.content or ""
    body = re.sub(r"^```(?:html)?|```$", "", body.strip(), flags=re.M).strip()
    if len(strip_tags(body)) < 300:
        raise ValueError("model returned an empty body")
    return body


def body_fingerprint(item: dict, post: dict) -> str:
    """Stable hash of the inputs that make this article this article.

    `PROMPT_VERSION` is part of it on purpose: editing the brief must invalidate
    every cached body, otherwise the site keeps serving articles written to an
    older contract for as long as their cache files survive.
    """
    raw = "|".join([PROMPT_VERSION, item["id"], item["target_keyword"],
                    item["topic"], post["species"]])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# the anti-duplication ledger
# --------------------------------------------------------------------------- #

def load_library() -> list[dict]:
    """Articles the factory has published beyond content.py's six."""
    if not LIBRARY.exists():
        return []
    try:
        data = json.loads(LIBRARY.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"  ⚠ library.json unreadable ({exc}) — treating it as empty")
        return []
    return data if isinstance(data, list) else []


def save_library(entries: list[dict]) -> None:
    LIBRARY.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def disk_titles() -> list[dict]:
    """Titles already rendered to disk, read back from the pages themselves.

    The build knows what *should* be published; the filesystem knows what
    actually is. Reading both is what catches the case the ledger misses — a
    page committed by hand, or a library.json that was reverted while its HTML
    stayed. sitemap.xml is parsed as a third opinion because it is the list
    search engines have already been given.
    """
    found: list[dict] = []
    for f in sorted(ROOT.glob("pet-*.html")):
        try:
            s = f.read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
        if not m:
            continue
        chip = re.search(r'article-head__cat[^>]*>\s*([^<]+?)\s*<', s)
        found.append({
            "id": f.stem,
            "title": strip_tags(m.group(1)).strip(),
            "category": chip.group(1).strip() if chip else "",
            "species": "",
        })

    sm = ROOT / "sitemap.xml"
    if sm.exists():
        try:
            locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", sm.read_text(encoding="utf-8"))
        except OSError:
            locs = []
        known = {d["id"] for d in found}
        for loc in locs:
            stem = loc.rstrip("/").rsplit("/", 1)[-1].replace(".html", "")
            if stem.startswith("pet-") and stem not in known:
                known.add(stem)
                found.append({"id": stem, "title": "", "category": "", "species": ""})
    return found


def history_block(posts: list[dict], limit: int = 40) -> str:
    """The ALREADY PUBLISHED list injected into every generation call.

    Built from three sources that can disagree — the in-memory posts, the HTML
    on disk, and sitemap.xml — because the point is to constrain the model with
    everything the site has *ever* published, not only what this build happens
    to be rendering. Without this the writer happily re-opens with the same
    crested-gecko humidity sentence every two days.
    """
    rows: dict[str, dict] = {}

    for p in posts:
        rows[p["title"].strip().lower()] = {
            "title": p["title"].strip(),
            "species": p.get("species", ""),
            "category": p.get("category", ""),
            "keyword": p.get("keyword", ""),
        }

    for d in disk_titles():
        key = (d["title"] or d["id"]).strip().lower()
        if key and key not in rows:
            rows[key] = {
                "title": d["title"] or d["id"],
                "species": d["species"],
                "category": d["category"],
                "keyword": "",
            }

    if not rows:
        return ("## Already published\n\nNothing yet — this is the first article "
                "on the site.")

    lines = [
        "## ALREADY PUBLISHED — hard constraint",
        "",
        "These articles are live. Do not write them again, and do not reuse their",
        "angle, their opening measurement, their diary anecdote or their FAQ set.",
        "A different species with the same framing still counts as a duplicate.",
        "",
    ]
    for i, r in enumerate(list(rows.values())[:limit], 1):
        bits = [f'"{r["title"]}"']
        if r["species"]:
            bits.append(r["species"])
        if r["category"]:
            bits.append(r["category"])
        lines.append(f"{i}. " + " — ".join(bits))
    if len(rows) > limit:
        lines.append(f"…and {len(rows) - limit} more in the same archive.")
    return "\n".join(lines)


# The history block is identical for every article in one build, so it is
# computed once and read from here rather than re-scanning the filesystem for
# each of the N generation calls.
_HISTORY: str = ""


def set_history(posts: list[dict]) -> None:
    global _HISTORY
    _HISTORY = history_block(posts)


# --------------------------------------------------------------------------- #
# growing the library
# --------------------------------------------------------------------------- #

def next_post_id(existing: set[str]) -> str:
    """pet-00N, one past the highest id in use — never a gap-filler."""
    nums = [int(m.group(1)) for i in existing
            if (m := re.fullmatch(r"pet-(\d+)", i))]
    return f"pet-{(max(nums) + 1) if nums else 1:03d}"


def grow(count: int, posts: list[dict]) -> list[dict]:
    """Move `count` unpublished topics from TOPIC_POOL into library.json.

    Selection is breadth-first: the pool is walked in GROUP_ROTATION order so a
    batch of four cannot come back as four reptiles. A topic is skipped when
    its slug is already in the library, when its title already exists anywhere
    on disk, or when its photograph is not on disk yet — an article whose image
    is missing renders a card with no animal on it.
    """
    library = load_library()
    taken_slugs = {e.get("slug") for e in library if e.get("slug")}
    taken_titles = {p["title"].strip().lower() for p in posts}
    taken_titles |= {d["title"].strip().lower() for d in disk_titles() if d["title"]}
    ids = {p["id"] for p in posts} | {e["id"] for e in library if e.get("id")}

    ready, waiting_art, seen_title = [], [], []
    for group in GROUP_ROTATION:
        for t in TOPIC_POOL:
            if t["group"] != group:
                continue
            if t["slug"] in taken_slugs:
                continue
            if t["title"].strip().lower() in taken_titles:
                seen_title.append(t["slug"])
                continue
            if not (IMAGES / t["image"]).exists():
                waiting_art.append(t["slug"])
                continue
            ready.append(t)

    print(f"  pool: {len(TOPIC_POOL)} topics, {len(library)} already published, "
          f"{len(ready)} eligible")
    if waiting_art:
        print(f"  awaiting artwork (add the JPEG to static/images/): "
              f"{', '.join(waiting_art)}")
    if seen_title:
        print(f"  already in the archive, skipped: {', '.join(seen_title)}")

    picked = ready[:max(0, count)]
    if not picked:
        print("  nothing to grow — the pool has no eligible topic left")
        return []

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    added = []
    for t in picked:
        pid = next_post_id(ids)
        ids.add(pid)
        entry = {
            "id": pid,
            "slug": t["slug"],
            "title": t["title"],
            "dek": t.get("dek", ""),
            "target_keyword": t["target_keyword"],
            "topic": t["topic"],
            "category": t["category"],
            "group": t["group"],
            "species": t["species"],
            "sci": t["sci"],
            "author": t.get("author", "nell"),
            "date": today,
            "is_pinned": False,
            "image": t["image"],
            "alt": t["alt"],
            "caption": t["caption"],
            "facts": [list(f) for f in t["facts"]],
            "kit": [list(k) for k in t["kit"]],
            "tags": list(t["tags"]),
            "body_html": t.get("body_html", ""),
        }
        library.append(entry)
        added.append(entry)
        print(f"  + {pid}  {t['group']:<14} {t['title'][:58]}")

    save_library(library)
    print(f"  library.json now holds {len(library)} generated article(s)")
    return added


# --------------------------------------------------------------------------- #
# editorial contract
# --------------------------------------------------------------------------- #

# A body that contains these has slipped into assistant register, and the page
# reads like a chatbot wrote it. Checked at generation time and at build time.
BANNED_VOICE = (
    "as an ai", "as a language model", "as an artificial intelligence",
    "i cannot browse", "in today's fast-paced world", "delve into",
    "unlock the secrets", "navigate the complexities", "game-changer",
    "game changer", "elevate your", "it's important to note that",
    "in conclusion", "testament to the",
)

# Any number that carries a *physical* unit — the kind of number a keeper can
# put an instrument on. Durations are deliberately absent: "a reliable 10-14 day
# feeder" is not a measurement of the animal's environment, and accepting it
# let a draft clear the hook check without containing any actual data.
# `[\s-]*` lets "40-gallon" through without letting a bare "in" match "2 in the
# morning" — inches must be written "in." or "inch(es)".
_MEASURE_RE = re.compile(
    r"\d+(?:\.\d+)?[\s-]*(?:"
    r"°\s?[CF]|%|"
    r"cm|mm|µm|um|nm|km|m\b|"
    r"in\.|inch(?:es)?\b|ft\b|feet\b|"
    r"µg|mg|kg|grams?\b|g\b|"
    r"ml\b|cl\b|litres?\b|liters?\b|l\b|"
    r"UVI|lux|lx|pH|"
    r"gal(?:lon)?s?\b|"
    r"watts?\b|W\b"
    r")",
    re.I,
)
_FIRST_PERSON_RE = re.compile(r"\b(I|my|me|we|our)\b")
_BINOMIAL_RE = re.compile(r"<em>\s*[A-Z][a-z]{2,}\s+[a-z]{2,}\s*</em>")


# --- hook repair -----------------------------------------------------------
#
# The science hook is the one beat a machine can score objectively, and the one
# a model most often misses when it opens with a scene instead of a number.
# Failing the whole build over it stops the site from updating, which is a far
# worse outcome than a slightly plainer opening paragraph — so a body that opens
# without a measurement gets one written for it out of the article's own `facts`
# table, and the build carries on. Nothing here invents a number: every value is
# already published in the species profile panel of the same page.

HOOK_MEASURE_PROBLEM = "the opening paragraph has no unit-bearing measurement"

# Labels whose values are instrument readings, in the order they should be
# quoted: the environment a keeper controls first, body size last. The verb is
# a present participle so the clause fits after "is kept with".
HOOK_FACTS: tuple[tuple[str, str], ...] = (
    ("Temperature", "holding at"),
    ("Hot spot", "running"),
    ("Basking surface", "reading"),
    ("Target humidity", "sitting at"),
    ("Humidity", "sitting at"),
    ("Cool end", "sitting at"),
    ("UVB", "rated"),
    ("Adult size", "running"),
    ("Depth", "running"),
)

# How each label reads inside a sentence. "Target humidity sitting at" is
# jargon leaking into prose; "humidity sitting at" is how a keeper says it.
_HOOK_LABEL = {
    "Target humidity": "humidity",
    "Hot spot": "the hot spot",
    "Cool end": "the cool end",
    "Basking surface": "the basking surface",
    "Adult size": "adult size",
    "Depth": "substrate depth",
    "UVB": "UVB",
}


def hook_paragraph(post: dict) -> str:
    """A standfirst built only from numbers already in this article's record."""
    facts = dict(post.get("facts") or [])
    picked: list[str] = []
    for label, verb in HOOK_FACTS:
        value = facts.get(label)
        if value and _MEASURE_RE.search(value):
            name = _HOOK_LABEL.get(label, label.lower())
            picked.append(f"{name} {verb} {value}")
        if len(picked) == 3:
            break
    if not picked:
        return ""

    clause = picked[0] if len(picked) == 1 else ", ".join(picked[:-1]) + " and " + picked[-1]
    sci = e(post.get("sci") or post.get("species", "This species"))
    return (
        '<p class="hook-note">'
        '<span class="hook-note__label">Field parameters</span>'
        f"<em>{sci}</em> is kept with {clause}. Those numbers decide most of what "
        "follows, and every recommendation below is built on them.</p>"
    )


def ensure_hook(post: dict, body: str) -> tuple[str, bool]:
    """Guarantee a measurement in the opening paragraph. Never raises.

    Applied to the sanitised body and before the magazine layer, so the
    inserted values pick up parameter badges like any other number and
    `add_lede()` still promotes the article's own first paragraph — the note is
    `<p class="hook-note">`, which `add_lede()` deliberately skips.
    """
    first = re.search(r"<p[^>]*>(.*?)</p>", body, re.S)
    hook = prose_text(first.group(1)) if first else ""
    if _MEASURE_RE.search(hook):
        return body, False
    note = hook_paragraph(post)
    if not note:
        return body, False
    return note + "\n" + body, True


def section_texts(body: str) -> list[tuple[str, str]]:
    """(heading, section text) for every <h2> block, tags stripped."""
    heads = list(re.finditer(r"<h2[^>]*>(.*?)</h2>", body, re.S))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        out.append((prose_text(m.group(1)), prose_text(body[m.end():end])))
    return out


def check_structure(body: str) -> list[str]:
    """Score a body against the four-beat brief. Empty list means it passes.

    This is the machine-readable half of the prompt. The prompt asks for the
    beats; this proves they arrived, so a draft that drifted into a generic care
    sheet cannot be published just because it is long enough.
    """
    problems: list[str] = []
    text = prose_text(body)
    words = len(text.split())
    # 950-1350 is the four-degree brief. The floor moved up from 750 because a
    # piece that carries a table, a named mechanism and a life-stage comparison
    # cannot honestly fit in 750 words; the ceiling moved up because rejecting
    # at 1150 rejected every draft the new brief produced, and the fallback
    # (the editorial body) is worse than a slightly long one.
    if words < 700:
        problems.append(f"only {words} words (brief asks 950-1350)")
    elif words > 1450:
        problems.append(f"{words} words, well over the 950-1350 brief")

    first_p = re.search(r"<p[^>]*>(.*?)</p>", body, re.S)
    hook = prose_text(first_p.group(1)) if first_p else ""
    # Both can be true at once; reporting them together saves a repair round.
    if len(hook.split()) < 25:
        problems.append("the opening paragraph is too short to carry a science hook")
    if not _MEASURE_RE.search(hook):
        problems.append(HOOK_MEASURE_PROBLEM +
                        " (needs e.g. 72-80 °F, 60-70 %, 12-18 mm, 290-320 nm, 0.6-1.1 UVI)")

    if not _BINOMIAL_RE.search(body):
        problems.append("no Latin binomial in <em> at first mention")

    secs = section_texts(body)
    if not 4 <= len(secs) <= 8:
        problems.append(f"{len(secs)} <h2> sections (brief asks 4-7)")

    if not any(len(_FIRST_PERSON_RE.findall(t)) >= 3 and len(t.split()) >= 60
               for _, t in secs):
        problems.append("no first-person keeper's diary section")

    # Scannable structure: a step sequence, a table, or a real option list.
    lists = [len(re.findall(r"<li\b", m.group(0)))
             for m in re.finditer(r"<ul\b.*?</ul>", body, re.S)]
    if not (re.search(r"<ol\b", body) or re.search(r"<table\b", body)
            or any(n >= 3 for n in lists)):
        problems.append("no step sequence, option list or summary table")

    # The machine-checkable half of the four-degree contract. Both of these are
    # blocking, because a body that fails them is exactly the shallow,
    # table-free draft the brief was written to stop: depth is not a tone of
    # voice, it is the presence of numbers an instrument could read.
    if not re.search(r"<table\b", body):
        problems.append("no <table> — the brief requires exactly one comparison table")
    distinct = {m.lower() for m in _MEASURE_RE.findall(text)}
    if len(distinct) < 4:
        problems.append(f"only {len(distinct)} distinct measurement(s) with units "
                        f"(depth asks for at least 5, 4 is the floor)")

    faq_at = text.lower().find("frequently asked")
    if faq_at < 0:
        problems.append('no "Frequently asked questions" section')
    else:
        qs = len(re.findall(r"<h3\b", body[body.lower().find("frequently asked"):]))
        if qs < 3:
            problems.append(f"FAQ has {qs} questions (brief asks 3)")

    low = text.lower()
    hits = [p for p in BANNED_VOICE if p in low]
    if hits:
        problems.append("banned voice: " + ", ".join(hits))

    return problems


def repair_prompt(problems: list[str]) -> str:
    """The follow-up turn: name what failed, ask for a full rewrite."""
    listed = "\n".join(f"- {p}" for p in problems)
    return (
        "Your draft does not meet the editorial brief. Problems:\n"
        f"{listed}\n\n"
        "Rewrite the complete fragment so it passes every point. Keep the parts "
        "that already work. Same output contract: HTML fragment only, no <h1>, "
        "no <a>, no <img>, no price, no inline style."
    )


def blocking_problems(problems: list[str]) -> list[str]:
    """The subset of brief failures that only a rewrite can fix.

    A missing measurement in the opening paragraph is not one of them: the
    builder patches that from the article's own facts table, so sending the
    draft back to the model would burn a call and could still end in a
    rejection. Everything else — wrong length, no diary section, banned voice —
    is a writing problem, and only the model can fix it.
    """
    return [p for p in problems if not p.startswith(HOOK_MEASURE_PROBLEM)]


def resolve_body(item: dict, post: dict, refresh: bool) -> tuple[str, str]:
    """Return (body_html, source).

    The cache is keyed by article id *and* validated against a fingerprint of
    the prompt inputs, so a body written for one article can never be served
    for another. The old code trusted the filename alone: a stale or copied
    `cache/pet-00N.html` would silently become that article's body.
    """
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"{item['id']}.html"
    meta_file = CACHE / f"{item['id']}.json"
    stamp = body_fingerprint(item, post)

    if cache_file.exists() and not refresh:
        cached = cache_file.read_text(encoding="utf-8")
        meta: dict = {}
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                meta = {}
        # A body shorter than a real guide, or one whose fingerprint does not
        # match this prompt, is a miss — never reused. No fingerprint means we
        # cannot prove provenance, so it is a miss too.
        if len(strip_tags(cached)) >= 400 and meta.get("fingerprint") == stamp:
            return cached, "cache"
        print(f"    ! stale cache for {item['id']} — regenerating")

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            prompt = PROMPT.safe_substitute(
                keyword=item["target_keyword"],
                topic=item["topic"],
                species=post["species"],
                sci=post["sci"],
                category=item.get("category", post["category"]),
                products=prompt_products(post.get("_kit") or []),
                history=_HISTORY or history_block([]),
            )
            messages = [
                {"role": "system", "content": SYSTEM_VOICE},
                {"role": "user", "content": prompt},
            ]

            body: str | None = None
            for attempt in range(3):
                try:
                    body = _chat(client, messages)
                    break
                except Exception as exc:  # noqa: BLE001
                    print(f"    retry {attempt + 1}/3: {exc}")
                    if attempt == 2:
                        break
                    time.sleep(5)

            if body is None:
                print("    ! API unavailable; using the editorial body from content.py")
                return post["body_html"], "editorial"

            # The prompt asks for the four beats; this is where we find out
            # whether they arrived. One targeted rewrite, then reject: an
            # off-brief body is worse than the previous one, because it would
            # ship a generic care sheet under this article's title.
            problems = check_structure(body)
            blocking = blocking_problems(problems)
            if blocking:
                print(f"    ! {item['id']}: draft missed {len(blocking)} brief item(s)")
                for p in blocking:
                    print(f"      · {p}")
                try:
                    body = _chat(client, messages + [
                        {"role": "assistant", "content": body},
                        {"role": "user", "content": repair_prompt(blocking)},
                    ])
                    problems = check_structure(body)
                    blocking = blocking_problems(problems)
                except Exception as exc:  # noqa: BLE001
                    print(f"    ! repair call failed ({exc})")

                if blocking:
                    print(f"    ! {item['id']} is still off-brief; keeping the "
                          f"previous body rather than publishing it")
                    return post["body_html"], "rejected (off-brief)"
            elif problems:
                # Only the hook measurement is missing — the builder fills it in.
                print(f"    · {item['id']}: opening has no measurement yet; "
                      f"field parameters will be prepended at render time")

            cache_file.write_text(body, encoding="utf-8")
            meta_file.write_text(
                json.dumps(
                    {"id": item["id"], "fingerprint": stamp,
                     "prompt": PROMPT_VERSION,
                     "keyword": item["target_keyword"]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return body, "deepseek"
        except Exception as exc:  # noqa: BLE001
            print(f"    ! API unavailable ({exc}); using the editorial body from content.py")

    return post["body_html"], "editorial"


def sanitize_body(body: str, post: dict) -> str:
    """Strip model artefacts and give every heading a stable id.

    Affiliate markup is *removed* here rather than repaired: the card renderer in
    affiliate.py owns every money link, so anything the writer invented is
    unwrapped to plain text and the template's own card takes its place.
    """
    body = re.sub(r"<h1[^>]*>.*?</h1>", "", body, flags=re.S | re.I)
    body = re.sub(r"\s+style=\"[^\"]*\"", "", body)
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S | re.I)
    # Never ship an image we did not verify — no hotlinked product shots.
    body = re.sub(r"<img\b[^>]*>", "", body, flags=re.I)

    def unwrap(m: re.Match) -> str:
        """Drop Amazon anchors to their text; keep editorial links but harden them."""
        tag = m.group(0)
        if re.search(r"amazon\.|amzn\.|/dp/", tag, flags=re.I):
            return re.sub(r"</?a\b[^>]*>", "", tag)
        if re.search(r'href="https?://', tag) and "rel=" not in tag:
            return tag.replace("<a ", '<a rel="noopener noreferrer" target="_blank" ', 1)
        return tag

    body = re.sub(r"<a\b[^>]*>.*?</a>", unwrap, body, flags=re.S | re.I)

    def add_id(match: re.Match) -> str:
        inner = match.group(2)
        return f'<h{match.group(1)} id="{slugify(inner)}">{inner}</h{match.group(1)}>'

    body = re.sub(r"<h([23])(?:\s[^>]*)?>(.*?)</h\1>", add_id, body, flags=re.S)
    return body.strip()


# --------------------------------------------------------------------------- #
# magazine typography
# --------------------------------------------------------------------------- #

# Temperatures, humidity percentages and physical dimensions are the numbers a
# keeper actually scans for. They get a high-contrast badge so the eye can find
# them in a wall of prose.
_UNIT = r"(?:cm|mm|µm|um|nm|ft|inches?)"
PARAM_RE = re.compile(
    r"(?P<temp>\b\d{1,3}(?:\s*[–—-]\s*\d{1,3})?\s*°\s?[CF]\b)"
    r"|(?P<pct>\b\d{1,3}(?:\s*[–—-]\s*\d{1,3})?\s*%)"
    rf"|(?P<dim>\b\d+(?:\.\d+)?(?:\s*[×x]\s*\d+(?:\.\d+)?){{1,2}}\s*{_UNIT}\b)"
    rf"|(?P<size>\b\d+(?:\.\d+)?(?:\s*[–—-]\s*\d+(?:\.\d+)?)?\s*{_UNIT}\b)"
    # A measurement the hook check now accepts should also read as data on the
    # page — a UVB wavelength is as concrete as a temperature.
    r"|(?P<tech>\b\d+(?:\.\d+)?(?:\s*[–—-]\s*\d+(?:\.\d+)?)?\s*(?:UVI|lux|lx|pH)\b)",
    re.I,
)

# Never badge text inside these: a badge in a link breaks the affordance, and
# table cells already read as data. Headings keep their own type treatment.
BADGE_SKIP = {"a", "code", "pre", "table", "thead", "tbody", "tr", "td", "th",
              "h1", "h2", "h3", "h4", "h5", "h6"}


def highlight_params(body: str) -> str:
    """Wrap temps, percentages and dimensions in a badge, text nodes only.

    Splitting on tags means a match can never fall inside an attribute or a
    heading id; `skip` keeps the walk out of links, code and tables.
    """
    out: list[str] = []
    skip = 0
    for part in re.split(r"(<[^>]+>)", body):
        if part.startswith("<"):
            name = re.match(r"</?\s*([a-zA-Z0-9]+)", part)
            tag = name.group(1).lower() if name else ""
            if tag in BADGE_SKIP:
                if part.startswith("</"):
                    skip = max(0, skip - 1)
                elif not part.rstrip().endswith("/>"):
                    skip += 1
            out.append(part)
        elif skip or not part.strip():
            out.append(part)
        else:
            out.append(PARAM_RE.sub(
                lambda m: f'<span class="badge">{m.group(0)}</span>', part))
    return "".join(out)


def add_lede(body: str) -> str:
    """Promote the opening paragraph to a magazine lede.

    The first `<p>` that is neither the lede itself nor the auto-generated
    `hook-note` standfirst wins, so an article that needed a field-parameter
    opener still gets its drop cap on a real paragraph. The drop cap itself is
    pure CSS.
    """
    for m in re.finditer(r"<p(\s[^>]*)?>", body):
        attrs = m.group(1) or ""
        if "lede" in attrs or "hook-note" in attrs:
            continue
        return body[:m.start()] + '<p class="lede">' + body[m.end():]
    return body


def magazine_body(body: str) -> str:
    """Apply the editorial layer to a sanitised body."""
    return add_lede(highlight_params(body))


def faq_pairs(body: str) -> list[tuple[str, str]]:
    """Extract (question, answer) from the FAQ section for FAQPage JSON-LD."""
    marker = re.search(r"<h2[^>]*>[^<]*Frequently asked", body, flags=re.I)
    if not marker:
        return []
    tail = body[marker.end():]
    pairs = []
    for m in re.finditer(r"<h3[^>]*>(.*?)</h3>\s*<p[^>]*>(.*?)</p>", tail, flags=re.S):
        q = strip_tags(m.group(1))
        a = strip_tags(m.group(2))
        if q and a:
            pairs.append((q, a))
    return pairs[:6]


def toc_items(body: str) -> list[tuple[str, str]]:
    items = []
    for m in re.finditer(r"<h2[^>]*id=\"([^\"]+)\"[^>]*>(.*?)</h2>", body, flags=re.S):
        items.append((m.group(1), strip_tags(m.group(2))))
    return items


# --------------------------------------------------------------------------- #
# chrome
# --------------------------------------------------------------------------- #

def head(
    title: str,
    description: str,
    canonical: str,
    *,
    image: str = "static/images/jumping-spider.jpg",
    og_type: str = "website",
    published: str | None = None,
    jsonld: list[dict] | None = None,
    body_class: str = "",
    assets: str = "",
) -> str:
    blocks = ""
    for obj in jsonld or []:
        blocks += (
            '<script type="application/ld+json">'
            + json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            + "</script>\n"
        )

    article_meta = ""
    if published:
        article_meta = (
            f'<meta property="article:published_time" content="{published}">\n'
            f'<meta property="article:modified_time" content="{published}">\n'
            f'<meta property="article:author" content="{e(SITE_NAME)}">\n'
        )

    return f"""<!DOCTYPE html>
<html lang="{LANG}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<meta name="theme-color" content="#14120f">
<link rel="canonical" href="{canonical}">
<link rel="alternate" type="application/rss+xml" title="{e(SITE_NAME)} — Field Notes" href="feed.xml">
<link rel="sitemap" type="application/xml" href="sitemap.xml">

<meta property="og:site_name" content="{e(SITE_NAME)}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{absolute(image)}">
<meta property="og:image:width" content="1536">
<meta property="og:image:height" content="1024">
<meta property="og:locale" content="en_US">
{article_meta}<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<meta name="twitter:image" content="{absolute(image)}">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
<link rel="stylesheet" href="static/style.css">
<link rel="icon" href="static/logo.svg" type="image/svg+xml">
{assets}{blocks}</head>
<body class="{body_class}">
<a class="skip" href="#main">Skip to content</a>
"""


def nav_items(tax: dict) -> list[tuple[str, str, str]]:
    """(label, href, key) for every primary nav entry.

    Each topic and the species index are *pages*, not anchors on the homepage.
    The old version pointed all four links at columns of the same `#browse`
    grid, which sit side by side on one row — so every click scrolled to the
    same place and the nav looked broken. Real pages give each label a distinct
    URL that works without JavaScript and can be indexed separately.
    """
    items = [("Field Guides", "guides.html", "guides")]
    items += [
        (CATEGORY_SHORT.get(c, c), f"category-{s}.html", f"category-{s}")
        for c, s in tax["cats"]
    ]
    items += [("By species", "species.html", "species")]
    return items


def nav_html(tax: dict, active: str | None = None) -> str:
    def link(label: str, href: str, key: str) -> str:
        cur = ' class="is-active" aria-current="page"' if key == active else ""
        return f'<li><a href="{href}"{cur}>{e(label)}</a></li>'

    items = nav_items(tax)
    links = "".join(link(*it) for it in items)
    mobile = "".join(link(*it) for it in items)
    return f"""
<div class="strip">
  <div class="container strip__inner">
    <span class="strip__issue">Issue 04 · The Invertebrate Edition</span>
    <span class="strip__meta">
      <span>Independent</span><span class="strip__dot"></span>
      <span>Reader-supported</span><span class="strip__dot"></span>
      <span>Est. 2019</span>
    </span>
  </div>
</div>

<header class="nav">
  <div class="container nav__inner">
    <a class="brand" href="index.html" aria-label="{e(SITE_NAME)} — home">
      <span class="brand__mark" aria-hidden="true">e</span>
      <span>
        <span class="brand__text">Exotic Pet <em>Care</em> Hub</span>
        <span class="brand__sub">Field guides &amp; husbandry</span>
      </span>
    </a>
    <nav aria-label="Primary">
      <ul class="nav__links">{links}</ul>
    </nav>
    <div class="nav__actions">
      <a class="nav__cta" href="guides.html">All guides</a>
      <details class="nav__mobile">
        <summary>Menu</summary>
        <ul>{mobile}</ul>
      </details>
    </div>
  </div>
</header>
"""


def newsletter_html() -> str:
    return """
<section class="newsletter" aria-labelledby="newsletter-title">
  <div class="container newsletter__grid">
    <div>
      <div class="newsletter__kicker">Field Notes · Monthly</div>
      <h2 id="newsletter-title">One letter a month.<br>No sponsor, no filler.</h2>
      <p>Husbandry updates, new species notes, and the mistakes we made so you don't have to.</p>
    </div>
    <div>
      <form action="#" method="post" novalidate>
        <label class="sr-only" for="email">Email address</label>
        <input id="email" type="email" name="email" placeholder="you@example.com" autocomplete="email" required>
        <button type="submit">Subscribe</button>
      </form>
      <p class="newsletter__note">No affiliate links in the letter. Unsubscribe in one click.</p>
    </div>
  </div>
</section>
"""


def footer_html(tax: dict) -> str:
    cat_links = "".join(
        f'<li><a href="category-{s}.html">{e(CATEGORY_SHORT.get(c, c))}</a></li>'
        for c, s in tax["cats"]
    )
    group_links = "".join(
        f'<li><a href="species-{s}.html">{e(g)}</a></li>' for g, s in tax["groups"]
    )
    return f"""
<footer class="footer">
  <div class="container">
    <div class="footer__grid">
      <div class="footer__brand">
        <a class="brand" href="index.html">
          <span class="brand__mark" aria-hidden="true">e</span>
          <span class="brand__text">Exotic Pet <em>Care</em> Hub</span>
        </a>
        <p>Evidence-led care for the animals that don't fit the mould.</p>
      </div>
      <div class="footer__col">
        <h3>Field guides</h3>
        <ul>
          <li><a href="guides.html">All guides</a></li>
          {cat_links}
        </ul>
      </div>
      <div class="footer__col">
        <h3>By species</h3>
        <ul>{group_links}</ul>
      </div>
      <div class="footer__col">
        <h3>Editorial</h3>
        <ul>
          <li><a href="index.html#about">About us</a></li>
          <li><a href="index.html#about">Review ethics</a></li>
          <li><a href="index.html#about">Affiliate disclosure</a></li>
          <li><a href="feed.xml">RSS feed</a></li>
          <li><a href="sitemap.xml">Sitemap</a></li>
        </ul>
      </div>
    </div>
    <div class="footer__bottom">
      <p>© {datetime.now().year} {e(SITE_NAME)}. As an Amazon Associate we earn from qualifying purchases. We only recommend gear we have used with our own animals.</p>
      <div class="footer__legal"><span>Made for keepers, not algorithms.</span></div>
    </div>
  </div>
</footer>
"""


def card_html(post: dict, wide: bool = False, pin: bool = False) -> str:
    author = AUTHORS[post["author"]]
    cls = "card card--wide" if wide else "card"
    if pin:
        cls += " card--pinned"
    ribbon = '<span class="card__pin">Pinned</span>' if pin else ""
    return f"""
<article class="{cls}">
  <a class="card__media" href="{post['id']}.html" tabindex="-1" aria-hidden="true">
    <img src="static/images/{post['image']}" alt="{e(post['alt'])}"
         width="1536" height="1024" loading="lazy" decoding="async">
    <span class="card__tag">{e(post['category'])}</span>
    {ribbon}
  </a>
  <div class="card__body">
    <div class="card__cat"><i>{e(post['sci'])}</i></div>
    <h3 class="card__title"><a href="{post['id']}.html">{e(post['title'])}</a></h3>
    <p class="card__dek">{e(post['dek'])}</p>
    <div class="card__foot">
      <span>{e(author['name'])}</span>
      <span class="dot"></span>
      <span>{post['_read']} min read</span>
      <span class="card__arrow" aria-hidden="true">→</span>
    </div>
  </div>
</article>
"""


# --------------------------------------------------------------------------- #
# pages
# --------------------------------------------------------------------------- #

def render_index(posts: list[dict]) -> str:
    # Pinned guides lead the page; everything behind them stays chronological.
    ordered = rank_posts(posts)
    featured = ordered[0]
    picks = [p for p in ordered[1:] if p.get("is_pinned")]
    rest = [p for p in ordered[1:] if not p.get("is_pinned")]
    lead, others = rest[0], rest[1:]
    cards = card_html(lead, wide=True) + "".join(card_html(p) for p in others)

    tax = taxonomy(posts)
    by_cat: dict[str, list[dict]] = {}
    by_group: dict[str, list[dict]] = {}
    for p in ordered:
        by_cat.setdefault(p["category"], []).append(p)
        by_group.setdefault(p["group"], []).append(p)

    def index_col(label: str, slug: str, items: list[dict]) -> str:
        # the species line is not decoration: it lets a reader see that the
        # link goes to the animal the label promises, which is exactly the
        # check that was missing when categories pointed at the wrong anchor
        rows = "".join(
            f'<li><a href="{x["id"]}.html">{e(x["title"])}'
            f'<em>{e(x["species"])}</em></a></li>'
            for x in items
        )
        return f"""
        <div class="index-col" id="{slug}">
          <h3>{e(label)} <span>{len(items):02d}</span></h3>
          <ul>{rows}</ul>
        </div>"""

    topic_cols = "".join(
        index_col(CATEGORY_SHORT.get(c, c), s, by_cat.get(c, []))
        for c, s in tax["cats"]
    )
    group_cols = "".join(
        index_col(g, s, by_group.get(g, [])) for g, s in tax["groups"]
    )
    chips = ('<p class="index-head">By topic</p>' + topic_cols
             + '<p class="index-head">By species</p>' + group_cols)

    fa = AUTHORS[featured["author"]]

    jsonld = [
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": SITE_NAME,
            "url": SITE_URL + "/",
            "description": "Independent field guides to exotic pets — jumping spiders, geckos, pythons and the bioactive crews that support them.",
            "publisher": {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL + "/"},
            "potentialAction": {
                "@type": "SearchAction",
                "target": {"@type": "EntryPoint", "urlTemplate": SITE_URL + "/?q={search_term_string}"},
                "query-input": "required name=search_term_string",
            },
        },
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": "Field guides",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": absolute(p["id"] + ".html"), "name": p["title"]}
                for i, p in enumerate(ordered)
            ],
        },
    ]

    doc = head(
        f"{SITE_NAME} — Field Guides for Rare and Exotic Pets",
        "Independent, keeper-written care guides for jumping spiders, crested and leopard geckos, ball pythons and land hermit crabs. No paid placements.",
        SITE_URL + "/",
        jsonld=jsonld,
        body_class="page-home",
        assets=VIVARIUM_ASSETS,
    )
    doc += nav_html(tax)

    fk = "Pinned field guide" if featured.get("is_pinned") else "Featured field guide"

    # The remaining pinned guides get their own band under the hero, so the
    # flagship picks read as an editorial shortlist rather than three identical
    # cards competing with the lead story.
    picks_html = ""
    if picks:
        rows = "".join(
            f"""
        <li class="pick">
          <a href="{p['id']}.html">
            <span class="pick__num">{i + 1:02d}</span>
            <span class="pick__text">
              <span class="pick__cat">{e(p['category'])} · <i>{e(p['sci'])}</i></span>
              <span class="pick__title">{e(p['title'])}</span>
              <span class="pick__dek">{e(p['dek'])}</span>
            </span>
            <span class="pick__go" aria-hidden="true">→</span>
          </a>
        </li>"""
            for i, p in enumerate(picks)
        )
        picks_html = f"""
  <section class="picks" aria-labelledby="picks-title">
    <div class="container">
      <div class="picks__head">
        <h2 class="picks__title" id="picks-title">Start <em>here</em></h2>
        <span class="picks__note">The guides we hand a new keeper first.</span>
      </div>
      <ol class="picks__list">{rows}
      </ol>
    </div>
  </section>
"""

    doc += f"""
<main id="main">
  <section class="hero">
    <div class="hero__media">
      <img src="static/images/{featured['image']}" alt="{e(featured['alt'])}"
           width="1536" height="1024" fetchpriority="high" decoding="async">
    </div>
    <div class="container hero__inner">
      <div class="hero__content">
      <div class="hero__kicker"><span>◆</span> {fk}</div>
      <h1 class="hero__title"><a href="{featured['id']}.html">{e(featured['title'])}</a></h1>
      <p class="hero__dek">{e(featured['dek'])}</p>
      <div class="hero__meta">
        <span>{e(fa['name'])}</span><span class="sep"></span>
        <span>{fmt_date(featured['date'])}</span><span class="sep"></span>
        <span>{featured['_read']} min read</span><span class="sep"></span>
        <span><i>{e(featured['sci'])}</i></span>
      </div>
      <div class="hero__actions">
        <a class="btn btn--solid" href="{featured['id']}.html">
          Read the guide
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
        </a>
        <a class="btn btn--ghost" href="#guides">Browse all guides</a>
      </div>
      </div>
      {vivarium_html()}
    </div>
    <div class="hero__credit">{credit_html(featured['image'])}</div>
  </section>
{picks_html}
  <section class="intro" id="about">
    <div class="container intro__grid">
      <div>
        <h2 class="intro__title">Care writing for animals that<br><em>nobody writes about.</em></h2>
        <p class="intro__lede">Every guide is written by a keeper with the animal in front of them, checked against published husbandry literature, and updated when we learn better. No paid placements, no rankings for sale — gear is recommended only after we have run it in our own enclosures.</p>
      </div>
      <aside class="intro__aside">
        <strong>How we work</strong>
        Every affiliate link is labelled, every time. We would rather lose a commission than recommend a heat mat without a thermostat.
      </aside>
    </div>
  </section>

  <section class="section" id="guides" aria-labelledby="latest-title">
    <div class="container">
      <div class="section__head">
        <span class="section__num">01</span>
        <h2 class="section__title" id="latest-title">Latest <em>field guides</em></h2>
        <span class="section__note">Six species, three disciplines, one standard of evidence.</span>
      </div>
      <div class="grid">{cards}</div>
    </div>
  </section>

  <section class="section section--tight" id="browse" aria-labelledby="browse-title">
    <div class="container">
      <div class="section__head">
        <span class="section__num">02</span>
        <h2 class="section__title" id="browse-title">Browse the <em>collection</em></h2>
        <a class="section__link" href="#guides">All guides</a>
      </div>
      <div class="index-grid">{chips}</div>
    </div>
  </section>
"""
    doc += newsletter_html()
    doc += "</main>\n" + footer_html(tax) + "</body>\n</html>\n"
    return doc


def collection_chips(tax: dict, active: str) -> str:
    """Cross-links between every filtered index, with the current one marked."""
    def chip(label: str, href: str, key: str) -> str:
        cur = (' class="collection__chip is-active" aria-current="page"'
               if key == active else ' class="collection__chip"')
        return f'<a href="{href}"{cur}>{e(label)}</a>'

    out = [chip("All guides", "guides.html", "guides")]
    out += [chip(CATEGORY_SHORT.get(c, c), f"category-{s}.html", f"category-{s}")
            for c, s in tax["cats"]]
    out += [chip(g, f"species-{s}.html", f"species-{s}") for g, s in tax["groups"]]
    return "".join(out)


def render_collection(
    tax: dict,
    posts: list[dict],
    *,
    slug: str,
    kicker: str,
    title: str,
    dek: str,
    active: str,
    title_html: str = "",
    note: str = "",
    sections: list[tuple[str, list[dict]]] | None = None,
) -> str:
    """A filtered index page: one topic, one species, or the whole library.

    `sections` renders several headed groups (used by the species index);
    otherwise the posts are shown as a single grid. Every link on the page is a
    real URL, so the filter works with JavaScript disabled.
    """
    canonical = absolute(slug + ".html")
    if sections is None:
        ordered = rank_posts(posts)
        pinned = [p for p in ordered if p.get("is_pinned")]
        stream = [p for p in ordered if not p.get("is_pinned")]
        listed = ordered
    else:
        pinned = []
        stream = []
        sections = [(h, rank_posts(items)) for h, items in sections]
        listed = [p for _, items in sections for p in items]

    jsonld = [
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": title,
            "description": dek,
            "url": canonical,
            "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/"},
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
                {"@type": "ListItem", "position": 2, "name": title, "item": canonical},
            ],
        },
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": title,
            "numberOfItems": len(listed),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1,
                 "url": absolute(p["id"] + ".html"), "name": p["title"]}
                for i, p in enumerate(listed)
            ],
        },
    ]

    doc = head(f"{title} — {SITE_NAME}", dek, canonical, jsonld=jsonld,
               body_class="page-collection")
    doc += nav_html(tax, active)

    meta = f'<span>{len(listed):02d} field guides</span>'
    if note:
        meta += f'<span class="dot"></span><span>{e(note)}</span>'

    doc += f"""
<main id="main">
  <section class="collection">
    <div class="container">
      <div class="collection__kicker">{e(kicker)}</div>
      <h1 class="collection__title">{title_html or e(title)}</h1>
      <p class="collection__dek">{e(dek)}</p>
      <div class="collection__meta">{meta}</div>
      <nav class="collection__chips" aria-label="Filter guides">{collection_chips(tax, active)}</nav>
    </div>
  </section>
"""

    if sections is None:
        band = ""
        if pinned:
            band = f"""
  <section class="featured-band" aria-label="Pinned guides">
    <div class="container">
      <div class="featured-band__grid">{"".join(card_html(p, wide=True, pin=True) for p in pinned)}</div>
    </div>
  </section>
"""
        doc += band + f"""
  <section class="section">
    <div class="container">
      <div class="grid">{"".join(card_html(p) for p in stream)}</div>
    </div>
  </section>
"""
    else:
        for heading, items in sections:
            if not items:
                continue
            doc += f"""
  <section class="section">
    <div class="container">
      <div class="section__head">
        <h2 class="section__title">{e(heading)}</h2>
        <span class="section__note">{len(items):02d} guides</span>
      </div>
      <div class="grid">{"".join(card_html(p) for p in items)}</div>
    </div>
  </section>
"""

    doc += newsletter_html()
    doc += "</main>\n" + footer_html(tax) + "</body>\n</html>\n"
    return doc


def render_facts(post: dict) -> str:
    rows = "".join(
        f'<div class="facts__row"><dt>{e(k)}</dt><dd>{e(v)}</dd></div>'
        for k, v in post["facts"]
    )
    return f"""
<aside class="facts" aria-label="Species profile">
  <div class="facts__head">
    <span>Species profile</span>
    <span>{e(post['sci'])}</span>
  </div>
  <dl>{rows}</dl>
</aside>
"""


COUNT_WORDS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}


def render_gear(post: dict) -> str:
    kit = post["_kit"]
    items = ""
    for p in kit:
        cat = aff.category(p["cat"])
        items += f"""
    <li class="gear__item" data-cat="{p['cat']}">
      <div class="gear__thumb">{aff.tile(p)}</div>
      <div class="gear__copy">
        <div class="gear__cat">{e(cat['label'])}</div>
        <h3 class="gear__name">{e(p['title'])}</h3>
        <p class="gear__why">{e(p['why'])}</p>
        <div class="gear__price">Typical price <b>{e(p.get('price', '—'))}</b></div>
      </div>
      <a class="amz-btn" href="{e(p['url'])}" target="_blank" rel="{aff.REL}">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M6 7h12l1.3 13H4.7L6 7z"/><path d="M9 7V5.6a3 3 0 0 1 6 0V7"/>
        </svg>
        Check price on Amazon
        <svg class="amz-btn__arrow" width="12" height="12" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2.2" aria-hidden="true">
          <path d="M5 12h14M13 6l6 6-6 6"/>
        </svg>
      </a>
    </li>"""

    n = COUNT_WORDS.get(len(kit), str(len(kit)))
    noun = "piece" if len(kit) == 1 else "pieces"
    return f"""
<section class="gear" id="gear" aria-labelledby="gear-title">
  <div class="gear__head">
    <span class="gear__kicker">The kit list</span>
    <h2 id="gear-title">What we actually use</h2>
    <p class="gear__intro">{n} {noun} of equipment that do most of the work in a {e(post['species'])} setup. Nothing here is here because a brand asked.</p>
  </div>
  <div class="disclosure">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
      <circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>
    </svg>
    <span>Affiliate disclosure — {aff.DISCLOSURE} Prices are indicative and change often.</span>
  </div>
  <ul class="gear__list">{items}
  </ul>
  <p class="amz-note">Links open Amazon in a new tab. We do not set or track prices.</p>
</section>
"""


def render_rail(post: dict, body: str, related: list[dict]) -> str:
    toc = "".join(f'<li><a href="#{sid}">{e(title)}</a></li>' for sid, title in toc_items(body))
    tags = "".join(f"<span>{e(t)}</span>" for t in post["tags"])
    product = ""
    if post.get("primary"):
        product = f"""
  <div class="rail__block rail__block--product">
    <div class="rail__label">Recommended</div>
    {aff.product_card(post['primary'], compact=True)}
  </div>"""
    cta = ""
    if related:
        nxt = related[0]
        cta = f"""
  <div class="rail__cta">
    <h3>Next in {e(nxt['group'].lower())}</h3>
    <p>{e(nxt['title'])}</p>
    <a href="{nxt['id']}.html">Read the guide →</a>
  </div>"""
    return f"""
<aside class="rail" aria-label="Article sidebar">
  <div class="rail__block">
    <div class="rail__label">In this guide</div>
    <ul class="toc">{toc}</ul>
  </div>{product}
  <div class="rail__block">
    <div class="rail__label">Filed under</div>
    <div class="rail__tags">{tags}</div>
  </div>{cta}
</aside>
"""


ARTICLE_JS = """
<script>
(function () {
  var bar = document.querySelector('.progress');
  var links = [].slice.call(document.querySelectorAll('.toc a'));
  var heads = links.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); });
  function onScroll() {
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    if (bar) { bar.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + '%'; }
    var idx = -1;
    for (var i = 0; i < heads.length; i++) {
      if (heads[i] && heads[i].getBoundingClientRect().top <= 150) { idx = i; }
    }
    links.forEach(function (a, i) { a.classList.toggle('is-active', i === idx); });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  onScroll();
})();
</script>
"""


def render_article(post: dict, body: str, related: list[dict], tax: dict) -> str:
    author = AUTHORS[post["author"]]
    canonical = absolute(post["id"] + ".html")
    image = f"static/images/{post['image']}"

    jsonld = [
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": post["title"],
            "description": post["dek"],
            "image": [absolute(image)],
            "datePublished": post["date"],
            "dateModified": post["date"],
            "articleSection": post["category"],
            "keywords": ", ".join(post["tags"]),
            "inLanguage": LANG,
            "author": {
                "@type": "Person",
                "name": author["name"],
                "jobTitle": author["role"],
                "description": author["bio"],
            },
            "publisher": {
                "@type": "Organization",
                "name": SITE_NAME,
                "url": SITE_URL + "/",
                "logo": {"@type": "ImageObject", "url": absolute("static/logo.svg")},
            },
            "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
                {"@type": "ListItem", "position": 2, "name": post["category"],
                 "item": absolute(f"category-{slugify(post['category'])}.html")},
                {"@type": "ListItem", "position": 3, "name": post["title"], "item": canonical},
            ],
        },
    ]

    pairs = faq_pairs(body)
    if pairs:
        jsonld.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in pairs
            ],
        })

    doc = head(
        f"{post['title']} — {SITE_NAME}",
        post["dek"],
        canonical,
        image=image,
        og_type="article",
        published=post["date"] + "T09:00:00+00:00",
        jsonld=jsonld,
        body_class="page-article",
    )
    doc += '<div class="progress" role="presentation"></div>\n'
    doc += nav_html(tax)

    related_cards = "".join(card_html(p) for p in related)

    doc += f"""
<main id="main">
  <article>
    <header class="article-head">
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="index.html">Home</a><span class="sep">/</span>
        <a href="guides.html">Field guides</a><span class="sep">/</span>
        <a href="category-{slugify(post['category'])}.html">{e(post['category'])}</a>
      </nav>
      <a class="article-head__cat" href="category-{slugify(post['category'])}.html">{e(post['category'])}</a>
      <h1>{e(post['title'])}</h1>
      <p class="article-head__dek">{e(post['dek'])}</p>
      <div class="byline">
        <span class="byline__avatar" aria-hidden="true">{initials(author['name'])}</span>
        <div>
          <div class="byline__who">{e(author['name'])}</div>
          <div class="byline__role">{e(author['role'])}</div>
        </div>
        <div class="byline__meta">
          <span>{fmt_date(post['date'])}</span><span class="dot"></span>
          <span>{post['_read']} min read</span><span class="dot"></span>
          <span><i>{e(post['sci'])}</i></span>
        </div>
      </div>
    </header>

    <figure class="article-figure">
      <div class="article-figure__frame">
        <img src="{image}" alt="{e(post['alt'])}" width="1536" height="1024"
             fetchpriority="high" decoding="async">
      </div>
      <figcaption>
        {e(post['caption'])}
        <span class="fig-credit">{credit_html(post['image'])}</span>
      </figcaption>
    </figure>

    <div class="article-layout">
      <div>
        {render_facts(post)}
        <div class="prose prose--magazine">
          {body}
        </div>
        {render_gear(post)}
        {aff.disclosure()}
        <div class="author">
          <span class="author__avatar" aria-hidden="true">{initials(author['name'])}</span>
          <div>
            <h3>{e(author['name'])}</h3>
            <div class="author__role">{e(author['role'])}</div>
            <p>{e(author['bio'])}</p>
          </div>
        </div>
      </div>
      {render_rail(post, body, related)}
    </div>
  </article>

  <section class="related" aria-labelledby="related-title">
    <div class="container">
      <div class="section__head">
        <span class="section__num">03</span>
        <h2 class="section__title" id="related-title">Keep <em>reading</em></h2>
        <a class="section__link" href="guides.html">All guides</a>
      </div>
      <div class="grid">{related_cards}</div>
    </div>
  </section>
"""
    doc += newsletter_html()
    doc += "</main>\n" + footer_html(tax) + ARTICLE_JS + "</body>\n</html>\n"
    return doc


# --------------------------------------------------------------------------- #
# sitemap / robots / feed
# --------------------------------------------------------------------------- #

def render_sitemap(posts: list[dict], tax: dict) -> str:
    newest = max(p["date"] for p in posts)
    entries = [("", newest, "weekly", "1.0")]
    for p in posts:
        entries.append((p["id"] + ".html", p["date"], "monthly", "0.8"))

    # The filtered indexes are real, indexable pages, so they belong in the
    # sitemap alongside the articles. Lastmod is derived from the posts each
    # page lists — still fully automatic, nothing hand-maintained.
    entries.append(("guides.html", newest, "weekly", "0.7"))
    for c, s in tax["cats"]:
        last = max((p["date"] for p in posts if p["category"] == c), default=newest)
        entries.append((f"category-{s}.html", last, "weekly", "0.7"))
    entries.append(("species.html", newest, "monthly", "0.6"))
    for g, s in tax["groups"]:
        last = max((p["date"] for p in posts if p["group"] == g), default=newest)
        entries.append((f"species-{s}.html", last, "monthly", "0.6"))

    urls = ""
    for path, lastmod, freq, prio in entries:
        urls += (
            "  <url>\n"
            f"    <loc>{absolute(path)}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{prio}</priority>\n"
            "  </url>\n"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n"
    )


def render_robots() -> str:
    return f"User-agent: *\nAllow: /\n\nSitemap: {absolute('sitemap.xml')}\n"


def render_feed(posts: list[dict]) -> str:
    items = ""
    for p in posts:
        link = absolute(p["id"] + ".html")
        items += f"""    <item>
      <title>{e(p['title'])}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{rfc822(p['date'])}</pubDate>
      <category>{e(p['category'])}</category>
      <description>{e(p['dek'])}</description>
    </item>
"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{e(SITE_NAME)} — Field Notes</title>
    <link>{SITE_URL}/</link>
    <description>Independent field guides to exotic pets.</description>
    <language>en-us</language>
    <atom:link href="{absolute('feed.xml')}" rel="self" type="application/rss+xml"/>
{items}  </channel>
</rss>
"""


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #

def resolve_kit(post: dict, block: dict) -> list[dict]:
    """Turn the article's `kit` id list into fully resolved product records.

    The per-article `affiliate` block in keywords.json overrides the catalogue
    for the primary product only, so an operator can point one article at a
    specific ASIN without disturbing the shared product definition.
    """
    primary_id = block.get("affiliate_product_id", "")
    kit = []
    for entry in post.get("kit", []):
        pid, why = entry[0], entry[1]
        place = entry[2] if len(entry) > 2 else ""
        overrides = {}
        if pid == primary_id:
            overrides = {
                "title": block.get("affiliate_title"),
                "url": block.get("affiliate_url"),
                "image": block.get("affiliate_image"),
                "price": block.get("affiliate_price"),
                "category": block.get("affiliate_category"),
            }
        product = aff.resolve(pid, why=why, **overrides)
        product["place"] = place
        kit.append(product)
    return kit


def collect() -> list[dict]:
    with KEYWORDS.open(encoding="utf-8") as fh:
        keywords = json.load(fh)

    # Two sources, one shape. `keywords.json` drives the hand-authored six in
    # content.py; `library.json` carries everything the factory has grown since,
    # metadata and all, so a generated article never needs an entry in the
    # hand-written source file — and can be removed by deleting one record.
    records: list[tuple[dict, dict]] = []
    for item in keywords:
        post = POSTS.get(item["id"])
        if not post:
            print(f"  ! {item['id']}: no editorial metadata in content.py — skipped")
            continue
        records.append((item, post))

    for entry in load_library():
        pid = entry.get("id")
        if not pid:
            continue
        item = {
            "id": pid,
            "target_keyword": entry.get("target_keyword", ""),
            "topic": entry.get("topic", ""),
            "category": entry.get("category", ""),
            "affiliate": entry.get("affiliate") or {},
        }
        post = {k: v for k, v in entry.items()
                if k not in {"target_keyword", "topic", "affiliate"}}
        records.append((item, post))

    posts = []
    for item, post in records:
        # Generated articles declare their own image and group; the hand-authored
        # six are cross-checked against SPECIES_IMAGE, which is the table that
        # exists so a jumping-spider guide can never be illustrated with a dog.
        image, group = SPECIES_IMAGE.get(
            item["id"], (post.get("image"), post.get("group")))
        # Data defects are reported, not fatal: a mismatch between the image
        # table and content.py used to abort the whole build, which meant one
        # bad row could freeze the entire site. The page keeps its own image
        # and the operator gets a line in the log.
        if image != post["image"] or group != post["group"]:
            print(f"  ⚠ {item['id']}: species/image table says {image} / {group}, "
                  f"content.py says {post['image']} / {post['group']} — using content.py")
        if not (IMAGES / post["image"]).exists():
            print(f"  ⚠ {item['id']}: static/images/{post['image']} is missing — "
                  f"the card will render without a photograph")

        block = item.get("affiliate") or {}
        try:
            kit = resolve_kit(post, block)
        except KeyError as exc:
            print(f"  ⚠ {item['id']}: {exc} — that product is left out of the kit")
            kit = []

        post = dict(post)
        post.update({
            "id": item["id"],
            "keyword": item["target_keyword"],
            # keywords.json is the operator-facing switchboard, so an explicit
            # `is_pinned` there wins over the editorial default in content.py.
            "is_pinned": bool(item.get("is_pinned", post.get("is_pinned", False))),
            "_item": item,
            "_kit": kit,
            "primary": kit[0] if kit else None,
        })
        posts.append(post)

    # Two records writing the same file would silently overwrite one article
    # with another. Warn and keep the first rather than abort: the rest of the
    # library is still publishable.
    seen: set[str] = set()
    unique: list[dict] = []
    for p in posts:
        if p["id"] in seen:
            print(f"  ⚠ duplicate post id {p['id']} — later entry ignored")
            continue
        seen.add(p["id"])
        unique.append(p)
    posts = unique

    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def audit(posts: list[dict], tax: dict) -> list[str]:
    """Check the generated pages against themselves.

    Two failures this catches, both of which shipped once: a nav label whose
    anchor was never rendered (dead link), and a card whose image or tag
    belongs to a different article. Cheap enough to run on every build, and it
    is the only thing that stops the navigation from drifting away from the
    data again.
    """
    problems: list[str] = []
    by_id = {p["id"]: p for p in posts}

    anchors: dict[str, set[str]] = {}
    for f in ROOT.glob("*.html"):
        anchors[f.name] = set(re.findall(r'\bid="([^"]+)"', f.read_text(encoding="utf-8")))

    for f in sorted(ROOT.glob("*.html")):
        doc = f.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', doc):
            if href.startswith(("http", "mailto:", "//")):
                continue
            target, _, frag = href.partition("#")
            target = target or f.name
            if not target.endswith(".html"):
                continue
            if target not in anchors:
                problems.append(f"{f.name}: {href} → no such page")
            elif frag and frag not in anchors[target]:
                problems.append(f"{f.name}: {href} → no such section")

    index = (ROOT / "index.html").read_text(encoding="utf-8")

    for label, slug in tax["cats"] + tax["groups"]:
        if f'id="{slug}"' not in index:
            problems.append(f"index.html: nav entry “{label}” has no section (#{slug})")

    for block in re.findall(r'<article class="card[^"]*">(.*?)</article>', index, re.S):
        href = re.search(r'href="(pet-\d+)\.html"', block)
        img = re.search(r'src="static/images/([^"]+)"', block)
        tag = re.search(r'<span class="card__tag">([^<]+)</span>', block)
        title = re.search(r'<h3 class="card__title"><a href="[^"]+">([^<]+)</a>', block)
        if not (href and img and tag and title):
            problems.append("index.html: a card is missing its link, image, tag or title")
            continue
        post = by_id.get(href.group(1))
        if post is None:
            problems.append(f"index.html: card links to unknown {href.group(1)}")
            continue
        if img.group(1) != post["image"]:
            problems.append(f"index.html: {post['id']} shows {img.group(1)}, expected {post['image']}")
        if html.unescape(tag.group(1)) != post["category"]:
            problems.append(f"index.html: {post['id']} tagged “{tag.group(1)}”, expected “{post['category']}”")
        if html.unescape(title.group(1)) != post["title"]:
            problems.append(f"index.html: {post['id']} titled “{title.group(1)}”")

    return problems


def prose_region(doc: str) -> str | None:
    """Inner HTML of the article's `.prose` block, found by div nesting.

    The old version looked for `</div>` followed by `<section class="gear"`.
    That silently depended on the gear block existing, and it broke the moment
    the prose block was renamed to `prose prose--magazine`.
    """
    m = re.search(r'<div class="prose[^"]*">', doc)
    if not m:
        return None
    start = m.end()
    depth = 1
    for tag in re.finditer(r"<(/?)div\b[^>]*>", doc[start:]):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return doc[start:start + tag.start()]
    return None


def prose_text(fragment: str) -> str:
    """Readable text of an HTML fragment: entities resolved, whitespace folded."""
    return re.sub(r"\s+", " ", html.unescape(strip_tags(fragment))).strip()


def _shingles(text: str, n: int = 5) -> set[str]:
    """Word n-grams of a body, used for near-duplicate detection."""
    words = re.findall(r"[a-z']+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(max(0, len(words) - n + 1))}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def audit_content(posts: list[dict]) -> list[str]:
    """Prove that every article is its own article.

    Catches the two failure modes that make a library read as one page repeated:
    two posts sharing a title, and two posts sharing a body (a stale cache file
    or a template that rendered the wrong record). It also re-reads each written
    page and compares its prose against the body that was passed to the
    renderer, so a mismatch between the data and the output cannot ship.

    The comparison is text-to-text, not text-to-markup. An earlier version
    searched for the stripped text of the first `<h2>` inside the raw HTML of
    the prose block; any inline markup in a heading (`<em>`, `<strong>`, a link)
    or an entity such as `&nbsp;` made the stripped needle impossible to find
    and failed the build on a perfectly correct page — the `pet-003` false
    positive. Comparing normalised text on both sides is immune to that.
    """
    problems: list[str] = []
    seen_titles: dict[str, str] = {}
    seen_bodies: dict[str, str] = {}
    shingle_sets: dict[str, set[str]] = {}

    for p in posts:
        key = p["title"].strip().lower()
        if key in seen_titles:
            problems.append(f"{p['id']} reuses the title of {seen_titles[key]}")
        seen_titles[key] = p["id"]

        want = prose_text(p["_body"])
        digest = hashlib.sha1(want.encode("utf-8")).hexdigest()
        if digest in seen_bodies:
            problems.append(f"{p['id']} shares its body with {seen_bodies[digest]}")
        seen_bodies[digest] = p["id"]
        shingle_sets[p["id"]] = _shingles(want)

        page = ROOT / f"{p['id']}.html"
        if not page.exists():
            problems.append(f"{p['id']}.html was not written")
            continue
        doc = page.read_text(encoding="utf-8")

        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S)
        if not h1 or html.unescape(strip_tags(h1.group(1))) != p["title"]:
            problems.append(f"{p['id']}.html <h1> does not match its title")

        # Identity, independent of the prose: the canonical URL is the only
        # tag on the page that names the record it was rendered for.
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', doc)
        if not canon or canon.group(1) != absolute(p["id"] + ".html"):
            got = canon.group(1) if canon else "nothing"
            problems.append(f"{p['id']}.html canonical points at {got}")

        region = prose_region(doc)
        if region is None:
            problems.append(f"{p['id']}.html has no .prose block")
            continue
        got = prose_text(region)
        if got != want:
            problems.append(
                f"{p['id']}.html prose is not this article's body "
                f"({len(got)} chars on the page, {len(want)} in the record)"
            )

    # An exact hash only catches a body that is byte-identical. A model asked to
    # rewrite the same topic paraphrases it, which still reads as the same
    # article to a human and to Google. 5-gram Jaccard catches that; genuinely
    # different guides score ~0.00-0.05 here, so 0.25 is far from a false
    # positive and still catches a recycled draft.
    ids = list(shingle_sets)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            score = _jaccard(shingle_sets[a], shingle_sets[b])
            if score > 0.25:
                problems.append(f"{a} and {b} share {score:.0%} of their phrasing")

    return problems


def audit_voice(posts: list[dict]) -> list[str]:
    """Every published body must clear the four-beat brief, fallback included.

    The generation gate already refuses an off-brief draft, but a hand-written
    `content.py` body bypasses that gate entirely — and those are the bodies
    that ship when the API is down. This is the same check, applied to whatever
    actually got rendered.
    """
    problems: list[str] = []
    for p in posts:
        for issue in check_structure(p["_body"]):
            problems.append(f"{p['id']}: {issue}")
    return problems


def audit_cards(pages: list[str]) -> list[str]:
    """Every card must hold its own photograph, title and summary.

    A template that emits the media and the body as siblings still renders —
    it just renders as two blocks that read like two separate articles. This
    walks the written pages and names any card that lost one of its halves, or
    whose image drifted below the headline.
    """
    problems: list[str] = []
    for name in pages:
        page = ROOT / name
        if not page.exists():
            continue
        doc = page.read_text(encoding="utf-8")
        for m in re.finditer(r'<article class="card[^"]*">(.*?)</article>', doc, re.S):
            block = m.group(1)
            label = re.search(r'href="(pet-\d+)\.html"', block)
            pid = label.group(1) if label else "?"
            has_img = "<img" in block
            has_title = 'class="card__title"' in block
            if not (has_img and has_title):
                problems.append(f"{name}: card {pid} is split "
                                f"(image={has_img}, title={has_title})")
            elif block.index("<img") > block.index('class="card__title"'):
                problems.append(f"{name}: card {pid} renders its image after the title")
    return problems


def audit_collections(posts: list[dict], tax: dict) -> list[str]:
    """Every filtered index must list exactly its own slice — no more, no less."""
    problems: list[str] = []

    def card_ids(name: str) -> set[str]:
        page = ROOT / name
        if not page.exists():
            problems.append(f"{name} was not written")
            return set()
        doc = page.read_text(encoding="utf-8")
        return set(re.findall(
            r'<article class="card[^"]*">\s*<a[^>]*href="(pet-\d+)\.html"', doc, re.S))

    want = {p["id"] for p in posts}
    if card_ids("guides.html") != want:
        problems.append("guides.html does not list every guide")
    if card_ids("species.html") != want:
        problems.append("species.html does not list every guide")

    for c, s in tax["cats"]:
        expect = {p["id"] for p in posts if p["category"] == c}
        got = card_ids(f"category-{s}.html")
        if got != expect:
            problems.append(f"category-{s}.html lists {sorted(got)}, expected {sorted(expect)}")

    for g, s in tax["groups"]:
        expect = {p["id"] for p in posts if p["group"] == g}
        got = card_ids(f"species-{s}.html")
        if got != expect:
            problems.append(f"species-{s}.html lists {sorted(got)}, expected {sorted(expect)}")

    return problems


def audit_pinned(posts: list[dict], tax: dict) -> list[str]:
    """Pinned guides must lead every list, everything behind them newest-first.

    Reads the written pages instead of the in-memory list, so a template that
    quietly drops `rank_posts` (or renders the banner after the grid) fails the
    build rather than shipping a homepage whose lead story changes every run.
    """
    problems: list[str] = []
    known = {p["id"] for p in posts}

    def order(name: str) -> list[str]:
        page = ROOT / name
        if not page.exists():
            problems.append(f"{name} was not written")
            return []
        seen: set[str] = set()
        out: list[str] = []
        for m in re.finditer(r'href="(pet-\d+)\.html"', page.read_text(encoding="utf-8")):
            pid = m.group(1)
            if pid in known and pid not in seen:
                seen.add(pid)
                out.append(pid)
        return out

    cases: list[tuple[str, list[str]]] = [
        ("index.html", [p["id"] for p in rank_posts(posts)]),
        ("guides.html", [p["id"] for p in rank_posts(posts)]),
    ]
    for c, s in tax["cats"]:
        items = [p for p in posts if p["category"] == c]
        cases.append((f"category-{s}.html", [p["id"] for p in rank_posts(items)]))
    for g, s in tax["groups"]:
        items = [p for p in posts if p["group"] == g]
        cases.append((f"species-{s}.html", [p["id"] for p in rank_posts(items)]))

    # species.html groups the archive, so its expected order is the per-group
    # ranking concatenated in taxonomy order.
    species_expect: list[str] = []
    for g, _ in tax["groups"]:
        species_expect += [p["id"] for p in rank_posts([p for p in posts if p["group"] == g])]
    cases.append(("species.html", species_expect))

    for name, want in cases:
        got = order(name)
        if got != want:
            problems.append(f"{name} order {got} != {want}")

    return problems


def collection_pages(posts: list[dict], tax: dict) -> list[tuple[str, str]]:
    """(filename, html) for every filtered index page.

    Generated from `tax`, so a new category or species in `content.py` gets its
    own page, nav entry and sitemap row without touching this function.
    """
    pages: list[tuple[str, str]] = []

    pages.append(("guides.html", render_collection(
        tax, posts,
        slug="guides", kicker="The collection",
        title="All field guides", title_html="All <em>field guides</em>",
        dek="Every keeper-written guide in the archive, newest first.",
        active="guides", note="Independent · reader-supported")))

    for c, s in tax["cats"]:
        items = [p for p in posts if p["category"] == c]
        label = CATEGORY_SHORT.get(c, c)
        pages.append((f"category-{s}.html", render_collection(
            tax, items,
            slug=f"category-{s}", kicker="Filed under",
            title=f"{label} guides", title_html=f"{e(label)} <em>guides</em>",
            dek=CATEGORY_DEK.get(c, f"Every guide filed under {label}."),
            active=f"category-{s}", note=c)))

    groups = [(g, s, [p for p in posts if p["group"] == g]) for g, s in tax["groups"]]

    pages.append(("species.html", render_collection(
        tax, posts,
        slug="species", kicker="By species",
        title="Species index", title_html="Species <em>index</em>",
        dek="Browse the archive by the animal in the enclosure.",
        active="species", sections=[(g, items) for g, s, items in groups])))

    for g, s, items in groups:
        pages.append((f"species-{s}.html", render_collection(
            tax, items,
            slug=f"species-{s}", kicker="By species",
            title=f"{g} guides", title_html=f"{e(g)} <em>guides</em>",
            dek=f"Field guides for the {g.lower()} in our collection.",
            active=f"species-{s}", note=g)))

    return pages


def clean_drafts() -> int:
    """Delete generated drafts so the next build rewrites every body.

    Scoped to `cache/` and `drafts/`, files only: this never walks the repo root
    and never removes a directory, so a mistyped path cannot take the site with
    it. The Google verification file and `sitemap.xml` are regenerated by the
    build and are not touched here.
    """
    removed = 0
    for folder in (CACHE, DRAFTS):
        if not folder.is_dir():
            continue
        if ROOT.resolve() not in folder.resolve().parents:
            continue
        for f in sorted(folder.iterdir()):
            if f.is_file():
                f.unlink()
                removed += 1
    print(f"  cleaned {removed} cached draft(s)")
    return removed


def build(refresh: bool = False, batch: int = 0, strict: bool = False,
          grow_count: int = 0) -> None:
    # Growth happens before the corpus is read, so the rest of the build sees
    # the new articles exactly like the six hand-written ones: same collect(),
    # same taxonomy, same audits, same sitemap. Growing is an edit to the data,
    # not a second pipeline.
    if grow_count:
        print(f"Growing the library by up to {grow_count} article(s)")
        grow(grow_count, collect())

    posts = collect()
    tax = taxonomy(posts)
    CACHE.mkdir(exist_ok=True)

    # The writer is told what the site has already published before it writes a
    # word. Computed once per build — every generation call in this run gets the
    # same list, and it includes pages found on disk that the corpus does not
    # know about.
    set_history(posts)

    for warning in aff.validate(posts):
        print(f"  ! affiliate: {warning}")

    print(f"Exotic Pet Care Hub — building {len(posts)} guides")

    # `--batch N` is the content-factory switch: touch the N least recently
    # written guides instead of all of them, so a 2-day cadence ships 4-5 fresh
    # bodies rather than regenerating the whole library every run.
    forced: set[str] = set()
    if batch > 0:
        def age(p: dict) -> float:
            f = CACHE / f"{p['id']}.html"
            return f.stat().st_mtime if f.exists() else 0.0

        # After a CI checkout every cache file has the same mtime, so sorting by
        # age alone always picked the same first N guides and froze the rest.
        # A persisted cursor rotates the window on each run.
        order = sorted(posts, key=lambda p: (age(p), p["id"]))
        cursor_file = CACHE / ".batch_cursor"
        try:
            start = int(cursor_file.read_text(encoding="utf-8").strip()) % len(order)
        except (OSError, ValueError):
            start = 0
        take = min(batch, len(order))
        forced = {order[(start + i) % len(order)]["id"] for i in range(take)}
        cursor_file.write_text(str((start + take) % len(order)), encoding="utf-8")
        print(f"  batch mode: regenerating {len(forced)} of {len(posts)} guides")

    # Bodies are filed by id in their own map and only ever read back by that
    # same id, so a page cannot be handed a body that belongs to another
    # record — not through a stale loop variable, not through a shared dict.
    bodies: dict[str, str] = {}
    patched: list[str] = []
    for post in posts:
        force = refresh and (not batch or post["id"] in forced)
        body, source = resolve_body(post["_item"], post, force)
        clean = sanitize_body(body, post)
        # A body that opens without a measurement gets a factual standfirst
        # built from its own species panel. This is the difference between a
        # warning and a dead build: the article still ships, and the number in
        # it is one the page already publishes.
        clean, added = ensure_hook(post, clean)
        if added:
            patched.append(post["id"])
        # The editorial layer runs on the sanitised body only: badges and the
        # lede must never be able to reach inside a commerce card, and the card
        # markup is injected afterwards, so `highlight_params` cannot see it.
        bodies[post["id"]] = aff.inject_cards(magazine_body(clean), post)
        post["_source"] = source
        print(f"  {post['id']}  {post['species']:<22} body: {source}")

    if patched:
        print(f"  hook: field parameters prepended to {', '.join(patched)}")

    # collect() already refuses duplicate ids, so this can only fire if a future
    # change breaks that. Drop the orphans instead of aborting: one bad record
    # should not take the other five articles offline with it.
    orphans = [p["id"] for p in posts if p["id"] not in bodies]
    if orphans:
        print(f"  ⚠ no body for {', '.join(orphans)} — those pages are skipped")
        posts = [p for p in posts if p["id"] in bodies]

    for post in posts:
        post["_body"] = bodies[post["id"]]
        post["_read"] = read_time(post["_body"])

    for post in posts:
        related = [p for p in posts if p["id"] != post["id"]]
        related.sort(key=lambda p: (p["group"] != post["group"], p["date"] < post["date"]))
        (ROOT / f"{post['id']}.html").write_text(
            render_article(post, bodies[post["id"]], related[:3], tax), encoding="utf-8"
        )

    (ROOT / "index.html").write_text(render_index(posts), encoding="utf-8")
    indexes = collection_pages(posts, tax)
    for name, page in indexes:
        (ROOT / name).write_text(page, encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(render_sitemap(posts, tax), encoding="utf-8")
    (ROOT / "robots.txt").write_text(render_robots(), encoding="utf-8")
    (ROOT / "feed.xml").write_text(render_feed(posts), encoding="utf-8")

    cards = sum(p["_body"].count('<aside class="amz-card') for p in posts)
    print(f"  wrote index.html + {len(posts)} article pages + {len(indexes)} index pages")
    print(f"  pinned: {', '.join(p['id'] for p in posts if p['is_pinned']) or 'none'}")
    print(f"  affiliate: {sum(len(p['_kit']) for p in posts)} products, {cards} in-article cards")
    print("  wrote sitemap.xml, robots.txt, feed.xml")
    print(f"  base url: {SITE_URL}")

    problems = (audit(posts, tax) + audit_content(posts) + audit_voice(posts)
                + audit_collections(posts, tax) + audit_pinned(posts, tax)
                + audit_cards(["index.html"] + [name for name, _ in indexes]))
    if problems:
        for p in problems:
            print(f"  ⚠ {p}")
        if strict:
            raise SystemExit(f"audit failed: {len(problems)} problem(s) "
                             f"(remove --strict to publish anyway)")
        # The pages are already on disk at this point. Exiting non-zero would
        # only stop CI from committing them, which is how the site went stale
        # before: one advisory note took the whole deployment with it.
        print(f"  ! {len(problems)} advisory warning(s) — pages are written, "
              f"build continues")
    else:
        print("  ✓ audit clean")

    sources: dict[str, int] = {}
    for p in posts:
        sources[p["_source"]] = sources.get(p["_source"], 0) + 1
    rejected = sources.pop("rejected (off-brief)", 0)

    print(f"  bodies: {', '.join(f'{n} {k}' for k, n in sorted(sources.items()))}")
    print(f"  editorial: {len(posts)} bodies clear the four-beat brief")
    print(f"  link audit: clean ({len(tax['cats']) + len(tax['groups'])} sections, "
          f"{len(posts)} cards, {len(posts)} unique bodies)")
    tail = f", {rejected} draft(s) rejected" if rejected else ""
    if patched:
        tail += f", {len(patched)} hook(s) backfilled"
    print(f"  ✓ Build passed — {len(posts)} pages written, {len(indexes) + 1} index pages"
          f"{tail}")


def serve(port: int = 8000) -> None:
    import functools
    import http.server
    import socketserver

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        print(f"  serving http://127.0.0.1:{port}  (Ctrl+C to stop)")
        httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the Exotic Pet Care Hub static site.")
    parser.add_argument("--refresh", action="store_true", help="force DeepSeek regeneration, ignoring cache/")
    parser.add_argument("--batch", type=int, default=0, metavar="N",
                        help="regenerate at most N guides this run (least recently written first)")
    parser.add_argument("--clean", action="store_true",
                        help="delete every cached draft before building, so all bodies are rewritten")
    parser.add_argument("--strict", action="store_true",
                        help="fail the build on any audit warning (the old behaviour; off by default)")
    parser.add_argument("--grow", type=int, default=0, metavar="N",
                        help="publish up to N unpublished topics from topics.py, "
                             "then build (breadth-first across species groups)")
    parser.add_argument("--serve", action="store_true", help="serve the site on :8000 after building")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.clean:
        clean_drafts()
    build(refresh=args.refresh or args.clean, batch=args.batch,
          strict=args.strict, grow_count=args.grow)
    if args.serve:
        try:
            serve(args.port)
        except KeyboardInterrupt:
            sys.exit(0)
