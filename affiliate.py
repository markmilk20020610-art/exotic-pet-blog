# -*- coding: utf-8 -*-
"""
affiliate.py — the affiliate layer for Exotic Pet Care Hub.

Everything money-related lives here so that `generate.py` stays a layout file:

    CATEGORIES   the three merchandising buckets, with the copy each one uses
    PRODUCTS     the product catalogue, keyed by a stable id
    product_card()   the "Expert recommended" card rendered inside the prose
    inject_cards()   places cards where the article actually needs them
    validate()       build-time guard rails

Design rules
------------
* **One catalogue, many articles.** A product is defined once and referenced by
  id from `content.py`. Adding a product is a one-line change; adding a whole
  category is one dict entry.
* **Links are never trusted from the model.** Every outbound anchor is built
  here with the affiliate tag and `rel="nofollow noopener sponsored noreferrer"`.
* **No invented ratings.** `rating` is the site's own keeper verdict, labelled
  as such. Amazon star counts are only rendered when `amazon_rating` is
  supplied — we never fabricate review volume.
* **Images degrade gracefully.** `affiliate_image` may point at a local file or
  a remote URL. When it is empty or missing, a designed category tile is drawn
  inline instead of shipping a broken <img>.
"""

from __future__ import annotations

import html
import os
import re
from urllib.parse import quote_plus

AMAZON_TAG = os.environ.get("AMAZON_TAG", "exoticpethub-20")

# Google's guidance for affiliate outbound links. Order is irrelevant to
# crawlers; this string is used verbatim on every money link on the site.
REL = "nofollow noopener sponsored noreferrer"

DISCLOSURE = "As an Amazon Associate, we earn from qualifying purchases."

# Cards inserted into the body of a single article. Two is the point where a
# guide still reads like a guide; three starts to read like a storefront.
MAX_INLINE_CARDS = 2


# --------------------------------------------------------------------------- #
# categories
# --------------------------------------------------------------------------- #

CATEGORIES: dict[str, dict] = {
    "feeding": {
        "label": "Feeding",
        "kicker": "Food & feeding kit",
        "tint": "#b4622c",
        "icon": "insect",
        "blurb": "What we actually feed, and the tools that keep portions honest.",
        "keywords": (
            "feed", "feeding", "eat", "diet", "food", "prey", "feeder",
            "nutrition", "supplement", "gut-load", "calcium", "portion",
        ),
    },
    "habitat": {
        "label": "Habitat & Decor",
        "kicker": "Enclosure & decor",
        "tint": "#3f6b4a",
        "icon": "terrarium",
        "blurb": "Substrate, structure and sensors — the parts that decide whether a setup works.",
        "keywords": (
            "enclosure", "setup", "substrate", "tank", "terrarium", "decor",
            "humidity", "ventilation", "lighting", "light", "uvb", "heat",
            "hide", "climb", "drainage", "moss", "bioactive", "gradient",
        ),
    },
    "health": {
        "label": "Disease & Health",
        "kicker": "Health & recovery",
        "tint": "#7a3f52",
        "icon": "shield",
        "blurb": "Quarantine, hydration and the first-aid shelf we hope you never need.",
        "keywords": (
            "health", "disease", "illness", "sick", "mite", "mites", "mould",
            "mold", "moult", "shed", "impaction", "dehydration", "infection",
            "quarantine", "vet", "refus", "stress", "injury", "parasite",
        ),
    },
}

CATEGORY_ORDER = ("feeding", "habitat", "health")


def category(slug: str) -> dict:
    return CATEGORIES.get(slug, CATEGORIES["habitat"])


# --------------------------------------------------------------------------- #
# catalogue
# --------------------------------------------------------------------------- #

