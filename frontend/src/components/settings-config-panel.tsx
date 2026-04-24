"use client";

import { useState, useTransition } from "react";

import { BACKEND_BASE_URL } from "@/lib/backend";
import type { SettingsPayload } from "@/lib/mock-data";

type Props = {
	payload: SettingsPayload;
	onConfigSaved?: (response: ConfigMutationResponse) => void;
	onRuleVersionRestored?: (
		response: RuleVersionRestoreResponse,
		version: number,
	) => void;
};

type ConfigMutationResponse = {
	status?: string;
	message?: string;
	ruleVersionCount?: number;
	recentRuleVersions?: Array<{
		version: number;
		createdAt: string;
		description: string;
	}>;
	configEditor?: {
		coreKeywords: string[];
		relatedKeywords: string[];
		competitorAsins: string[];
		ownVariants: string[];
	};
};

type RuleVersionRestoreResponse = {
	status?: string;
	message?: string;
	ruleVersionCount?: number;
	recentRuleVersions?: Array<{
		version: number;
		createdAt: string;
		description: string;
	}>;
};

type RuleVersionPreviewResponse = {
	status?: string;
	version: number;
	configEditor: {
		coreKeywords: string[];
		relatedKeywords: string[];
		competitorAsins: string[];
		ownVariants: string[];
	};
	diff: {
		coreKeywords: { added: string[]; removed: string[] };
		relatedKeywords: { added: string[]; removed: string[] };
		competitorAsins: { added: string[]; removed: string[] };
		ownVariants: { added: string[]; removed: string[] };
	};
};

function splitLines(value: string) {
	return value
		.split(/[\n,]/)
		.map((item) => item.trim())
		.filter(Boolean);
}

