/**
 * اختبارات الدوال الصرفة للبريد — node:test بلا اعتماديات.
 * التشغيل: npm test (من مجلد app).
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { selectProvider, scopeFooter, scopeTag } from "./mailer.ts";

describe("selectProvider", () => {
  it("يفضّل Resend عند وجود مفتاحه", () => {
    assert.equal(selectProvider({ RESEND_API_KEY: "x" }), "resend");
  });

  it("يسقط على Gmail عند غياب Resend ووجود بياناته", () => {
    assert.equal(
      selectProvider({ GMAIL_USER: "a@b.c", GMAIL_APP_PASSWORD: "p" }),
      "gmail",
    );
  });

  it("يطلب Gmail كاملاً — المستخدم وحده لا يكفي", () => {
    assert.equal(selectProvider({ GMAIL_USER: "a@b.c" }), null);
  });

  it("يعيد null بلا أي مزوّد (not_configured بصدق)", () => {
    assert.equal(selectProvider({}), null);
  });
});

describe("scopeFooter", () => {
  it("التدريب يُسنَد لمدرب الحاسب", () => {
    assert.match(scopeFooter("TRAINING"), /مدرب الحاسب/);
  });

  it("الشخصي يُسنَد لمدير الحاسب", () => {
    assert.match(scopeFooter("PERSONAL"), /مدير الحاسب/);
  });

  it("الإسنادان لا يختلطان", () => {
    assert.ok(!scopeFooter("TRAINING").includes("مدير الحاسب"));
    assert.ok(!scopeFooter("PERSONAL").includes("مدرب الحاسب"));
  });
});

describe("scopeTag", () => {
  it("يوسم النطاقين", () => {
    assert.equal(scopeTag("TRAINING"), "تدريب");
    assert.equal(scopeTag("PERSONAL"), "شخصي");
  });
});