PRODUCTS: dict[str, dict] = {
    # ---- habitat ---------------------------------------------------------- #
    "spider-enclosure": {
        "title": "Jumping Spider Enclosure Starter Kit",
        "brand": "Arboreal cube",
        "price": "$28–42",
        "rating": 4.5,
        "category": "habitat",
        "shape": "terrarium",
        "badge": "Editor’s pick",
        "blurb": "Ventilated 10 × 10 × 12 cm cube with cork bark and a feeding ledge — the whole starting point in one box.",
        "query": "jumping spider enclosure starter kit arboreal",
    },
    "bioactive-substrate": {
        "title": "Reptile Bioactive Substrate Mix",
        "brand": "Coir · bark · sand",
        "price": "$18–28",
        "rating": 4.6,
        "category": "habitat",
        "shape": "bag",
        "badge": "Keeper tested",
        "blurb": "Pre-mixed coir, orchid bark and sand that holds structure when damp instead of turning to sludge.",
        "query": "reptile bioactive substrate soil mix",
    },
    "leca-drainage": {
        "title": "LECA Clay Pebbles for Drainage",
        "brand": "2 qt",
        "price": "$12–20",
        "rating": 4.4,
        "category": "habitat",
        "shape": "bag",
        "badge": "",
        "blurb": "The false bottom that keeps the substrate wicking instead of sitting in water.",
        "query": "leca clay pebbles drainage substrate",
    },
    "springtail-culture": {
        "title": "Temperate Springtail Culture",
        "brand": "Live culture",
        "price": "$12–20",
        "rating": 4.7,
        "category": "habitat",
        "shape": "insect",
        "badge": "Bioactive staple",
        "blurb": "The cleanup crew that eats mould and frass before either becomes a problem.",
        "query": "springtail culture temperate live",
    },
    "hygrometer": {
        "title": "Digital Hygrometer & Thermometer, 2-pack",
        "brand": "Two probes",
        "price": "$16–28",
        "rating": 4.5,
        "category": "habitat",
        "shape": "device",
        "badge": "Buy two",
        "blurb": "One sensor at each end of the enclosure. A single probe hides exactly the gradient that causes problems.",
        "query": "digital hygrometer thermometer terrarium 2 pack",
    },
    "mesh-vents": {
        "title": "25 mm Mesh Vent Discs, 20-pack",
        "brand": "Stainless mesh",
        "price": "$8–14",
        "rating": 4.3,
        "category": "habitat",
        "shape": "device",
        "badge": "",
        "blurb": "The cheapest way to fix a stuffy culture: add cross-ventilation before you change anything else.",
        "query": "terrarium mesh vent disc 25mm",
    },
    "ir-thermometer": {
        "title": "Infrared Thermometer Gun",
        "brand": "Surface temp",
        "price": "$18–30",
        "rating": 4.6,
        "category": "habitat",
        "shape": "device",
        "badge": "Underrated",
        "blurb": "Reads the basking surface itself, not the air two inches above it. This is the number that matters.",
        "query": "infrared thermometer gun reptile",
    },
    "snug-hides": {
        "title": "Snug Hide Cave, Medium (pair)",
        "brand": "Two identical",
        "price": "$14–24",
        "rating": 4.5,
        "category": "habitat",
        "shape": "terrarium",
        "badge": "",
        "blurb": "Two hides, one warm and one cool. A snake that can choose its temperature is a snake that eats.",
        "query": "reptile hide cave medium snug",
    },
    "uvb-fixture": {
        "title": "UVB + Heat Lamp Fixture Combo",
        "brand": "Dome + tube",
        "price": "$45–75",
        "rating": 4.6,
        "category": "habitat",
        "shape": "lamp",
        "badge": "Editor’s pick",
        "blurb": "A dimmable dome for heat and a low-output UVB tube in one fitting — the combination leopard geckos actually use.",
        "query": "reptile uvb heat lamp fixture combo",
    },
    "heat-mat": {
        "title": "Heat Mat with Dimming Thermostat",
        "brand": "Under-tank",
        "price": "$45–75",
        "rating": 4.7,
        "category": "habitat",
        "shape": "device",
        "badge": "Non-negotiable",
        "blurb": "A heat mat without a thermostat is a burn risk. Buy them as one item, never separately.",
        "query": "reptile heat mat dimming thermostat",
    },
    "salt-set": {
        "title": "Instant Ocean Sea Salt + Hydrometer Set",
        "brand": "Marine mix",
        "price": "$22–34",
        "rating": 4.5,
        "category": "habitat",
        "shape": "bucket",
        "badge": "",
        "blurb": "Hermit crabs need real salt water, not table salt. The hydrometer is what makes the mix repeatable.",
        "query": "instant ocean sea salt hydrometer set",
    },
    "coco-fibre": {
        "title": "Coco Fibre Substrate Block",
        "brand": "Compressed",
        "price": "$8–15",
        "rating": 4.4,
        "category": "habitat",
        "shape": "bag",
        "badge": "",
        "blurb": "Holds humidity without souring, and one block expands to fill a 60 cm tank twice over.",
        "query": "coco fibre substrate block reptile",
    },

    # ---- feeding ---------------------------------------------------------- #
    "hydei-culture": {
        "title": "Hydei Fruit Fly Culture (live)",
        "brand": "Live culture",
        "price": "$12–18",
        "rating": 4.6,
        "category": "feeding",
        "shape": "insect",
        "badge": "Best staple",
        "blurb": "The correct prey size for adult jumpers, and a culture keeps producing for weeks.",
        "query": "hydei fruit fly culture live",
    },
    "feeding-tongs": {
        "title": "Long Stainless Feeding Tongs, 30 cm",
        "brand": "30 cm",
        "price": "$10–16",
        "rating": 4.7,
        "category": "feeding",
        "shape": "tongs",
        "badge": "",
        "blurb": "Hand-feeding is the best part of keeping a regal. Tongs keep your fingers out of the strike zone.",
        "query": "long feeding tongs reptile 30cm",
    },
    "kitchen-scale": {
        "title": "Digital Kitchen Scale, 0.1 g",
        "brand": "0.1 g resolution",
        "price": "$18–30",
        "rating": 4.6,
        "category": "feeding",
        "shape": "device",
        "badge": "Track the weight",
        "blurb": "Weigh the snake, not the rat. A 10 % drop over two months is data; a refusal on its own is not.",
        "query": "digital kitchen scale 0.1g reptile",
    },
    "calcium-d3": {
        "title": "Rep-Cal Calcium with D3",
        "brand": "Ultrafine",
        "price": "$11–17",
        "rating": 4.7,
        "category": "feeding",
        "shape": "bottle",
        "badge": "Dust every feed",
        "blurb": "The default supplement for anything eating insects. Dust the prey, not the enclosure.",
        "query": "rep cal calcium with d3 ultrafine",
    },
    "repashy-cgd": {
        "title": "Repashy Crested Gecko Diet",
        "brand": "Complete MRP",
        "price": "$16–24",
        "rating": 4.8,
        "category": "feeding",
        "shape": "bottle",
        "badge": "Complete diet",
        "blurb": "A complete meal replacement, so a gecko that ignores insects still gets a balanced diet.",
        "query": "repashy crested gecko diet",
    },
    "waxworms": {
        "title": "Live Waxworms, 25 ct",
        "brand": "Treat only",
        "price": "$10–16",
        "rating": 4.2,
        "category": "feeding",
        "shape": "insect",
        "badge": "Treat",
        "blurb": "The spider equivalent of cake. Useful for a shy feeder, dangerous as a staple.",
        "query": "live waxworms cup 25",
    },

    # ---- health ----------------------------------------------------------- #
    "critical-care": {
        "title": "Vetark Critical Care Formula",
        "brand": "Convalescence",
        "price": "$19–29",
        "rating": 4.6,
        "category": "health",
        "shape": "bottle",
        "badge": "Vet shelf",
        "blurb": "A syringe-feedable recovery formula for a reptile that has stopped eating for husbandry reasons.",
        "query": "vetark critical care formula reptile",
    },
    "mite-treatment": {
        "title": "Provent-a-Mite",
        "brand": "Quarantine",
        "price": "$16–24",
        "rating": 4.4,
        "category": "health",
        "shape": "bottle",
        "badge": "Quarantine kit",
        "blurb": "For the mites that arrive on new cork bark. Treat the enclosure, never the animal.",
        "query": "provent a mite reptile",
    },
    "shed-aid": {
        "title": "Repti Shedding Aid",
        "brand": "Spray",
        "price": "$8–13",
        "rating": 4.1,
        "category": "health",
        "shape": "bottle",
        "badge": "",
        "blurb": "For stuck shed on toes and tail tips, where a bad shed turns into a lost digit.",
        "query": "zoo med repti shedding aid",
    },
    "electrolyte": {
        "title": "Reptile Electrolyte Soak",
        "brand": "Hydration",
        "price": "$12–18",
        "rating": 4.3,
        "category": "health",
        "shape": "bottle",
        "badge": "",
        "blurb": "A 20-minute soak for a dehydrated animal, before you reach for anything stronger.",
        "query": "reptile electrolyte soak hydration",
    },
}


