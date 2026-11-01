# -*- coding: utf-8 -*-
"""Fast, font-accurate text measurement (HarfBuzz) used for layout decisions.

MuPDF renders the text; this module predicts how much room it needs. Both use
the same TTF files and the same shaping engine, so the prediction is reliable.
"""
from __future__ import annotations

import os
import re

import uharfbuzz as hb

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
_CACHE = {}


def _face(path):
    if path not in _CACHE:
        blob = hb.Blob.from_file_path(path)
        face = hb.Face(blob)
        font = hb.Font(face)
        _CACHE[path] = (face, font, face.upem)
    return _CACHE[path]


REG = os.path.join(FONT_DIR, "NotoSansArabic-Regular.ttf")
BOLD = os.path.join(FONT_DIR, "NotoSansArabic-Bold.ttf")

_TAG = re.compile(r"<[^>]+>")


def width(text, size, bold=False):
    """Advance width of one unbroken line, in points."""
    if not text:
        return 0.0
    face, font, upem = _face(BOLD if bold else REG)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True, "liga": True})
    total = sum(p.x_advance for p in buf.glyph_positions)
    return total * size / upem


def lines(text, w, size, bold=False):
    """How many rendered lines `text` occupies inside width `w`."""
    plain = _TAG.sub("", text)
    total = 0
    for para in re.split(r"<br\s*/?>|\n", plain):
        words = para.split(" ")
        cur = 0.0
        n = 1
        space = width(" ", size, bold)
        for word in words:
            ww = width(word, size, bold)
            add = ww + (space if cur > 0 else 0)
            if cur + add <= w or cur == 0:
                cur += add
            else:
                n += 1
                cur = ww
                # a word longer than the line still counts as one line
        total += n
    return max(1, total)


def height(text, w, size, line=1.5, bold=False):
    """Rendered height in points for the given width, size and line spacing."""
    n = lines(text, w, size, bold)
    return n * size * line + 3.0
