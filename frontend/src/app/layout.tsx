import type { Metadata } from "next";
import { ThemeProvider } from "next-themes";
import { geistSans, geistMono } from "./fonts";
import { ToastProvider } from "@/components/ui/toast";
import { CommandPalette } from "@/components/ui/command-palette";
import { WebVitalsTracker } from "@/components/web-vitals-tracker";
import "./globals.css";

export const metadata: Metadata = {
	title: "Zeoprix Ops Workbench",
	description: "Amazon 广告运营工作台",
};

export default function RootLayout({
	children,
}: Readonly<{ children: React.ReactNode }>) {
	return (
		<html
			lang="zh-CN"
			suppressHydrationWarning
			className={`${geistSans.variable} ${geistMono.variable}`}
		>
			<body>
				<ThemeProvider
					attribute="class"
					defaultTheme="system"
					enableSystem
					disableTransitionOnChange
				>
					<ToastProvider>
						<WebVitalsTracker />
						<CommandPalette />
						{children}
					</ToastProvider>
				</ThemeProvider>
			</body>
		</html>
	);
}
