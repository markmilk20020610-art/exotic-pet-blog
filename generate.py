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
from vivarium import VIVARIUM_ASSETS, vivarium_html

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
IMAGES = STATIC / "images"
CACHE = ROOT / "cache"
KEYWORDS = ROOT / "keywords.json"

SITE_URL = os.environ.get("SITE_URL", "https://exoticpethub.com").rstrip("/")
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

PROMPT = Template("""You are the senior keeper writing for Exotic Pet Care Hub, an independent
exotic-animal magazine. Write the body of a field guide in English.

Target keyword: "$keyword"
Topic: $topic
Species: $species ($sci)
Editorial category: $category

Gear this article is allowed to recommend — refer to it by token, never by name
or price:
$products

Rules:
- Return an HTML fragment only. No <html>, no <head>, no markdown fences.
- Do NOT include an <h1>; the page template renders the title.
- Do NOT write any <a> tag, price, star rating or button. The template renders
  the product card for you.
- CARD PLACEMENT. Insert the token on its own line at the moment the reader
  first meets the problem the product solves:
    {{affiliate:feeding}}   first time you say what to feed, or how to measure a portion
    {{affiliate:habitat}}   first time you specify enclosure, substrate, heating, lighting or decor
    {{affiliate:health}}    only if the piece covers illness, quarantine, mites, shedding or a refusal to eat
  Use each token at most once. Never invent a token. Never explain the token.
  The sentence before it must lead in naturally — "The cheapest fix here is a
  second hygrometer:" not "Buy this:".
- Structure: 4-6 <h2> sections, <h3> sub-points where useful, one <table> summary,
  and a closing "Frequently asked questions" section with 3 <h3> questions each
  followed by a single <p> answer.
- 700-950 words. Practical, specific, E-E-A-T compliant. No invented statistics.
- Never mention other animal species as the subject of the article.
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


def body_fingerprint(item: dict, post: dict) -> str:
    """Stable hash of the inputs that make this article this article."""
    raw = "|".join([item["id"], item["target_keyword"], item["topic"], post["species"]])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


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
            )
            for attempt in range(3):
                try:
                    resp = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": "You are a professional exotic pet husbandry writer and SEO editor."},
                            {"role": "user", "content": prompt},
                        ],
                        stream=False,
                    )
                    body = resp.choices[0].message.content
                    body = re.sub(r"^```(?:html)?|```$", "", body.strip(), flags=re.M).strip()
                    if len(strip_tags(body)) < 300:
                        raise ValueError("model returned an empty body")
                    cache_file.write_text(body, encoding="utf-8")
                    meta_file.write_text(
                        json.dumps(
                            {"id": item["id"], "fingerprint": stamp,
                             "keyword": item["target_keyword"]},
                            ensure_ascii=False,
                        ),
                        encoding="utf-8",
                    )
                    return body, "deepseek"
                except Exception as exc:  # noqa: BLE001
                    print(f"    retry {attempt + 1}/3: {exc}")
                    if attempt == 2:
                        raise
                    time.sleep(5)
        except Exception as exc:  # noqa: BLE001
            print(f"    ! API unavailable ({exc}); using editorial fallback")

    return post["body_html"], "fallback"


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


def card_html(post: dict, wide: bool = False) -> str:
    author = AUTHORS[post["author"]]
    cls = "card card--wide" if wide else "card"
    return f"""
<article class="{cls}">
  <a class="card__media" href="{post['id']}.html" tabindex="-1" aria-hidden="true">
    <img src="static/images/{post['image']}" alt="{e(post['alt'])}"
         width="1536" height="1024" loading="lazy" decoding="async">
    <span class="card__tag">{e(post['category'])}</span>
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
    featured = posts[0]
    rest = posts[1:]
    lead, others = rest[0], rest[1:]
    cards = card_html(lead, wide=True) + "".join(card_html(p) for p in others)

    tax = taxonomy(posts)
    by_cat: dict[str, list[dict]] = {}
    by_group: dict[str, list[dict]] = {}
    for p in posts:
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
                for i, p in enumerate(posts)
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

    doc += f"""
<main id="main">
  <section class="hero">
    <div class="hero__media">
      <img src="static/images/{featured['image']}" alt="{e(featured['alt'])}"
           width="1536" height="1024" fetchpriority="high" decoding="async">
    </div>
    <div class="container hero__inner">
      <div class="hero__content">
      <div class="hero__kicker"><span>◆</span> Featured field guide</div>
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
    listed = posts if sections is None else [p for _, items in sections for p in items]

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
        doc += f"""
  <section class="section">
    <div class="container">
      <div class="grid">{"".join(card_html(p) for p in posts)}</div>
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
        <div class="prose">
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

    posts = []
    for item in keywords:
        post = POSTS.get(item["id"])
        if not post:
            print(f"  ! {item['id']}: no editorial metadata in content.py — skipped")
            continue
        image, group = SPECIES_IMAGE[item["id"]]
        if image != post["image"] or group != post["group"]:
            raise SystemExit(f"  ! species/image mismatch for {item['id']}: {image} vs {post['image']}")
        if not (IMAGES / image).exists():
            raise SystemExit(f"  ! missing species image: static/images/{image}")

        block = item.get("affiliate") or {}
        try:
            kit = resolve_kit(post, block)
        except KeyError as exc:
            raise SystemExit(f"  ! {item['id']}: {exc} — add it to affiliate.PRODUCTS") from exc

        post = dict(post)
        post.update({
            "id": item["id"],
            "keyword": item["target_keyword"],
            "_item": item,
            "_kit": kit,
            "primary": kit[0] if kit else None,
        })
        posts.append(post)

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


def audit_content(posts: list[dict]) -> list[str]:
    """Prove that every article is its own article.

    Catches the two failure modes that make a library read as one page repeated:
    two posts sharing a title, and two posts sharing a body (a stale cache file
    or a template that rendered the wrong record). It also re-reads each written
    page and checks that its <h1> and prose belong to that post, so a mismatch
    between the data and the output cannot ship silently.
    """
    problems: list[str] = []
    seen_titles: dict[str, str] = {}
    seen_bodies: dict[str, str] = {}

    for p in posts:
        key = p["title"].strip().lower()
        if key in seen_titles:
            problems.append(f"{p['id']} reuses the title of {seen_titles[key]}")
        seen_titles[key] = p["id"]

        text = re.sub(r"\s+", " ", strip_tags(p["_body"])).strip()
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
        if digest in seen_bodies:
            problems.append(f"{p['id']} shares its body with {seen_bodies[digest]}")
        seen_bodies[digest] = p["id"]

        page = ROOT / f"{p['id']}.html"
        if not page.exists():
            problems.append(f"{p['id']}.html was not written")
            continue
        doc = page.read_text(encoding="utf-8")

        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S)
        if not h1 or html.unescape(strip_tags(h1.group(1))) != p["title"]:
            problems.append(f"{p['id']}.html <h1> does not match its title")

        h2 = re.search(r"<h2[^>]*>(.*?)</h2>", p["_body"], re.S)
        prose = re.search(r'<div class="prose">(.*?)</div>\s*<section class="gear"', doc, re.S)
        if h2 and prose:
            needle = html.unescape(strip_tags(h2.group(1))).strip()
            if needle and needle not in html.unescape(prose.group(1)):
                problems.append(f"{p['id']}.html prose is not this article's body")

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


