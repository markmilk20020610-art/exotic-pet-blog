# Exotic Pet Care Hub

An English-language exotic-pet magazine, generated as a static site by a single
Python script. Editorial layout (Inter + Instrument Serif), full-bleed hero,
card grid, long-form article template with a designed Amazon affiliate block.

```
keywords.json      topic + target keyword + affiliate override per article
content.py         editorial metadata, species facts, kit lists, fallback HTML body
affiliate.py       product catalogue, card markup, placement, disclosure, QA
generate.py        templates, SEO head, JSON-LD, sitemap.xml, robots.txt, feed.xml
vivarium.py        the hero widget's markup + the generated orb web
static/style.css   the entire design system (one file, no build step)
static/vivarium.css  the widget's own styles, scoped to .viv
static/vivarium.js   resident roster + the click-to-hunt sequence
tools/build_vivarium_assets.py  source photos → the widget's WebP layers
static/images/     species photographs + credits.json
cache/             generated bodies, committed so the site is reproducible
```

## Build

```bash
pip install -r requirements.txt      # only needed for DeepSeek generation
python generate.py                   # build from cache/ (or fallback content)
python generate.py --refresh         # force DeepSeek regeneration
python generate.py --refresh --batch 4   # regenerate the 4 stalest guides only
python generate.py --serve           # build, then serve on http://127.0.0.1:8000
```

Output is written to the repository root (`index.html`, `pet-00N.html`,
`sitemap.xml`, `robots.txt`, `feed.xml`) so GitHub Pages keeps serving the same
URLs it always has.

Environment variables:

| Variable           | Default                    | Purpose                       |
| ------------------ | -------------------------- | ----------------------------- |
| `DEEPSEEK_API_KEY` | —                          | enables AI body generation    |
| `SITE_URL`         | `https://exoticpethub.com` | canonical / OG / sitemap host |
| `AMAZON_TAG`       | `exoticpethub-20`          | affiliate tag on Amazon links |

## Content pipeline

For each entry in `keywords.json`, the body is resolved in this order:

1. `cache/<id>.html` — previously generated, committed
2. DeepSeek API — only with a key and `--refresh`
3. `content.py` → `body_html` — deterministic fallback

Whichever source wins is passed through `sanitize_body()`: `<h1>` is stripped,
inline styles and stray scripts are removed, any `<img>` the model invented is
dropped, hand-rolled Amazon anchors are unwrapped to plain text, other outbound
links are hardened with `rel="noopener noreferrer"`, and heading ids are
generated for the table of contents. The model is never allowed to write
commerce markup — the template owns that.

The GitHub Action runs **every two days** with `--refresh --batch 4`, so four
guides are rewritten per run rather than the whole library, then commits the
regenerated pages and cache.

### The editorial contract

`PROMPT` is a brief, not a request. Every body — generated or hand-written —
has to clear `check_structure()`, which is the machine-readable half of the
same document:

| Beat | What the checker looks for |
| ---- | -------------------------- |
| ① Science hook | the opening `<p>` carries a number with a unit, and a Latin binomial appears in `<em>` at first mention |
| ② Keeper's diary | one `<h2>` section with ≥3 first-person markers and ≥60 words |
| ③ Care guide | 4–7 `<h2>` sections, plus a step sequence, an option list or a summary table |
| ④ Quiet recommendation | affiliate tokens only, never hand-written commerce markup |
| — | a "Frequently asked questions" `<h2>` with three `<h3>` |

`BANNED_VOICE` catches the assistant register: "as an AI", "in today's
fast-paced world", "delve into", "in conclusion" and friends. A body that
contains any of them cannot ship.

Two gates run the same check:

- **At generation time.** `resolve_body()` scores the draft; if it falls short,
  the problems are sent back as one targeted rewrite turn. A draft that still
  fails is **rejected** — the previous body is kept rather than publishing a
  generic care sheet under this article's title.
- **At build time.** `audit_voice()` scores whatever actually got rendered,
  fallback included, and fails the build. `content.py` is not exempt: it is
  what ships when the API is down.

`PROMPT_VERSION` is part of the cache fingerprint, so editing the brief
invalidates every cached body instead of leaving old-contract articles in place.

## The hero vivarium widget

The homepage hero carries a small interactive enclosure. It is deliberately
built to cost the rest of the site nothing:

- `static/vivarium.css` and `static/vivarium.js` are injected **only on the
  homepage** via `head(..., assets=VIVARIUM_ASSETS)`. Every article page contains
  zero widget bytes — `grep -c vivarium pet-00*.html` is 0 for all six guides —
  and neither the SEO tags nor the sitemap build path touch it.
