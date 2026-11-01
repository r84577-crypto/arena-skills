# -*- coding: utf-8 -*-
"""يبني ملفات تدريب المتدرب (Word/Excel) مع مفاتيح إجابة منفصلة.

كل المحتوى أصلي من إعداد المعهد، والأسماء والأرقام وهمية للتدريب فقط.
يُشغَّل من مجلد course-builder:  python make_handouts.py
"""
import os

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

import exam
import practice_text

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "دورة_إدخال_البيانات_ومعالجة_النصوص_معهد_الفاو")

FONT = "Noto Sans Arabic"
RED = RGBColor(0xA9, 0x26, 0x2E)
GREEN = RGBColor(0x06, 0x81, 0x4A)
INK = RGBColor(0x18, 0x24, 0x20)
GRAY = RGBColor(0x55, 0x64, 0x5E)
HEAD_FILL = PatternFill("solid", fgColor="06814A")
KEY_FILL = PatternFill("solid", fgColor="E6F2EA")
THIN = Side(style="thin", color="DCE3DF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


# ---------------------------------------------------------------- docx utils
PPR_ORDER = ["w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore",
             "w:framePr", "w:widowControl", "w:numPr", "w:suppressLineNumbers",
             "w:pBdr", "w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku",
             "w:wordWrap", "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE",
             "w:autoSpaceDN", "w:bidi", "w:adjustRightInd", "w:snapToGrid",
             "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents",
             "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment",
             "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr",
             "w:sectPr", "w:pPrChange"]

SECT_ORDER = ["w:footnotePr", "w:endnotePr", "w:type", "w:pgSz", "w:pgMar",
              "w:paperSrc", "w:pgBorders", "w:lnNumType", "w:pgNumType", "w:cols",
              "w:formProt", "w:vAlign", "w:noEndnote", "w:titlePg",
              "w:textDirection", "w:bidi", "w:rtlGutter", "w:docGrid",
              "w:printerSettings", "w:sectPrChange"]

TBL_ORDER = ["w:tblStyle", "w:tblpPr", "w:tblOverlap", "w:bidiVisual",
             "w:tblStyleRowBandSize", "w:tblStyleColBandSize", "w:tblW", "w:jc",
             "w:tblCellSpacing", "w:tblInd", "w:tblBorders", "w:shd",
             "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption",
             "w:tblDescription"]


def _insert_ordered(parent, tag, order):
    """Insert <tag> into parent at its schema position and return it."""
    el = parent.makeelement(qn(tag), {})
    idx = order.index(tag)
    after = {qn(t) for t in order[idx + 1:]}
    for child in list(parent):
        if child.tag in after:
            child.addprevious(el)
            return el
    parent.append(el)
    return el


def _rtl(par):
    par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pPr = par._p.get_or_add_pPr()
    if pPr.find(qn("w:bidi")) is None:
        _insert_ordered(pPr, "w:bidi", PPR_ORDER)


def _run(par, text, size=12, bold=False, color=INK, font=FONT):
    r = par.add_run(text)
    r.font.name = font
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    rPr = r._element.get_or_add_rPr()
    rPr.append(rPr.makeelement(qn("w:rtl"), {}))
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = rPr.makeelement(qn("w:rFonts"), {})
        rPr.append(rFonts)
    rFonts.set(qn("w:cs"), font)
    rFonts.set(qn("w:ascii"), font)
    rFonts.set(qn("w:hAnsi"), font)
    return r


def para(doc, text, size=12, bold=False, color=INK, after=6, before=0, font=FONT):
    p = doc.add_paragraph()
    _rtl(p)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing = 1.3
    _run(p, text, size=size, bold=bold, color=color, font=font)
    return p


def heading(doc, text, color=GREEN, size=14):
    p = doc.add_paragraph()
    _rtl(p)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    _run(p, text, size=size, bold=True, color=color)
    return p


def rule(doc):
    p = doc.add_paragraph()
    _rtl(p)
    pPr = p._p.get_or_add_pPr()
    from docx.oxml import OxmlElement
    bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:color"), "DCE3DF")
    bdr.append(bottom)
    pPr.append(bdr)
    p.paragraph_format.space_after = Pt(4)


def _logo(doc, width_cm=4.2):
    """Official logo image in the document header (image only, never redrawn)."""
    p = doc.add_paragraph()
    _rtl(p)
    p.paragraph_format.space_after = Pt(4)
    p.add_run().add_picture(os.path.join(HERE, "fonts", "logo_t@2x.png"),
                            width=Cm(width_cm))
    return p


def new_doc(header_line, title, subtitle):
    doc = Document()
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.PORTRAIT
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(2.0)
    sec.left_margin = Cm(2.2)
    sec.right_margin = Cm(2.2)
    # RTL section
    sectPr = sec._sectPr
    if sectPr.find(qn("w:bidi")) is None:
        _insert_ordered(sectPr, "w:bidi", SECT_ORDER)
    _logo(doc)
    para(doc, header_line, size=9.5, color=GRAY, after=2)
    para(doc, title, size=20, bold=True, color=RED, after=2)
    para(doc, subtitle, size=10.5, color=GRAY, after=8)
    rule(doc)
    return doc


def table(doc, header, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    # RTL table
    tblPr = t._tbl.tblPr
    if tblPr.find(qn("w:bidiVisual")) is None:
        _insert_ordered(tblPr, "w:bidiVisual", TBL_ORDER)
    hdr = t.rows[0].cells
    for i, h in enumerate(header):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        _rtl(p)
        _run(p, h, size=10.5, bold=True, color=GREEN)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            _rtl(p)
            _run(p, str(v), size=10.5)
    doc.add_paragraph()
    return t


def box(doc, title, lines, color=GREEN):
    heading(doc, title, color=color)
    for ln in lines:
        para(doc, "• " + ln, size=10.5, after=2)


# ---------------------------------------------------------------- Word files
def w16(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 16 — ورقة تدريب: تنسيق الخط",
                  "المدرّب: الأستاذ عادل الحربي · تدريبات أصلية من إعداد المعهد · بيانات وهمية")
    heading(doc, "1) النص كما وصل إليك (غير منسق)")
    para(doc, "محاضرة تدريبية", size=12)
    para(doc, "يقدّم المعهد محاضرة قصيرة عن مهارات العرض، يوم الأحد القادم، في قاعة التدريب الرئيسية.", size=12)
    para(doc, "الحضور مجانًا لجميع المتدربين المسجلين في الدورة.", size=12)
    para(doc, "اسم المحاضر: الأستاذ عادل الحربي.", size=12)
    heading(doc, "2) المطلوب — نفّذ الخطوات بالترتيب")
    for i, s in enumerate([
        "احفظ الملف باسم «إعلان_المحاضرة» داخل مجلد الأسبوع 16.",
        "اجعل السطر «محاضرة تدريبية» عنوانًا: حجم 28، غامق، لون أحمر داكن.",
        "اجعل الأسطر الثلاثة التالية حجم 14، وخطًا واحدًا لجميعها.",
        "اجعل كلمة «مجانًا» غامقة ومظللة.",
        "اجعل اسم المحاضر مائلًا.",
        "اضبط تباعد الأسطر على 1.15 إن كان متاحًا.",
    ], 1):
        para(doc, f"{i}) {s}", size=11, after=4)
    heading(doc, "3) مواصفات التنسيق (اقرأها قبل البدء)")
    table(doc,
          ["العنصر", "الحجم", "التأكيد", "اللون"],
          [["العنوان", "28", "غامق", "أحمر داكن"],
           ["النص الأساسي", "14", "عادي", "أسود"],
           ["كلمة «مجانًا»", "كما هي", "غامق + تظليل", "تظليل أصفر خفيف"],
           ["اسم المحاضر", "14", "مائل", "أسود"]])
    heading(doc, "4) تدريب التصحيح")
    para(doc, "هذا النص نسخه زميل من صفحة إنترنت، وفيه تنسيقات مختلفة. حدّده كاملًا ثم امسح التنسيق بـ Ctrl+Space، وأعد تنسيقه بالخط نفسه وبحجم 12.", size=11)
    table(doc,
          ["السطر", "التنسيق الحالي"],
          [["تعريف قصير بالمعمل", "خط كبير ولون أزرق"],
           ["مواعيد العمل", "خط صغير جدًا"],
           ["رقم القاعة", "تسطير وغامق"]])
    heading(doc, "5) قائمة تحقق قبل التسليم")
    for s in ["العنوان بالحجم واللون المطلوبين.",
              "كل النص الأساسي بالحجم 14 والخط نفسه.",
              "كلمة واحدة فقط مظللة في المستند (أو كلمتان كما في المواصفات).",
              "اسم الملف صحيح وموجود في مجلد الأسبوع 16.",
              "لم يتبقَّ أي نص بتنسيق قديم بعد مسح التنسيق."]:
        para(doc, "☐ " + s, size=11, after=3)
    para(doc, "ملاحظة: هذه ورقة تدريب داخلية من إعداد المعهد، ولا تُستخدم كأسئلة اختبار رسمي.", size=9, color=GRAY, before=8)
    doc.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.docx"))


def w16_key(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 16 — مفتاح الإجابة: تنسيق الخط (للمدرّب فقط)",
                  "ملف منفصل عن ورقة المتدرب · لا يُوزَّع على المتدربين")
    heading(doc, "1) التنسيق المطلوب — الحل النموذجي")
    table(doc,
          ["العنصر", "كيف يُنفَّذ", "ملاحظة للمدرّب"],
          [["العنوان", "تحديد السطر ← حجم 28 ← Ctrl+B ← لون أحمر داكن", "اللون الغامق يضمن الوضوح عند الطباعة"],
           ["النص الأساسي", "تحديد الأسطر ← حجم 14 ← خط Noto Sans Arabic للجميع", "لا تسمح بأكثر من خط واحد"],
           ["كلمة «مجانًا»", "تحديد الكلمة فقط ← Ctrl+B ← أداة تظليل النص", "التظليل يبدأ وينتهي داخل الكلمة"],
           ["اسم المحاضر", "تحديد الاسم ← Ctrl+I", "المائل لا يُستخدم في النص الطويل"]])
    heading(doc, "2) الحل النموذجي لتدريب التصحيح")
    para(doc, "تحديد النص كاملًا ← Ctrl+Space لمسح التنسيق ← ضبط حجم 12 ← اختيار خط واحد ← إعادة تظليل الكلمة المطلوبة فقط.", size=11)
    para(doc, "الخطأ المتوقع: مسح التنسيق عن سطر واحد فقط ثم إعادة تنسيق السطر التالي يدويًا؛ اسأل المتدرب: هل يمكن تحديد كل النص مرة واحدة؟", size=11, color=GRAY)
    heading(doc, "3) معايير التقييم (تدريبية داخل الدورة)")
    table(doc,
          ["المعيار", "مقبول", "يحتاج إعادة"],
          [["حجم العنوان", "24 إلى 28", "أقل من 18 أو مساوٍ للنص"],
           ["عدد الخطوط", "خط واحد", "خطان أو أكثر"],
           ["عدد الألوان", "لونان كحد أقصى", "ثلاثة ألوان أو أكثر"],
           ["التظليل", "على كلمة أو كلمتين فقط", "على سطر كامل أو فقرة"]])
    heading(doc, "4) أخطاء شائعة وحلولها")
    for s in ["تحديد غير كامل: التنسيق يُطبَّق على جزء من الكلمة.",
              "تنسيق قبل التحديد: يُطبَّق على الكتابة التالية.",
              "نسيان مسح التنسيق القديم بعد اللصق.",
              "استخدام الغامق والمائل والتسطير في السطر نفسه."]:
        para(doc, "• " + s, size=11, after=2)
    heading(doc, "5) المصدر")
    para(doc, "Microsoft Support — صفحة «تغيير الخط وحجمه ولونه في Word» — تم الاطلاع عليها في 1 نوفمبر 2026.", size=10, color=GRAY)
    para(doc, "أسماء الأدوات قد تختلف قليلًا بحسب إصدار Office؛ يُرجى اعتماد المصدر الرسمي عند الحاجة إلى تدقيق نهائي.", size=9.5, color=GRAY)
    doc.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.docx"))


def w17(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 17 — ورقة تدريب: اتجاه النص والمحاذاة",
                  "المدرّب: الأستاذ عادل الحربي · تدريبات أصلية من إعداد المعهد")
    heading(doc, "1) التمرين الأول: فقرة عربية وفقرة إنجليزية")
    para(doc, "اكتب الفقرة العربية التالية بخط 14، واضبط اتجاهها إلى اليمين ومحاذاتها إلى اليمين:", size=11)
    para(doc, "يقدّم معمل الحاسب خدمة الطباعة للمتدربين من الأحد إلى الخميس، ويُشترط إحضار بطاقة المتدرب.", size=12)
    para(doc, "ثم اكتب تحتها باللغة الإنجليزية:", size=11)
    para(doc, "Computer Lab Printing Service — Sunday to Thursday.", size=12, font="DejaVu Sans")
    heading(doc, "2) جدول الحالات — ضع علامة في العمود المناسب")
    table(doc,
          ["الحالة", "زر الاتجاه RTL", "زر المحاذاة", "الحل الصحيح"],
          [["فقرة عربية تظهر في يسار الصفحة", "", "", ""],
           ["نقطة في بداية السطر العربي", "", "", ""],
           ["فقرة إنجليزية محاذاة يمين", "", "", ""],
           ["سطور قصيرة متباعدة في فقرة مضبوطة", "", "", ""]])
    heading(doc, "3) المطلوب")
    for s in ["احفظ الملف باسم «اتجاه_ومحاذاة» في مجلد الأسبوع 17.",
              "اضبط اتجاه كل فقرة بحسب لغتها.",
              "استخدم «ضبط» في فقرة واحدة فقط وجرّب الفرق.",
              "أعد الفقرة العربية إلى المحاذاة اليمنى قبل الحفظ."]:
        para(doc, "• " + s, size=11, after=3)
    heading(doc, "4) قائمة تحقق")
    for s in ["كل فقرة عربية باتجاه RTL.", "علامات الترقيم في نهاية الجمل لا بدايتها.",
              "الفقرة الإنجليزية باتجاه LTR.", "«ضبط» مستخدم في فقرة واحدة فقط."]:
        para(doc, "☐ " + s, size=11, after=3)
    doc.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.docx"))


def w17_key(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 17 — مفتاح الإجابة: الاتجاه والمحاذاة (للمدرّب فقط)",
                  "ملف منفصل عن ورقة المتدرب · لا يُوزَّع على المتدربين")
    heading(doc, "1) جدول الحالات — الإجابات النموذجية")
    table(doc,
          ["الحالة", "التشخيص", "الإجراء"],
          [["فقرة عربية في يسار الصفحة", "محاذاة يسار أو اتجاه LTR", "اتجاه RTL ثم محاذاة يمين"],
           ["نقطة في بداية السطر", "اتجاه الفقرة معاكس", "RTL ثم كتابة النقطة في النهاية"],
           ["فقرة إنجليزية محاذاة يمين", "اتجاه أو محاذاة عربية", "LTR ثم محاذاة يسار"],
           ["سطور متباعدة في فقرة مضبوطة", "الضبط لا يناسب النص القصير", "محاذاة يمين بدل الضبط"]])
    heading(doc, "2) معيار التقييم (تدريبي)")
    for s in ["الفقرة العربية: اتجاه RTL + محاذاة يمين.",
              "الفقرة الإنجليزية: اتجاه LTR + محاذاة يسار.",
              "علامات الترقيم في نهايات الجمل.",
              "استخدام الضبط في فقرة واحدة كتجربة فقط."]:
        para(doc, "• " + s, size=11, after=2)
    heading(doc, "3) صعوبات متوقعة")
    for s in ["الخلط بين الزرين لأنهما متجاوران في الشريط.",
              "تغيير المحاذاة فقط ثم توقّع أن يتحسن الاتجاه.",
              "نسيان أن التنسيق يُطبَّق على الفقرة كلها."]:
        para(doc, "• " + s, size=11, after=2)
    heading(doc, "4) المصدر")
    para(doc, "Microsoft Support — «ضبط اتجاه النص ومحاذاته في Word» — تم الاطلاع عليها في 1 نوفمبر 2026.", size=10, color=GRAY)
    doc.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.docx"))


def w18(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 18 — ورقة تدريب: القوائم النقطية والرقمية",
                  "المدرّب: الأستاذ عادل الحربي · تدريبات أصلية من إعداد المعهد")
    heading(doc, "1) مستلزماتي اليومية")
    para(doc, "المطلوب: قائمة نقطية بأربعة عناصر. اكتبها في المكان التالي:", size=11)
    for _ in range(4):
        para(doc, "• ________________________________________", size=12, after=6)
    heading(doc, "2) خطوات بدء العمل في المعمل")
    para(doc, "المطلوب: قائمة رقمية بثلاث خطوات مرتبة. الترتيب مهم هنا.", size=11)
    for _ in range(3):
        para(doc, "____ . __________________________________", size=12, after=6)
    heading(doc, "3) تصحيح قائمة")
    para(doc, "القائمة التالية نسخها زميل من ملف قديم؛ الترقيم يبدأ من 4 والنقاط في الجهة اليسرى. أصلحها.", size=11)
    table(doc,
          ["الترقيم الحالي", "النص"],
          [["4", "افتح البرنامج"], ["5", "أنشئ ملفًا جديدًا"], ["6", "احفظ الملف"]])
    heading(doc, "4) المطلوب")
    for s in ["احفظ الملف باسم «قوائمي» في مجلد الأسبوع 18.",
              "اضبط اتجاه الفقرات إلى اليمين قبل إنشاء القوائم.",
              "أضف عنصرًا في منتصف القائمة النقطية.",
              "احذف خطوة من القائمة الرقمية وتحقق من إعادة الترقيم تلقائيًا.",
              "أصلح ترقيم القائمة الثالثة ليبدأ من 1."]:
        para(doc, "• " + s, size=11, after=3)
    heading(doc, "5) قائمة تحقق")
    for s in ["قائمة نقطية بأربعة عناصر.", "قائمة رقمية بثلاث خطوات.", "الترقيم يبدأ من 1.",
              "النقاط والأرقام على يمين السطر.", "لا خلط بين النقطي والرقمي في قائمة واحدة."]:
        para(doc, "☐ " + s, size=11, after=3)
    doc.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.docx"))


def w18_key(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 18 — مفتاح الإجابة: القوائم (للمدرّب فقط)",
                  "ملف منفصل عن ورقة المتدرب · لا يُوزَّع على المتدربين")
    heading(doc, "1) الأجوبة النموذجية")
    table(doc,
          ["المهمة", "الإجابة", "ملاحظة"],
          [["قائمة المستلزمات", "نقطية (Bullets)", "العناصر غير مرتبة"],
           ["خطوات العمل", "رقمية (Numbering)", "الترتيب إلزامي"],
           ["إصلاح ترقيم يبدأ من 4", "زر الفأرة الأيمن ← «إعادة بدء الترقيم من 1»", "أو «تعيين قيمة الترقيم»"],
           ["نقاط على اليسار", "اتجاه الفقرة غير مضبوط", "RTL قبل إنشاء القائمة"]])
    heading(doc, "2) معيار التقييم (تدريبي)")
    for s in ["نوع القائمة مناسب للمحتوى.",
              "الترقيم يبدأ من 1 بعد الإصلاح.",
              "النقاط على يمين النص.",
              "إضافة عنصر في المنتصف لا تُفسد الترتيب."]:
        para(doc, "• " + s, size=11, after=2)
    heading(doc, "3) اختصارات مفيدة")
    para(doc, "Enter لسطر جديد داخل القائمة · Tab لمستوى أعمق · Shift+Tab لمستوى أعلى · Enter مرتين لإنهاء القائمة.", size=11)
    heading(doc, "4) المصدر")
    para(doc, "Microsoft Support — «إنشاء قائمة نقطية أو مرقمة في Word» — تم الاطلاع عليها في 1 نوفمبر 2026.", size=10, color=GRAY)
    doc.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.docx"))


def w19(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 19 — ورقة تدريب: الجداول في Word",
                  "المدرّب: الأستاذ عادل الحربي · بيانات وهمية للتدريب · تدريبات أصلية")
    heading(doc, "1) بيانات التدريب (انسخها في جدول)")
    para(doc, "أنشئ جدولًا بأربعة أعمدة وثلاثة صفوف، وضع فيه البيانات التالية كما هي:", size=11)
    table(doc,
          ["المتدرب", "المادة", "الدرجة", "التقدير"],
          [["خالد", "حاسب", "88", "جيد جدًا"],
           ["فهد", "حاسب", "75", "جيد"],
           ["عمر", "حاسب", "92", "ممتاز"]])
    heading(doc, "2) بيانات إضافية — أضف صفًا")
    table(doc,
          ["المتدرب", "المادة", "الدرجة", "التقدير"],
          [["سعد", "حاسب", "64", "مقبول"]])
    heading(doc, "3) مواعيد لقاءات الأسبوع")
    para(doc, "المطلوب: جدول ثانٍ بثلاثة أعمدة وثلاثة صفوف، واملأه بما يلي:", size=11)
    table(doc,
          ["اليوم", "الوقت", "القاعة"],
          [["الأحد", "5:00 م", "قاعة 1"],
           ["الاثنين", "5:00 م", "معمل الحاسب"],
           ["الثلاثاء", "7:00 م", "Zoom"]])
    heading(doc, "4) المطلوب")
    for s in ["احفظ الملف باسم «جدول_المتدربين» في مجلد الأسبوع 19.",
              "اضبط اتجاه الصفحة إلى اليمين.",
              "أضف صف سعد في المنتصف (بين فهد وعمر).",
              "نسّق صف العنوان: غامق + تعبئة لون خفيفة + محاذاة وسط.",
              "تأكد أن الجدول لا يخرج عن حدود الصفحة."]:
        para(doc, "• " + s, size=11, after=3)
    heading(doc, "5) قائمة تحقق")
    for s in ["عناوين الأعمدة مكتوبة في الصف الأول.", "خلية واحدة = معلومة واحدة.",
              "صف العنوان منسّق ومميز.", "البيانات مطابقة تمامًا للأرقام المطلوبة."]:
        para(doc, "☐ " + s, size=11, after=3)
    doc.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.docx"))


def w19_key(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 19 — مفتاح الإجابة: الجداول (للمدرّب فقط)",
                  "ملف منفصل عن ورقة المتدرب · لا يُوزَّع على المتدربين")
    heading(doc, "1) الجدول النموذجي بعد الإضافة")
    table(doc,
          ["المتدرب", "المادة", "الدرجة", "التقدير"],
          [["خالد", "حاسب", "88", "جيد جدًا"],
           ["فهد", "حاسب", "75", "جيد"],
           ["سعد", "حاسب", "64", "مقبول"],
           ["عمر", "حاسب", "92", "ممتاز"]])
    heading(doc, "2) معيار التقييم (تدريبي)")
    for s in ["أربعة أعمدة وثلاثة صفوف على الأقل.", "صف عنوان واضح وجميع الخلايا مملوءة.",
              "بيانات سعد في المنتصف لا في النهاية.", "صف العنوان غامق ومحاذى وسط."]:
        para(doc, "• " + s, size=11, after=2)
    heading(doc, "3) أخطاء متوقعة")
    for s in ["إدخال درجة واسم في خلية واحدة.", "البدء بالبيانات قبل صف العنوان.",
              "جدول يتجاوز عرض الصفحة بسبب عمود عريض."]:
        para(doc, "• " + s, size=11, after=2)
    heading(doc, "4) المصدر")
    para(doc, "Microsoft Support — «إدراج جدول وتنسيقه في Word» — تم الاطلاع عليها في 1 نوفمبر 2026.", size=10, color=GRAY)
    doc.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.docx"))


def w20(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 20 — ورقة تدريب: الأشكال ومربعات النص",
                  "المدرّب: الأستاذ عادل الحربي · تدريبات أصلية من إعداد المعهد")
    heading(doc, "1) نص الإعلان (استخدمه كما هو)")
    para(doc, "ورشة عمل: مهارات العرض", size=13)
    para(doc, "يقدّم المعهد ورشة قصيرة يوم الأحد في قاعة التدريب. الحضور مجاني للمسجلين في الدورة.", size=11)
    heading(doc, "2) المطلوب")
    for s in ["احفظ الملف باسم «إعلاني_البصري» في مجلد الأسبوع 20.",
              "أدرج مستطيلًا أعلى الصفحة واكتب فيه: «ورشة عمل الأحد».",
              "غيّر تعبئة المستطيل إلى لون هادئ، وحدوده إلى لون داكن واضح.",
              "أدرج مربع نص أسفل الإعلان واكتب فيه: «القاعة: معمل الحاسب — الدور الأول».",
              "تأكد أن العنصرين لا يغطيان النص، واستخدم «خلف النص» إن لزم."]:
        para(doc, "• " + s, size=11, after=3)
    heading(doc, "3) مخطط الخطوات")
    para(doc, "ارسم ثلاثة أشكال متجاورة (من اليمين إلى اليسار) لكل خطوة، وضع بينها سهمًا أو سهمين يوضحان الترتيب:", size=11)
    table(doc,
          ["الخطوة", "النص داخل الشكل"],
          [["1", "املأ نموذج التسجيل"],
           ["2", "سلّم النموذج في الاستقبال"],
           ["3", "استلم بطاقة المتدرب"]])
    heading(doc, "4) قائمة تحقق")
    for s in ["لا يوجد نص مخفي خلف شكل.", "لكل شكل رسالة واحدة واضحة.",
              "اتجاه النص داخل الأشكال إلى اليمين.", "عدد الأشكال في المخطط ثلاثة فقط."]:
        para(doc, "☐ " + s, size=11, after=3)
    doc.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.docx"))


def w20_key(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 20 — مفتاح الإجابة: الأشكال (للمدرّب فقط)",
                  "ملف منفصل عن ورقة المتدرب · لا يُوزَّع على المتدربين")
    heading(doc, "1) الحل النموذجي")
    for s in ["مستطيل أعلى الصفحة بعرض مناسب (لا يغطي نصًا)، ونصه «ورشة عمل الأحد».",
              "مربع نص أسفل الصفحة بمحتوى القاعة، وحدود واضحة.",
              "ثلاثة أشكال متجاورة من اليمين إلى اليسار مع سهمين.",
              "كل نص داخل الشكل بخط موحد وحجم 11 أو 12.",
              " أي عنصر يغطي نصًا: «خلف النص» أو تصغير العنصر."]:
        para(doc, "• " + s, size=11, after=2)
    heading(doc, "2) معيار التقييم (تدريبي)")
    table(doc,
          ["المعيار", "مقبول", "يحتاج إعادة"],
          [["عدد الأشكال", "ثلاثة في المخطط", "أربعة أو أكثر"],
           ["تغطية النص", "لا يوجد نص مخفي", "نص غير مقروء خلف عنصر"],
           ["الاتجاه", "عربي داخل كل شكل", "نص عكسي في شكل واحد أو أكثر"]])
    heading(doc, "3) أسئلة مساندة")
    para(doc, "ما وظيفة «أمام النص» و«خلف النص»؟ متى نستخدم WordArt؟ كيف نُعيد ترتيب العناصر في آن واحد؟", size=11)
    heading(doc, "4) المصدر")
    para(doc, "Microsoft Support — «إدراج الأشكال ومربعات النص في Word» — تم الاطلاع عليها في 1 نوفمبر 2026.", size=10, color=GRAY)
    doc.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.docx"))


def w21(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 21 — ورقة تدريب: إعلان المعمل (مهمة Word المتكاملة)",
                  "المدرّب: الأستاذ عادل الحربي · تدريبات أصلية من إعداد المعهد")
    heading(doc, "1) المطلوب — صفحة واحدة تجمع كل المهارات")
    para(doc, "المعهد يحتاج إعلانًا من صفحة واحدة عن مواعيد معمل الحاسب يُطبع ويُعلّق على الباب.", size=11)
    for s in ["احفظ الملف باسم «إعلان_المعمل_الأسبوع21» في مجلد الأسبوع 21.",
              "العنوان: «مواعيد معمل الحاسب» بحجم 24، غامق، لون داكن.",
              "فقرة تعريفية من ثلاثة أسطر، بخط 12 أو 14.",
              "قائمة نقطية بأربعة عناصر للمواعيد.",
              "جدول بثلاثة صفوف وثلاثة أعمدة: اليوم، الوقت، العدد المتاح.",
              "مربع نص فيه ملاحظة واحدة فقط: «إحضار بطاقة المتدرب إلزامي».",
              "هوامش مضبوطة، ومعاينة سريعة قبل الحفظ."]:
        para(doc, "• " + s, size=11, after=3)
    heading(doc, "2) بيانات الجدول")
    table(doc,
          ["اليوم", "الوقت", "العدد المتاح"],
          [["الأحد", "5:00 م", "12"],
           ["الاثنين", "5:00 م", "12"],
           ["الثلاثاء", "7:00 م", "10"]])
    heading(doc, "3) قائمة تحقق قبل التسليم")
    for s in ["المستند في صفحة واحدة فقط.", "العنوان أكبر من النص الأساسي بوضوح.",
              "القائمة والجدول منسقان.", "لا يوجد عنصر بصري يغطي نصًا.",
              "الهوامش مضبوطة والملف مسمّى بشكل صحيح."]:
        para(doc, "☐ " + s, size=11, after=3)
    doc.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.docx"))


def w21_key(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 21 — مفتاح الإجابة: مهمة Word المتكاملة (للمدرّب فقط)",
                  "ملف منفصل عن ورقة المتدرب · لا يُوزَّع على المتدربين")
    heading(doc, "1) النموذج المرجعي للترتيب")
    table(doc,
          ["العنصر", "المواصفة", "وزن الملاحظة"],
          [["العنوان", "24 غامق لون داكن", "أساسي"],
           ["الفقرة", "3 أسطر، 12 إلى 14، RTL", "أساسي"],
           ["القائمة", "نقطية بأربعة عناصر", "أساسي"],
           ["الجدول", "3×3 مع صف عنوان", "أساسي"],
           ["مربع النص", "ملاحظة واحدة فقط", "أساسي"],
           ["الهوامش", "افتراضية أو مخصصة بحدود معقولة", "ثانوي"]])
    heading(doc, "2) معيار التقييم (تدريبي داخل الدورة)")
    for s in ["بقاء المستند في صفحة واحدة.",
              "وضوح العنوان من مسافة متر تقريبًا.",
              "عدم تغطية أي عنصر بصري للنص.",
              "وجود العناصر الخمسة كاملة."]:
        para(doc, "• " + s, size=11, after=2)
    heading(doc, "3) أخطاء متوقعة")
    for s in ["الجدول يعرض 3 صفوف بلا صف عنوان.", "مربع النص يغطي الفقرة.",
              "مستند من صفحتين بسبب حجم خط كبير أو أسطر فارغة."]:
        para(doc, "• " + s, size=11, after=2)
    heading(doc, "4) المصدر")
    para(doc, "Microsoft Support — «ضبط هوامش الصفحة ومعاينة الطباعة في Word» — تم الاطلاع عليها في 1 نوفمبر 2026.", size=10, color=GRAY)
    doc.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.docx"))


# --------------------------------------------------------------- Excel files
def _sheet_setup(ws, rtl=True):
    ws.sheet_view.rightToLeft = rtl
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def _title(ws, row, text, span=6):
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(name=FONT, size=13, bold=True, color="A9262E")
    c.alignment = Alignment(horizontal="right", readingOrder=2)


def _header(ws, row, values):
    for i, v in enumerate(values, 1):
        c = ws.cell(row=row, column=i, value=v)
        c.font = Font(name=FONT, size=11, bold=True, color="FFFFFF")
        c.fill = HEAD_FILL
        c.alignment = Alignment(horizontal="center", vertical="center",
                                readingOrder=2)
        c.border = BORDER
    ws.row_dimensions[row].height = 22


def _data(ws, row, values, fills=None):
    for i, v in enumerate(values, 1):
        c = ws.cell(row=row, column=i, value=v)
        c.font = Font(name=FONT, size=11, color="182420")
        c.alignment = Alignment(horizontal="center", vertical="center",
                                readingOrder=2)
        c.border = BORDER
        if fills and i in fills:
            c.fill = fills[i]


def _widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def _put(ws, row, col, value, fmt=None):
    """Write a cell value (with an optional number format).

    Strings that start with "=" become real Excel formulas, so the trainer's key
    file recalculates if the sample data is edited.
    """
    c = ws.cell(row=row, column=col, value=value)
    if fmt:
        c.number_format = fmt
    return c


def w22(outdir):
    wb = Workbook()
    ws = wb.active
    ws.title = "بياناتي"
    _sheet_setup(ws)
    _title(ws, 1, "الأسبوع 22 — ورقة تدريب: أول مصنّف (بيانات وهمية)")
    ws.cell(row=2, column=1,
            value="البيانات أدناه وهمية للتدريب. أضف صفًا خامسًا باسم متدرب وهمي آخر، وأكمل بقية الخطوات.").font = Font(
        name=FONT, size=10, color="55645E")
    _header(ws, 4, ["المتدرب", "المادة", "الدرجة", "التقدير"])
    rows = [("خالد", "حاسب", 88, "جيد جدًا"),
            ("فهد", "حاسب", 75, "جيد"),
            ("عمر", "حاسب", 92, "ممتاز"),
            ("سعد", "حاسب", 64, "مقبول")]
    r = 5
    for row in rows:
        _data(ws, r, list(row))
        r += 1
    ws.cell(row=r + 1, column=1, value="المطلوب: انتقل إلى الخلية A10 بصندوق الاسم، واكتب فيها كلمة «إضافي».").font = Font(
        name=FONT, size=10, color="06814A")
    ws.cell(row=r + 2, column=1, value="ثم انسخ النطاق A4:D9 إلى الورقة الثانية (Sheet2).").font = Font(
        name=FONT, size=10, color="06814A")
    _widths(ws, [18, 14, 12, 16])
    ws2 = wb.create_sheet("Sheet2")
    _sheet_setup(ws2)
    ws2.cell(row=1, column=1, value="الصق النسخة هنا").font = Font(name=FONT, size=11, color="55645E")
    _widths(ws2, [18, 14, 12, 16])
    wb.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.xlsx"))


def w22_key(outdir):
    wb = Workbook()
    ws = wb.active
    ws.title = "الحل"
    _sheet_setup(ws)
    _title(ws, 1, "الأسبوع 22 — مفتاح الإجابة (للمدرّب فقط)")
    _header(ws, 3, ["المتدرب", "المادة", "الدرجة", "التقدير"])
    rows = [("خالد", "حاسب", 88, "جيد جدًا"), ("فهد", "حاسب", 75, "جيد"),
            ("عمر", "حاسب", 92, "ممتاز"), ("سعد", "حاسب", 64, "مقبول")]
    r = 4
    for row in rows:
        _data(ws, r, list(row))
        r += 1
    ws.cell(row=9, column=1, value="إضافي (الخلية A10)").font = Font(name=FONT, size=11, color="182420")
    ws.cell(row=11, column=1, value="الخلية A10 تقع أسفل جدول البيانات، وهي المطلوبة في ورقة المتدرب.").font = Font(name=FONT, size=10, color="55645E")
    _widths(ws, [18, 14, 14, 16])
    wb.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.xlsx"))


def w23(outdir):
    wb = Workbook()
    ws = wb.active
    ws.title = "حضور"
    _sheet_setup(ws)
    _title(ws, 1, "الأسبوع 23 — ورقة تدريب: الحضور والدرجات")
    ws.cell(row=2, column=1, value="المطلوب: اضبط نوع البيانات وتنسيق الأرقام وعرض الأعمدة.").font = Font(
        name=FONT, size=10, color="55645E")
    _header(ws, 4, ["المتدرب", "الدرجة", "نسبة الحضور", "التقدير"])
    rows = [("خالد", 88, 0.95, "جيد جدًا"),
            ("فهد", 75, 0.80, "جيد"),
            ("عمر", 92, 1.00, "ممتاز"),
            ("سعد", 64, 0.65, "مقبول")]
    r = 5
    for name, deg, att, gr in rows:
        _data(ws, r, [name, deg, att, gr])
        ws.cell(row=r, column=3).number_format = "0.00"
        r += 1
    # صف تدريب إضافي فيه خطأ إدخال مقصود (ضمن الجدول نفسه)
    hr = r + 1
    _data(ws, hr, ["نورة", " 81", 0.75, "جيد"])
    ws.cell(row=hr, column=2).number_format = "@"
    ws.cell(row=hr, column=2).alignment = Alignment(horizontal="left")
    ws.cell(row=hr, column=1).fill = PatternFill("solid", fgColor="FCF3E2")
    r = hr
    ws.cell(row=r + 2, column=1, value="المطلوب: 1) حوّل درجة نورة المكتوبة كنص إلى رقم. 2) نسب الحضور مكتوبة كأرقام عشرية؛ اضبطها على النسبة المئوية. 3) وسّع الأعمدة تلقائيًا.").font = Font(
        name=FONT, size=10, color="06814A")
    _widths(ws, [16, 12, 16, 16])
    wb.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.xlsx"))


def w23_key(outdir):
    wb = Workbook()
    ws = wb.active
    ws.title = "الحل"
    _sheet_setup(ws)
    _title(ws, 1, "الأسبوع 23 — مفتاح الإجابة (للمدرّب فقط)")
    _header(ws, 3, ["المتدرب", "الدرجة", "نسبة الحضور", "التقدير"])
    rows = [("خالد", 88, 0.95, "جيد جدًا"), ("فهد", 75, 0.80, "جيد"),
            ("عمر", 92, 1.00, "ممتاز"), ("سعد", 64, 0.65, "مقبول"),
            ("نورة", 81, 0.75, "جيد")]
    r = 4
    for name, deg, att, gr in rows:
        _data(ws, r, [name, deg, att, gr])
        ws.cell(row=r, column=2).number_format = "0"
        ws.cell(row=r, column=3).number_format = "0%"
        r += 1
    ws.cell(row=r + 1, column=1, value="تصحيح نورة: الدرجة 81 برقم لا نص، والحضور 75% بالتنسيق النسبي.").font = Font(
        name=FONT, size=10, color="55645E")
    _widths(ws, [16, 12, 16, 16])
    wb.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.xlsx"))


def w24(outdir):
    wb = Workbook()
    ws = wb.active
    ws.title = "درجات"
    _sheet_setup(ws)
    _title(ws, 1, "الأسبوع 24 — ورقة تدريب: المجموع والمتوسط (بيانات وهمية)")
    ws.cell(row=2, column=1, value="المطلوب: اكتب صيغة الجمع في الخلية B11 وصيغة المتوسط في B12، ثم نسبة كل درجة من المجموع في العمود C.").font = Font(
        name=FONT, size=10, color="55645E")
    _header(ws, 4, ["المتدرب", "الدرجة", "النسبة من المجموع"])
    names = ["خالد", "فهد", "عمر", "سعد", "نورة"]
    degs = [88, 75, 92, 64, 81]
    r = 5
    for n, d in zip(names, degs):
        _data(ws, r, [n, d, ""])
        r += 1
    _data(ws, 10, ["المجموع", "", ""], fills={1: KEY_FILL})
    _data(ws, 11, ["المتوسط", "", ""], fills={1: KEY_FILL})
    ws.cell(row=14, column=1, value="تذكير: تبدأ كل صيغة بعلامة يساوي، وقد تكون فاصلة الوسائط (,) أو (;) بحسب منطقة الجهاز.").font = Font(
        name=FONT, size=10, color="06814A")
    _widths(ws, [18, 14, 20])
    wb.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.xlsx"))


def w24_key(outdir):
    wb = Workbook()
    ws = wb.active
    ws.title = "الحل"
    _sheet_setup(ws)
    _title(ws, 1, "الأسبوع 24 — مفتاح الإجابة (للمدرّب فقط)")
    _header(ws, 3, ["المتدرب", "الدرجة", "الصيغة المستخدمة"])
    names = ["خالد", "فهد", "عمر", "سعد", "نورة"]
    degs = [88, 75, 92, 64, 81]
    r = 4
    for n, d in zip(names, degs):
        _data(ws, r, [n, d, "B%d/SUM($B$4:$B$8)" % r])
        ws.cell(row=r, column=3).alignment = Alignment(
            horizontal="center", vertical="center", readingOrder=2)
        r += 1
    _data(ws, 9, ["المجموع", 400, "SUM(B4:B8)"], fills={1: KEY_FILL, 3: KEY_FILL})
    _data(ws, 10, ["المتوسط", 80, "AVERAGE(B4:B8)"], fills={1: KEY_FILL, 3: KEY_FILL})
    ws.cell(row=12, column=1, value="المجموع 400 والمتوسط 80 صحيحان لهذه القيم الوهمية. النسب: 22% و18.75% و23% و16% و20.25%.").font = Font(
        name=FONT, size=10, color="55645E")
    ws.cell(row=13, column=1, value="الصيغ مكتوبة في العمود الثالث كنص للعرض والنسخ؛ النتائج المحسوبة بجانبها هي المتوقعة من المتدربين.").font = Font(
        name=FONT, size=10, color="06814A")
    _widths(ws, [18, 22, 28])
    wb.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.xlsx"))


def w25(outdir):
    wb = Workbook()
    ws = wb.active
    ws.title = "درجات"
    _sheet_setup(ws)
    _title(ws, 1, "الأسبوع 25 — ورقة تدريب: الترتيب والتصفية والمخطط")
    ws.cell(row=2, column=1, value="المطلوب: رتّب الدرجات تنازليًا، صفِّ من حصل على 80 أو أكثر، ثم أنشئ مخطط أعمدة.").font = Font(
        name=FONT, size=10, color="55645E")
    _header(ws, 4, ["المتدرب", "المادة", "الدرجة"])
    rows = [("خالد", "حاسب", 88), ("فهد", "حاسب", 75), ("عمر", "حاسب", 92),
            ("سعد", "حاسب", 64), ("نورة", "حاسب", 81), ("ريم", "حاسب", 70)]
    r = 5
    for row in rows:
        _data(ws, r, list(row))
        r += 1
    ws.cell(row=r + 1, column=1, value="أسئلة التفكير: من الأعلى؟ من الأدنى؟ كم متدربًا حقق 80 أو أكثر؟").font = Font(
        name=FONT, size=10, color="06814A")
    _widths(ws, [16, 14, 12])
    wb.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.xlsx"))


def w25_key(outdir):
    wb = Workbook()
    ws = wb.active
    ws.title = "الحل"
    _sheet_setup(ws)
    _title(ws, 1, "الأسبوع 25 — مفتاح الإجابة (للمدرّب فقط)")
    _header(ws, 3, ["المتدرب", "المادة", "الدرجة", "ملاحظة"])
    rows = [("عمر", "حاسب", 92, "الأعلى"),
            ("خالد", "حاسب", 88, "حقق 80 أو أكثر"),
            ("نورة", "حاسب", 81, "حققت 80 أو أكثر"),
            ("فهد", "حاسب", 75, "أقل من 80"),
            ("ريم", "حاسب", 70, "أقل من 80"),
            ("سعد", "حاسب", 64, "الأدنى")]
    r = 4
    for row in rows:
        _data(ws, r, list(row), fills={4: KEY_FILL} if row[3] != "أقل من 80" and row[3] != "الأدنى" else None)
        r += 1
    ws.cell(row=r + 1, column=1, value="ثلاثة متدربين حققوا 80 أو أكثر: عمر 92، خالد 88، نورة 81.").font = Font(
        name=FONT, size=10, color="55645E")
    _widths(ws, [16, 14, 12, 24])
    wb.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.xlsx"))


def w26(outdir):
    wb = Workbook()
    ws = wb.active
    ws.title = "مشروعي"
    _sheet_setup(ws)
    _title(ws, 1, "الأسبوع 26 — ورقة تدريب: المشروع الختامي (بيانات وهمية)")
    ws.cell(row=2, column=1, value="المطلوب: أكمل الجدول بدالتين على الأقل (المجموع والمتوسط) ثم أنشئ مخططًا واحدًا.").font = Font(
        name=FONT, size=10, color="55645E")
    _header(ws, 4, ["اليوم", "المواصلات", "الطعام", "المجموع"])
    days = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس"]
    vals = [(10, 25), (12, 20), (8, 22), (15, 18), (10, 30)]
    r = 5
    for d, (a, b) in zip(days, vals):
        _data(ws, r, [d, a, b, ""])
        r += 1
    _data(ws, 10, ["الإجمالي", "", "", ""], fills={1: KEY_FILL})
    _data(ws, 11, ["المتوسط اليومي", "", "", ""], fills={1: KEY_FILL})
    ws.cell(row=13, column=1, value="ثم أنشئ في Word صفحة تشرح المشروع: الهدف، البيانات، النتيجة (ثلاثة أسطر وثلاث نقاط).").font = Font(
        name=FONT, size=10, color="06814A")
    _widths(ws, [18, 14, 12, 12])
    wb.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.xlsx"))


def w26_key(outdir):
    wb = Workbook()
    ws = wb.active
    ws.title = "الحل"
    _sheet_setup(ws)
    _title(ws, 1, "الأسبوع 26 — مفتاح الإجابة (للمدرّب فقط)")
    _header(ws, 3, ["اليوم", "المواصلات", "الطعام", "المجموع"])
    days = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس"]
    vals = [(10, 25), (12, 20), (8, 22), (15, 18), (10, 30)]
    r = 4
    for d, (a, b) in zip(days, vals):
        _data(ws, r, [d, a, b, a + b], fills={4: KEY_FILL})
        r += 1
    _data(ws, 9, ["الإجمالي", "=SUM(B4:B8)", "=SUM(C4:C8)", "=SUM(D4:D8)"], fills={1: KEY_FILL, 4: KEY_FILL})
    _data(ws, 10, ["المتوسط", "=AVERAGE(B4:B8)", "=AVERAGE(C4:C8)", "=AVERAGE(D4:D8)"], fills={1: KEY_FILL, 4: KEY_FILL})
    ws.cell(row=12, column=1, value="النتائج المتوقعة: مجموع المواصلات 55، مجموع الطعام 115، مجموع الأيام 170، والمتوسط اليومي 34.").font = Font(
        name=FONT, size=10, color="55645E")
    _widths(ws, [18, 18, 18, 14])
    wb.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.xlsx"))


# ------------------------------- W14 / W15 (بداية Word وتحرير النص)
def w14(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 14 — ورقة تدريب: بداية العمل في Word",
                  "المدرّب: الأستاذ عادل الحربي · تدريبات أصلية من إعداد المعهد")
    heading(doc, "1) تعرّف على الواجهة")
    para(doc, "افتح Word وأنشئ مستندًا فارغًا، ثم اكتب أمام كل منطقة اسم وظيفتها:", size=11)
    table(doc,
          ["المنطقة", "وظيفتها (اكتبها بنفسك)"],
          [["شريط العنوان", ""],
           ["الشريط الرئيسي", ""],
           ["منطقة الكتابة", ""],
           ["شريط الحالة", ""]])
    heading(doc, "2) أول مستند")
    for s in ["احفظ الملف باسم «تعريفي_الأسبوع14» في مجلد الأسبوع 14.",
              "اكتب عنوانًا: «تعريفي» ثم اضغط Enter.",
              "اكتب ثلاثة أسطر عن نفسك (اسم وهمي أو اسمك الأول فقط).",
              "أضف سطرًا رابعًا: «هدفي من الدورة» ثم اكتب هدفك في سطر.",
              "استخدم Ctrl+S للحفظ، ثم أغلق الملف وأعد فتحه للتأكد من الحفظ."]:
        para(doc, "• " + s, size=11, after=3)
    heading(doc, "3) تمرين الحفظ باسم")
    para(doc, "احفظ نسخة ثانية من الملف باسم «تعريفي_نسخة2» في المجلد نفسه، ثم أجب: ما الفرق بين «حفظ» و«حفظ باسم»؟", size=11)
    for _ in range(2):
        para(doc, "________________________________________________", size=11, after=8)
    heading(doc, "4) قائمة تحقق")
    for s in ["أعرف مكان شريط العنوان والشريط الرئيسي.", "أحفظ الملف بالاسم المطلوب.",
              "أستطيع إغلاق الملف وإعادة فتحه من مكانه.", "أفرّق بين «حفظ» و«حفظ باسم»."]:
        para(doc, "☐ " + s, size=11, after=3)
    doc.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.docx"))


def w14_key(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 14 — مفتاح الإجابة: بداية Word (للمدرّب فقط)",
                  "ملف منفصل عن ورقة المتدرب · لا يُوزَّع على المتدربين")
    heading(doc, "1) إجابات التعرف على الواجهة")
    table(doc,
          ["المنطقة", "الإجابة النموذجية"],
          [["شريط العنوان", "اسم الملف، وأزرار التحكم بالنافذة"],
           ["الشريط الرئيسي", "تبويبات الأوامر: ملف، الصفحة الرئيسية، إدراج..."],
           ["منطقة الكتابة", "الصفحة البيضاء ومؤشر الكتابة"],
           ["شريط الحالة", "عدد الصفحات والكلمات وحالة اللغة"]])
    heading(doc, "2) إجابة سؤال الحفظ")
    para(doc, "«حفظ» يحدّث الملف نفسه دون تغيير اسمه أو مكانه، و«حفظ باسم» يُنشئ ملفًا جديدًا باسم أو مسار مختلف مع بقاء الأصل.", size=11)
    heading(doc, "3) معيار التقييم (تدريبي)")
    for s in ["الملف موجود بالاسم الصحيح في المجلد الصحيح.",
              "النص يحتوي عنوانًا وثلاثة أسطر على الأقل.",
              "المتدرب يعيد فتح الملف بنفسه دون مساعدة.",
              "شرح صحيح للفرق بين الحفظ وحفظ باسم."]:
        para(doc, "• " + s, size=11, after=2)
    heading(doc, "4) المصدر")
    para(doc, "Microsoft Support — «إنشاء مستند في Word وحفظه» — تم الاطلاع عليها في 1 نوفمبر 2026.", size=10, color=GRAY)
    doc.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.docx"))


def w15(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 15 — ورقة تدريب: تحرير النص",
                  "المدرّب: الأستاذ عادل الحربي · تدريبات أصلية من إعداد المعهد")
    heading(doc, "1) النص للتحرير")
    para(doc, "النص التالي فيه أخطاء إملائية وترتيب غير منطقي وجملة مكررة. حرّره دون تغيير المعنى:", size=11)
    para(doc, "يقدّم معمل الحاسب خدمة الطبعبة للمتدربين. يقدّم معمل الحاسب خدمة الطبعبة للمتدربين. الدوام من الأحد إلى الخميس. إحضار البطاقة شرط أساسي. إحضار البطاقة شرط اساسي.", size=12)
    heading(doc, "2) المهام")
    for s in ["احفظ الملف باسم «نصي_المصحح» في مجلد الأسبوع 15.",
              "صحّح الخطأ الإملائي في كلمة «الطبعبة».",
              "احذف الجملة المكررة، وأصلح «اساسي» إلى «أساسي».",
              "أعد ترتيب الأسطر بحيث تبدأ الجملة التعريفية ثم الدوام ثم الشرط.",
              "جرّب Ctrl+Z مرة واحدة، ولاحظ ما عاد إلى حاله، ثم أعد التنفيذ.",
              "استخدم التحديد بالفأرة لحذف سطر كامل، ثم أعد كتابته."]:
        para(doc, "• " + s, size=11, after=3)
    heading(doc, "3) صندوق الاختصارات")
    table(doc,
          ["الاختصار", "وظيفته"],
          [["Ctrl+C", ""], ["Ctrl+X", ""], ["Ctrl+V", ""],
           ["Ctrl+Z", ""], ["Ctrl+A", ""]])
    heading(doc, "4) قائمة تحقق")
    for s in ["لا جملة مكررة في النص.", "الترتيب منطقي من التعريف إلى الشرط.",
              "أعرف وظيفة كل اختصار في الجدول.", "الملف محفوظ باسمه الصحيح."]:
        para(doc, "☐ " + s, size=11, after=3)
    doc.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.docx"))


def w15_key(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 15 — مفتاح الإجابة: تحرير النص (للمدرّب فقط)",
                  "ملف منفصل عن ورقة المتدرب · لا يُوزَّع على المتدربين")
    heading(doc, "1) النص النموذجي بعد التحرير")
    para(doc, "يقدّم معمل الحاسب خدمة الطباعة للمتدربين. الدوام من الأحد إلى الخميس. إحضار البطاقة شرط أساسي.", size=11.5)
    heading(doc, "2) صندوق الاختصارات — الإجابات")
    table(doc,
          ["الاختصار", "الوظيفة"],
          [["Ctrl+C", "نسخ"], ["Ctrl+X", "قص"], ["Ctrl+V", "لصق"],
           ["Ctrl+Z", "تراجع"], ["Ctrl+A", "تحديد الكل"]])
    heading(doc, "3) معيار التقييم (تدريبي)")
    for s in ["حذف الجملة المكررة بالكامل.", "تصحيح «الطبعبة» و«اساسي».",
              "ترتيب منطقي للنص.", "استخدام الاختصارات دون مساعدة."]:
        para(doc, "• " + s, size=11, after=2)
    heading(doc, "4) المصدر")
    para(doc, "Microsoft Support — «تحرير النص في Word: التحديد والنسخ واللصق والتراجع» — تم الاطلاع عليها في 1 نوفمبر 2026.", size=10, color=GRAY)
    doc.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.docx"))



# ------------------------------------------------ W13 typing-test simulation
def w13(outdir):
    """Learner sheet: rehearse the real typing-test condition, then mark it."""
    n = practice_text.check()
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 13 — ورقة تدريب: محاكاة اختبار الطباعة",
                  "تدريب أصلي من إعداد المعهد · النص وهمي للتدريب · ليس نموذجًا للاختبار")
    heading(doc, "1) شرط الاختبار الرسمي (كما أعلنه المعهد)")
    table(doc,
          ["البند", "الشرط"],
          [["طول النص", "170 كلمة على الأقل"],
           ["مدة الاختبار", "10 دقائق"],
           ["أقل سرعة", "10 كلمات في الدقيقة"],
           ["أقل دقة", "95%"],
           ["عدد كلمات هذا النص", f"{n} كلمة (كافٍ لإتمام الشرط)"]])
    heading(doc, "2) النص التدريبي — اكتبه كاملًا دون نظر إلى يديك")
    for block in practice_text.PARAS:
        para(doc, block, size=11, after=6)
    heading(doc, "3) سجّل نتيجتك بنفسك")
    table(doc,
          ["القياس", "المطلوب", "نتيجتك"],
          [["عدد الكلمات المكتوبة", "170 على الأقل", ""],
           ["الزمن بالدقائق", "10 دقائق أو أقل", ""],
           ["السرعة = الكلمات ÷ الدقائق", "10 كلمات/دقيقة على الأقل", ""],
           ["الدقة = (الكلمات الصحيحة ÷ الكلية) × 100", "95% على الأقل", ""]])
    para(doc, "مثال للحساب: كتبت 170 كلمة في 10 دقائق ← السرعة 17 كلمة في الدقيقة. "
              "كتبت 102 كلمة صحيحة من 105 ← الدقة 97.1%.", size=10.5, color=GRAY)
    heading(doc, "4) قائمة تحقق")
    for t in ["أكملت النص كاملًا داخل المدة.",
              "لم أنظر إلى يدي أثناء الكتابة.",
              "حسبت السرعة والدقة بنفسي.",
              "سجّلت نتيجتي في جدول المتابعة.",
              "كتبت ثلاث مهارات تحتاج تدريبًا."]:
        para(doc, "☐ " + t, size=11, after=3)
    doc.save(os.path.join(outdir, "ورقة_تدريب_المتدرب.docx"))


def w13_key(outdir):
    """Trainer key: worked arithmetic for two real-shaped cases."""
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 13 — مفتاح الإجابة: محاكاة الطباعة (للمدرّب فقط)",
                  "ملف منفصل عن ورقة المتدرب · لا يُوزَّع على المتدربين")
    heading(doc, "1) الشرط الرسمي وكيف يُقاس")
    table(doc,
          ["البند", "الشرط", "كيف نتحقق منه"],
          [["طول النص", "170 كلمة على الأقل", "نص الورقة 243 كلمة، فيكفي"],
           ["المدة", "10 دقائق", "مؤقت واحد يبدأ بعد ضبط الجلسة"],
           ["السرعة", "10 كلمات في الدقيقة", "الكلمات المكتوبة ÷ الدقائق المستغرقة"],
           ["الدقة", "95% على الأقل", "(الكلمات الصحيحة ÷ الكلمات الكلية) × 100"]])
    heading(doc, "2) أمثلة محسوبة (تدريبية)")
    table(doc,
          ["الحالة", "الكلمات", "الدقائق", "السرعة", "الصحيحة/الكلية", "الدقة", "النتيجة"],
          [["أ", "170", "10", "17.0", "166 / 170", "97.6%", "مستوفٍ للشروط"],
           ["ب", "120", "10", "12.0", "114 / 120", "95.0%", "لم يُكمل النص"],
           ["ج", "170", "10", "17.0", "158 / 170", "92.9%", "الدقة أقل من 95%"],
           ["د", "170", "12", "14.2", "165 / 170", "97.1%", "تجاوز المدة"]])
    para(doc, "القراءة: الحالة (ب) سرعتها أعلى من الحد الأدنى لكنها لم تُكمل النص، "
              "والحالة (ج) أكملت النص في المدة لكن دقتها تحت 95%. الشرط يُستوفى بتحقق "
              "الشروط الأربعة معًا لا بواحد منها.", size=10.5, color=GRAY)
    heading(doc, "3) ملاحظة حسابية للمدرّب")
    para(doc, "إتمام 170 كلمة في 10 دقائق يعني 17 كلمة في الدقيقة، أي أعلى من الحد "
              "الأدنى المعلن (10). لذلك الشرط العملي الذي يوقف المتدربين غالبًا هو إكمال "
              "النص ثم الدقة، لا السرعة وحدها. وضّح ذلك قبل التمرين لا بعده.", size=10.5)
    heading(doc, "4) المصدر")
    para(doc, "معايير أعلنها المعهد للمدرّب في 1 نوفمبر 2026: 170 كلمة، 10 دقائق، "
              "10 كلمات/دقيقة، دقة 95%؛ ويُعتمد ما يصدر كتابيًا يوم الاختبار.", size=10, color=GRAY)
    doc.save(os.path.join(outdir, "مفتاح_الإجابة_للمدرّب.docx"))


