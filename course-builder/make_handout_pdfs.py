# -*- coding: utf-8 -*-
"""docx/xlsx → PDF (معاينة مطبوعة) للملفات المرفقة في مجلدات الأسابيع.

الغرض: أن يكون لكل ملف Word/Excel نسخة PDF للعرض والطباعة بجانب الملف
القابل للتحرير — بنفس هوية الشرائح (ألوان المعهد، RTL، خط Noto Sans Arabic).

يُشغَّل من مجلد course-builder بعد make_handouts.py:
    python make_handout_pdfs.py
"""
import os

import pymupdf
from docx import Document
import metrics as _m
from docx.table import Table
from docx.text.paragraph import Paragraph

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "دورة_إدخال_البيانات_ومعالجة_النصوص_معهد_الفاو")

RED = (0xA9 / 255, 0x26 / 255, 0x2E / 255)
GREEN = (0x06 / 255, 0x81 / 255, 0x4A / 255)
INK = (0x18 / 255, 0x24 / 255, 0x20 / 255)
GRAY = (0x55 / 255, 0x64 / 255, 0x5E / 255)
LINE = (0xDC / 255, 0xE3 / 255, 0xDF / 255)
PANEL = (0xF5 / 255, 0xF7 / 255, 0xF6 / 255)
HEAD = (0x06 / 255, 0x81 / 255, 0x4A / 255)

CSS = (
    "@font-face{font-family:ara;src:url(NotoSansArabic-Regular.ttf);font-weight:normal;}"
    "@font-face{font-family:ara;src:url(NotoSansArabic-Bold.ttf);font-weight:bold;}"
    "@font-face{font-family:lat;src:url(DejaVuSans.ttf);font-weight:normal;}"
    "*{font-family:ara,lat;margin:0;padding:0;}"
    ".p{margin:0 0 5pt 0;line-height:1.45;}"
    ".h{margin:12pt 0 5pt 0;}"
    ".ltr{direction:ltr;unicode-bidi:isolate;font-family:lat;}"
    ".rule{border-bottom:1px solid #DCE3DF;margin:2pt 0 8pt 0;}"
)

PW, PH = 595.0, 842.0          # A4 pt
ML, MR, MT, MB = 62.0, 62.0, 58.0, 64.0
CW = PW - ML - MR


def _hex(rgb):
    return "%02X%02X%02X" % tuple(int(round(c * 255)) for c in rgb)


class Page:
    def __init__(self, doc, archive):
        self.doc = doc
        self.arch = archive
        self.page = None
        self.y = 0
        self.new()

    def new(self):
        self.page = self.doc.new_page(width=PW, height=PH)
        self.page.draw_rect(pymupdf.Rect(0, 0, PW, 4), color=None, fill=RED)
        self.page.draw_rect(pymupdf.Rect(0, 4, PW, 7), color=None, fill=GREEN)
        _logo_pdf(self.page, PW - MR, MT - 8, 34)
        a = self.arch
        div = ('<div style="font-size:8.6pt;line-height:1.5;color:#55645E">'
               'معهد الفاو — بريدة، القصيم</div>')
        self.page.insert_htmlbox(pymupdf.Rect(ML, MT + 34, PW - MR, MT + 48),
                                 div, css=CSS, archive=a, scale_low=0)
        self.page.draw_line(pymupdf.Point(ML, MT + 50), pymupdf.Point(PW - MR, MT + 50),
                            color=LINE, width=0.8)
        self.y = MT + 58

    def need(self, h):
        if self.y + h > PH - MB:
            self.new()

    # ---------------------------------------------------------------- text
    def text(self, s, size=11, bold=False, color=INK, ltr=False, indent=0.0,
             space_after=5.0, line=1.45):
        s = s.strip()
        if not s:
            return
        style = "font-size:%.2fpt;line-height:%.2f;color:#%s;%s" % (
            size, line, _hex(color), "font-weight:bold;" if bold else "")
        div = ('<div class="p" style="%s">%s</div>'
               % (style, _esc(s)))
        w = CW - indent
        h = _m.height(s, w, size, line=line, bold=bold) + 3
        self.need(h + space_after)
        self.page.insert_htmlbox(
            pymupdf.Rect(ML + indent, self.y, ML + indent + w, self.y + h),
            div, css=CSS, archive=self.arch, scale_low=0)
        self.y += h + space_after

    def rule(self):
        self.need(14)
        self.page.draw_line(pymupdf.Point(ML, self.y + 2), pymupdf.Point(PW - MR, self.y + 2),
                            color=LINE, width=0.8)
        self.y += 10

    # ---------------------------------------------------------------- table
    def table(self, rows, header=True):
        """RTL table; header=False for data blocks that continue on a sheet."""
        if not rows:
            return
        ncol = max(len(r) for r in rows)
        colw = CW / ncol
        rh = 22.0
        self.need(rh * len(rows) + 10)
        for ri, row in enumerate(rows):
            x = PW - MR                     # RTL: first column on the right
            is_head = header and ri == 0
            fill = HEAD if is_head else (PANEL if ri % 2 == 0 else (1, 1, 1))
            self.page.draw_rect(pymupdf.Rect(ML, self.y, PW - MR, self.y + rh),
                                color=None, fill=fill)
            for ci in range(ncol):
                val = row[ci] if ci < len(row) else ""
                x0 = x - colw
                self.page.draw_line(pymupdf.Point(x0, self.y), pymupdf.Point(x0, self.y + rh),
                                    color=LINE, width=0.6)
                style = ("font-size:10pt;line-height:1.3;color:#%s;%s"
                         % ("FFFFFF" if is_head else _hex(INK),
                            "font-weight:bold;" if is_head else ""))
                div = '<div style="%s">%s</div>' % (style, _esc(str(val)))
                self.page.insert_htmlbox(
                    pymupdf.Rect(x0 + 3, self.y + 3, x0 + colw - 3, self.y + rh - 2),
                    div, css=CSS, archive=self.arch, scale_low=0)
                x -= colw
            self.page.draw_line(pymupdf.Point(ML, self.y), pymupdf.Point(PW - MR, self.y),
                                color=LINE, width=0.6)
            self.y += rh
        self.page.draw_line(pymupdf.Point(ML, self.y), pymupdf.Point(PW - MR, self.y),
                            color=LINE, width=0.6)
        self.y += 12


