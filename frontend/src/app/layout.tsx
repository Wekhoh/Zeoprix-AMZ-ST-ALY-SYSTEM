import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Zeoprix Ops Workbench",
  description: "Amazon 广告运营工作台前端重构预览",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