# ---------------------------------------------- W26 exam-readiness handouts
def w26_ready(outdir):
    """Learner sheet: the two official tests, their thresholds, my standing."""
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 26 — ورقة الاستعداد للاختبارات",
                  "تدريب أصلي من إعداد المعهد · ليست أسئلة اختبار ولا نماذج رسمية")
    heading(doc, "1) المعياران الرسميان")
    table(doc,
          ["الاختبار", "المعيار"],
          [["المحوسب — المؤسسة العامة للتدريب التقني والمهني", "الدرجة من 100، والنجاح 60"],
           ["الطباعة (الكتابة السريعة)", "170 كلمة على الأقل في 10 دقائق"],
           ["الطباعة — أقل سرعة", "10 كلمات في الدقيقة"],
           ["الطباعة — أقل دقة", "95%"]])
    heading(doc, "2) موقفي الحالي (املأه من آخر قياس عندك)")
    table(doc,
          ["المهارة", "آخر نتيجة لي", "المطلوب", "الفجوة", "ما سأفعله هذا الأسبوع"],
          [["إكمال نص 170 كلمة في 10 دقائق", "", "170 كلمة", "", ""],
           ["السرعة (كلمة/دقيقة)", "", "10", "", ""],
           ["الدقة", "", "95%", "", ""],
           ["الملفات والمجلدات", "", "إتقان", "", ""],
           ["Word: كتابة، حفظ، تنسيق", "", "إتقان", "", ""],
           ["Excel: بيانات، صيغ، جمع", "", "إتقان", "", ""]])
    heading(doc, "3) سبع مهام للمراجعة الأخيرة")
    for t in ["أكمل نص 170 كلمة بمؤقت 10 دقائق وسجّل النتيجة.",
              "احسب سرعتك ودقتك بنفسك بالمعادلتين.",
              "أنشئ مجلدًا واحفظ فيه ملف Word باسم واضح.",
              "نسّق فقرة: خط وحجم واتجاه ومحاذاة وقائمة.",
              "أنشئ جدول Excel بـ 5 صفوف وأضف دالة الجمع (SUM).",
              "رتّب البيانات وطبّق التصفية، ثم ألغِ التصفية.",
              "راجع أخطاءك الشائعة من ملف الإنجاز."]:
        para(doc, "☐ " + t, size=11, after=3)
    heading(doc, "4) تنبيه")
    para(doc, "الأسئلة هنا تدريبية من إعداد المعهد. معايير النجاح معلنة من المعهد، أما "
              "شكل ورقة الاختبار وتوزيع درجاتها فلم يُعلن لنا ولم نضعه.", size=10.5, color=GRAY)
    doc.save(os.path.join(outdir, "ورقة_الاستعداد_للاختبار.docx"))


