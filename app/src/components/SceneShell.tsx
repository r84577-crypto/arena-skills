"use client";

import dynamic from "next/dynamic";

/**
 * الغلاف: يُحمّل المشهد بعد الترطيب فقط.
 * الحاوية موجودة دائماً ببُعدها المحجوز من CSS، ولهذا CLS = 0 مهما تأخّر three.
 */
const SovereignScene = dynamic(() => import("./SovereignScene"), {
  ssr: false,
  loading: () => (
    <div className="scene-shell">
      <span className="scene-fallback">يُهيّأ المشهد…</span>
    </div>
  ),
});

export default function SceneShell() {
  return <SovereignScene />;
}