# --------------------------------------------------------------------------- #
# placeholder artwork
# --------------------------------------------------------------------------- #

# Line-art silhouettes for the card media slot. They are deliberately generic:
# they describe the *kind* of product, and are replaced by a real photograph the
# moment `affiliate_image` is filled in.
SHAPES: dict[str, str] = {
    "terrarium": (
        '<rect x="24" y="26" width="52" height="50" rx="3"/>'
        '<path d="M24 40h52M30 76v8M70 76v8"/>'
        '<path d="M38 66c0-11 5-17 12-17s12 6 12 17"/>'
    ),
    "insect": (
        '<ellipse cx="50" cy="58" rx="14" ry="20"/>'
        '<circle cx="50" cy="32" r="8"/>'
        '<path d="M36 50 23 42M36 58 21 58M36 66 23 74"/>'
        '<path d="M64 50 77 42M64 58 79 58M64 66 77 74"/>'
        '<path d="M50 24 45 16M50 24 55 16"/>'
    ),
    "bottle": (
        '<rect x="33" y="36" width="34" height="44" rx="6"/>'
        '<rect x="39" y="23" width="22" height="13" rx="3"/>'
        '<path d="M33 52h34M40 64h14"/>'
    ),
    "device": (
        '<circle cx="50" cy="52" r="25"/>'
        '<path d="M50 52V34M42 74h16"/>'
        '<path d="M50 27v5"/>'
    ),
    "lamp": (
        '<path d="M30 34h40l7 15H23z"/>'
        '<path d="M50 49v21M36 70h28"/>'
    ),
    "tongs": (
        '<path d="M41 20 46 78M59 20 54 78"/>'
        '<path d="M41 20c4-6 14-6 18 0"/>'
        '<path d="M44 44h12"/>'
    ),
    "bag": (
        '<path d="M32 34h36l4 44H28z"/>'
        '<path d="M39 34V25h22v9"/>'
        '<path d="M40 52h20"/>'
    ),
    "bucket": (
        '<path d="M28 38h44l-5 40H33z"/>'
        '<ellipse cx="50" cy="38" rx="22" ry="7"/>'
        '<path d="M42 30h16"/>'
    ),
    "shield": (
        '<path d="M50 22 74 31v22c0 14-11 22-24 27-13-5-24-13-24-27V31z"/>'
        '<path d="M50 40v14M43 47h14"/>'
    ),
}


