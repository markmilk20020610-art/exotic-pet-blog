# -*- coding: utf-8 -*-
"""Prepare the vivarium widget's photographic layers.

1. Backdrop: crop the baked-in corner watermark, re-encode as WebP.
2. Spider: key out the white studio background with a border flood fill
   (so interior white leg bands survive), erode one pixel to kill the
   white fringe, un-premultiply the edge colours, then trim to content.
"""
import os
from collections import deque

from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(HERE, "static", "images")
SRC = os.path.join(HERE, "tools", "source")

BACKDROP_SRC = os.path.join(SRC, "Extreme_macro_photograph_taken_2026-10-29T12-45-07.png")
SPIDER_SRC = os.path.join(SRC, "Studio_macro_photograph_of_an__2026-10-29T12-46-21.png")


def backdrop():
    im = Image.open(BACKDROP_SRC).convert("RGB")
    w, h = im.size                       # 1024 x 1536
    # the generator stamps "AI生成" into the bottom-right corner; the widget
    # is 4:5, so cropping to 1024x1280 removes it and loses only dark foreground
    im = im.crop((0, 0, w, int(w * 1.25)))
    im = im.resize((880, 1100), Image.LANCZOS)
    out = os.path.join(IMG, "vivarium-scene.webp")
    im.save(out, "WEBP", quality=82, method=6)
    print("backdrop", out, im.size, os.path.getsize(out) // 1024, "KB")


def key_spider():
    im = Image.open(SPIDER_SRC).convert("RGB")
    w, h = im.size
    px = im.load()

    def is_bg(c):
        r, g, b = c
        return min(r, g, b) >= 232 and (max(c) - min(c)) <= 20

    # flood fill from every border pixel: the studio backdrop is one connected
    # white field, while the white bands inside the legs are enclosed by dark
    # chitin and therefore never reached
    bg = bytearray(w * h)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_bg(px[x, y]) and not bg[y * w + x]:
                bg[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_bg(px[x, y]) and not bg[y * w + x]:
                bg[y * w + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not bg[ny * w + nx] and is_bg(px[nx, ny]):
                bg[ny * w + nx] = 1
                q.append((nx, ny))

    # opaque mask, then bite one pixel off every edge so the anti-aliased
    # white halo is removed rather than merely made transparent
    mask = Image.new("L", (w, h), 255)
    mp = mask.load()
    for y in range(h):
        row = y * w
        for x in range(w):
            if bg[row + x]:
                mp[x, y] = 0
    mask = mask.filter(ImageFilter.MinFilter(3))
    mask = mask.filter(ImageFilter.GaussianBlur(0.6))

    # un-premultiply: edge pixels were blended against white, so
    # c' = (c - (1 - a) * 255) / a removes the pale rim
    out = Image.new("RGBA", (w, h))
    op, ap, np_ = out.load(), mask.load(), px
    for y in range(h):
        for x in range(w):
            a = ap[x, y]
            if a == 0:
                continue
            r, g, b = np_[x, y]
            if a < 250:
                f = a / 255.0
                r = max(0, min(255, int((r - (1 - f) * 255) / f)))
                g = max(0, min(255, int((g - (1 - f) * 255) / f)))
                b = max(0, min(255, int((b - (1 - f) * 255) / f)))
            op[x, y] = (r, g, b, a)

    bbox = mask.getbbox()
    pad = 6
    bbox = (max(0, bbox[0] - pad), max(0, bbox[1] - pad),
            min(w, bbox[2] + pad), min(h, bbox[3] + pad))
    out = out.crop(bbox)
    print("spider trimmed to", out.size)

    # keep the natural crop: the top edge of the element then sits at the top
    # of the animal, which is where the silk thread attaches
    for name, target in (("vivarium-spider.webp", 560), ("vivarium-spider@2x.webp", 1120)):
        scale = target / float(out.width)
        im2 = out.resize((target, max(1, int(round(out.height * scale)))), Image.LANCZOS)
        p = os.path.join(IMG, name)
        im2.save(p, "WEBP", quality=88, method=6)
        print("spider", p, im2.size, os.path.getsize(p) // 1024, "KB")

    # QA: composite over a mid-dark field so a white matte fringe is obvious
    qa = Image.new("RGB", out.size, (34, 46, 36))
    qa.paste(out, (0, 0), out)
    qa.save(os.path.join(IMG, "_qa-cutout.png"))


if __name__ == "__main__":
    backdrop()
    key_spider()
