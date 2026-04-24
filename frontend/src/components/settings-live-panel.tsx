"use client";
/**
 * settings-live-panel — Phase 7.8 Amazon Ads 风
 * 骨架：metric cards + 左 SettingsMutationPanel + SettingsConfigPanel（包卡）
 *                     右 规则版本 + 备份详情 + 活动 log
 */
import { useEffect, useState } from "react";
import {
	Info,
	History,
	Database,
	Settings as SettingsIcon,
} from "lucide-react";

import { recordFrontendActivity } from "@/components/live-activity";
import { writePageContext } from "@/components/page-context";
import { SettingsConfigPanel } from "@/components/settings-config-panel";
import { SettingsMutationPanel } from "@/components/settings-mutation-panel";
import type { SettingsPayload } from "@/lib/mock-data";

type Props = {
	payload: SettingsPayload;
};

type RestoreBackupResponse = {
	status?: string;
	restoredProductId?: number;
	productName?: string;
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

type SettingsState = NonNullable<SettingsPayload["settings"]>;

function buildInitialSettingsState(payload: SettingsPayload): SettingsState {
	return (
		payload.settings ?? {
			ruleVersionCount: 0,
			strategyProfileCount: 0,
			keywordLibraryCounts: {
				irrelevant: 0,
				weak: 0,
				generic: 0,
				car: 0,
				variants: 0,
			},
			backupSummary: {
				searchTerms: 0,
				analysisResults: 0,
				manualReviews: 0,
				snapshots: 0,
				executionBatches: 0,
			},
			configEditor: {
				coreKeywords: [],
				relatedKeywords: [],
				competitorAsins: [],
				ownVariants: [],
			},
			recentRuleVersions: [],
		}
	);
}

export function SettingsLivePanel({ payload }: Props) {
	const [settingsState, setSettingsState] = useState<SettingsState>(() =>
		buildInitialSettingsState(payload),
	);
	const [activityLog, setActivityLog] = useState<string[]>([]);

	const libs = settingsState.keywordLibraryCounts;
	const backup = settingsState.backupSummary;

	useEffect(() => {
		const latestActivity = activityLog[0] ?? null;
		writePageContext(payload.productId, "settings", {
			summary: `规则 ${settingsState.ruleVersionCount ?? 0} 个版本，策略 ${settingsState.strategyProfileCount ?? 0} 组，当前备份包含 ${backup.searchTerms ?? 0} 条搜索词${latestActivity ? `；最近操作：${latestActivity}` : ""}。`,
			rule_versions: settingsState.ruleVersionCount ?? 0,
			strategy_profiles: settingsState.strategyProfileCount ?? 0,
			backup_terms: backup.searchTerms ?? 0,
			latest_activity: latestActivity,
			core_keywords: settingsState.configEditor.coreKeywords.join("、"),
		});
	}, [activityLog, backup.searchTerms, payload.productId, settingsState]);

	function handleRuntimeCleared() {
		setSettingsState((current) => ({
			...current,
			backupSummary: {
				searchTerms: 0,
				analysisResults: 0,
				manualReviews: 0,
				snapshots: 0,
				executionBatches: 0,
			},
		}));
		setActivityLog((current) =>
			["已清空当前产品的运行数据。", ...current].slice(0, 4),
		);
		recordFrontendActivity(payload.productId, {
			label: "最近数据管理",
			title: "运行数据已清空",
			detail: "当前产品的搜索词、分析结果、审核记录与执行批次都已清空。",
			href: "/settings",
		});
	}

	function handleBackupRestored(
		response: RestoreBackupResponse,
		restoreAsNew: boolean,
	) {
		const line = `${restoreAsNew ? "已恢复为新产品副本" : "已恢复到当前产品"}：${response.productName ?? "恢复产品"}`;
		setActivityLog((current) => [line, ...current].slice(0, 4));
		recordFrontendActivity(payload.productId, {
			label: "最近数据管理",
			title: restoreAsNew
				? "完整备份已恢复为新副本"
				: "完整备份已恢复到当前产品",
			detail: line,
			href: "/settings",
		});
	}

	function handleConfigSaved(response: ConfigMutationResponse) {
		const configEditor = response.configEditor;
		if (!configEditor) return;
		setSettingsState((current) => ({
			...current,
			configEditor,
			ruleVersionCount: response.ruleVersionCount ?? current.ruleVersionCount,
			recentRuleVersions:
				response.recentRuleVersions ?? current.recentRuleVersions,
			keywordLibraryCounts: {
				...current.keywordLibraryCounts,
				variants: configEditor.ownVariants.length,
			},
		}));
		const line = `已保存配置：核心词 ${configEditor.coreKeywords.length} 个，竞品 ASIN ${configEditor.competitorAsins.length} 个。`;
		setActivityLog((current) => [line, ...current].slice(0, 4));
		recordFrontendActivity(payload.productId, {
			label: "最近配置",
			title: "规则与词库配置已更新",
			detail: line,
			href: "/settings",
		});
	}

	const metricItems: Array<{ label: string; value: string; hint: string }> = [
		{
			label: "规则版本",
			value: String(settingsState.ruleVersionCount ?? 0),
			hint: "已保存配置版本",
		},
		{
			label: "策略组合",
			value: String(settingsState.strategyProfileCount ?? 0),
			hint: "可用策略模板",
		},
		{
			label: "不相关词库",
			value: String(libs.irrelevant ?? 0),
			hint: "已过滤的词",
		},
		{
			label: "弱相关 / 泛词",
			value: String((libs.weak ?? 0) + (libs.generic ?? 0)),
			hint: "次要词库",
		},
	];

	const backupItems: Array<{ label: string; value: string }> = [
		{ label: "搜索词", value: String(backup.searchTerms ?? 0) },
		{ label: "分析结果", value: String(backup.analysisResults ?? 0) },
		{ label: "审核记录", value: String(backup.manualReviews ?? 0) },
		{ label: "执行批次", value: String(backup.executionBatches ?? 0) },
	];

	return (
		<div className="space-y-5">
			{/* ═══ 1. Configuration metric cards ═══ */}
			<div className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
				<div className="grid grid-cols-2 md:grid-cols-4">
					{metricItems.map((m, i) => (
						<div
							key={m.label}
							className={
								"px-4 py-3.5 border-border " +
								(i % 2 !== 0 ? "border-l " : "") +
								(i % 4 !== 0 ? "md:border-l " : "md:border-l-0 ") +
								(i >= 2 ? "border-t " : "") +
								(i >= 4 ? "md:border-t " : "md:border-t-0")
							}
						>
							<div className="flex items-center gap-1 text-[12px] font-semibold text-fg mb-1.5">
								<span>{m.label}</span>
								<Info className="h-3 w-3 text-fg-subtle" />
							</div>
							<div className="text-[20px] font-bold tabular-nums text-fg leading-none">
								{m.value}
							</div>
							<span className="block text-[12px] text-fg-subtle mt-2">
								{m.hint}
							</span>
						</div>
					))}
				</div>
			</div>

			{/* ═══ 2. Main 2-col ═══ */}
			<div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
				<div className="space-y-4">
					<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
						<div className="flex items-center justify-between px-4 py-3 border-b border-border">
							<div className="flex items-center gap-2">
								<Database className="h-3.5 w-3.5 text-accent-strong" />
								<h2 className="text-fg">数据管理</h2>
								<span className="text-[12px] text-fg-muted">
									清空 · 备份 · 恢复
								</span>
							</div>
						</div>
						<div className="p-4">
							<SettingsMutationPanel
								payload={payload}
								onRuntimeCleared={handleRuntimeCleared}
								onBackupRestored={handleBackupRestored}
							/>
						</div>
					</section>

					<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
						<div className="flex items-center justify-between px-4 py-3 border-b border-border">
							<div className="flex items-center gap-2">
								<SettingsIcon className="h-3.5 w-3.5 text-fg-muted" />
								<h2 className="text-fg">规则与词库配置</h2>
								<span className="text-[12px] text-fg-muted">
									核心词 / 竞品 / 变体
								</span>
							</div>
						</div>
						<div className="p-4">
							<SettingsConfigPanel
								payload={{ ...payload, settings: settingsState }}
								onConfigSaved={handleConfigSaved}
							/>
						</div>
					</section>
				</div>

				<aside className="space-y-4">
					{activityLog.length > 0 ? (
						<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
							<div className="flex items-center justify-between px-4 py-3 border-b border-border">
								<h2 className="text-fg">最近操作</h2>
								<span className="text-[12px] text-fg-muted">
									{activityLog.length}
								</span>
							</div>
							<ul className="divide-y divide-border">
								{activityLog.map((item, i) => (
									<li
										key={`${item}-${i}`}
										className="flex items-start gap-2 px-4 py-2.5"
									>
										<span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-success" />
										<span className="flex-1 text-[12.5px] text-fg-muted leading-[1.5]">
											{item}
										</span>
									</li>
								))}
							</ul>
						</section>
					) : null}

					<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
						<div className="flex items-center justify-between px-4 py-3 border-b border-border">
							<div className="flex items-center gap-2">
								<History className="h-3.5 w-3.5 text-fg-muted" />
								<h2 className="text-fg">规则版本历史</h2>
							</div>
							<span className="text-[12px] text-fg-muted">
								{settingsState.recentRuleVersions.length} 个
							</span>
						</div>
						{settingsState.recentRuleVersions.length ? (
							<ul className="divide-y divide-border">
								{settingsState.recentRuleVersions.slice(0, 5).map((item) => (
									<li
										key={`rule-version-${item.version}`}
										className="px-4 py-3 hover:bg-bg-subtle/40 transition-colors"
									>
										<div className="flex items-center justify-between gap-2">
											<span className="font-mono text-[12px] px-1.5 py-0.5 border border-border rounded text-fg font-semibold">
												v{item.version}
											</span>
											<span className="font-mono text-[11px] tabular-nums text-fg-subtle">
												{item.createdAt}
											</span>
										</div>
										<p className="mt-1.5 text-[12.5px] text-fg-muted leading-[1.5] line-clamp-2">
											{item.description}
										</p>
									</li>
								))}
							</ul>
						) : (
							<div className="p-6 text-center text-[12.5px] text-fg-muted">
								暂无已保存版本
							</div>
						)}
					</section>

					<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
						<div className="flex items-center justify-between px-4 py-3 border-b border-border">
							<h2 className="text-fg">当前备份</h2>
						</div>
						<ul className="divide-y divide-border">
							{backupItems.map((item) => (
								<li
									key={item.label}
									className="flex items-center justify-between px-4 py-2.5"
								>
									<span className="text-[12.5px] text-fg-muted">
										{item.label}
									</span>
									<span className="font-mono text-[13px] tabular-nums font-semibold text-fg">
										{item.value}
									</span>
								</li>
							))}
						</ul>
					</section>
				</aside>
			</div>
		</div>
	);
}
