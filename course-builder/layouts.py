# -*- coding: utf-8 -*-
"""Slide layouts. Every layout is shared by the PPTX and the PDF backends."""
from __future__ import annotations

from engine import (
    Canvas, L, M, SLIDE_W, SLIDE_H, CONTENT_W, RED, RED_D, RED_T, GREEN, GREEN_D,
    GREEN_T, INK, GRAY, GRAY_L, LINE, PANEL, PANEL2, WHITE, AMBER_T, AMBER,
    header, footer, background, LOGO_FULL, LOGO_MARK,
)

BOTTOM = 470.0          # content must end above this line



def _scaled(c, fn, avail, lo=0.72, hi=1.0):
    """Pick the largest type scale in [lo, hi] whose layout fits `avail`."""
    best = lo
    x = hi
    while x >= lo:
        if fn(x) <= avail:
            best = x
            break
        x -= 0.02
    return best

def _fit(c, y, limit=BOTTOM):
    """Warn if content would run past the printable area."""
    if y > limit + 1:
        c.warn.append(("below-footer", round(y, 1)))


# ------------------------------------------------------------------ helpers
def chip(c, x, y, text, fill=GREEN_T, color=GREEN_D, size=11, pad=10, h=24):
    w = c.width(text, size=size) + pad * 2
    c.rect(x, y, w, h, fill=fill, radius=h / 2)
    c.text(x, y + (h - size * 1.5) / 2 - 1, w, size * 1.6, text, size=size,
           color=color, align="center", line=1.1)
    return w


def number_badge(c, cx, cy, r, text, fill=RED, color=WHITE, size=15):
    c.circle(cx, cy, r, fill=fill)
    c.text(cx - r, cy - r, 2 * r, 2 * r, text, size=size, bold=True, color=color,
           align="center", anchor="middle", line=1.0)


def card(c, x, y, w, h, title=None, body=None, fill=PANEL, stroke=None,
         accent=None, title_color=INK, body_color=GRAY, pad=16, size=14.5,
         radius=12, tsize=15.5, tline=1.3):
    c.rect(x, y, w, h, fill=fill, stroke=stroke, radius=radius)
    if accent:
        c.rect(x + w - 4, y + 12, 4, min(28, h - 24), fill=accent, radius=2)
    ty = y + pad
    if title:
        used = c.text(x + pad, ty, w - 2 * pad, h, title, size=tsize, bold=True,
                      color=title_color, line=tline)
        ty += used + 6
    if body:
        c.text(x + pad, ty, w - 2 * pad, (y + h) - ty - pad + 6, body, size=size,
               color=body_color, line=1.45)
    return y + h


def table(c, x, y, w, cols, rows, head_fill=GREEN_D, head_color=WHITE,
          row_h=None, size=13, head_size=13, zebra=PANEL, stroke=LINE,
          align=None, col_w=None, first_bold=False):
    """RTL table: cols[0] is drawn at the right edge."""
    n = len(cols)
    col_w = col_w or [w / n] * n
    total = sum(col_w)
    scale = w / total
    col_w = [cw * scale for cw in col_w]
    align = align or ["center"] * n
    hh = 30
    row_h = row_h or 28
    # header
    cx = x + w
    for i, name in enumerate(cols):
        cw = col_w[i]
        cx -= cw
        c.rect(cx, y, cw, hh, fill=head_fill, stroke=stroke, width=0.75)
        c.text(cx + 4, y + 4, cw - 8, hh - 6, name, size=head_size, bold=True,
               color=head_color, align=align[i], anchor="middle", line=1.15)
    cy = y + hh
    for r, row in enumerate(rows):
        cx = x + w
        for i, val in enumerate(row):
            cw = col_w[i]
            cx -= cw
            c.rect(cx, cy, cw, row_h, fill=(zebra if r % 2 else WHITE),
                   stroke=stroke, width=0.75)
            bold = first_bold and i == 0
            c.text(cx + 4, cy + 1, cw - 8, row_h - 2, str(val), size=size,
                   bold=bold, color=INK if bold else GRAY, align=align[i],
                   anchor="middle", line=1.15)
            cx += 0
        cy += row_h
    return cy


def mock_label(c, x, y, text="رسم توضيحي", size=8.5):
    w = c.width(text, size=size) + 26
    c.rect(x, y, w, size * 2.4, fill=AMBER_T, radius=size)
    c.text(x, y, w, size * 2.4, text, size=size, color=AMBER, align="center",
           anchor="middle", line=1.0, wrap=False)
    return w


def window_mock(c, x, y, w, h, title_bar=GREEN_D, title_text="", rows=3,
                body_fill=WHITE, labels=None):
    """A clearly-labelled illustration of a generic application window."""
    c.rect(x, y, w, h, fill=body_fill, stroke=LINE, radius=6)
    c.rect(x, y, w, 20, fill=title_bar, radius=6)
    c.text(x + 8, y + 2, w - 60, 16, title_text, size=9, color=WHITE,
           align="left", line=1.0)
    for i in range(3):
        c.circle(x + w - 14 - i * 11, y + 10, 3, fill=WHITE)
    for i in range(rows):
        c.line(x + 12, y + 34 + i * 18, x + w - 12, y + 34 + i * 18, LINE, 0.6)


# ------------------------------------------------------------------ layouts
def s_cover(d, wk, idx, total):
    c, _ = d.new()
    background(c)
    # left brand panel
    c.rect(0, 0, 300, SLIDE_H, fill=GREEN_D)
    c.rect(300, 0, 6, SLIDE_H, fill=RED)
    c.rect(44, 44, 176, 148, fill=WHITE, radius=10)
    c.image(55, 57, 154, 122, LOGO_FULL)
    c.rect(52, 206, 130, 3, fill=WHITE, radius=2)
    c.text(46, 222, 210, 120,
           "معهد الفاو\nللتدريب\nبريدة — القصيم", size=17, color=WHITE, line=1.5)
    c.text(46, 412, 210, 60, "دورة إدخال البيانات\nومعالجة النصوص", size=12.5,
           color="C9E3D6", line=1.55)
    # right content
    x0 = 340
    w = SLIDE_W - x0 - M
    c.text(x0, 44, w, 26, wk["phase"], size=12.5, color=GREEN, align="right")
    c.text(x0, 74, w, 30, f"الأسبوع {wk['no_ar']} · رقم {wk['no']:02d}", size=13,
           color=GRAY, align="right")
    c.text(x0, 112, w, 120, wk["title"], size=40, bold=True, color=RED,
           align="right", line=1.25)
    c.rect(SLIDE_W - M - 110, 244, 110, 5, fill=GREEN, radius=2)
    c.text(x0, 266, w, 40, wk["cover_note"], size=16, color=INK, align="right",
           line=1.5)
    # mission strip
    mh = c.measure(wk["mission"], w - 36, size=14.5) + 34
    c.rect(x0, 330, w, mh, fill=PANEL, radius=10)
    c.rect(x0 + w - 5, 340, 5, mh - 20, fill=RED, radius=2)
    c.text(x0 + 18, 342, w - 44, mh - 20,
           "<b>مهمة الأسبوع:</b> " + wk["mission"], size=14.5, color=INK,
           line=1.5)
    c.text(x0, 452, w, 40, "المدرّب: الأستاذ عادل الحربي  ·  3 لقاءات أسبوعيًا: الأحد، الاثنين، الثلاثاء",
           size=11.5, color=GRAY, align="right")
    c.text(x0, 472, w, 30, "مادة تدريبية أصلية — جميع الأسماء والبيانات وهمية",
           size=10, color=GRAY_L, align="right")
    c.notes(wk["notes"]["cover"])
    return c