def _esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _logo_pdf(page, x, y, h=26.0):
    """Draw the official logo image (aspect kept) at top-right of the sheet."""
    path = os.path.join(FONT_DIR, "logo_t@2x.png")
    from PIL import Image
    with Image.open(path) as im:
        w, hh = im.size
    w = h * w / hh
    page.insert_image(pymupdf.Rect(x - w, y, x, y + h), filename=path)
    return w


def _iter_blocks(doc):
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, doc)
        elif child.tag.endswith("}tbl"):
            yield Table(child, doc)


def render(docx_path, pdf_path):
    doc = Document(docx_path)
    archive = pymupdf.Archive(FONT_DIR)
    pdf = pymupdf.open()
    pg = Page(pdf, archive)
    # عنوان الصفحة يأتي من أول ثلاثة فقرات في ملفاتنا: سطر علوي، عنوان، سطر فرعي
    head_done = 0
    for block in _iter_blocks(doc):
        if isinstance(block, Table):
            rows = []
            for r in block.rows:
                rows.append([c.text.strip() for c in r.cells])
            pg.table(rows)
            continue
        txt = block.text.strip()
        if not txt:
            continue
        runs = [r for r in block.runs if r.text.strip()]
        size = 11.0
        bold = False
        color = INK
        ltr = False
        if block.runs:
            r0 = block.runs[0]
            if r0.font.size:
                size = r0.font.size.pt
            bold = bool(r0.font.bold)
            if r0.font.color and r0.font.color.rgb:
                c = str(r0.font.color.rgb)
                color = tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
            ltr = (r0.font.name == "DejaVu Sans")
        if head_done == 0:
            head_done += 1        # already drawn by the page header stamp
            continue
        if head_done == 1:
            pg.text(txt, size=17, bold=True, color=RED, space_after=1)
            head_done += 1
            continue
        if head_done == 2:
            pg.text(txt, size=10, color=GRAY, space_after=3)
            pg.rule()
            head_done += 3
            continue
        if txt[0] in "☐□☑▪●◻✔":
            # move the box glyph to its own LTR segment so it stays at the start edge
            txt = "\u2066" + txt[0] + "\u2069" + txt[1:]
        pg.text(txt, size=max(9.0, size), bold=bold, color=color, ltr=ltr, space_after=4)
    pdf.subset_fonts()
    pdf.save(pdf_path, garbage=4, deflate=True, clean=True)
    pdf.close()
    return pdf_path


# ---------------------------------------------------------------- xlsx preview
def _is_meta(text):
    """Sheet titles / instructions that the PDF header already renders."""
    t = text.strip().lstrip("\u200f\u2066\u2069(\u00a0 ")
    t = t.replace("\u200b", "")
    return ("الأسبوع" in t[:20]) or ("معهد الفاو" in t[:20])