def _shade(colour: str, amount: float) -> str:
    """Lighten (amount > 0) or darken (amount < 0) a #rrggbb colour."""
    c = colour.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    if amount >= 0:
        r, g, b = (round(v + (255 - v) * amount) for v in (r, g, b))
    else:
        r, g, b = (round(v * (1 + amount)) for v in (r, g, b))
    return "#%02x%02x%02x" % (r, g, b)


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def amazon_search(query: str) -> str:
    return f"https://www.amazon.com/s?k={quote_plus(query)}&tag={AMAZON_TAG}"


def stars(rating: float) -> str:
    """Five-star row with a fractional fill, no invented review counts."""
    pct = max(0.0, min(1.0, rating / 5.0)) * 100
    return (
        '<span class="amz-card__stars" aria-hidden="true">'
        f'<i style="width:{pct:.0f}%">★★★★★</i>★★★★★</span>'
    )


# --------------------------------------------------------------------------- #
# resolution
# --------------------------------------------------------------------------- #

def resolve(pid: str, *, why: str = "", **overrides) -> dict:
    """Return a fully populated product record.

    `overrides` lets an article pin its own title, url, image or price without
    touching the shared catalogue — that is how a per-article `affiliate` block
    in keywords.json stays authoritative.
    """
    base = PRODUCTS.get(pid)
    if base is None:
        raise KeyError(f"unknown product id: {pid}")
    p = dict(base)
    p["id"] = pid
    p["why"] = why or base.get("blurb", "")
    for key, value in overrides.items():
        if value:
            p[key] = value
    p.setdefault("url", "")
    if not p["url"]:
        p["url"] = amazon_search(p.get("query") or p["title"])
    p.setdefault("image", "")
    p.setdefault("badge", "")
    p["cat"] = p.get("category", "habitat")
    return p