def w26_ready_key(outdir):
    doc = new_doc("معهد الفاو — بريدة، القصيم · دورة إدخال البيانات ومعالجة النصوص",
                  "الأسبوع 26 — مفتاح ورقة الاستعداد (للمدرّب فقط)",
                  "ملف منفصل عن ورقة المتدرب · لا يُوزَّع على المتدربين")
    heading(doc, "1) كيف تقرأ جدول «موقفي الحالي»")
    for t in ["الفجوة = المطلوب ناقص آخر نتيجة؛ إن كانت صفرًا أو سالبة فالمهارة مستوفاة.",
              "لا تُقارن متدربًا بمتدرب؛ قارن آخر نتيجة بنتيجته السابقة.",
              "من لم يُكمل 170 كلمة في 10 دقائق يبدأ بإكمال النص ثم يرفع السرعة.",
              "من دقته أقل من 95% يخفض السرعة مؤقتًا حتى تثبت الدقة."]:
        para(doc, "• " + t, size=10.5, after=3)
    heading(doc, "2) مثال محسوب")
    table(doc,
          ["الحالة", "الكلمات/الكلية", "الدقائق", "السرعة", "الدقة", "التوجيه"],
          [["أ", "168 / 170", "10", "16.8", "98.8%", "يزيد كلمتين فقط، ثم يثبّت"],
           ["ب", "150 / 170", "10", "15.0", "88.2%", "يخفض السرعة ويصلح الأخطاء"],
           ["ج", "170 / 170", "13", "13.1", "96.5%", "يتدرب على المؤقت لا على الدقة"]])
    heading(doc, "3) خطة الأسبوع الأخير (مقترح)")
    table(doc,
          ["اليوم", "النشاط", "الزمن"],
          [["الأحد", "نص كامل بمؤقت ثم حساب النتيجة", "20 دقيقة"],
           ["الاثنين", "مهمة Word قصيرة + مهمة Excel قصيرة", "30 دقيقة"],
           ["الثلاثاء", "مراجعة الأخطاء الشائعة مع المدرّب", "15 دقيقة"]])
    heading(doc, "4) المصدر")
    para(doc, "المعايير: 60 من 100 للاختبار المحوسب، و170 كلمة/10 دقائق/10 كلمات في الدقيقة/دقة 95% "
              "لاختبار الطباعة — أعلنها المعهد للمدرّب في 1 نوفمبر 2026، ويُعتمد ما يصدر كتابيًا يوم الاختبار.",
         size=10, color=GRAY)
    doc.save(os.path.join(outdir, "مفتاح_الاستعداد_للاختبار.docx"))

WORD = {13: (w13, w13_key), 14: (w14, w14_key), 15: (w15, w15_key), 16: (w16, w16_key), 17: (w17, w17_key), 18: (w18, w18_key),
        19: (w19, w19_key), 20: (w20, w20_key), 21: (w21, w21_key)}
EXCEL = {22: (w22, w22_key), 23: (w23, w23_key), 24: (w24, w24_key),
         25: (w25, w25_key), 26: (w26, w26_key)}

EXTRA = {26: (w26_ready, w26_ready_key)}

if __name__ == "__main__":
    for no, (fn, key) in {**WORD, **EXCEL, **EXTRA}.items():
        d = os.path.join(OUT, f"W{no:02d}")
        os.makedirs(d, exist_ok=True)
        fn(d)
        key(d)
        print("W%02d handouts ok" % no)