def render_xlsx(xlsx_path, pdf_path, title, subtitle):
    """معاينة مطبوعة لورقة Excel: أسطر الشرح نصًّا، وصفوف البيانات جدولًا،
    مع الحفاظ على ترتيبها الأصلي في الورقة."""
    from openpyxl import load_workbook
    wb = load_workbook(xlsx_path)
    archive = pymupdf.Archive(FONT_DIR)
    pdf = pymupdf.open()
    for ws in wb.worksheets:
        pg = Page(pdf, archive)
        pg.text(title, size=17, bold=True, color=RED, space_after=1)
        pg.text(subtitle + " · ورقة: " + ws.title, size=10, color=GRAY,
                space_after=3)
        pg.rule()

        rows = []
        for r in ws.iter_rows(values_only=True):
            cells = ["" if v is None else (("%g" % v) if isinstance(v, float) else str(v))
                     for v in r]
            while cells and cells[-1] == "":
                cells.pop()
            rows.append(cells)

        ncol = max([len(c) for c in rows if any(c)] or [3])
        ncol = max(3, min(6, ncol))

        def is_row(cells):
            ne = [c for c in cells if c]
            if len(ne) >= 2:
                return True
            if len(ne) == 1 and cells[0] == ne[0] and len(ne[0]) <= 22:
                return not ne[0].startswith("المطلوب")
            return False

        block = []
        first_block = True

        def flush():
            nonlocal block, first_block
            if block:
                pg.table(list(block), header=first_block)
                first_block = False
                block = []

        blank = 0
        for cells in rows:
            ne = [c for c in cells if c]
            if not ne:
                blank += 1
                if block and blank <= 1:
                    block.append([""] * ncol)
                continue
            blank = 0
            first = ne[0]
            if _is_meta(first):
                continue
            if is_row(cells) and not first.endswith(":"):
                block.append(cells + [""] * (ncol - len(cells)))
            else:
                flush()
                pg.text(" ".join(ne), size=10,
                        color=RED if first.endswith(":") else GRAY, space_after=3)
        flush()
    pdf.subset_fonts()
    pdf.save(pdf_path, garbage=4, deflate=True, clean=True)
    pdf.close()
    return pdf_path


# ---------------------------------------------------------------- xlsx preview
def _is_meta(text):
    """Sheet titles / instructions that the PDF header already renders."""
    t = text.strip().lstrip("\u200f\u2066\u2069(\u00a0 ")
    t = t.replace("\u200b", "")
    return ("الأسبوع" in t[:20]) or ("معهد الفاو" in t[:20])


def render_xlsx(xlsx_path, pdf_path, title, subtitle):
    """معاينة مطبوعة لورقة Excel: أسطر الشرح نصًّا، وصفوف البيانات جدولًا،
    مع الحفاظ على ترتيبها الأصلي في الورقة."""
    from openpyxl import load_workbook
    wb = load_workbook(xlsx_path)
    archive = pymupdf.Archive(FONT_DIR)
    pdf = pymupdf.open()
    for ws in wb.worksheets:
        pg = Page(pdf, archive)
        pg.text(title, size=17, bold=True, color=RED, space_after=1)
        pg.text(subtitle + " · ورقة: " + ws.title, size=10, color=GRAY, space_after=3)
        pg.rule()

        rows = []
        for r in ws.iter_rows(values_only=True):
            cells = ["" if v is None else (("%g" % v) if isinstance(v, float) else str(v))
                     for v in r]
            while cells and cells[-1] == "":
                cells.pop()
            rows.append(cells)

        ncol = max((len([c for c in r if c]) and len(r) for r in rows), default=3)
        ncol = max(3, min(6, ncol))

        def is_row(cells):
            ne = [c for c in cells if c]
            if len(ne) >= 2:
                return True
            if len(ne) == 1 and cells[0] == ne[0] and len(ne[0]) <= 22:
                return not ne[0].startswith("المطلوب")
            return False

        block, blank = [], 0
        state = {"first": True}

        def flush():
            nonlocal block
            if block:
                pg.table(list(block), header=state["first"])
                state["first"] = False
                block = []

        for cells in rows:
            ne = [c for c in cells if c]
            if not ne:
                blank += 1
                if block and blank <= 1:
                    block.append([""] * ncol)
                continue
            blank = 0
            first = ne[0]
            if _is_meta(first):
                continue
            if is_row(cells) and not (len(ne) == 1 and first.endswith(":")):
                block.append(cells + [""] * (ncol - len(cells)))
            else:
                flush()
                pg.text(" ".join(ne), size=10,
                        color=RED if first.endswith(":") else GRAY, space_after=3)
        flush()
    pdf.subset_fonts()
    pdf.save(pdf_path, garbage=4, deflate=True, clean=True)
    pdf.close()
    return pdf_path