def build(refresh: bool = False, batch: int = 0) -> None:
    posts = collect()
    tax = taxonomy(posts)
    CACHE.mkdir(exist_ok=True)

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

    for post in posts:
        force = refresh and (not batch or post["id"] in forced)
        body, source = resolve_body(post["_item"], post, force)
        post["_body"] = aff.inject_cards(sanitize_body(body, post), post)
        post["_read"] = read_time(post["_body"])
        print(f"  {post['id']}  {post['species']:<22} body: {source}")

    for post in posts:
        related = [p for p in posts if p["id"] != post["id"]]
        related.sort(key=lambda p: (p["group"] != post["group"], p["date"] < post["date"]))
        (ROOT / f"{post['id']}.html").write_text(
            render_article(post, post["_body"], related[:3], tax), encoding="utf-8"
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
    print(f"  affiliate: {sum(len(p['_kit']) for p in posts)} products, {cards} in-article cards")
    print("  wrote sitemap.xml, robots.txt, feed.xml")
    print(f"  base url: {SITE_URL}")

    problems = audit(posts, tax) + audit_content(posts) + audit_collections(posts, tax)
    if problems:
        for p in problems:
            print(f"  ✗ {p}")
        raise SystemExit(f"audit failed: {len(problems)} problem(s)")
    print(f"  link audit: clean ({len(tax['cats']) + len(tax['groups'])} sections, "
          f"{len(posts)} cards, {len(posts)} unique bodies)")


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
    parser.add_argument("--serve", action="store_true", help="serve the site on :8000 after building")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    build(refresh=args.refresh, batch=args.batch)
    if args.serve:
        try:
            serve(args.port)
        except KeyboardInterrupt:
            sys.exit(0)
