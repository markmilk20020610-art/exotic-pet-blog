# -*- coding: utf-8 -*-
"""
vivarium.py — the interactive vivarium widget for the homepage hero.

Markup only. The backdrop is a macro photograph (one WebP, served as a CSS
background so there is no layout shift and no extra DOM); the resident is a
matte-cut WebP pendant. Both are produced by tools/build_vivarium_assets.py.

The resident is rendered server-side, so with JavaScript disabled the enclosure
still shows a spider hanging from its web. The script only takes over the
physics — it never creates the animal.
"""

import math

VIVARIUM_ASSETS = (
    '<link rel="stylesheet" href="static/vivarium.css">\n'
    '<script defer src="static/vivarium.js"></script>\n'
)


def _web_svg() -> str:
    """A sector of orb web anchored to the top-right corner of its box.

    Built rather than hand-drawn: radial spokes with true concentric rings
    between them. Hand-placed arcs read as scratches on glass because the
    spacing between them never stays constant.
    """
    ox, oy = 122.0, 10.0                       # the retreat, top-right
    angles = [92, 106, 121, 137, 152, 167, 178]
    lengths = [70, 86, 92, 86, 74, 58, 40]

    def pt(deg, r):
        a = math.radians(deg)
        return ox + math.cos(a) * r, oy + math.sin(a) * r

    parts = []
    for deg, ln in zip(angles, lengths):
        x, y = pt(deg, ln)
        parts.append('<path d="M%.1f %.1f L%.1f %.1f" stroke-width="%.2f" opacity="%.2f"/>'
                     % (ox, oy, x, y, 0.75 + ln / 260.0, 0.26 + ln / 520.0))

    for r in (15, 25, 36, 48, 61, 74):
        for i in range(len(angles) - 1):
            if lengths[i] < r + 3 or lengths[i + 1] < r + 3:
                continue
            x1, y1 = pt(angles[i], r)
            x2, y2 = pt(angles[i + 1], r)
            xm, ym = pt((angles[i] + angles[i + 1]) / 2.0, r * 1.045)
            # the rings sit in a 132-unit box that renders ~100 px wide, so a
            # sub-unit stroke disappears; 1.2 is the thinnest that survives
            parts.append('<path d="M%.1f %.1f Q%.1f %.1f %.1f %.1f" stroke-width="1.2" opacity="%.2f"/>'
                         % (x1, y1, xm, ym, x2, y2, 0.50 - r / 1000.0))

    # the retreat itself: a short tangle, plus the knot the dragline leaves from
    tangle = (
        '<path d="M122 10 L112 16 L120 22 L110 26" stroke-width=".9" opacity=".5"/>'
        '<path d="M122 10 L115 8 L118 18" stroke-width=".8" opacity=".42"/>'
    )

    return (
        '<svg class="viv__web" viewBox="0 0 132 132" aria-hidden="true" focusable="false">'
        '<g fill="none" stroke="currentColor" stroke-linecap="round">'
        + ''.join(parts) + tangle +
        '</g>'
        '<circle cx="122" cy="10" r="1.9" fill="#f2f8ee" opacity=".85"/>'
        '</svg>'
    )


WEB = _web_svg()


def vivarium_html() -> str:
    return f"""
<div class="viv" data-vivarium>
  <div class="viv__frame" tabindex="0" role="group"
       aria-label="Interactive vivarium. Lucas the regal jumping spider waits in a web nest in the corner. Click anywhere in the enclosure to drop a fruit fly and watch him hunt.">
    <div class="viv__scene" aria-hidden="true">
      <span class="viv__lamp"></span>
      <span class="viv__glass"></span>
      <span class="viv__vignette"></span>
      <span class="viv__beads"></span>
    </div>

    {WEB}

    <svg class="viv__silk" aria-hidden="true" focusable="false">
      <path class="viv__silk-glow" d="M346 58 Q 315 105 285 152"/>
      <path class="viv__silk-line" d="M346 58 Q 315 105 285 152"/>
    </svg>

    <div class="viv__pet" data-species="spider">
      <div class="viv__pet-gait">
        <div class="viv__pet-sway">
          <img class="viv__pet-img" src="static/images/vivarium-spider.webp"
               width="560" height="363" alt="" draggable="false" decoding="async">
        </div>
      </div>
    </div>

    <div class="viv__hud" aria-hidden="true">
      <div class="viv__hud-tag"><span>Enclosure 04</span><span class="viv__live">Live</span></div>
      <div class="viv__hud-row"><span>Temp</span><b data-temp>26.0<i>°C</i></b></div>
      <div class="viv__hud-row"><span>Humidity</span><b data-hum>68<i>%</i></b></div>
      <div class="viv__hud-bar"><i data-hum-bar style="width:68%"></i></div>
      <div class="viv__hud-status"><i></i><span>Bioactive · stable</span></div>
    </div>

    <button class="viv__feed" type="button" aria-label="Drop a feeder insect into the enclosure">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
           stroke-linecap="round" aria-hidden="true">
        <ellipse cx="12" cy="14" rx="5.5" ry="4.2"/>
        <circle cx="12" cy="8.6" r="2.8"/>
        <path d="M9.4 7.2 C7 4.6 6 3 5.2 2.2 M14.6 7.2 C17 4.6 18 3 18.8 2.2"/>
      </svg>
      <span>Feed</span>
    </button>

    <div class="viv__bubble" aria-live="polite"></div>
    <div class="viv__hint">Click the glass to hunt</div>

    <div class="viv__info">
      <div class="viv__kicker"><span>Resident</span><i></i><span>Enclosure 04</span></div>
      <div class="viv__name">Lucas</div>
      <div class="viv__meta">
        <span class="viv__latin">Phidippus regius</span>
        <span class="viv__traits">Bold · curious · never still</span>
      </div>
      <p class="viv__line">“I have been watching you since the page loaded.”</p>
    </div>
  </div>
</div>
"""