def s_warmup(d, wk, idx, total):
    c, _ = d.new()
    background(c)
    y = header(c, "مهمة الأسبوع والتهيئة", kicker=f"لوحة الاسترجاع · {wk['recall_from']}",
               sub="5 دقائق — يعمل المتدربون فرادى ثم نناقش الإجابات معًا", chip="استرجاع")
    wu = wk["warmup"]

    # ---- pre-measure everything, then place from the top (no overlap possible)
    qh = c.measure(wu["q"], CONTENT_W - 120, size=22, line=1.45) + 44
    rows = [(t, c.measure(t, CONTENT_W - 56, size=15.5) + 12) for t in wu["task"]]
    bh = c.measure(wu["bridge"], CONTENT_W - 30, size=13) + 20 if wu.get("bridge") else 0
    total_h = (qh + 26 + 30 + sum(h + 8 for _, h in rows) + (bh + 10 if bh else 0))
    avail = BOTTOM - y - 4
    gap = 26 if total_h <= avail else 12

    c.rect(M, y + 6, CONTENT_W, qh, fill=RED_T, radius=12)
    c.circle(M + 44, y + 6 + qh / 2, 20, fill=RED)
    c.text(M + 24, y + 6 + qh / 2 - 15, 40, 30, "؟", size=22, bold=True,
           color=WHITE, align="center", anchor="middle", line=1.0)
    c.text(M + 84, y + 18, CONTENT_W - 110, qh - 22, wu["q"], size=22, bold=True,
           color=RED_D, line=1.45)
    y2 = y + qh + gap
    c.text(M, y2, CONTENT_W, 26, "ابدأ من هنا:", size=14, bold=True, color=GREEN,
           align="right")
    yy = y2 + 30
    for i, (t, hh) in enumerate(rows, 1):
        c.rect(M, yy, CONTENT_W, hh, fill=PANEL, radius=8)
        number_badge(c, M + CONTENT_W - 20, yy + hh / 2, 12, str(i), fill=GREEN,
                     size=12)
        c.text(M + 16, yy + 6, CONTENT_W - 56, hh - 8, t, size=15.5, color=INK,
               line=1.4)
        yy += hh + 8
    if bh:
        by = yy + 4
        c.rect(M, by, CONTENT_W, bh, fill=GREEN_T, radius=8)
        c.text(M + 14, by + 8, CONTENT_W - 28, bh - 12, wu["bridge"],
               size=13, color=GREEN_D, line=1.4)
        yy = by + bh
    footer(c, f"الأسبوع {wk['no_ar']}", wk["topic_short"], idx, total)
    c.notes(wk["notes"]["warmup"])
    _fit(c, yy)
    return c


