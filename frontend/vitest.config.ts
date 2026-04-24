/**
 * Vitest config — Sprint 5 · D.8 (2026-04-24)
 *
 * 当前定位：只跑纯 TS 单元测（无 DOM / 无 React render），Node 环境即可。
 * 以后若要加组件 render 测试（`copilot-rich-text.tsx` 等）：
 *   - 安装 `@testing-library/react` + `happy-dom` 或 `jsdom`
 *   - 把 `environment` 改 `happy-dom` 或做 workspace 拆分
 *
 * Next.js 16 + React 19 兼容：vitest 4 对 Node 20.18+ / TS 5 / ESM 天然支持，
 * 不需要额外 babel/swc 插件；alias `@/*` 跟 tsconfig.json 的 paths 对齐。
 */

import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
	test: {
		environment: "node",
		globals: true, // 让测试里直接写 describe/it/expect 不用显式 import
		include: ["src/**/*.{test,spec}.{ts,tsx}"],
		exclude: ["node_modules", ".next", "dist"],
		coverage: {
			provider: "v8",
			reporter: ["text", "html"],
			include: ["src/lib/**/*.ts", "src/components/**/*.tsx"],
			exclude: ["**/*.test.*", "**/*.spec.*"],
		},
	},
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "./src"),
		},
	},
});