def tile(product: dict) -> str:
    """Media slot: a real photograph when one exists, otherwise a drawn tile."""
    image = product.get("image") or ""
    if image:
        return (
            f'<img class="amz-card__img" src="{esc(image)}" alt="{esc(product["title"])}" '
            'loading="lazy" decoding="async">'
        )
    tint = category(product["cat"])["tint"]
    shape = SHAPES.get(product.get("shape") or category(product["cat"])["icon"], SHAPES["terrarium"])
    return (
        f'<span class="amz-card__tile" style="--ta:{_shade(tint, 0.26)};--tb:{_shade(tint, -0.34)}">'
        '<svg viewBox="0 0 100 100" aria-hidden="true" fill="none" stroke="currentColor" '
        'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">'
        f"{shape}</svg></span>"
    )


# --------------------------------------------------------------------------- #
# markup
# --------------------------------------------------------------------------- #

def product_card(product: dict, *, compact: bool = False) -> str:
    """The in-article 'expert recommended' card."""
    cat = category(product["cat"])
    badge = (
        f'<span class="amz-card__badge">{esc(product["badge"])}</span>'
        if product.get("badge") else ""
    )
    cls = "amz-card amz-card--compact" if compact else "amz-card"
    rating = float(product.get("rating") or 0)
    rating_html = ""
    if rating:
        amazon = ""
        if product.get("amazon_rating"):
            amazon = (
                f'<span class="amz-card__amazon">{float(product["amazon_rating"]):.1f} on Amazon</span>'
            )
        rating_html = (
            '<div class="amz-card__rating">'
            f'{stars(rating)}'
            f'<b>{rating:.1f}</b>'
            '<span class="amz-card__rlabel">Keeper verdict</span>'
            f'{amazon}'
            "</div>"
        )

    return f"""
<aside class="{cls}" data-cat="{product['cat']}" aria-label="Recommended product: {esc(product['title'])}">
  <div class="amz-card__media">
    {tile(product)}
    {badge}
  </div>
  <div class="amz-card__body">
    <div class="amz-card__kicker"><span>{esc(cat['label'])}</span><i></i><span>Expert recommended</span></div>
    <h3 class="amz-card__title">{esc(product['title'])}</h3>
    <p class="amz-card__blurb">{esc(product['why'])}</p>
    {rating_html}
    <div class="amz-card__foot">
      <div class="amz-card__price"><span>Typical price</span><b>{esc(product.get('price', '—'))}</b></div>
      <a class="amz-card__cta" href="{esc(product['url'])}" target="_blank" rel="{REL}">
        Check best price on Amazon
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M5 12h13M12 6l6 6-6 6"/>
        </svg>
      </a>
    </div>
    <p class="amz-card__fine">{DISCLOSURE}</p>
  </div>
</aside>
"""


