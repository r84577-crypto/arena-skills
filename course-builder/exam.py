# -*- coding: utf-8 -*-
"""Official passing criteria, supplied by the institute (Al-Faw, Buraydah).

Single source of truth: every slide, note and handout that quotes a threshold
reads it from here, so the numbers can never drift apart between files.

Supplied by the institute in the 1 Nov 2026 brief and confirmed as official:
  * Computer-based exam of the Technical and Vocational Training Corporation
    (المؤسسة العامة للتدريب التقني والمهني) — pass mark 60 out of 100.
  * Typing / speed-writing test — text of at least 170 words, 10-minute
    duration, minimum speed 10 words per minute, minimum accuracy 95%.
"""

# --- computer-based exam ---------------------------------------------------
COMPUTER = {
    "name": "الاختبار المحوسب — المؤسسة العامة للتدريب التقني والمهني",
    "total": 100,
    "pass": 60,
    "pass_text": "60 من 100",
}

# --- typing / speed-writing test ------------------------------------------
TYPING = {
    "name": "اختبار الطباعة (الكتابة السريعة)",
    "words": 170,          # minimum length of the test text
    "minutes": 10,         # duration
    "wpm": 10,             # minimum speed, words per minute
    "accuracy": 95,        # minimum accuracy, percent
}

# Note on the arithmetic: completing a 170-word text in 10 minutes is 17 wpm,
# which is above the 10 wpm floor — so the binding requirement in practice is
# finishing the text. This is stated to learners as-is (no invented rules) and
# listed in the README as a point for the institute to confirm in writing.

SOURCE = ("الأرقام المذكورة في هذه المادة (60 من 100 للاختبار المحوسب، و170 كلمة "
          "في 10 دقائق بسرعة 10 كلمات في الدقيقة ودقة 95%) واردة من المعهد "
          "ويُعتمد ما يصدر عنه كتابيًا يوم الاختبار.")


def computer_line():
    return (f"【الاختبار المحوسب】{COMPUTER['name']}: النجاح {COMPUTER['pass_text']}. "
            "التدريبات في هذه الدورة أصلية وليست أسئلة الاختبار، لكنها تغطي المهارات "
            "نفسها: الملفات، لوحة المفاتيح، Word، وExcel.")


def typing_line():
    return (f"【اختبار الطباعة】نص لا يقل عن {TYPING['words']} كلمة، في "
            f"{TYPING['minutes']} دقائق، بسرعة {TYPING['wpm']} كلمات في الدقيقة "
            f"على الأقل ودقة {TYPING['accuracy']}% على الأقل. أكمل النص أولًا ثم "
            "ارفع السرعة دون أن تنزل بالدقة.")


def exam_line(no):
    """One line of exam framing for a given week number (or '' if not useful)."""
    if 8 <= no <= 13:
        return typing_line()
    if 14 <= no <= 26:
        return computer_line()
    return (f"{computer_line()}\n{typing_line()}")


def wpm(words, minutes):
    """Words per minute, one decimal."""
    return round(words / minutes, 1)


def accuracy(correct, total):
    """Accuracy percent, one decimal."""
    return round(correct / total * 100, 1)


def passes_typing(words, minutes, acc):
    """True when all three thresholds of the typing test are met."""
    return (words >= TYPING["words"] and minutes <= TYPING["minutes"]
            and wpm(words, minutes) >= TYPING["wpm"]
            and acc >= TYPING["accuracy"])