- The enclosure is one photograph rather than an illustration: a 880×1100 WebP
  scene painted as a CSS `background-image` on `.viv__scene`, so there is no
  layout shift and no extra DOM node per texture.
- The resident is a server-rendered `<img>` cut-out, so the widget is coherent
  with JavaScript disabled.
- On the wire: 10 KB gzipped for the CSS + JS pair, 130 KB for the scene, 64 KB
  for the animal. All four residents share one photograph, so the daily rotation
  costs nothing.

### Artwork: photographs, not vector illustration

`tools/build_vivarium_assets.py` turns the two sources in `tools/source/`
(gitignored) into the shipped WebP layers:

| output | source | step |
| ------ | ------ | ---- |
| `vivarium-scene.webp` | 1024×1536 backdrop | crop the generator watermark off the bottom, resize to 880×1100 (exactly the widget's 4:5), q82 |
| `vivarium-spider.webp` | square cut-out on white | border flood-fill key, erode 3 px, un-premultiply, trim with 6 px pad |

The key is a **border flood fill**, not a colour threshold: only white that is
connected to the edge is removed, so the pale bands on the spider's legs
survive. `MinFilter(3)` then eats the fringe the key leaves behind, and alpha is
un-premultiplied (`c' = (c − (1−a)·255) / a`) so the edges do not go grey over
dark moss. A `_qa-cutout.png` composite over `(34,46,36)` is written for fringe
inspection.

The readout panel is glassmorphism, not a translucent box: a 155° white-to-black
gradient at 8–26 % alpha, `backdrop-filter: blur(16px) saturate(170%)`, an inset
top highlight and a specular sheen across its upper 42 %.

### The dragline

The silk is a quadratic Bézier from the web's retreat to the animal's
spinnerets, redrawn every frame:

- the bow is `−v⊥ · 7` — velocity **perpendicular** to the thread bows it,
  velocity along it does not — plus a slow sine wobble, clamped to ±34 px;
- it attaches at `pos.y − petH·0.46`, the top of the abdomen, so the animal hangs
  from it rather than being pierced by it;
- hovering the animal brightens and thickens both strokes (`.viv.is-hover`), so
  the thread reads as live silk instead of a drawn line.

The orb web behind it is generated, not drawn. `_web_svg()` in `vivarium.py`
places radial spokes at fixed angles, then walks true concentric rings between
adjacent spokes and skips any ring that would overshoot a spoke's length.
Hand-placed arcs read as scratches on glass, because the spacing between them
never stays constant. Ring strokes are 1.2 units in a 132-unit box that renders
~100 px wide; anything thinner vanishes into antialiasing.

The web is anchored by percentage, and `--nest-x` / `--nest-y` on `.viv__frame`
must land exactly on the SVG's retreat at (122, 10) of that box. If you resize
the web to a width of `k` (as a share of the frame), solve
`left = 0.805 − 0.924·k` and `top = 0.108 − 0.0606·k` — otherwise the thread
visibly leaves from empty glass beside the hub.

### Kinematics — click to hunt

The widget no longer follows the pointer. It is a small state machine
(`idle → spot → lunge → wrap → haul → idle`) driven by clicks, so the enclosure
stays still until someone touches it.

The animal is one flat cut-out, so movement is built in three composed layers.
Each owns exactly one thing:

1. **Position** — `.viv__pet` gets a `translate3d` from the script. During the
   lunge and the haul the position is sampled from a quadratic Bézier, not
   lerped toward a point.
2. **Gait** — `.viv__pet-gait` runs the `vivGait` keyframes (0.58 s, two steps
   per cycle) and the script only writes `--gait` (0 → 1, from measured speed).
   The keyframes scale themselves off that variable: `--bob` 3 px, `--roll`
   ±2.4°, `--shove` 1.3 px. The pivot is `transform-origin: 50% 0%` — the
   spinnerets — so the body swings on the thread like the pendulum it is and the
   silk stays attached at the top.
3. **Idle sway** — `.viv__pet-sway` keeps the slow ±1.5° breathing plus a 2.4 px
   rise; the silk breathes with an opacity pulse (`vivSilkBreath`, only while
   `.viv.is-idle`), so both endpoints stay welded to the web hub and the
   spinnerets.

Writing a *variable* rather than the animation duration matters: changing
`animation-duration` restarts the cycle and snaps the phase, which at full
amplitude is a visible 5° jolt. Scaling amplitude through a var lets the gait
follow the speed every frame without ever restarting.

**The sequence.**

- **A — prey.** A click spawns a 27 px fly at the click point, clamped into
  `ROAM` and pushed at least 78 px from the spider so the strike is always
  visible. It pops in (`scale(0) → 1`), flutters its wings at 90 ms and jitters
  on a 160 ms `steps(2)` cycle. A soft warm halo keeps the dark body legible on
  the moss.
- **B — lunge.** A 220 ms beat of attention, then a quadratic from the resting
  spot to the fly whose control point bows off the chord and lifts by
  `0.42 · d`. Progress is eased with `easeOutBack` (one ~12 % overshoot, no
  oscillation), so the animal arrives with momentum and settles exactly on the
  prey. Duration is `clamp(d · 0.26, 16, 40)` frames — ~270–660 ms.
- **C — wrap.** On arrival: a light flash, three dashed silk rings spun in
  sequence, six flecks thrown outward, and the bubble "Caught a snack! 🪰". The
  bubble flips below the catch when it is high in the frame, so it never covers
  the readout panel.
- **D — haul.** The spider retracts along the thread with `smoothstep`
  (ease-in-out) over `clamp(d · 0.5, 26, 64)` frames, the parcel trailing at
  `pos.y + petH · 0.24`. At the nest the fly and the burst are removed, the
  bubble is dismissed, and the animal parks back into idle.

The wrap burst is z-index 4, above the animal, so the rings read even though the
spider is sitting on the prey.

| Input | Response |
| ----- | -------- |
| click anywhere in the enclosure | spawn a fly there and run the full hunt |
| click while a hunt is running | ignored — one hunt at a time |
| `Feed` button / <kbd>Enter</kbd> / <kbd>Space</kbd> | the same hunt, at a random spot in `ROAM` |
| hover the animal | the dragline brightens and thickens; it no longer lures the animal |
| touch device | a tap is the click |

`ROAM` clamps the prey — 17–83 % across, 19–58 % down — so a hunt never ends
under the caption scrim.

`prefers-reduced-motion: reduce` keeps the hunt (it is user-triggered feedback)
but strips the decoration: no fly flutter, no wrap rings, no flash, no idle
breathing, and shorter waits. The position arc still runs.

### Residents

`ROSTER` in `static/vivarium.js` holds four *Phidippus* individuals — Lucas,
Mira, Otis and Wren — each with a latin name, three traits and one line of
dialogue. The pick is `ROSTER[Math.floor(Date.now() / 86400000) % 4]`, so the
enclosure changes resident at UTC midnight. The server always renders Lucas, so
the markup is correct before the script runs. Append
`?pet=lucas|mira|otis|wren` to force one while developing.

The roster rotates individuals rather than species on purpose: the silk physics
only makes sense for a spider, and a crested gecko hanging from a dragline would
be a lie.

### Visual QA without a browser session

Two headless-Chrome traps, both of which cost real time to find:

- `requestAnimationFrame` **never fires** under `--virtual-time-budget`, so the
  physics look dead in a DOM dump. Shim it to `setTimeout(cb, 16)` in the probe
  page, never in production.
- Chrome SIGTERMs on a non-ASCII `file://` URL. Copy the site to `%TEMP%` and
  screenshot from there; the repo path is `D:\异宠博客`.


## Images: bound to species, not to category

`SPECIES_IMAGE` in `generate.py` maps each article id to exactly one
photograph. The build fails loudly if the file is missing or if the species in
`content.py` disagrees with the mapping, so a jumping-spider guide cannot end up
illustrated with a dog.

All six photographs are CC-licensed (CC0 / CC BY / CC BY-SA) from Wikimedia
Commons. Attribution is stored in `static/images/credits.json` and rendered
under every figure.

## Adding an article

1. Add an entry to `keywords.json` (`id`, `topic`, `target_keyword`, `category`,
   plus the `affiliate` block described below).
2. Add the matching metadata block to `POSTS` in `content.py` (`title`, `dek`,
   `species`, `sci`, `image`, `alt`, `caption`, `facts`, `kit`, `body_html`).
   `kit` is a list of `(product_id, why, heading_hint)` triples.
3. Add the image to `static/images/` plus a `credits.json` record, and register
   it in `SPECIES_IMAGE`.
4. `python generate.py`.

The nav, the filtered index pages (`guides.html`, `category-*.html`,
`species*.html`) and their sitemap rows are all derived from the new post's
`category` / `group`, so there is nothing else to edit by hand.

## Navigation and filtered indexes

The primary nav is generated from the posts, never hand-written. Each label is a
real page:

| Label | URL | Lists |
| ----- | --- | ----- |
| Field Guides | `guides.html` | every guide, pinned first, then newest |
| Feeding / Habitat / Health | `category-<slug>.html` | that editorial category |
| By species | `species.html` | every group, in sections |
| — | `species-<group>.html` | one species class |

`nav_items(tax)` is the single source of truth; `collection_pages(posts, tax)`
writes one page per entry. The nav, footer, article breadcrumb and the category
chip on each article all point at these URLs, so a click always lands on a page
that shows exactly that slice.

Why pages and not `#anchors`: the old nav linked Feeding, Habitat, Health and
By species at four columns of the same `#browse` grid. Those columns sit on one
row, so every link scrolled to the same place and the nav looked dead. The
filtered pages also work without JavaScript and are indexed individually.

`audit_collections()` re-reads each page and asserts that its card ids equal the
expected set — a category page that lists a stray article fails the build.

## Magazine layer

Article bodies come out of the model as plain semantic HTML. Everything visual
is added afterwards, in `generate.py`, in this order:

```
resolve_body() → sanitize_body() → magazine_body() → aff.inject_cards() → .prose
```

`magazine_body()` = `add_lede(highlight_params(body))`:

- **`highlight_params()`** wraps temperatures, percentages, dimensions
  (`20×20×30 cm`) and bare sizes in `<span class="badge">`. It splits the string
  on tags and walks the text nodes only, so a match can never land inside an
  attribute, a heading id or a link. `BADGE_SKIP` keeps the walk out of `a`,
  `code`, `pre`, tables and headings — a badge inside a link breaks the
  affordance, and table cells already read as data.
- **`add_lede()`** promotes the first bare `<p>` to `<p class="lede">`, which
  CSS renders as a larger italic serif opener. The drop cap stays on
  `p:first-of-type` and is rescaled for the lede's size.

The order matters: badges are applied **before** the affiliate cards are
injected, so the regex can never badge-ify a price or a dimension inside
`.amz-card` markup.

## Pinned guides

`is_pinned` lives on each post — in `content.py` as the editorial default and in
`keywords.json` as the operator switch (the JSON value wins, so pinning does not
need a code change). `rank_posts()` floats pinned guides to the top in two
stable passes, which keeps the date order intact inside both groups.

Where they land:

| Page | Pinned treatment |
| ---- | ---------------- |
| `index.html` | the lead story becomes the hero; any further pinned guides fill a "Start here" band under it |
| `guides.html`, `category-*.html`, `species-*.html` | a full-width banner card with a red **Pinned** ribbon, above the chronological grid |
| `species.html` | ranked inside each group |

`audit_pinned()` reads the written pages back and compares the document order of
`pet-00N.html` links against `rank_posts()`, so a template that quietly drops the
ranking fails the build instead of shipping a homepage whose lead story drifts.

## Content integrity

Two articles must never share a title or a body. `audit_content()` hashes the
sanitised prose of every post and fails the build on a collision; it also
re-reads each written page and checks that the `<h1>`, the canonical URL and the
prose all belong to that post, so a data/template mix-up cannot ship silently.

The prose check compares **normalised text to normalised text**: `prose_region()`
finds the `.prose` block by counting `<div>` nesting, `prose_text()` strips tags,
resolves entities and folds whitespace, and the two strings must be equal. An
earlier version searched for the stripped text of the first `<h2>` inside the
*raw HTML* of the prose block — so any inline markup in a heading (`<em>`,
`<strong>`, a link) or an entity like `&nbsp;` made the needle impossible to find
and failed the build on a correct page. That was the `pet-003` false positive.
Exact comparison also catches a swapped or truncated body, which the old
"does this phrase appear anywhere" test could not.

`build()` keeps bodies in a `bodies[id]` map and renders each page from
`bodies[post["id"]]`, never from a loop variable — a page cannot be handed
another record's body. `collect()` refuses duplicate ids, so the map is
one-to-one by construction.

`resolve_body()` writes a `cache/<id>.json` sidecar with a fingerprint of the
prompt inputs (id, keyword, topic, species). A cache file is only reused when
its fingerprint matches, and a body under 400 characters is treated as a miss —
so a stale or copied cache file can never become another article's content.

## Affiliate system

Everything money-related lives in `affiliate.py`; `generate.py` only calls into
it. That split exists so a new product, category or placement rule never
requires touching the page template.

### The catalogue

`PRODUCTS` is a 20-entry dict keyed by a stable id (`spider-enclosure`,
`bioactive-substrate`, `uvb-fixture`, `critical-care`, …). Each record carries
`title`, `brand`, `price`, `rating`, `category`, `badge`, `blurb`, `query`, and
optionally `url` / `image`. `resolve()` merges a catalogue entry with per-article
overrides and defaults the URL to an Amazon search built from `query` +
`AMAZON_TAG`.

Three merchandising buckets drive both the colour system and the placement
logic — `CATEGORIES` holds their label, tint, icon and keyword set:

| id        | label              | tint      | maps to                        |
| --------- | ------------------ | --------- | ------------------------------ |
| `feeding` | Feeding            | `#b4622c` | food, prey cultures, tongs     |
| `habitat` | Habitat & Decor    | `#3f6b4a` | enclosure, substrate, heat, UVB |
| `health`  | Disease & Health   | `#7a3f52` | quarantine, mites, shedding    |

A new category is one entry in `CATEGORIES` plus a `[data-cat]` colour rule;
nothing else in the pipeline needs to know about it.

### The per-article override

`keywords.json` carries a dedicated block so an editor can promote a specific
product for a specific article without editing Python:

```json
"affiliate": {
  "affiliate_product_id": "spider-enclosure",
  "affiliate_title": "Jumping Spider Enclosure Starter Kit",
  "affiliate_url": "https://www.amazon.com/s?k=...&tag=exoticpethub-20",
  "affiliate_image": "",
  "affiliate_price": "$28–42",
  "affiliate_category": "habitat"
}
```

The override applies only when `affiliate_product_id` matches the id the article
actually references in `content.py`. `affiliate_image` may stay empty — the card
then renders a designed gradient tile with a category line-art silhouette rather
than hot-linking an unverified photo.

### Placement: three tiers of certainty

The prompt tells DeepSeek to drop a token (`{{affiliate:feeding}}`) at the moment
the reader first meets the problem a product solves. `inject_cards()` then
resolves placement with decreasing certainty:

1. **Explicit token** — `{{affiliate:<cat>}}` or `<!-- AFFILIATE:<cat> -->` in
   the body. Used verbatim, in the section it sits in.
2. **Editor hint** — the third element of a `kit` tuple names a heading
   substring (`"two mistakes"`). The card lands in that `<section>`.
3. **Heuristic** — score every `<h2>` section on category keywords plus
   `0.8 ×` title-word hits, after dropping title words that appear in more than
   a third of the headings (a word in every heading carries no signal). Reusing
   a category takes a 0.9 penalty.

Cards are capped at `MAX_INLINE_CARDS` (2) and dropped after the section's
second `</p>`, so the first two paragraphs always introduce the problem before
the pitch appears. The build prints which heading each card landed under:

```
== pet-005
   What UVB actually does for this species  | UVB + Heat Lamp Fixture Combo
   Belly heat is still the main event       | Heat Mat with Dimming Thermostat
```

### What a card contains

`.amz-card` is a 148 px + flexible grid: a full-height image tile with an
optional badge, a category kicker (`Feeding — Expert recommended`), the title,
a one-line selling point, a five-star row with fractional fill and a "Keeper
verdict" score, the typical price, and the gradient CTA
`Check best price on Amazon →`. The rail repeats a `--compact` variant, and the
kit list at the end of each article renders the same products as three rows.

The panel itself is frosted rather than filled: a translucent tint over the
paper, `backdrop-filter: blur(18px) saturate(1.08)`, and an inset white
top-highlight. On light paper a purely translucent panel reads as a printing
mistake, so the inset highlight is what defines the edge; the 3 px category
colour bar on the left is what makes three stacked cards readable as three
different recommendations.

Star counts and review volumes are **not** fabricated — the card shows the
editorial score unless a real `rating` is supplied in the catalogue.

### Compliance

- Every outbound Amazon anchor is written with
  `rel="nofollow noopener sponsored noreferrer"` and `target="_blank"`, from a
  single constant (`affiliate.REL`) that no template can bypass.
- The disclosure *"As an Amazon Associate, we earn from qualifying purchases."*
  appears under every inline card, inside the compact rail card, and again as a
  standalone block above the kit list.
- `aff.validate()` runs at build time and warns on a missing kit, a relative
  URL, a missing affiliate tag, a rating outside 0–5, or one URL reused by two
  different products. It does not fail the build — a broken affiliate link
  should be fixed, not take the site down.

A full build reports `affiliate: 20 products, N in-article cards`; the current
library ships 12 inline cards across 6 guides and 38 compliant Amazon anchors.

## SEO

Every page ships a canonical URL, Open Graph and Twitter card tags, and JSON-LD.
Home carries `WebSite` + `ItemList`; articles carry `Article`,
`BreadcrumbList` and `FAQPage` (parsed from the FAQ section). `sitemap.xml` is
regenerated on every build with per-page `lastmod`.