def disclosure(note: str = "") -> str:
    """The standalone disclosure block that sits at the end of every guide."""
    extra = f" {esc(note)}" if note else ""
    return f"""
<div class="amz-disclosure">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
       stroke-linecap="round" aria-hidden="true">
    <circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>
  </svg>
  <p><strong>Affiliate disclosure.</strong> {DISCLOSURE} Every card in this guide is an
  affiliate link — it costs you nothing, and we only list gear we have run in our own
  enclosures.{extra}</p>
</div>
"""


# --------------------------------------------------------------------------- #
# placement
# --------------------------------------------------------------------------- #

TOKEN_RE = re.compile(r"\{\{\s*affiliate:([a-z-]+)\s*\}\}|<!--\s*AFFILIATE:([a-z-]+)\s*-->", re.I)


def _sections(body: str) -> list[tuple[int, int, str]]:
    """(start, end, heading text) for every <h2> block."""
    heads = list(re.finditer(r"<h2[^>]*>(.*?)</h2>", body, flags=re.S))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        out.append((m.start(), end, re.sub(r"<[^>]+>", "", m.group(1)).strip()))
    return out


def _best_section(body: str, slug: str, taken: set[int]) -> int | None:
    """Index of the section whose heading best matches this category."""
    keywords = category(slug)["keywords"]
    best, best_score = None, 0
    for i, (_, _, heading) in enumerate(_sections(body)):
        if i in taken:
            continue
        low = heading.lower()
        score = sum(1 for k in keywords if k in low)
        if score > best_score:
            best, best_score = i, score
    return best


