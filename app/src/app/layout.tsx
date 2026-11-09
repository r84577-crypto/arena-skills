import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "عادل الحربي — النظام السيادي",
  description: "توأم رقمي شخصي: ذاكرة دائمة، روتين صحي، ولوحة سيادة.",
  robots: { index: false, follow: false },
  authors: [{ name: "عادل عبدالله الحربي" }],
};

export const viewport: Viewport = {
  themeColor: "#0a0d14",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
