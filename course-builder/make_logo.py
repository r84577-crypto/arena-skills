# -*- coding: utf-8 -*-
"""يبني نسخ الشعار المستخدمة في العروض والأوراق من الملف الرسمي المرفق.

المصدر: fonts/logo_source.jpg (800×200) — يُقتص منه الشعار وتُزال خلفيته البيضاء
ليظهر على الألواح الخضراء. لا يُعاد رسم الشعار أو تقليده، بل يُستخدم كصورة كما هو.
    python make_logo.py
"""
import os

from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
SRC = os.path.join(FONTS, "logo_source.jpg")


def build():
    import numpy as np
    src = Image.open(SRC).convert("RGB")
    a = np.asarray(src).astype(np.int16)
    # near-white -> transparent (tolerates JPEG artefacts around the artwork)
    dist = 255 - a.min(axis=2)
    alpha = np.clip((dist - 8) * 12, 0, 255).astype(np.uint8)
    img = Image.fromarray(np.dstack([a.astype(np.uint8), alpha]), "RGBA")
    img = img.crop(img.split()[3].getbbox())
    img.save(os.path.join(FONTS, "logo_t.png"))

    w, h = img.size
    mark = img.crop((0, 0, w, int(h * 0.56)))
    mark = mark.crop(mark.split()[3].getbbox())
    mark.save(os.path.join(FONTS, "logo_mark_t.png"))

    # 3x / 4x upscale with a light unsharp mask: the supplied file is only 800px
    # wide, and the deck is 960pt wide, so PDF export would otherwise look soft.
    for name, k in (("logo_t.png", 3), ("logo_mark_t.png", 4)):
        im = Image.open(os.path.join(FONTS, name)).convert("RGBA")
        up = im.resize((im.size[0] * k, im.size[1] * k), Image.LANCZOS)
        r, g, b, a2 = up.split()
        rgb = Image.merge("RGB", (r, g, b)).filter(
            ImageFilter.UnsharpMask(radius=2.2, percent=110, threshold=2))
        r2, g2, b2 = rgb.split()
        Image.merge("RGBA", (r2, g2, b2, a2)).save(
            os.path.join(FONTS, name.replace(".png", "@%dx.png" % k)))
    print("logo assets rebuilt")


if __name__ == "__main__":
    build()