def _section_scores(body: str, product: dict) -> list[tuple[float, int]]:
    """Rank every section for one product.

    Category keywords alone are too coarse — a substrate mix and a drainage
    layer are both "habitat", so the card lands in whichever section happens to
    come first. Adding the product's own title words fixes most of that, but a
    word like "spider" appears in every heading of a spider article and carries
    no signal, so it is dropped by document frequency.
    """
    keywords = category(product["cat"])["keywords"]
    sections = _sections(body)
    if not sections:
        return []

    headings = [h.lower() for _, _, h in sections]
    words = [w for w in re.findall(r"[a-z]{4,}", product["title"].lower())]
    limit = max(1, len(headings) // 3)
    words = [w for w in words if sum(1 for h in headings if w in h) <= limit]

    scored = []
    for i, low in enumerate(headings):
        score = float(sum(1 for k in keywords if k in low))
        score += 0.8 * sum(1 for w in words if w in low)
        scored.append((score, i))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return scored


def _section_by_hint(body: str, hint: str) -> int | None:
    """Section index for an editor-supplied heading hint."""
    needle = hint.lower()
    for i, (_, _, heading) in enumerate(_sections(body)):
        if needle in heading.lower():
            return i
    return None


def _insert_in_section(body: str, index: int, card: str) -> str:
    """Drop a card after the second paragraph of a section (or its last)."""
    sections = _sections(body)
    if index >= len(sections):
        return body + card
    start, end, _ = sections[index]
    segment = body[start:end]
    breaks = [m.end() for m in re.finditer(r"</p>", segment)]
    at = breaks[1] if len(breaks) > 1 else (breaks[0] if breaks else len(segment))
    segment = segment[:at] + card + segment[at:]
    return body[:start] + segment + body[end:]


def _tidy(body: str) -> str:
    """Remove the empty <p> left behind when a token stood on its own line."""
    body = re.sub(r"<p>\s*(?:<br\s*/?>)?\s*</p>", "", body)
    return re.sub(r"\n{3,}", "\n\n", body)


def _first_in_category(slug: str) -> dict | None:
    """A catalogue product for a category the article's own kit does not cover."""
    for pid, raw in PRODUCTS.items():
        if raw.get("category") == slug:
            return resolve(pid)
    return None


def inject_cards(body: str, post: dict) -> str:
    """Place affiliate cards, in descending order of certainty.

    1. `{{affiliate:cat}}` tokens — the writer said exactly where it goes.
    2. `place` hints on the kit entry — an editor pinned the heading.
    3. Heuristic ranking — last resort for bodies we did not author.

    Returns the body with at most MAX_INLINE_CARDS cards inserted.
    """
    kit: list[dict] = post.get("_kit") or []
    if not kit:
        return body

    by_cat: dict[str, dict] = {}
    for p in kit:
        by_cat.setdefault(p["cat"], p)

    placed: set[str] = set()
    used_sections: set[int] = set()
    used_cats: set[str] = set()

    # 1. explicit tokens
    def swap(m: re.Match) -> str:
        slug = (m.group(1) or m.group(2)).lower()
        if slug in used_cats or len(placed) >= MAX_INLINE_CARDS:
            return ""
        product = by_cat.get(slug) or _first_in_category(slug)
        if not product:
            return ""
        placed.add(product["id"])
        used_cats.add(slug)
        return "\n" + product_card(product) + "\n"

    body = TOKEN_RE.sub(swap, body)

    # 2. editor-pinned headings, spread through the article in reading order
    pinned: list[tuple[int, dict]] = []
    for p in kit:
        if p["id"] in placed or not p.get("place"):
            continue
        idx = _section_by_hint(body, p["place"])
        if idx is not None and idx not in used_sections:
            pinned.append((idx, p))
    pinned.sort(key=lambda t: t[0])

    for idx, p in pinned:
        if len(placed) >= MAX_INLINE_CARDS:
            break
        if idx in used_sections or p["id"] in placed:
            continue
        body = _insert_in_section(body, idx, product_card(p))
        used_sections.add(idx)
        placed.add(p["id"])
        used_cats.add(p["cat"])

    # 3. heuristic: rank (product, section) pairs, prefer category variety
    candidates: list[tuple[float, int, dict]] = []
    for p in kit:
        if p["id"] in placed:
            continue
        for score, idx in _section_scores(body, p):
            if idx in used_sections or score <= 0:
                continue
            penalty = 0.9 if p["cat"] in used_cats else 0.0
            candidates.append((score - penalty, idx, p))

    candidates.sort(key=lambda t: (-t[0], t[1]))

    for score, idx, p in candidates:
        if len(placed) >= MAX_INLINE_CARDS:
            break
        if idx in used_sections or p["id"] in placed:
            continue
        body = _insert_in_section(body, idx, product_card(p))
        used_sections.add(idx)
        placed.add(p["id"])
        used_cats.add(p["cat"])

    return _tidy(body)


# --------------------------------------------------------------------------- #
# build-time checks
# --------------------------------------------------------------------------- #

def validate(posts: list[dict]) -> list[str]:
    """Return human-readable warnings; the build prints them and carries on."""
    from pathlib import Path

    root = Path(__file__).resolve().parent
    warnings: list[str] = []
    seen_urls: dict[str, tuple[str, str]] = {}

    for post in posts:
        pid = post["id"]
        kit = post.get("_kit") or []
        if not kit:
            warnings.append(f"{pid}: no kit products — the guide will render without a kit list")
        for p in kit:
            if not p["url"].startswith("http"):
                warnings.append(f"{pid}: {p['id']} has a non-absolute affiliate_url")
            if AMAZON_TAG not in p["url"]:
                warnings.append(f"{pid}: {p['id']} URL is missing the affiliate tag {AMAZON_TAG}")
            # The same product legitimately appears in several guides; only a
            # URL collision between *different* products is a real mistake.
            if p["url"] in seen_urls and seen_urls[p["url"]][0] != p["id"]:
                warnings.append(
                    f"{pid}: {p['id']} reuses the URL of {seen_urls[p['url']][0]}"
                )
            seen_urls[p["url"]] = (p["id"], pid)
            image = p.get("image") or ""
            if image and not image.startswith(("http://", "https://")):
                if not (root / image).exists():
                    warnings.append(f"{pid}: affiliate_image not found ({image}) — using the drawn tile")
            if p.get("rating") and not (0 < float(p["rating"]) <= 5):
                warnings.append(f"{pid}: {p['id']} rating {p['rating']} is outside 0–5")

    return warnings
