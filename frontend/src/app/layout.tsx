import type { Metadata } from "next";
import { Instrument_Sans, Sora } from "next/font/google";
import "./globals.css";

const display = Sora({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["500", "600", "700"],
});

const body = Instrument_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Zeoprix Ops Workbench",
  description: "Amazon 广告运营工作台前端重构预览",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" className={`${display.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}
