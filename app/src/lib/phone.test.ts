/**
 * اختبارات تطبيع الأرقام — node:test بلا اعتماديات.
 * التشغيل: npm test (من مجلد app).
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { OWNER_NUMBER, normalize } from "./phone.ts";

describe("normalize", () => {
  it("يقبل الصيغة المعتمدة كما هي", () => {
    assert.equal(normalize("966508247153"), "966508247153");
  });

  it("يطبّع الصيغة المحلية 05…", () => {
    assert.equal(normalize("0508247153"), "966508247153");
  });

  it("يطبّع الصيغة بلا صفر", () => {
    assert.equal(normalize("508247153"), "966508247153");
  });

  it("يطبّع الصيغة الدولية +966…", () => {
    assert.equal(normalize("+966508247153"), "966508247153");
  });

  it("يرفض أي رقم آخر (البوابة)", () => {
    assert.equal(normalize("0500000000"), "966500000000");
    assert.notEqual(normalize("0500000000"), OWNER_NUMBER);
  });

  it("يرفض الخردة", () => {
    assert.equal(normalize("abc"), null);
    assert.equal(normalize(""), null);
    assert.equal(normalize("123"), null);
  });
});
