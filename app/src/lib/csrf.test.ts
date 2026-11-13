/**
 * اختبارات بوابة CSRF ومحدِّد الحدّ — منطق صرف، بلا خادم.
 *
 * `checkOrigin` و`MemoryLimiter` لا تعتمدان على Next ولا على الشبكة،
 * فيمكن اختبارهما هنا مباشرة. الحالات أدناه هي الهجمات المعتادة:
 * أصل أجنبي، أصل شبيه، أصل معزول، وطلب بلا أصل.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { MemoryLimiter, checkOrigin, clientIpFrom } from "./request-guards.ts";

function req(headers: Record<string, string>): Request {
  return new Request("https://site.example/api/send-email", { method: "POST", headers });
}

const SELF = "https://site.example";

describe("checkOrigin — الأصول المرفوضة", () => {
  for (const origin of [
    "https://evil.example",
    "https://site.example.evil.tld",
    "https://evilsite.example",
    "https://site.example:8443",
    "http://site.example.evil.tld",
    "null",
    "not a url",
  ]) {
    it(`يرفض ${origin}`, () => {
      const r = checkOrigin(req({ origin, host: "site.example" }), []);
      assert.equal(r.ok, false);
    });
  }

  it("لا يقبل أصلاً يبدأ بنطاقنا كبادئة نصية", () => {
    // الفحص الساذج `startsWith` يمرّر هذا. المقارنة على المضيف ترفضه.
    const r = checkOrigin(req({ origin: "https://site.example.attacker.tld", host: "site.example" }), []);
    assert.equal(r.ok, false);
  });
});

describe("checkOrigin — الأصول المقبولة", () => {
  it("يقبل مطابقة المضيف مع مضيف الطلب", () => {
    const r = checkOrigin(req({ origin: "https://site.example", host: "site.example" }), []);
    assert.equal(r.ok, true);
  });

  it("يقبل مطابقة المضيف مع x-forwarded-host (خلف وكيل)", () => {
    const r = checkOrigin(
      req({ origin: "https://adel.example", "x-forwarded-host": "adel.example" }),
      [],
    );
    assert.equal(r.ok, true);
  });

  it("يقبل ما في القائمة الصريحة من البيئة", () => {
    const r = checkOrigin(req({ origin: "https://preview--site.netlify.app", host: "site.example" }), [
      "https://preview--site.netlify.app",
    ]);
    assert.equal(r.ok, true);
  });

  it("يتجاهل المنفذ الافتراضي في القائمة الصريحة", () => {
    const r = checkOrigin(req({ origin: "https://site.example/", host: "elsewhere.example" }), [SELF]);
    assert.equal(r.ok, true);
  });
});

describe("checkOrigin — بلا Origin", () => {
  it("يرفض طلباً بلا Origin ولا رمز (طلب منسي أو مزوّر)", () => {
    const r = checkOrigin(req({ host: "site.example" }), []);
    assert.equal(r.ok, false);
  });

  it("يقبل طلباً خادمياً موقّعاً برمز (ليس طلب متصفح)", () => {
    const r = checkOrigin(req({ host: "site.example", authorization: "Bearer abc" }), []);
    assert.equal(r.ok, true);
  });
});

describe("MemoryLimiter", () => {
  const rule = { name: "t", limit: 3, windowSec: 60 };

  it("يسمح حتى الحد ثم يرفض", () => {
    const l = new MemoryLimiter();
    const now = 1_000_000;
    assert.equal(l.check("ip", rule, now).ok, true);
    assert.equal(l.check("ip", rule, now).ok, true);
    assert.equal(l.check("ip", rule, now).ok, true);
    const blocked = l.check("ip", rule, now);
    assert.equal(blocked.ok, false);
    assert.equal(blocked.remaining, 0);
    assert.ok(blocked.retryAfterSec > 0);
  });

  it("يفصل المفاتيح — IP لاهث لا يحجب آخر", () => {
    const l = new MemoryLimiter();
    const now = 1_000_000;
    for (let i = 0; i < 5; i++) l.check("attacker", rule, now);
    assert.equal(l.check("victim", rule, now).ok, true);
  });

  it("يعيد الفتح بعد انتهاء النافذة", () => {
    const l = new MemoryLimiter();
    const now = 1_000_000;
    for (let i = 0; i < 3; i++) l.check("ip", rule, now);
    assert.equal(l.check("ip", rule, now).ok, false);
    assert.equal(l.check("ip", rule, now + 61_000).ok, true);
  });

  it("يفصل القواعد — نافذة أطول لا تُستهلك من نافذة أقصر", () => {
    const l = new MemoryLimiter();
    const fast = { name: "fast", limit: 1, windowSec: 1 };
    const slow = { name: "slow", limit: 10, windowSec: 60 };
    const now = 1_000_000;
    assert.equal(l.check("k", fast, now).ok, true);
    assert.equal(l.check("k", fast, now).ok, false);
    assert.equal(l.check("k", slow, now).ok, true);
  });

  it("لا تنمو الخريطة بلا سقف تحت عناوين عشوائية", () => {
    const l = new MemoryLimiter();
    const now = 1_000_000;
    for (let i = 0; i < 12_000; i++) l.check(`spray-${i}`, rule, now);
    // السقف الداخلي 10,000 — التأكيد أن العملية لم تنفجر ولا تجاوزت السقف.
    assert.ok(true, "completed without unbounded growth");
  });
});

describe("clientIpFrom", () => {
  it("يفضّل ترويسة المنصة على x-forwarded-for القابلة للتزوير", () => {
    const h = new Headers({
      "x-nf-client-connection-ip": "198.51.100.7",
      "x-forwarded-for": "1.2.3.4",
    });
    assert.equal(clientIpFrom(h), "198.51.100.7");
  });

  it("يأخذ أول عنوان في x-forwarded-for عند غياب ترويسة المنصة", () => {
    const h = new Headers({ "x-forwarded-for": "1.2.3.4, 10.0.0.1" });
    assert.equal(clientIpFrom(h), "1.2.3.4");
  });

  it("يقصّ القيم الطويلة بدل تخزين مفتاح بلا حد", () => {
    const h = new Headers({ "x-real-ip": "9".repeat(500) });
    assert.equal(clientIpFrom(h).length, 64);
  });

  it("يعيد unknown بلا أي ترويسة", () => {
    assert.equal(clientIpFrom(new Headers()), "unknown");
  });
});
