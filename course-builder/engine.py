# -*- coding: utf-8 -*-
"""
Rendering engine for the Al-Fao Institute weekly training decks.

One content specification is drawn twice, in the same pass:
  * a native, fully editable .pptx (python-pptx, RTL-aware)
  * a pixel-matched .pdf (PyMuPDF, real Arabic shaping through HarfBuzz)

Both backends are driven by the same geometry and the same font files, so the
PDF doubles as a layout proof for the PPTX.
"""
from __future__ import annotations

import os
import re
import html as _html

import pymupdf
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn, nsdecls
from lxml import etree

import metrics as _m

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
LOGO = os.path.join(FONT_DIR, "logo_t@3x.png")
LOGO_MARK = os.path.join(FONT_DIR, "logo_mark_t@3x.png")
_IMG_SIZE_CACHE = {}


def _img_size(path):
    """Intrinsic pixel size of an image file (cached)."""
    if path not in _IMG_SIZE_CACHE:
        from PIL import Image
        with Image.open(path) as im:
            _IMG_SIZE_CACHE[path] = im.size
    return _IMG_SIZE_CACHE[path]

# ---------------------------------------------------------------- geometry
SLIDE_W, SLIDE_H = 960.0, 540.0
M = 46.0
CONTENT_W = SLIDE_W - 2 * M

# ---------------------------------------------------------------- palette
RED = "A12C33"
RED_D = "7C1B24"
RED_T = "FBEAEC"
GREEN = "117B48"
GREEN_D = "0C5B35"
GREEN_T = "E9F3EC"
INK = "182420"
GRAY = "55645E"
GRAY_L = "8A9791"
LINE = "DCE3DF"
PANEL = "F5F7F6"
PANEL2 = "EDF1EF"
WHITE = "FFFFFF"
AMBER_T = "FCF3E2"
AMBER = "8A5F0E"

FONT = "Noto Sans Arabic"

_CSS_BASE = (
    "@font-face{font-family:ara;src:url(NotoSansArabic-Regular.ttf);font-weight:normal;}"
    "@font-face{font-family:ara;src:url(NotoSansArabic-Bold.ttf);font-weight:bold;}"
    "@font-face{font-family:lat;src:url(DejaVuSans.ttf);font-weight:normal;}"
    "@font-face{font-family:lat;src:url(DejaVuSans-Bold.ttf);font-weight:bold;}"
    "*{font-family:ara,lat;margin:0;padding:0;}"
    ".ltr{direction:ltr;unicode-bidi:isolate;}"
    ".mono{font-family:lat;font-weight:normal;}"
)


def _rgb(h) -> RGBColor:
    return RGBColor.from_string(h.upper().lstrip("#"))


def _rgb_f(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)


LRI, PDI = "\u2066", "\u2069"


def L(text):
    """Wrap a Latin/path run so Arabic text cannot reorder it (isolate)."""
    return LRI + text + PDI


_TAG = re.compile(r"(<b>|</b>|<i>|</i>|<u>|</u>|<br\s*/?>|</?span[^>]*>|</?strong>|</?em>)")


def parse_runs(s):
    out, cur = [], {"b": False, "i": False, "u": False, "color": None}
    for tok in _TAG.split(s):
        if not tok:
            continue
        low = tok.lower()
        if low.startswith("<br"):
            out.append(("\n", dict(cur)))
        elif low in ("<b>", "<strong>"):
            cur["b"] = True
        elif low in ("</b>", "</strong>"):
            cur["b"] = False
        elif low in ("<i>", "<em>"):
            cur["i"] = True
        elif low in ("</i>", "</em>"):
            cur["i"] = False
        elif low == "<u>":
            cur["u"] = True
        elif low == "</u>":
            cur["u"] = False
        elif low.startswith("<span"):
            m = re.search(r"color\s*:\s*#?([0-9A-Fa-f]{6})", tok)
            if m:
                cur["color"] = m.group(1)
        elif low == "</span>":
            cur["color"] = None
        else:
            out.append((_html.unescape(tok), dict(cur)))
    merged = []
    for t, st in out:
        if merged and merged[-1][1] == st:
            merged[-1] = (merged[-1][0] + t, st)
        else:
            merged.append((t, st))
    return merged