export function SettingsConfigPanel({
	payload,
	onConfigSaved,
	onRuleVersionRestored,
}: Props) {
	const productId = payload.productId;
	const editor = payload.settings?.configEditor ?? {
		coreKeywords: [],
		relatedKeywords: [],
		competitorAsins: [],
		ownVariants: [],
	};
	const recentRuleVersions = payload.settings?.recentRuleVersions ?? [];
	const [coreKeywords, setCoreKeywords] = useState(
		editor.coreKeywords.join("\n"),
	);
	const [relatedKeywords, setRelatedKeywords] = useState(
		editor.relatedKeywords.join("\n"),
	);
	const [competitorAsins, setCompetitorAsins] = useState(
		editor.competitorAsins.join("\n"),
	);
	const [ownVariants, setOwnVariants] = useState(editor.ownVariants.join("\n"));
	const [message, setMessage] = useState<string | null>(null);
	const [preview, setPreview] = useState<RuleVersionPreviewResponse | null>(
		null,
	);
	const [pending, startTransition] = useTransition();

	function saveConfig() {
		if (!productId) return;
		setMessage(null);
		startTransition(async () => {
			const response = await fetch(
				`${BACKEND_BASE_URL}/frontend/settings/product-config`,
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						product_id: productId,
						core_keywords: splitLines(coreKeywords),
						related_keywords: splitLines(relatedKeywords),
						competitor_asins: splitLines(competitorAsins),
						own_variants: splitLines(ownVariants),
					}),
				},
			);
			const body = (await response
				.json()
				.catch(() => ({ message: "保存失败" }))) as ConfigMutationResponse & {
				detail?: string;
			};
			if (!response.ok) {
				setMessage(body.detail ?? body.message ?? "保存失败");
				return;
			}
			setMessage(body.message ?? "配置已保存。");
			if (body.configEditor) {
				setCoreKeywords(body.configEditor.coreKeywords.join("\n"));
				setRelatedKeywords(body.configEditor.relatedKeywords.join("\n"));
				setCompetitorAsins(body.configEditor.competitorAsins.join("\n"));
				setOwnVariants(body.configEditor.ownVariants.join("\n"));
			}
			onConfigSaved?.(body);
		});
	}

	function restoreRuleVersion(version: number) {
		if (!productId) return;
		setMessage(null);
		startTransition(async () => {
			const response = await fetch(
				`${BACKEND_BASE_URL}/frontend/settings/rule-versions/restore`,
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ product_id: productId, version }),
				},
			);
			const body = (await response.json().catch(() => ({
				message: "恢复规则版本失败",
			}))) as RuleVersionRestoreResponse & { detail?: string };
			if (!response.ok) {
				setMessage(body.detail ?? body.message ?? "恢复规则版本失败");
				return;
			}
			setMessage(body.message ?? `已恢复规则版本 v${version}`);
			setPreview(null);
			onRuleVersionRestored?.(body, version);
		});
	}

	function previewRuleVersion(version: number) {
		if (!productId) return;
		setMessage(null);
		startTransition(async () => {
			const response = await fetch(
				`${BACKEND_BASE_URL}/frontend/settings/rule-versions/${version}?product_id=${productId}`,
			);
			const body = (await response.json().catch(() => ({
				message: "读取规则版本失败",
			}))) as RuleVersionPreviewResponse & {
				detail?: string;
				message?: string;
			};
			if (!response.ok) {
				setMessage(body.detail ?? body.message ?? "读取规则版本失败");
				return;
			}
			setPreview(body);
		});
	}

	return (
		<section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
			<div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">
				Config Editor
			</div>
			<h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">
				快速配置编辑
			</h3>
			<p className="mt-3 text-sm leading-relaxed text-zinc-500">
				先把核心词、相关词、竞品 ASIN 和自家变体在这里维护好，再让分析和 Copilot
				继续引用。
			</p>
			<div className="mt-5 grid gap-4 sm:grid-cols-2">
				<label className="flex flex-col gap-2 text-sm text-zinc-500">
					<span className="font-medium text-zinc-900">核心词</span>
					<textarea
						value={coreKeywords}
						onChange={(e) => setCoreKeywords(e.target.value)}
						className="min-h-28 rounded-2xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-900 outline-none placeholder:text-zinc-400"
						placeholder="每行一个核心词"
					/>
				</label>
				<label className="flex flex-col gap-2 text-sm text-zinc-500">
					<span className="font-medium text-zinc-900">相关词</span>
					<textarea
						value={relatedKeywords}
						onChange={(e) => setRelatedKeywords(e.target.value)}
						className="min-h-28 rounded-2xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-900 outline-none placeholder:text-zinc-400"
						placeholder="每行一个相关词"
					/>
				</label>
				<label className="flex flex-col gap-2 text-sm text-zinc-500">
					<span className="font-medium text-zinc-900">竞品 ASIN</span>
					<textarea
						value={competitorAsins}
						onChange={(e) => setCompetitorAsins(e.target.value)}
						className="min-h-28 rounded-2xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-900 outline-none placeholder:text-zinc-400"
						placeholder="每行一个竞品 ASIN"
					/>
				</label>
				<label className="flex flex-col gap-2 text-sm text-zinc-500">
					<span className="font-medium text-zinc-900">自家变体 ASIN</span>
					<textarea
						value={ownVariants}
						onChange={(e) => setOwnVariants(e.target.value)}
						className="min-h-28 rounded-2xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-900 outline-none placeholder:text-zinc-400"
						placeholder="每行一个自家变体 ASIN"
					/>
				</label>
			</div>
			<div className="mt-5 flex items-center gap-3">
				<button
					disabled={pending || !productId}
					onClick={saveConfig}
					className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50"
				>
					{pending ? "保存中…" : "保存配置"}
				</button>
				{message ? (
					<span className="text-sm leading-relaxed text-zinc-500">
						{message}
					</span>
				) : null}
			</div>
			{recentRuleVersions.length ? (
				<div className="mt-6 rounded-2xl bg-zinc-50 p-4">
					<div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">
						规则版本恢复
					</div>
					<div className="mt-3 space-y-2">
						{recentRuleVersions.slice(0, 3).map((item) => (
							<div
								key={`restore-rule-version-${item.version}`}
								className="rounded-2xl bg-white px-4 py-3 ring-1 ring-zinc-200/80"
							>
								<div className="flex items-center justify-between gap-3">
									<div>
										<div className="font-medium text-zinc-950">
											v{item.version} · {item.createdAt}
										</div>
										<div className="mt-1 text-sm leading-relaxed text-zinc-500">
											{item.description}
										</div>
									</div>
									<div className="flex flex-wrap items-center gap-2">
										<button
											onClick={() => previewRuleVersion(item.version)}
											disabled={pending || !productId}
											className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 shadow-sm transition hover:bg-zinc-50 disabled:opacity-50"
										>
											查看差异
										</button>
										<button
											onClick={() => restoreRuleVersion(item.version)}
											disabled={pending || !productId}
											className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 shadow-sm transition hover:bg-zinc-50 disabled:opacity-50"
										>
											恢复此版本
										</button>
									</div>
								</div>
							</div>
						))}
					</div>
					{preview ? (
						<div className="mt-4 rounded-2xl bg-white p-4 ring-1 ring-zinc-200/80">
							<div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">
								版本差异预览
							</div>
							<div className="mt-2 text-sm font-medium text-zinc-950">
								v{preview.version}
							</div>
							<div className="mt-3 grid gap-3 sm:grid-cols-2">
								{(
									[
										["核心词", preview.diff.coreKeywords],
										["相关词", preview.diff.relatedKeywords],
										["竞品 ASIN", preview.diff.competitorAsins],
										["自家变体", preview.diff.ownVariants],
									] as const
								).map(([label, diff]) => (
									<div key={label} className="rounded-2xl bg-zinc-50 p-4">
										<div className="text-sm font-medium text-zinc-950">
											{label}
										</div>
										<div className="mt-2 text-sm leading-relaxed text-zinc-500">
											{diff.added.length
												? `新增：${diff.added.join("、")}`
												: "新增：无"}
										</div>
										<div className="mt-1 text-sm leading-relaxed text-zinc-500">
											{diff.removed.length
												? `移除：${diff.removed.join("、")}`
												: "移除：无"}
										</div>
									</div>
								))}
							</div>
						</div>
					) : null}
				</div>
			) : null}
		</section>
	);
}
