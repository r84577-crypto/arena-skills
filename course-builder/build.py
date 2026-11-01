# -*- coding: utf-8 -*-
import os, sys, importlib, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import Deck
import layouts
from notes_builder import build_notes

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "دورة_إدخال_البيانات_ومعالجة_النصوص_معهد_الفاو")
PREVIEW = "/tmp/preview"

def load(no):
    m = importlib.import_module(f"content.w{no:02d}")
    return m.W

def build(no, preview=False):
    W = load(no)
    if not isinstance(W.get("notes"), dict):
        W["notes"] = {}
    generated = build_notes(W)
    for k, v in generated.items():
        W["notes"].setdefault(k, v)
    d = Deck(f"الأسبوع {W['no']:02d} — {W['title']}")
    layouts.render(d, W)
    slug = W["slug"]
    name = f"W{W['no']:02d}_{slug}"
    wdir = os.path.join(OUT, f"W{W['no']:02d}")
    os.makedirs(wdir, exist_ok=True)
    p1 = os.path.join(wdir, name + ".pptx")
    p2 = os.path.join(wdir, name + ".pdf")
    d.save(p1, p2)
    print(f"W{W['no']:02d} slides={d.count} warn={d.warn}")
    return p2, wdir, name

if __name__ == "__main__":
    nos = [int(a) for a in sys.argv[1:]] or [1]
    for n in nos:
        build(n)