class Canvas:
    def __init__(self, prs_slide, pdf_page, archive, scratch):
        self.s = prs_slide
        self.p = pdf_page
        self.arch = archive
        self.scratch = scratch
        self.warn = []

    # ------------------------------------------------------------ measuring
    def width(self, text, size=12, bold=False):
        """Advance width of one line of text, in points."""
        return _m.width(re.sub(r"<[^>]+>", "", text), size, bold=bold)

    def measure(self, content, w, size=18, line=1.5, direction="rtl", bold=False):
        """Predicted height in pt that `content` needs inside width w."""
        return _m.height(content, w, size, line=line, bold=bold)

    # ------------------------------------------------------------ primitives
    def rect(self, x, y, w, h, fill=None, stroke=None, radius=0, width=1.0,
             dash=None):
        self.p.draw_rect(pymupdf.Rect(x, y, x + w, y + h),
                         color=(_rgb_f(stroke) if stroke else None),
                         fill=(_rgb_f(fill) if fill else None),
                         width=width,
                         radius=(min(0.5, radius / min(w, h)) if radius else None),
                         dashes="[3 2] 0" if dash else None, overlay=True)
        kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
        sh = self.s.shapes.add_shape(kind, Emu(int(x * 12700)), Emu(int(y * 12700)),
                                     Emu(int(w * 12700)), Emu(int(h * 12700)))
        if radius:
            try:
                sh.adjustments[0] = min(0.5, radius / min(w, h))
            except Exception:
                pass
        if fill:
            sh.fill.solid()
            sh.fill.fore_color.rgb = _rgb(fill)
        else:
            sh.fill.background()
        if stroke:
            sh.line.color.rgb = _rgb(stroke)
            sh.line.width = Pt(width)
            if dash:
                from pptx.enum.dml import MSO_LINE_DASH_STYLE
                sh.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        else:
            sh.line.fill.background()
        sh.shadow.inherit = False
        spPr = sh._element.spPr
        if spPr.find(qn("a:effectLst")) is None:
            spPr.append(etree.fromstring("<a:effectLst %s/>" % nsdecls("a")))
        sh.text_frame.word_wrap = True
        return sh

    def circle(self, cx, cy, r, fill=None, stroke=None, width=1.0):
        self.p.draw_circle(pymupdf.Point(cx, cy), r,
                           color=(_rgb_f(stroke) if stroke else None),
                           fill=(_rgb_f(fill) if fill else None), width=width)
        sh = self.s.shapes.add_shape(MSO_SHAPE.OVAL, Emu(int((cx - r) * 12700)),
                                     Emu(int((cy - r) * 12700)), Emu(int(2 * r * 12700)),
                                     Emu(int(2 * r * 12700)))
        if fill:
            sh.fill.solid()
            sh.fill.fore_color.rgb = _rgb(fill)
        else:
            sh.fill.background()
        if stroke:
            sh.line.color.rgb = _rgb(stroke)
            sh.line.width = Pt(width)
        else:
            sh.line.fill.background()
        sh.shadow.inherit = False
        return sh

    def line(self, x1, y1, x2, y2, color=LINE, width=1.0, dash=False):
        self.p.draw_line(pymupdf.Point(x1, y1), pymupdf.Point(x2, y2),
                         color=_rgb_f(color), width=width,
                         dashes="[3 2] 0" if dash else None)
        conn = self.s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                           Emu(int(x1 * 12700)), Emu(int(y1 * 12700)),
                                           Emu(int(x2 * 12700)), Emu(int(y2 * 12700)))
        conn.line.color.rgb = _rgb(color)
        conn.line.width = Pt(width)
        if dash:
            from pptx.enum.dml import MSO_LINE_DASH_STYLE
            conn.line.dash_style = MSO_LINE_DASH_STYLE.DASH

    def arrow(self, x1, y1, x2, y2, color=GRAY_L, width=1.4):
        self.p.draw_line(pymupdf.Point(x1, y1), pymupdf.Point(x2, y2),
                         color=_rgb_f(color), width=width)
        self.p.draw_line(pymupdf.Point(x2, y2),
                         pymupdf.Point(x2 + (4 if x2 > x1 else -4), y2), color=_rgb_f(color))
        conn = self.s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                           Emu(int(x1 * 12700)), Emu(int(y1 * 12700)),
                                           Emu(int(x2 * 12700)), Emu(int(y2 * 12700)))
        conn.line.color.rgb = _rgb(color)
        conn.line.width = Pt(width)
        ln = conn.line._get_or_add_ln()
        tail = etree.SubElement(ln, qn("a:tailEnd"))
        tail.set("type", "triangle")
        tail.set("w", "med")
        tail.set("len", "med")

    def image(self, x, y, w, h, path):
        """Draw an image, keeping its aspect ratio inside the given box."""
        src = _img_size(path)
        k = min(w / src[0], h / src[1])
        w, h = src[0] * k, src[1] * k
        self.p.insert_image(pymupdf.Rect(x, y, x + w, y + h), filename=path)
        self.s.shapes.add_picture(path, Emu(int(x * 12700)), Emu(int(y * 12700)),
                                  Emu(int(w * 12700)), Emu(int(h * 12700)))

    # ------------------------------------------------------------ text
    def text(self, x, y, w, h, content, size=18, bold=False, color=INK,
             align="right", anchor="top", line=1.5, direction="rtl",
             italic=False, underline=False, wrap=True, space_after=0):
        """Draw rich text; returns the height actually used (pt)."""
        if content is None or content == "":
            return 0.0
        initial = size
        # --- auto-fit: MuPDF leaves a broken content stream if text overflows
        # its box, so shrink to fit instead of ever overflowing.
        if wrap and h > 0:
            for _ in range(24):
                need = self.measure(content, w, size=size, line=line,
                                    direction=direction, bold=bold)
                if need <= h + 0.5 or size <= 8.5:
                    break
                size = max(8.5, size - 1)
            if size < initial:
                self.warn.append(("shrunk", round(initial, 1), round(size, 1),
                                  re.sub(r"<[^>]+>", "", content)[:40]))
        al = {"right": "right", "center": "center", "left": "left",
              "justify": "justify"}[align]
        # MuPDF maps text-align:right onto the *inline start* edge, which would
        # invert right alignment for RTL; RTL is right-aligned by default.
        ta = "" if (direction == "rtl" and align == "right") else f"text-align:{al};"
        style = f"font-size:{size}pt;color:#{color};line-height:{line};" + ta
        if bold:
            style += "font-weight:bold;"
        if italic:
            style += "font-style:italic;"
        body = content.replace("\n", "<br/>")
        div = f'<div dir="{direction}" style="{style}">{body}</div>'
        rect = pymupdf.Rect(x, y, x + w, y + h)
        needed = _m.height(content, w, size, line=line, bold=bold)
        spare = max(0.0, h - needed)
        if anchor == "middle":
            rect = pymupdf.Rect(x, y + spare / 2.0, x + w, y + h)
        elif anchor == "bottom":
            rect = pymupdf.Rect(x, y + spare, x + w, y + h)
        rc = self.p.insert_htmlbox(rect, div, css=_CSS_BASE, archive=self.arch,
                                   scale_low=0)
        used = needed
        if wrap and h > 0 and needed > h + 2:
            self.warn.append(("tight", round(needed, 1), round(h, 1),
                              re.sub(r"<[^>]+>", "", content)[:44]))

        # ---- pptx
        box = self.s.shapes.add_textbox(Emu(int(x * 12700)), Emu(int(y * 12700)),
                                        Emu(int(w * 12700)), Emu(int(h * 12700)))
        tf = box.text_frame
        tf.word_wrap = wrap
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE,
                              "bottom": MSO_ANCHOR.BOTTOM}[anchor]
        tf.auto_size = MSO_AUTO_SIZE.NONE
        pa = {"right": PP_ALIGN.RIGHT, "center": PP_ALIGN.CENTER,
              "left": PP_ALIGN.LEFT, "justify": PP_ALIGN.JUSTIFY}[align]
        for i, para in enumerate(re.split(r"<br\s*/?>|\n", content)):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = pa
            p.line_spacing = line
            if space_after:
                p.space_after = Pt(space_after)
            pPr = p._p.get_or_add_pPr()
            pPr.set("rtl", "1" if direction == "rtl" else "0")
            runs = parse_runs(para) or [(" ", {})]
            for txt, st in runs:
                txt = txt.replace(LRI, "").replace(PDI, "")
                r = p.add_run()
                r.text = txt
                f = r.font
                f.size = Pt(size)
                f.bold = bool(st["b"] or bold)
                f.italic = bool(st["i"] or italic)
                f.underline = bool(st["u"] or underline)
                f.color.rgb = _rgb(st["color"] or color)
                f.name = FONT
                rPr = f._rPr
                for tag in ("a:latin", "a:cs", "a:ea"):
                    el = rPr.find(qn(tag))
                    if el is None:
                        el = etree.SubElement(rPr, qn(tag))
                    el.set("typeface", FONT)
        return used

    def bullets(self, x, y, w, items, size=17, color=INK, gap=11, line=1.42,
                marker="dot", marker_color=GREEN, bold=False, direction="rtl"):
        """Vertical bullet list; returns bottom y."""
        cx = x + w - 4 if direction == "rtl" else x + 4
        tx = x + (0 if direction == "rtl" else 20)
        tw = w - 20
        cy = y
        for it in items:
            hs = self.measure(it, tw, size=size, line=line, direction=direction, bold=bold)
            if marker == "dot":
                self.circle(cx - 5, cy + size * 0.72, 2.6, fill=marker_color)
            elif marker == "num":
                pass
            self.text(tx, cy, tw, hs + 2, it, size=size, color=color, line=line,
                      bold=bold, direction=direction)
            cy += hs + gap
        return cy

    def notes(self, text):
        self.s.notes_slide.notes_text_frame.text = text


