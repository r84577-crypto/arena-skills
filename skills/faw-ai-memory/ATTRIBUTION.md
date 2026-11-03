# The mandatory credit line

Every document, slide, sheet, PDF, report, and generated email must carry, without
exception:

```text
تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدير الحاسب
```

Do not hard-code it. The string lives in one place, `public.settings` key
`attribution_footer`, and is returned by `public.api_attribution_footer()`. Changing the
wording later must be one row update, not a search across generators.

## Per surface

| Surface | Where it goes | How |
| --- | --- | --- |
| Google Docs | footer of the document body | `documents.batchUpdate` with `createFooter` + `insertText` in the footer segment, or a `FOOTER` section via the Docs API |
| Google Slides | final slide, or the footer placeholder | `presentations.batchUpdate` → `createShape` + `insertText` on the closing slide |
| Google Sheets | a dedicated last row, or the sheet's developer metadata | append a row in column A; **not** a cell inside the data range, so it cannot be dragged into a formula |
| PDF / DOCX export | document footer | set before export; the export inherits the document footer |
| HTML / markdown report | visible footer, `role="contentinfo"` | literal text, not an image — it must be selectable and searchable |
| Email | signature block | plain text line above the legal signature |
| Notion page | last block, italic | append a `paragraph` block on create, not on every update |

Two rules that follow from the wording: the title is `مدير الحاسب` (not "مدير الحاسب
الآلي"), and the name is `عادل الحربي` — the full name and the honorific are not
substituted per document. If the legal attribution must differ (a contract, say), the
requirement is confirmed with the principal first; it is not changed by an agent.

## Verification

A generator is not finished when it writes the footer. It is finished when a check reads
the produced artifact back and finds the exact string. For Docs, Slides, and Sheets:

```text
export the file as plain text → assert the line is present → assert it is in the footer
(or the final slide / last row), not merely somewhere in the body.
```

For an email, assert it is present in the `text/plain` part, not only the HTML part — many
clients strip HTML signatures.

## What never carries it

- Test fixtures and sample rows.
- A message in a chat thread.
- Internal memory rows (`faw_ai.*`) — they are data, not deliverables.
- A file quoted from a third party; adding the line to someone else's work is a false
  attribution, which is worse than a missing one.

## Arabic note

العبارة إلزامية في تذييل أي مُخرَج (مستند، عرض تقديمي، جدول، تقرير، بريد). تُقرأ من
`public.api_attribution_footer()` ولا تُكتب يدوياً في الشيفرة، حتى يبقى تحديثها في مكان
واحد. ولا تُضاف إلى أعمال الآخرين أو إلى ملفات الاختبار.
