import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	// Next.js 16 默认仅允许 localhost 访问 dev 资源（含 client JS chunks /
	// HMR）。desktop launcher (start.ps1) 用 127.0.0.1，会被当跨源屏蔽，
	// 导致 client bundle 不送 → hydration 失败 → 按钮 onClick 无响应
	// （sidebar / Copilot drawer 折叠按钮失效即由此引起）。
	allowedDevOrigins: ["127.0.0.1", "localhost", "0.0.0.0"],
};

export default nextConfig;
