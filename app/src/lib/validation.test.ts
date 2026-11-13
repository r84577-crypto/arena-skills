/**
 * اختبارات التحقق من المدخلات — node:test بلا اعتماديات.
 *
 * هذه الدوال هي الحاجز بين ما يرسله أي عميل وما يصل إلى قاعدة البيانات
 * أو المزوّد. كل حالة هنا مأخوذة من طلب حقيقي يمكن لمهاجم إرساله.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  MAX_API_BODY_BYTES,
  email,
  int,
  oneOf,
  readJsonBody,
  sanitizeText,
  str,
} from "./validation.ts";

function post(body: string, headers: Record<string, string> = {}): Request {
  return new Request("http://127.0.0.1/api/send-email", {
    method: "POST",
    body,
    headers: { "content-type": "application/json", ...headers },
  });
}

describe("readJsonBody — سقف الحجم", () => {
  it("يرفض جسماً أكبر من السقف بـ 413", async () => {
    const big = JSON.stringify({ body: "ا".repeat(MAX_API_BODY_BYTES) });
    const r = await readJsonBody(post(big));
    assert.equal(r.ok, false);
    if (!r.ok) assert.equal(r.status, 413);
  });

  it("يقيس البايتات لا الحروف — العربي بايتان لكل حرف", async () => {
    // نصف السقف حروفاً عربية = السقف بايتات تقريباً. فوقه بقليل يجب أن يُرفض.
    const chars = Math.ceil(MAX_API_BODY_BYTES / 2) + 10;
    const r = await readJsonBody(post(JSON.stringify({ body: "ا".repeat(chars) })));
    assert.equal(r.ok, false);
    if (!r.ok) assert.equal(r.status, 413);
  });

  it("يرفض Content-Length معلناً أكبر من السقف قبل القراءة", async () => {
    const r = await readJsonBody(
      post("{}", { "content-length": String(MAX_API_BODY_BYTES + 1) }),
    );
    assert.equal(r.ok, false);
    if (!r.ok) assert.equal(r.status, 413);
  });
});

describe("readJsonBody — الشكل", () => {
  it("يرفض JSON مشوّهاً", async () => {
    const r = await readJsonBody(post('{"id": '));
    assert.equal(r.ok, false);
    if (!r.ok) assert.equal(r.status, 400);
  });

  it("يرفض المصفوفة (يجب كائن)", async () => {
    const r = await readJsonBody(post("[1,2,3]"));
    assert.equal(r.ok, false);
  });

  it("يرفض null", async () => {
    const r = await readJsonBody(post("null"));
    assert.equal(r.ok, false);
  });

  it("يرفض الجسم الفارغ", async () => {
    const r = await readJsonBody(post(""));
    assert.equal(r.ok, false);
    if (!r.ok) assert.equal(r.status, 400);
  });

  it("يقبل كائناً صغيراً صالحاً", async () => {
    const r = await readJsonBody(post('{"id":1}'));
    assert.equal(r.ok, true);
    if (r.ok) assert.equal(r.value.id, 1);
  });
});

describe("str", () => {
  it("يقصّ الفراغات الطرفية", () => {
    assert.equal(str("  مرحبا  ", { max: 20 }), "مرحبا");
  });

  it("يرفض ما يتجاوز الحد", () => {
    assert.equal(str("a".repeat(11), { max: 10 }), null);
  });

  it("يرفض ما هو أقصر من الحد الأدنى", () => {
    assert.equal(str("ab", { max: 10, min: 3 }), null);
  });

  it("يرفض الأنواع غير النصية — لا تحويل صامت", () => {
    assert.equal(str(123, { max: 10 }), null);
    assert.equal(str({ a: 1 }, { max: 10 }), null);
    assert.equal(str(["x"], { max: 10 }), null);
    assert.equal(str(null, { max: 10 }), null);
    assert.equal(str(undefined, { max: 10 }), null);
  });

  it("يرفض النص الذي كله فراغات عند اشتراط حد أدنى", () => {
    assert.equal(str("    ", { max: 10, min: 1 }), null);
  });
});

describe("int", () => {
  it("يقبل صحيحاً داخل الحدود", () => {
    assert.equal(int(42, { min: 1, max: 100 }), 42);
  });

  it("يرفض الكسور", () => {
    assert.equal(int(1.5, { min: 1, max: 100 }), null);
  });

  it("يرفض NaN و Infinity", () => {
    assert.equal(int(Number.NaN, { min: 0, max: 10 }), null);
    assert.equal(int(Number.POSITIVE_INFINITY, { min: 0, max: 10 }), null);
  });

  it("يرفض النص الرقمي — لا تحويل صامت", () => {
    assert.equal(int("42", { min: 1, max: 100 }), null);
  });

  it("يرفض خارج الحدود", () => {
    assert.equal(int(0, { min: 1, max: 100 }), null);
    assert.equal(int(101, { min: 1, max: 100 }), null);
    assert.equal(int(-5, { min: 1, max: 100 }), null);
  });
});

describe("email", () => {
  it("يقبل بريداً عادياً ويوحّد حالته", () => {
    assert.equal(email("Name@Example.COM"), "name@example.com");
  });

  it("يرفض ما بلا نطاق أو بلا نقطة", () => {
    assert.equal(email("no-at-sign"), null);
    assert.equal(email("a@b"), null);
    assert.equal(email("a@b.c"), null);
  });

  it("يرفض ما فيه فراغ أو سطر جديد — رأس بريد محقون", () => {
    assert.equal(email("a b@c.co"), null);
    assert.equal(email("a@c.co\nBcc: victim@evil.example"), null);
  });

  it("يرفض تجاوز الحد", () => {
    assert.equal(email("a".repeat(320) + "@b.co"), null);
  });
});

describe("oneOf", () => {
  it("يقبل قيمة من القائمة", () => {
    assert.equal(oneOf("PERSONAL", ["PERSONAL", "TRAINING"] as const), "PERSONAL");
  });

  it("يرفض أي قيمة خارج القائمة", () => {
    assert.equal(oneOf("AON", ["PERSONAL", "TRAINING"] as const), null);
    assert.equal(oneOf("personal", ["PERSONAL"] as const), null);
    assert.equal(oneOf(1, ["PERSONAL"] as const), null);
  });
});

describe("sanitizeText", () => {
  it("يحيّد أحرف التحكم التي تقطع الرسالة", () => {
    assert.equal(sanitizeText("a\u0000b\u0007c"), "abc");
  });

  it("يزيل محارف قلب الاتجاه (خداع العرض)", () => {
    assert.equal(sanitizeText("abc\u202Edef"), "abcdef");
  });

  it("يبقي الفواصل والنص العربي كما هو", () => {
    const s = "سطر أول\nسطر ثانٍ — بفاصلة، ونقطة.";
    assert.equal(sanitizeText(s), s);
  });
});
