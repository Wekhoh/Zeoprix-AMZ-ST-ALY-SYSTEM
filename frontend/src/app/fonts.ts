/**
 * fonts.ts — Phase 6 Vercel × Notion
 * Geist Sans 为 Vercel 灵魂主字（vercel.com 同款），Geist Mono 为数字/code。
 * 中文通过 font-family fallback 走微软雅黑/PingFang（globals.css 中定义）
 */
import { Geist, Geist_Mono } from "next/font/google";

export const geistSans = Geist({
	subsets: ["latin"],
	variable: "--font-geist-sans",
	display: "swap",
});

export const geistMono = Geist_Mono({
	subsets: ["latin"],
	variable: "--font-geist-mono",
	display: "swap",
});
