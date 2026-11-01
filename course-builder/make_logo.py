# -*- coding: utf-8 -*-
"""يبني نسخ الشعار المستخدمة في العروض والأوراق من الملف الرسمي المرفق.

المصدر: fonts/logo_source.png (شعار بخلفية شفافة) مع بديل fonts/logo_source.jpg.
لا يُعاد رسم الشعار أو تقليده، بل يُقتص ويُستخدم كصورة كما هو.
    python make_logo.py
"""
import os

from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
PNG_SRC = os.path.join(FONTS, "logo_source.png")
JPG_SRC = os.path.join(FONTS, "logo_source.jpg")


def _load():
    """Return the artwork with a transparent background, trimmed to its ink."""
    if os.path.exists(PNG_SRC):
        img = Image.open(PNG_SRC).convert("RGBA")
        img = img.crop(img.split()[3].getbbox())
        return img
    import numpy as np
    src = Image.open(JPG_SRC).convert("RGB")
    a = np.asarray(src).astype(np.int16)
    dist = 255 - a.min(axis=2)
    alpha = np.clip((dist - 8) * 12, 0, 255).astype(np.uint8)
    img = Image.fromarray(np.dstack([a.astype(np.uint8), alpha]), "RGBA")
    return img.crop(img.split()[3].getbbox())


def build():
    img = _load()
    img.save(os.path.join(FONTS, "logo_t.png"))

    w, h = img.size
    # emblem only: the top 56% of the lock-up (above the wordmark)
    mark = img.crop((0, 0, w, int(h * 0.56)))
    mark = mark.crop(mark.split()[3].getbbox())
    mark.save(os.path.join(FONTS, "logo_mark_t.png"))

    # modest upscale with a light unsharp mask, so the small logo stays crisp
    # in the PDF export without inventing detail
    for name, k in (("logo_t.png", 2), ("logo_mark_t.png", 3)):
        im = Image.open(os.path.join(FONTS, name)).convert("RGBA")
        up = im.resize((im.size[0] * k, im.size[1] * k), Image.LANCZOS)
        r, g, b, a2 = up.split()
        rgb = Image.merge("RGB", (r, g, b)).filter(
            ImageFilter.UnsharpMask(radius=1.6, percent=90, threshold=2))
        r2, g2, b2 = rgb.split()
        Image.merge("RGBA", (r2, g2, b2, a2)).save(
            os.path.join(FONTS, name.replace(".png", "@%dx.png" % k)))
    print("logo assets rebuilt")


def palette():
    """Median red / green of the artwork, for the deck palette."""
    from collections import Counter
    img = _load()
    a = list(img.getdata())
    strong = [p for p in a if p[3] > 200 and max(p[:3]) - min(p[:3]) > 40]
    red = [p[:3] for p in strong if p[0] > p[1] and p[0] > p[2]]
    grn = [p[:3] for p in strong if p[1] > p[0] and p[1] > p[2]]
    def mode(lst):
        return "#%02X%02X%02X" % Counter(lst).most_common(1)[0][0]
    return mode(red), mode(grn)


if __name__ == "__main__":
    build()
    r, g = palette()
    print("palette:", r, g)