class Deck:
    def __init__(self, title, subject="", author="معهد الفاو للتدريب"):
        self.prs = Presentation()
        self.prs.slide_width = Emu(int(SLIDE_W * 12700))
        self.prs.slide_height = Emu(int(SLIDE_H * 12700))
        self.pdf = pymupdf.open()
        self.archive = pymupdf.Archive(FONT_DIR)
        self.sdoc = pymupdf.open()
        self.spage = self.sdoc.new_page(width=SLIDE_W + 1200, height=3000)
        self.warn = []
        cp = self.prs.core_properties
        cp.title = title
        cp.author = author
        cp.subject = subject
        cp.language = "ar-SA"
        cp.comments = ("مواد تدريبية أصلية من إعداد معهد الفاو — بريدة. "
                       "جميع الأسماء والبيانات وهمية لأغراض التدريب.")
        self.count = 0

    def new(self):
        s = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        page = self.pdf.new_page(width=SLIDE_W, height=SLIDE_H)
        self.count += 1
        return Canvas(s, page, self.archive, (self.sdoc, self.spage)), page

    def save(self, pptx_path, pdf_path):
        self.prs.save(pptx_path)
        self.pdf.set_metadata({"title": self.prs.core_properties.title,
                               "author": "معهد الفاو للتدريب",
                               "subject": "مواد تدريبية — دورة إدخال البيانات ومعالجة النصوص",
                               "creator": "معهد الفاو — بريدة"})
        self.pdf.save(pdf_path, garbage=4, deflate=True)
        return self.warn


