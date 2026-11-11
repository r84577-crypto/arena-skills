/**
 * أرقام الهاتف — تطبيع خالص قابل للاختبار (يُستخدم خادماً ومتصفحاً).
 *
 * القاعدة المؤسسية: صيغة واحدة معتمدة (966 المحلية بلا +)، وكل صيغة
 * أخرى تُطبَّع إليها أو تُرفَض — لا مقارنة بلا تطبيع أبداً.
 */

/** رقم المالك الوحيد المقبول للواتساب (0508247153). */
export const OWNER_NUMBER = "966508247153";

/** تطبيع كل الصيغ (0508247153، ‎+966…‎، 966…) إلى صيغة واحدة. */
export function normalize(input: string): string | null {
  const digits = input.replace(/\D/g, "");
  if (/^9665\d{8}$/.test(digits)) return digits;
  if (/^05\d{8}$/.test(digits)) return `966${digits.slice(1)}`;
  if (/^5\d{8}$/.test(digits)) return `966${digits}`;
  return null;
}