# ---------------------------------------------------------------- xlsx preview
def _is_meta(text):
    """Sheet titles / instructions that the PDF header already renders."""
    t = text.strip().lstrip("\u200f\u2066\u2069(\u00a0 ")
    t = t.replace("\u200b", "")
    return ("الأسبوع" in t[:20]) or ("معهد الفاو" in t[:20])


def render_xlsx(xlsx_path, pdf_path, title, subtitle):
    """معاينة مطبوعة لورقة Excel: أسطر الشرح كنص، والبيانات كجدول."""
    from openpyxl import load_workbook
    wb = load_workbook(xlsx_path)
    archive = pymupdf.Archive(FONT_DIR)
    pdf = pymupdf.open()
    for ws in wb.worksheets:
        pg = Page(pdf, archive)
        pg.text("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                size=9.2, color=GRAY, space_after=1)
        pg.text(title, size=17, bold=True, color=RED, space_after=1)
        pg.text(subtitle + " · ورقة: " + ws.title, size=10, color=GRAY, space_after=3)
        pg.rule()
        grid = []
        for r in ws.iter_rows(values_only=True):
            cells = ["" if v is None else (("%g" % v) if isinstance(v, float) else str(v))
                     for v in r]
            while cells and cells[-1] == "":
                cells.pop()
            if not cells:
                grid.append([""])
                continue
            grid.append(cells)
        head = next((i for i, r in enumerate(grid)
                     if len([c for c in r if c]) >= 3), None)
        pre, table_rows, post = [], [], []
        started = False
        for i, r in enumerate(grid):
            ne = [c for c in r if c]
            if head is not None and i < head:
                if not _is_meta(r[0]):
                    pre.append(" ".join(ne))
                continue
            short = max((len(c) for c in ne), default=0)
            is_row = len(ne) >= 2 or (len(ne) == 1 and r[0] == ne[0]
                                      and short <= 24 and not r[0].startswith("المطلوب"))
            if len(ne) == 0:
                if started:
                    table_rows.append([""] * len(table_rows[0]))
                continue
            if is_row:
                table_rows.append(r)
                started = True
            else:
                if not _is_meta(r[0]):
                    (post if started else pre).append(" ".join(ne))
        for n in pre:
            pg.text(n, size=10, color=GRAY, space_after=3)
        pg.table(table_rows)
        for n in post:
            pg.text(n, size=10, color=GRAY, space_after=3)
    pdf.subset_fonts()
    pdf.save(pdf_path, garbage=4, deflate=True, clean=True)
    pdf.close()
    return pdf_path


# ---------------------------------------------------------------- xlsx preview
def _is_meta(text):
    """Sheet titles / instructions that the PDF header already renders."""
    t = text.strip().lstrip("\u200f\u2066\u2069(\u00a0 ")
    t = t.replace("\u200b", "")
    return ("الأسبوع" in t[:20]) or ("معهد الفاو" in t[:20])


TITLES = {
    22: ("الأسبوع 22 — بداية العمل في Excel", "ورقة تدريب المتدرب"),
    23: ("الأسبوع 23 — إدخال البيانات وتنسيق الخلايا", "ورقة تدريب المتدرب"),
    24: ("الأسبوع 24 — الصيغ والدوال", "ورقة تدريب المتدرب"),
    25: ("الأسبوع 25 — الترتيب والتصفية والمخططات", "ورقة تدريب المتدرب"),
    26: ("الأسبوع 26 — المشروع الختامي", "ورقة تدريب المتدرب"),
}


def _xlsx_pass():
    for no, (t, sub) in TITLES.items():
        d = os.path.join(OUT, "W%02d" % no)
        for f in sorted(os.listdir(d)):
            if not f.endswith(".xlsx"):
                continue
            key = "مفتاح" in f
            render_xlsx(os.path.join(d, f), os.path.join(d, f[:-5] + ".pdf"),
                        (t + " — مفتاح الإجابة (للمدرّب فقط)") if key else t,
                        "مفتاح إجابة منفصل · لا يُوزَّع" if key else sub)
            print("pdf:", f)


if __name__ == "__main__":
    n = 0
    for wk in sorted(os.listdir(OUT)):
        d = os.path.join(OUT, wk)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(".docx"):
                render(os.path.join(d, f), os.path.join(d, f[:-5] + ".pdf"))
                n += 1
    print("pdf handouts:", n)
    _xlsx_pass()