# ---------------------------------------------------------------- chrome
def background(c, fill=WHITE):
    c.rect(0, 0, SLIDE_W, SLIDE_H, fill=fill)


def footer(c, week_label, topic, idx, total):
    c.line(M, 493, SLIDE_W - M, 493, LINE, 0.75)
    c.image(M, 497, 22, 20, LOGO_MARK)
    c.text(M + 28, 501, 320, 18,
           "معهد الفاو للتدريب — دورة إدخال البيانات ومعالجة النصوص",
           size=9, color=GRAY_L, align="left")
    c.text(SLIDE_W / 2 - 60, 500, 120, 18, f"{idx} / {total}", size=9, color=GRAY_L,
           align="center")
    c.text(SLIDE_W - M - 360, 501, 360, 18, f"{week_label} · {topic}", size=9,
           color=GRAY_L, align="right")


def header(c, title, kicker=None, sub=None, chip=None, tone="red", logo=False,
           mark=False):
    if logo:
        c.image(M, 34, 62, 50, LOGO_FULL)
        c.text(M + 74, 46, 300, 22, "معهد الفاو للتدريب — بريدة", size=11,
               color=GRAY, align="left")
    if mark:
        c.image(SLIDE_W - M - 26, 34, 26, 25, LOGO_MARK)
    if kicker:
        kw = CONTENT_W - (60 if (mark or logo) else 0)
        c.text(M + (74 if logo else 0), 40, kw, 22, kicker, size=12.5, color=GRAY,
               align="right")
    if chip:
        w = c.width(chip, size=11) + 26
        c.rect(M, 36, w, 25, fill=GREEN_T, radius=12)
        c.text(M + 6, 40, w - 12, 20, chip, size=11, color=GREEN_D, align="center")
    ty = 64 if (kicker or chip or mark) else 46
    used = c.text(M, ty, CONTENT_W, 52, title, size=31, bold=True,
                  color=RED if tone == "red" else INK, align="right", line=1.15)
    ny = ty + max(52, used + 6)
    c.rect(SLIDE_W - M - 68, ny, 68, 4, fill=GREEN, radius=2)
    if sub:
        c.text(M, ny + 15, CONTENT_W, 26, sub, size=13.5, color=GRAY, align="right",
               line=1.3)
        return ny + 48
    return ny + 18


LOGO_FULL = LOGO