def s_outcomes(d, wk, idx, total):
    c, _ = d.new()
    background(c)
    y = header(c, "ماذا ستكون قادرًا على فعله؟", kicker="أهداف التعلم القابلة للقياس",
               sub="تُقاس بالمخرجات: كل هدف ينتهي بفعل يمكن ملاحظته على جهاز الحاسب",
               chip="أهداف")
    items = wk["outcomes"]
    n = len(items)
    colw = (CONTENT_W - 20) / 2
    rowh_needed = []
    for it in items:
        rowh_needed.append(max(c.measure(it, colw - 62, size=15) + 26, 66))
    per_col = [i % 2 for i in range(n)]
    avail_h = BOTTOM - y - 4 - 10 * 2 - 96   # leave room for the success strip
    stretch = avail_h / max(1, (n + 1) // 2)
    if all(r < stretch for r in rowh_needed):
        rowh_needed = [stretch] * n
    # two columns, right column first
    positions = [(M + colw + 20, 0), (M, 0)]
    yy = [y + 4, y + 4]
    for i, it in enumerate(items):
        col = i % 2
        x = positions[col][0]
        hh = rowh_needed[i]
        ytop = yy[col]
        c.rect(x, ytop, colw, hh, fill=PANEL, radius=10)
        number_badge(c, x + colw - 26, ytop + hh / 2, 15, str(i + 1), fill=GREEN_T,
                     color=GREEN_D, size=13)
        c.text(x + 14, ytop + 10, colw - 56, hh - 14, it, size=15, color=INK,
               line=1.45)
        yy[col] = ytop + hh + 10
    yy_max = max(yy)
    # success criteria strip
    ch = c.measure(wk["success"], CONTENT_W - 150, size=13.5) + 26
    cy = max(yy_max + 8, BOTTOM - ch)
    c.rect(M, cy, CONTENT_W, ch, fill=GREEN_T, radius=8)
    c.text(M + 16, cy + 8, 120, 20, "معيار النجاح", size=12.5, bold=True,
           color=GREEN_D, align="right", line=1.1)
    c.text(M + 16, cy + 24, CONTENT_W - 150, ch - 20, wk["success"], size=13,
           color=GREEN_D, line=1.4)
    footer(c, f"الأسبوع {wk['no_ar']}", wk["topic_short"], idx, total)
    c.notes(wk["notes"]["outcomes"])
    _fit(c, cy + ch)
    return c


# ---- visual explanation -------------------------------------------------
def s_visual(d, wk, idx, total):
    c, _ = d.new()
    background(c)
    v = wk["visual"]
    y = header(c, v["title"], kicker="الشرح البصري — جوهر الأسبوع",
               sub=v.get("lead"), chip="شرح")
    cap_h = (c.measure(v["caption"], CONTENT_W - 30, size=12) + 18) if v.get("caption") else 0
    if v.get("caption_ltr"):
        cap_h += c.measure(v["caption_ltr"], CONTENT_W - 30, size=12, line=1.3) + 8
    area_bottom = BOTTOM - (cap_h + 10 if cap_h else 0)
    kind = v["kind"]
    fn = {
        "flow": _flow, "grid": _grid, "compare": _compare, "stack": _stack,
        "steps": _steps_visual, "table": _table_visual, "window": _window_visual,
        "keyboard": _keyboard_visual, "excel": _excel_visual, "wheel": _wheel,
    }.get(kind)
    if fn is None:
        raise ValueError(kind)
    try:
        bottom = fn(c, v, y + 4, area_bottom)
    except TypeError:
        bottom = fn(c, v, y + 4)
    if v.get("caption"):
        cy = min(max(bottom + 10, area_bottom - cap_h + 6), BOTTOM - cap_h)
        cy = max(cy, bottom + 8)
        c.rect(M, cy, CONTENT_W, cap_h, fill=PANEL2, radius=8)
        ch1 = c.measure(v["caption"], CONTENT_W - 30, size=12) + 4
        c.text(M + 14, cy + 7, CONTENT_W - 28, ch1, v["caption"], size=12,
               color=GRAY, line=1.35)
        if v.get("caption_ltr"):
            c.text(M + 28, cy + 8 + ch1, CONTENT_W - 56,
                   c.measure(v["caption_ltr"], CONTENT_W - 56, size=11.5, line=1.3) + 6,
                   v["caption_ltr"], size=11.5, color=GREEN_D, line=1.3,
                   direction="ltr", align="right")
    footer(c, f"الأسبوع {wk['no_ar']}", wk["topic_short"], idx, total)
    c.notes(wk["notes"]["visual"])
    _fit(c, BOTTOM)
    return c


def _flow(c, v, y, bottom=BOTTOM):
    items = v["items"]
    n = len(items)
    gap = 34
    w = (CONTENT_W - gap * (n - 1)) / n
    h = min(215, max(130, (bottom - y - 34) * 0.80))
    for i, (lab, sub) in enumerate(items):
        x = SLIDE_W - M - w - i * (w + gap)
        c.rect(x, y + 16, w, h, fill=PANEL, radius=12)
        c.rect(x, y + 16, w, 5, fill=(GREEN if i % 2 == 0 else RED), radius=2)
        c.rect(x + w / 2 - 13, y + 16 + 22, 26, 26, fill=WHITE, stroke=GREEN,
               radius=13, width=1.2)
        c.text(x + w / 2 - 13, y + 16 + 26, 26, 22, str(i + 1), size=12.5,
               bold=True, color=GREEN_D, align="center", anchor="middle", line=1.0)
        lh = c.measure(lab, w - 20, size=15, bold=True, line=1.25)
        sh = c.measure(sub, w - 16, size=11.5, line=1.35)
        top = y + 16 + 58 + max(0, (h - 74 - lh - sh) * 0.42)
        c.text(x + 10, top, w - 20, lh + 2, lab, size=15, bold=True,
               color=INK, align="center", line=1.25)
        c.text(x + 8, top + lh + 8, w - 16, sh + 2, sub, size=11.5, color=GRAY,
               align="center", line=1.35)
        if i < n - 1:
            ay = y + 16 + h / 2
            c.arrow(x - gap + 5, ay, x - 13, ay, GREEN, 1.6)
    yy = y + 16 + h
    if v.get("below"):
        bh = c.measure(v["below"], CONTENT_W, size=13.5) + 8
        by = min(yy + 22, bottom - bh)
        c.text(M, by, CONTENT_W, bh, v["below"], size=13.5, color=INK,
               align="center", line=1.5)
        yy = by + bh
    return yy


def _grid(c, v, y, bottom=BOTTOM):
    items = v["items"]
    n = len(items)
    cols = 2 if n <= 4 else 3
    rows = (n + cols - 1) // cols
    gap = 14
    w = (CONTENT_W - gap * (cols - 1)) / cols
    h = min(190, (bottom - y - gap * (rows - 1)) / rows)
    for i, it in enumerate(items):
        r, col = divmod(i, cols)
        x = SLIDE_W - M - w - col * (w + gap)
        yy = y + r * (h + gap)
        lab, sub = (it if isinstance(it, tuple) else (it, ""))
        accent = RED if i % 2 else GREEN
        c.rect(x, yy, w, h, fill=PANEL, radius=12)
        c.rect(x + w - 46, yy + 16, 32, 32, fill=WHITE, radius=16, stroke=accent,
               width=1.1)
        c.text(x + w - 46, yy + 22, 32, 22, str(i + 1), size=13, bold=True,
               color=accent, align="center", anchor="middle", line=1.0)
        lh = c.measure(lab, w - 66, size=15.5, line=1.3)
        c.text(x + 14, yy + 18, w - 66, lh + 2, lab, size=15.5, bold=True,
               color=INK, line=1.3)
        if sub:
            sh_ = c.measure(sub, w - 28, size=12, line=1.4)
            top = yy + 26 + lh + max(0, (h - 34 - lh - sh_) / 2 * 0.5)
            c.text(x + 14, top, w - 28, sh_ + 4, sub, size=12, color=GRAY,
                   line=1.4)
    return y + rows * h + (rows - 1) * gap


def _compare(c, v, y, bottom=BOTTOM):
    left, right = v["left"], v["right"]
    gap = 26
    w = (CONTENT_W - gap) / 2
    need = 0
    for side in (left, right):
        need = max(need, 62 + sum(c.measure(i, w - 44, size=13.4) + 8 for i in side["items"]) + 26)
    h = min(max(need, 170), bottom - y)
    # centre the pair vertically in the free area
    if bottom - y > h + 20:
        y = y + (bottom - y - h) / 2 * 0.6
    for i, (side, accent) in enumerate([(left, GREEN), (right, RED)]):
        tint = GREEN_T if i == 0 else RED_T
        x = SLIDE_W - M - w - i * (w + gap)
        c.rect(x, y, w, h, fill=WHITE, stroke=LINE, radius=12)
        c.rect(x, y, w, 42, fill=tint, radius=12)
        c.rect(x, y + 30, w, 12, fill=tint)
        c.text(x + 14, y + 9, w - 28, 26, side["title"], size=16, bold=True,
               color=accent, line=1.2)
        yy = y + 56
        for it in side["items"]:
            hh = c.measure(it, w - 46, size=13.4) + 4
            c.circle(x + w - 17, yy + 10, 3.2, fill=accent)
            c.text(x + 12, yy, w - 38, hh, it, size=13.4, color=INK, line=1.4)
            yy += hh + 6
        if side.get("note"):
            c.text(x + 14, y + h - 32, w - 28, 26, side["note"], size=11.5,
                   color=GRAY, line=1.2)
    return y + h


def _stack(c, v, y, bottom=BOTTOM):
    items = v["items"]
    n = len(items)
    gap = 10
    h = min(74, (bottom - y - gap * (n - 1)) / n)
    total = n * h + (n - 1) * gap
    yy = y + max(0, (bottom - y - total) / 2 * 0.55)
    for i, (lab, sub) in enumerate(items):
        w = CONTENT_W - 56 - i * 34
        x = SLIDE_W - M - w
        c.rect(x, yy, w, h, fill=(GREEN_T if i % 2 else PANEL), radius=8)
        c.rect(x + w - 5, yy + 10, 5, h - 20, fill=(GREEN if i % 2 else GRAY_L),
               radius=2)
        lh = c.measure(lab, w - 60, size=15, bold=True, line=1.2)
        c.text(x + 14, yy + 9, w - 50, lh + 2, lab, size=15, bold=True, color=INK,
               line=1.2)
        c.text(x + 14, yy + 13 + lh, w - 50, h - lh - 16, sub, size=11.5,
               color=GRAY, line=1.3)
        yy += h + gap
    return yy


def _steps_visual(c, v, y, bottom=BOTTOM):
    items = v["items"]
    n = len(items)
    w = (CONTENT_W - 12 * (n - 1)) / n
    h = min(230, bottom - y)
    for i, (lab, sub) in enumerate(items):
        x = SLIDE_W - M - w - i * (w + 12)
        c.rect(x, y, w, h, fill=PANEL, radius=10)
        number_badge(c, x + w / 2, y + 32, 18, str(i + 1), fill=RED if i % 2 else GREEN,
                     size=15)
        lh = c.measure(lab, w - 20, size=14.5, line=1.3, bold=True)
        sh_ = c.measure(sub, w - 20, size=11.5, line=1.35)
        top = y + 56 + max(0, (h - 66 - lh - sh_) / 2 * 0.55)
        c.text(x + 10, top, w - 20, lh + 2, lab, size=14.5, bold=True, color=INK,
               align="center", line=1.3)
        c.text(x + 10, top + lh + 8, w - 20, sh_ + 4, sub, size=11.5, color=GRAY,
               align="center", line=1.35)
    return y + h


def _table_visual(c, v, y, bottom=BOTTOM):
    rows = v["rows"]
    below = v.get("below")
    bh = c.measure(below, CONTENT_W, size=13.5) + 12 if below else 0
    avail = bottom - y - bh - (14 if below else 0)
    rh = max(30, min(46, (avail - 34) / max(1, len(rows))))
    band_h = 30 + rh * len(rows)
    ty = y + 4 + max(0, (avail - band_h) / 2 * 0.5)
    ye = table(c, M, ty, CONTENT_W, v["cols"], rows, row_h=rh, size=13,
               first_bold=True)
    if below:
        c.text(M, ye + 14, CONTENT_W, bh, below, size=13.5, color=GRAY,
               align="right", line=1.45)
        ye += 14 + bh
    return ye


def _window_visual(c, v, y, bottom=BOTTOM):
    iw = 320
    ix = M + 8
    ih = min(200, bottom - y - 34)
    window_mock(c, ix, y + 8, iw, ih, title_text=v.get("mock_title", ""), rows=7)
    mock_label(c, ix + 2, y + 16 + ih)
    lx = ix + iw + 32
    lw = SLIDE_W - M - lx
    items = v["items"]
    hs = [c.measure(l, lw - 26, size=13, bold=True) + c.measure(x_, lw - 26, size=10.8) + 20
          for l, x_ in items]
    gap = 7
    total = sum(hs) + gap * (len(items) - 1)
    area = bottom - y - 4
    sc = min(1.0, area / total)
    hs = [h_ * sc for h_ in hs]
    yy = y + 6 + max(0, (area - sum(hs) - gap * (len(items) - 1)) / 2 * 0.35)
    for (lab, sub), hh in zip(items, hs):
        c.rect(lx, yy, lw, hh, fill=PANEL, radius=8)
        c.rect(lx + lw - 4, yy + 7, 4, hh - 14, fill=GREEN, radius=2)
        lh = c.measure(lab, lw - 30, size=13, bold=True) * sc
        c.text(lx + 12, yy + 5, lw - 26, lh + 2, lab, size=13 * sc, bold=True,
               color=INK, line=1.15)
        c.text(lx + 12, yy + 8 + lh, lw - 26, hh - lh - 10, sub, size=10.8 * sc,
               color=GRAY, line=1.25)
        yy += hh + gap
    return max(yy, y + 20 + ih)


def _highlight(c, x, y, w, h, key, color, dot=True):
    """Key with a coloured rim and a small corner dot (never colour alone)."""
    c.rect(x, y, w, h, fill=WHITE, stroke=color, radius=6, width=2.0)
    c.text(x, y, w, h, key, size=w * 0.40, bold=True, color=INK,
           align="center", anchor="middle", line=1.0, wrap=False)
    if dot:
        c.circle(x + w - 9, y + h - 9, 3.2, fill=color)


def _keyboard_visual(c, v, y, bottom=BOTTOM):
    rows = v["rows"]
    home = v.get("home", [])
    ncol = max(len(r) for r in rows)
    below_h = (c.measure(v["below"], CONTENT_W - 40, size=12.5) + 16) if v.get("below") else 0
    avail_w = CONTENT_W - 110
    kw = min(76, (avail_w - (ncol - 1) * 8) / ncol)
    gap = 8
    kh = kw * 0.84
    total_h = len(rows) * kh + (len(rows) - 1) * gap
    area = bottom - y - below_h - 10
    yy = y + max(12, (area - total_h) * 0.42)
    for keys in rows:
        x = SLIDE_W / 2 - (len(keys) * kw + (len(keys) - 1) * gap) / 2
        for k in keys:
            if k in home:
                _highlight(c, x, yy, kw, kh, k,
                           GREEN if k not in v.get("anchor", []) else RED)
            else:
                c.rect(x, yy, kw, kh, fill=WHITE, stroke=LINE, radius=6)
                c.text(x, yy, kw, kh, k, size=kw * 0.40, color=INK, align="center",
                       anchor="middle", line=1.0)
            x += kw + gap
        yy += kh + gap
    if v.get("below"):
        by = min(yy + 10, bottom - below_h)
        c.rect(M, by, CONTENT_W, below_h, fill=PANEL2, radius=8)
        c.text(M + 14, by + 6, CONTENT_W - 28, below_h - 8, v["below"], size=12.5,
               color=GRAY, line=1.4)
        yy = by + below_h
    return yy


def _excel_visual(c, v, y, bottom=BOTTOM):
    cols = v["cols"]
    rows = v["rows"]
    w = CONTENT_W - 40
    x = SLIDE_W / 2 - w / 2
    rh = max(26, min(44, (bottom - y - 120) / max(1, len(rows) + 1)))
    h = 28 + rh * len(rows) + 4
    y = y + max(0, (bottom - y - 46 - h) / 2)
    c.rect(x, y + 8, w, h, fill=WHITE, stroke=LINE, radius=4)
    c.rect(x, y + 8, w, 26, fill=GREEN_D, radius=4)
    c.rect(x, y + 26, w, 8, fill=GREEN_D)
    colw = w / len(cols)
    for i, name in enumerate(cols):
        cx = x + i * colw
        c.text(cx + 4, y + 12, colw - 8, 18, name, size=11, color=WHITE,
               align="center", anchor="middle", line=1.0)
        if i:
            c.line(cx, y + 34, cx, y + 8 + h, LINE, 0.7)
    for r, row in enumerate(rows):
        ry = y + 34 + r * rh
        if r:
            c.line(x, ry, x + w, ry, LINE, 0.7)
        for i, val in enumerate(row):
            c.text(x + i * colw + 4, ry + 2, colw - 8, rh - 4, str(val), size=11,
                   color=INK, align="center", anchor="middle", line=1.0)
    mock_label(c, x, y + 22 + h)
    return y + h + 52


def _wheel(c, v, y, bottom=BOTTOM):
    """Central idea on the right, numbered principles on the left."""
    items = v["items"]
    n = len(items)
    area_h = bottom - y
    r = min(96, area_h * 0.34)
    cx = SLIDE_W - M - r - 26
    cy = y + area_h * 0.44
    c.circle(cx, cy, r, fill=PANEL2)
    c.circle(cx, cy, r, stroke=GREEN, width=1.6)
    c.text(cx - r + 14, cy - 34, 2 * r - 28, 68, v.get("center", ""), size=15.5,
           bold=True, color=RED_D, align="center", anchor="middle", line=1.35)
    lw = cx - r - 40 - M
    rows = []
    for lab, sub in items:
        h = c.measure(lab, lw - 52, size=14, bold=True) + c.measure(sub, lw - 52, size=11.5) + 22
        rows.append(h)
    gap = 12
    scale = min(1.0, (area_h - 6 - gap * (n - 1)) / sum(rows))
    rows = [min(r_ * scale, 82) for r_ in rows]
    yy = y + 6 + max(0, (area_h - 6 - (sum(rows) + gap * (n - 1))) / 2 * 0.7)
    for i, ((lab, sub), hh) in enumerate(zip(items, rows)):
        c.rect(M, yy, lw, hh, fill=(PANEL if i % 2 == 0 else WHITE),
               stroke=(None if i % 2 == 0 else LINE), radius=10)
        number_badge(c, M + lw - 24, yy + hh / 2, 13, str(i + 1),
                     fill=GREEN if i % 2 == 0 else RED, size=12)
        lh = c.measure(lab, lw - 56, size=14, bold=True)
        c.text(M + 12, yy + 6, lw - 52, lh + 2, lab, size=14, bold=True,
               color=INK, line=1.25)
        c.text(M + 12, yy + 10 + lh, lw - 52, hh - lh - 14, sub, size=11.5,
               color=GRAY, line=1.3)
        yy += hh + gap
    if v.get("below"):
        bh = c.measure(v["below"], CONTENT_W, size=12.5) + 8
        by = bottom - bh
        c.text(M, by, CONTENT_W, bh, v["below"], size=12.5, color=GRAY,
               align="center", line=1.4)
        yy = by + bh
    return yy


# ---- steps --------------------------------------------------------------
def s_steps(d, wk, idx, total):
    c, _ = d.new()
    background(c)
    st = wk["steps"]
    y = header(c, st["title"], kicker="خطوات التنفيذ — فكرة واحدة في كل خطوة",
               sub=st.get("lead"), chip="تطبيق")
    items = st["items"]
    n = len(items)
    rowgap = 9
    avail = BOTTOM - y - 2

    def measure_all(msz, hsz):
        out = []
        for main, hint in items:
            hm = c.measure(main, CONTENT_W - 74, size=msz, line=1.4)
            hh = c.measure(hint, CONTENT_W - 74, size=hsz, line=1.32) if hint else 0
            out.append((hm, hh, max(hm + hh + 20, 50)))
        return out

    msz, hsz = 15.5, 12
    dims = measure_all(msz, hsz)
    while sum(x[2] for x in dims) + rowgap * (n - 1) > avail and msz > 12:
        msz -= 0.5
        hsz = max(10.5, msz - 3.2)
        dims = measure_all(msz, hsz)
    # distribute the leftover space so the last row never floats above the footer
    slack = max(0.0, avail - (sum(x[2] for x in dims) + rowgap * (n - 1)))
    rowgap += min(14.0, slack / max(1, n - 1))

    yy = y
    for i, (main, hint) in enumerate(items):
        hm, hh, total_h = dims[i]
        c.rect(M, yy, CONTENT_W, total_h, fill=(PANEL if i % 2 == 0 else WHITE),
               stroke=(None if i % 2 == 0 else LINE), radius=10)
        number_badge(c, M + CONTENT_W - 26, yy + total_h / 2, 14, str(i + 1),
                     fill=GREEN if i % 2 == 0 else RED, size=12.5)
        pad = 6
        c.text(M + 16, yy + pad, CONTENT_W - 74, hm + 2, main, size=msz,
               color=INK, line=1.4)
        if hint:
            c.text(M + 16, yy + pad + hm + 2, CONTENT_W - 74, hh + 2, hint,
                   size=hsz, color=GREEN_D, line=1.32)
        yy += total_h + rowgap
    footer(c, f"الأسبوع {wk['no_ar']}", wk["topic_short"], idx, total)
    c.notes(wk["notes"]["steps"])
    _fit(c, yy)
    return c


# ---- demonstration ------------------------------------------------------
def s_demo(d, wk, idx, total):
    c, _ = d.new()
    background(c)
    dm = wk["demo"]
    y = header(c, "عرض المدرّب المباشر", kicker="ينفّذ المدرّب على شاشة المعمل — المتدربون يلاحظون فقط",
               sub=dm.get("lead"), chip="عرض حي")
    left_w = CONTENT_W * 0.62
    right_w = CONTENT_W - left_w - 24
    lx = SLIDE_W - M - left_w
    rx = M
    yy = y
    for i, t in enumerate(dm["items"], 1):
        hh = c.measure(t, left_w - 56, size=14.5) + 18
        c.rect(lx, yy, left_w, hh, fill=PANEL, radius=8)
        number_badge(c, lx + left_w - 22, yy + hh / 2, 13, str(i), fill=WHITE,
                     color=RED, size=12)
        c.rect(lx + left_w - 34, yy + hh / 2 - 12, 24, 24, fill=WHITE, stroke=RED,
               radius=12, width=1.1)
        c.text(lx + left_w - 34, yy + hh / 2 - 9, 24, 20, str(i), size=11.5,
               bold=True, color=RED, align="center", anchor="middle", line=1.0)
        c.text(lx + 14, yy + 8, left_w - 52, hh - 12, t, size=14.5, color=INK,
               line=1.4)
        yy += hh + 8
    # right: watch-fors + timing
    rh = max(yy - y - 8, 150)
    c.rect(rx, y, right_w, rh, fill=GREEN_T, radius=10)
    c.text(rx + 14, y + 12, right_w - 28, 24, "ماذا يلاحظ المتدرب؟", size=13,
           bold=True, color=GREEN_D, line=1.2)
    yy2 = y + 42
    for t in dm["watch"]:
        hh = c.measure(t, right_w - 46, size=12.5) + 6
        c.circle(rx + right_w - 18, yy2 + 9, 3, fill=GREEN)
        c.text(rx + 12, yy2, right_w - 36, hh, t, size=12.5, color=GREEN_D,
               line=1.35)
        yy2 += hh + 6
    # timing strip
    c.rect(M, BOTTOM - 42, CONTENT_W, 38, fill=PANEL, radius=8)
    c.text(M + 16, BOTTOM - 34, CONTENT_W - 32, 24,
           "<b>الزمن:</b> 15 دقيقة عرضًا مباشرًا داخل لقاء الأحد (5 استرجاع + 10 شرح + 15 عرض + 25 تدريب + 5 خروج)",
           size=12, color=GRAY, line=1.3)
    footer(c, f"الأسبوع {wk['no_ar']}", wk["topic_short"], idx, total)
    c.notes(wk["notes"]["demo"])
    _fit(c, yy)
    return c


# ---- guided practice ----------------------------------------------------
def s_guided(d, wk, idx, total):
    c, _ = d.new()
    background(c)
    g = wk["guided"]
    y = header(c, g["title"], kicker="تدريب موجّه داخل معمل الحاسب — بإشراف المدرّب",
               sub=g.get("lead"), chip="تدريب موجّه")
    # scenario band
    sh = c.measure(g["scenario"], CONTENT_W - 150, size=13.5) + 24
    c.rect(M, y, CONTENT_W, sh, fill=RED_T, radius=8)
    c.text(M + CONTENT_W - 136, y + 7, 120, 20, "السياق", size=11.5, bold=True,
           color=RED, align="right", line=1.1)
    c.text(M + 14, y + 7, CONTENT_W - 156, sh - 12, g["scenario"], size=13.5,
           color=RED_D, line=1.4)
    yy = y + sh + 14
    # task checklist in two columns
    tasks = g["tasks"]
    half = (len(tasks) + 1) // 2
    cols = [tasks[:half], tasks[half:]]
    colw = (CONTENT_W - 20) / 2
    for ci, group in enumerate(cols):
        x = SLIDE_W - M - colw - ci * (colw + 20)
        ytop = yy
        for t in group:
            hh = c.measure(t, colw - 40, size=13.5) + 14
            c.rect(x, ytop, colw, hh, fill=WHITE, stroke=LINE, radius=8)
            c.rect(x + colw - 26, ytop + hh / 2 - 8, 16, 16, fill=WHITE,
                   stroke=GREEN, radius=3, width=1.1)
            c.text(x + 12, ytop + 7, colw - 40, hh - 10, t, size=13.5, color=INK,
                   line=1.38)
            ytop += hh + 8
        if ci == 0:
            right_bottom = ytop
    # deliverable strip
    dh = c.measure(g["deliverable"], CONTENT_W - 130, size=12.5) + 20
    dy = max(right_bottom + 6, BOTTOM - dh)
    c.rect(M, dy, CONTENT_W, dh, fill=GREEN_T, radius=8)
    c.text(M + 14, dy + 5, 100, 18, "المُخرَج", size=11.5, bold=True,
           color=GREEN_D, align="right", line=1.1)
    c.text(M + 14, dy + 20, CONTENT_W - 130, dh - 16, g["deliverable"], size=12.5,
           color=GREEN_D, line=1.35)
    footer(c, f"الأسبوع {wk['no_ar']}", wk["topic_short"], idx, total)
    c.notes(wk["notes"]["guided"])
    _fit(c, dy + dh)
    return c


# ---- individual challenge ----------------------------------------------
def s_challenge(d, wk, idx, idx_total):
    c, _ = d.new()
    background(c)
    ch = wk["challenge"]
    y = header(c, "التحدّي الفردي", kicker="ينفّذه المتدرب وحده — لا يُسلَّم عمل جماعي",
               sub=ch.get("lead"), chip="تحدٍّ")
    lw = CONTENT_W * 0.44
    rw = CONTENT_W - lw - 22
    rx = SLIDE_W - M - rw
    lx = M
    avail = BOTTOM - y - 2

    def layout(sc):
        bs = 13.2 * sc
        req_h = [c.measure(t, rw - 56, size=bs) + 8 for t in ch["requirements"]]
        bh = max(48 + sum(h + 6 for h in req_h) + 8,
                 c.measure(ch["scenario"], lw - 32, size=bs, line=1.5) + 62)
        ch_ = [c.measure(t, CONTENT_W - 40, size=bs * 0.98) + 4 for t in ch["criteria"]]
        need = bh + 12 + 22 + 26 + sum(h + 5 for h in ch_) + 24
        return bs, req_h, bh, ch_, need

    sc = _scaled(c, lambda x: layout(x)[4], avail)
    bs, req_h, box_h, crit_h, _need = layout(sc)

    c.rect(rx, y, rw, box_h, fill=PANEL, radius=12)
    c.text(rx + 16, y + 14, rw - 32, 24, "المطلوب بالضبط", size=14, bold=True,
           color=GREEN_D, line=1.2)
    yy = y + 44
    for i, (t, hh) in enumerate(zip(ch["requirements"], req_h), 1):
        number_badge(c, rx + rw - 24, yy + hh / 2, 11, str(i), fill=GREEN, size=11)
        c.text(rx + 12, yy + 2, rw - 48, hh, t, size=bs, color=INK, line=1.38)
        yy += hh + 6
    c.rect(lx, y, lw, box_h, fill=RED_T, radius=12)
    c.text(lx + 16, y + 14, lw - 32, 24, "السيناريو التدريبي", size=14, bold=True,
           color=RED, line=1.2)
    c.text(lx + 16, y + 44, lw - 32, box_h - 56, ch["scenario"], size=bs,
           color=RED_D, line=1.5)

    yy2 = y + box_h + 12
    c.text(M, yy2, CONTENT_W, 22, "كيف يعرف المتدرب أنه نجح؟", size=12.5,
           bold=True, color=GRAY, align="right", line=1.2)
    yy2 += 26
    for t, hh in zip(ch["criteria"], crit_h):
        c.circle(SLIDE_W - M - 6, yy2 + 9, 3, fill=GREEN)
        c.text(M, yy2, CONTENT_W - 20, hh, t, size=bs * 0.98, color=INK, line=1.35)
        yy2 += hh + 5
    c.text(M, yy2 + 2, CONTENT_W, 20,
           f"الزمن المقترح: {ch['time']}  ·  يُحفظ العمل في ملف الإنجاز",
           size=11.5, color=GRAY, align="right", line=1.2)
    footer(c, f"الأسبوع {wk['no_ar']}", wk["topic_short"], idx, idx_total)
    c.notes(wk["notes"]["challenge"])
    _fit(c, yy2 + 22)
    return c


# ---- common mistakes ----------------------------------------------------
def s_mistakes(d, wk, idx, total):
    c, _ = d.new()
    background(c)
    y = header(c, "أخطاء شائعة وكيف نصحّحها", kicker="لاحظ الخطأ ← افهم السبب ← صحّح فورًا",
               sub="يُعرض كل خطأ على الشاشة ويُطلب من المتدربين تحديده قبل كشف التصحيح",
               chip="تصحيح")
    items = wk["mistakes"]
    n = len(items)
    h = min(84, (BOTTOM - y - 60) / n - 10)
    yy = y
    cw = [CONTENT_W * 0.30, CONTENT_W * 0.34, CONTENT_W * 0.36]
    heads = ["الخطأ كما يظهر", "السبب الحقيقي", "التصحيح خطوة بخطوة"]
    xs = [SLIDE_W - M - cw[0], SLIDE_W - M - cw[0] - cw[1], M]
    for i, hh_txt in enumerate(heads):
        c.text(xs[i], y, cw[i] - 10, 20, hh_txt, size=11.5, bold=True,
               color=GRAY, align="right", line=1.1)
    yy = y + 24
    for wrong, cause, fix in items:
        c.rect(M, yy, CONTENT_W, h, fill=PANEL, radius=10)
        c.rect(M + CONTENT_W - 4, yy + 10, 4, h - 20, fill=RED, radius=2)
        c.text(xs[0] + 4, yy + 8, cw[0] - 18, h - 12, wrong, size=13, bold=True,
               color=RED_D, line=1.35)
        c.text(xs[1] + 4, yy + 8, cw[1] - 18, h - 12, cause, size=12.5,
               color=GRAY, line=1.35)
        c.text(xs[2] + 4, yy + 8, cw[2] - 18, h - 12, fix, size=12.5, color=INK,
               line=1.35)
        yy += h + 10
    # correction routine
    c.rect(M, BOTTOM - 40, CONTENT_W, 36, fill=GREEN_T, radius=8)
    c.text(M + 14, BOTTOM - 33, CONTENT_W - 28, 24,
           "<b>روتين التصحيح:</b> يُظهر المدرّب الخطأ على الشاشة ← يسأل: ماذا حدث؟ ← يكتب الحل على السبورة ← يعيد المتدرب التنفيذ بنفسه",
           size=11.5, color=GREEN_D, line=1.3)
    footer(c, f"الأسبوع {wk['no_ar']}", wk["topic_short"], idx, total)
    c.notes(wk["notes"]["mistakes"])
    _fit(c, yy)
    return c


# ---- simulation --------------------------------------------------------
def s_sim(d, wk, idx, total):
    c, _ = d.new()
    background(c)
    sm = wk["simulation"]
    y = header(c, sm["title"], kicker="محاكاة تدريب أصلية — من إعداد المعهد، وليست أسئلة اختبار مسرّبة",
               sub=sm.get("lead"), chip="محاكاة")
    yy = y
    # scenario
    sh = c.measure(sm["scenario"], CONTENT_W - 30, size=13.5) + 20
    c.rect(M, yy, CONTENT_W, sh, fill=PANEL, radius=8)
    c.text(M + 14, yy + 6, CONTENT_W - 28, sh - 10, sm["scenario"], size=13.5,
           color=INK, line=1.4)
    yy += sh + 12
    # questions
    for i, q in enumerate(sm["questions"], 1):
        qh = c.measure(q, CONTENT_W - 60, size=14) + 16
        c.rect(M, yy, CONTENT_W, qh, fill=WHITE, stroke=LINE, radius=8)
        number_badge(c, SLIDE_W - M - 22, yy + qh / 2, 12, str(i), fill=RED,
                     size=11)
        c.text(M + 14, yy + 7, CONTENT_W - 60, qh - 10, q, size=14, color=INK,
               line=1.4)
        yy += qh + 8
    # answer rule note
    nh = c.measure(sm["note"], CONTENT_W - 30, size=11.5) + 16
    ny = max(yy + 6, BOTTOM - nh)
    c.rect(M, ny, CONTENT_W, nh, fill=GREEN_T, radius=8)
    c.text(M + 14, ny + 5, CONTENT_W - 28, nh - 8, sm["note"], size=11.5,
           color=GREEN_D, line=1.35)
    footer(c, f"الأسبوع {wk['no_ar']}", wk["topic_short"], idx, total)
    c.notes(wk["notes"]["simulation"])
    _fit(c, ny + nh)
    return c


# ---- exit quiz + self check --------------------------------------------
def s_quiz(d, wk, idx, total):
    c, _ = d.new()
    background(c)
    qz = wk["quiz"]
    y = header(c, "اختبار الخروج وقائمة التحقق الذاتي", kicker="5 دقائق في نهاية لقاء الأحد — إجابات في ملاحظات المدرّب",
               chip="تقويم")
    lw = CONTENT_W * 0.60
    rw = CONTENT_W - lw - 24
    lx = SLIDE_W - M - lw
    rx = M
    yy = y
    for i, q in enumerate(qz["questions"], 1):
        qh = c.measure(q, lw - 46, size=13.5) + 14
        c.rect(lx, yy, lw, qh, fill=PANEL, radius=8)
        number_badge(c, lx + lw - 20, yy + qh / 2, 11, str(i), fill=RED, size=10.5)
        c.text(lx + 12, yy + 6, lw - 44, qh - 8, q, size=13.5, color=INK, line=1.38)
        yy += qh + 7
    # self checklist
    ch = c.measure("", 10)  # noop
    top = y
    c.rect(rx, top, rw, 268, fill=GREEN_T, radius=10)
    c.text(rx + 14, top + 12, rw - 28, 22, "قائمة التحقق الذاتي", size=13.5,
           bold=True, color=GREEN_D, line=1.2)
    c.text(rx + 14, top + 34, rw - 28, 18, "ضع علامة أمام ما تستطيع فعله بثقة:",
           size=10.5, color=GREEN, line=1.2)
    yy2 = top + 56
    for t in qz["checklist"]:
        hh = c.measure(t, rw - 56, size=11.5) + 8
        c.rect(rx + rw - 26, yy2 + 3, 14, 14, fill=WHITE, stroke=GREEN, radius=3,
               width=1.0)
        c.text(rx + 10, yy2, rw - 42, hh, t, size=11.5, color=GREEN_D, line=1.3)
        yy2 += hh + 4
    c.rect(M, BOTTOM - 36, CONTENT_W, 32, fill=PANEL, radius=8)
    c.text(M + 12, BOTTOM - 30, CONTENT_W - 24, 22,
           "<b>مقياس الثقة:</b> 3 = أستطيع فعلها وحدي · 2 = أحتاج تذكيرًا بسيطًا · 1 = أحتاج إعادة شرح",
           size=11, color=GRAY, line=1.25)
    footer(c, f"الأسبوع {wk['no_ar']}", wk["topic_short"], idx, total)
    c.notes(wk["notes"]["quiz"])
    _fit(c, max(yy, yy2))
    return c


# ---- Tuesday zoom ------------------------------------------------------
def s_zoom(d, wk, idx, total):
    c, _ = d.new()
    background(c)
    z = wk["zoom"]
    y = header(c, "لقاء الثلاثاء عبر Zoom — مراجعة الأسبوع والمتابعة",
               kicker="45 دقيقة: تحضير 5 · مراجعة 8 · تدريب ومشاركة شاشة 22 · اختبار 7 · مهمة المتابعة 3",
               chip="Zoom")
    # timeline
    segs = [("5", "تحضير"), ("8", "مراجعة"), ("22", "تدريب ومشاركة"), ("7", "اختبار"), ("3", "المتابعة")]
    tw = CONTENT_W / len(segs)
    for i, (mins, lab) in enumerate(segs):
        x = SLIDE_W - M - tw - i * tw
        c.rect(x + 2, y, tw - 4, 28, fill=(GREEN if i in (2,) else PANEL2 if i != 0 else PANEL),
               radius=6)
        c.text(x + 2, y + 4, tw - 4, 20, f"{mins} د · {lab}", size=10.5,
               color=(WHITE if i == 2 else GRAY), align="center", line=1.1)
    yy = y + 40
    # review points right, tasks left
    lw = CONTENT_W * 0.46
    rw = CONTENT_W - lw - 22
    rx = SLIDE_W - M - rw
    lx = M
    c.rect(rx, yy, rw, 150, fill=PANEL, radius=10)
    c.text(rx + 14, yy + 10, rw - 28, 22, "مراجعة المهارة نفسها", size=12.5,
           bold=True, color=RED, line=1.2)
    y2 = yy + 34
    for t in z["review"]:
        hh = c.measure(t, rw - 44, size=11.5) + 4
        c.circle(rx + rw - 16, y2 + 8, 2.8, fill=RED)
        c.text(rx + 12, y2, rw - 34, hh, t, size=11.5, color=INK, line=1.3)
        y2 += hh + 4
    c.rect(lx, yy, lw, 150, fill=GREEN_T, radius=10)
    c.text(lx + 14, yy + 10, lw - 28, 22, "تدريب مباشر ومشاركة الشاشة", size=12.5,
           bold=True, color=GREEN_D, line=1.2)
    c.text(lx + 14, yy + 34, lw - 28, 110, z["practice"], size=11.5,
           color=GREEN_D, line=1.4)
    yy += 162
    # quiz + homework, anchored so the slide always closes on the same line
    qtext = " · ".join(z["quiz"])
    qh = c.measure(qtext, CONTENT_W - 130, size=11.5) + 34
    hh = c.measure(z["homework"], CONTENT_W - 150, size=12) + 30
    hy = BOTTOM - hh
    qy = hy - qh - 10
    if qy < yy:
        qy = yy
        hy = qy + qh + 10
    c.rect(M, qy, CONTENT_W, qh, fill=WHITE, stroke=LINE, radius=8)
    c.text(M + CONTENT_W - 110, qy + 8, 96, 20, "اختبار سريع", size=11, bold=True,
           color=RED, align="right", line=1.1)
    c.text(M + 14, qy + 24, CONTENT_W - 130, qh - 26, qtext, size=11.5, color=INK,
           line=1.35)
    c.rect(M, hy, CONTENT_W, hh, fill=RED_T, radius=8)
    c.text(M + CONTENT_W - 120, hy + 8, 106, 20, "مهمة المتابعة", size=11,
           bold=True, color=RED, align="right", line=1.1)
    c.text(M + 14, hy + 24, CONTENT_W - 140, hh - 26, z["homework"], size=12,
           color=RED_D, line=1.35)
    footer(c, f"الأسبوع {wk['no_ar']}", wk["topic_short"], idx, total)
    c.notes(wk["notes"]["zoom"])
    _fit(c, hy + hh)
    return c

    _fit(c, yy + hh)
    return c


# ---- review / consolidation (weeks 7, 13, 21, 26) ----------------------
def s_review(d, wk, idx, total):
    c, _ = d.new()
    background(c)
    rv = wk["review_slide"]
    y = header(c, rv["title"], kicker="مراجعة شاملة للمرحلة — أسئلة استرجاع من كل مجال",
               sub=rv.get("lead"), chip="مراجعة")
    items = rv["domains"]
    n = len(items)
    gap = 12
    w = (CONTENT_W - gap * (n - 1)) / n
    avail = BOTTOM - y - 4

    def plan(sc):
        csz = 12.5 * sc
        ssz = 10.5 * sc
        rows = [[c.measure(x, w - 26, size=ssz) + 5 for x in subs] for _, subs in items]
        card_h = 46 + max(sum(r) for r in rows)
        qh = [c.measure(q, CONTENT_W - 44, size=csz) + 12 for q in rv["questions"]]
        need = card_h + 18 + sum(qh) + 6 * len(qh)
        return csz, ssz, rows, card_h, qh, need

    sc = _scaled(c, lambda x: plan(x)[5], avail, lo=0.68, hi=1.0)
    csz, ssz, rows, card_h, qh, _need = plan(sc)

    for i, (lab, subs) in enumerate(items):
        x = SLIDE_W - M - w - i * (w + gap)
        c.rect(x, y, w, card_h, fill=PANEL, radius=12)
        accent = [GREEN, RED, GRAY][i % 3]
        c.rect(x, y, w, 5, fill=accent, radius=2)
        c.text(x + 8, y + 15, w - 16, 22, lab, size=12.5, bold=True, color=INK,
               align="center", line=1.2)
        yy = y + 42
        for sub_t, h in zip(subs, rows[i]):
            c.text(x + 13, yy, w - 22, h, "• " + sub_t, size=ssz, color=GRAY,
                   line=1.3)
            yy += h

    yy = y + card_h + 18
    for i, (q, h) in enumerate(zip(rv["questions"], qh), 1):
        c.rect(M, yy, CONTENT_W, h, fill=(WHITE if i % 2 else PANEL), stroke=LINE,
               width=0.7, radius=8)
        number_badge(c, M + CONTENT_W - 22, yy + h / 2, 12, str(i), fill=RED_T,
                     color=RED, size=10.5)
        c.text(M + 14, yy + 6, CONTENT_W - 50, h - 8, q, size=csz, color=INK,
               line=1.35)
        yy += h + 6
    footer(c, f"الأسبوع {wk['no_ar']}", wk["topic_short"], idx, total)
    c.notes(wk["notes"]["review"])
    _fit(c, yy)
    return c


# ---- portfolio / wrap --------------------------------------------------
def s_wrap(d, wk, idx, total):
    c, _ = d.new()
    background(c)
    wr = wk["wrap"]
    y = header(c, wr["title"], kicker=wr.get("kicker", "الختام وحفظ العمل في ملف الإنجاز"),
               sub=wr.get("lead"), chip="ختام")
    lw = CONTENT_W * 0.5
    rw = CONTENT_W - lw - 22
    rx = SLIDE_W - M - rw
    lx = M
    c.rect(rx, y, rw, 230, fill=GREEN_T, radius=12)
    c.text(rx + 16, y + 14, rw - 32, 24, wr["box_title"], size=14, bold=True,
           color=GREEN_D, line=1.2)
    yy = y + 46
    for t in wr["items"]:
        hh = c.measure(t, rw - 46, size=12.5) + 6
        c.circle(rx + rw - 16, yy + 9, 2.8, fill=GREEN)
        c.text(rx + 12, yy, rw - 36, hh, t, size=12.5, color=GREEN_D, line=1.35)
        yy += hh + 5
    c.rect(lx, y, lw, 230, fill=PANEL, radius=12)
    c.text(lx + 16, y + 14, lw - 32, 24, wr["next_title"], size=14, bold=True,
           color=RED, line=1.2)
    c.text(lx + 16, y + 46, lw - 32, 170, wr["next"], size=13, color=INK, line=1.5)
    c.text(M, y + 250, CONTENT_W, 60, wr.get("closing", ""), size=13, color=GRAY,
           align="center", line=1.5)
    footer(c, f"الأسبوع {wk['no_ar']}", wk["topic_short"], idx, total)
    c.notes(wk["notes"]["wrap"])
    return c


LAYOUTS = {
    "cover": s_cover, "warmup": s_warmup, "outcomes": s_outcomes,
    "visual": s_visual, "steps": s_steps, "demo": s_demo, "guided": s_guided,
    "challenge": s_challenge, "mistakes": s_mistakes, "simulation": s_sim,
    "quiz": s_quiz, "zoom": s_zoom, "review": s_review, "wrap": s_wrap,
}


def render(d, wk):
    order = wk.get("order") or [
        "cover", "warmup", "outcomes", "visual", "steps", "demo", "guided",
        "challenge", "mistakes", "simulation", "quiz", "zoom",
    ]
    total = len(order)
    for i, key in enumerate(order, 1):
        LAYOUTS[key](d, wk, i, total)
