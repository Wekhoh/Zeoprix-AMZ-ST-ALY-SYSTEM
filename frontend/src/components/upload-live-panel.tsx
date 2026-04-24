"use client";
/**
 * upload-live-panel — Phase 7.4 Amazon Ads 风
 * 骨架：metric cards grid + 上传卡 + 活动 log + 最近导入列表 + 失败文件
 */
import { useEffect, useMemo, useState } from "react";
import {
	Info,
	CheckCircle2,
	AlertTriangle,
	Camera,
	Layers,
} from "lucide-react";

import { recordFrontendActivity } from "@/components/live-activity";
import { writePageContext } from "@/components/page-context";
import { UploadMutationPanel } from "@/components/upload-mutation-panel";
import type { UploadPayload } from "@/lib/mock-data";

type Props = {
	payload: UploadPayload;
};

type UploadMutationResponse = {
	importedFiles?: Array<{
		fileName?: string;
		campaignName?: string;
		rows?: number;
	}>;
	failedFiles?: Array<{ fileName?: string; reason?: string }>;
	importedRows?: number;
	campaignsCreated?: number;
	analysisState?: {
		status?: string;
		message?: string;
		termsAnalyzed?: number;
		resultsSaved?: number;
		pendingReviews?: number;
	} | null;
};

type AnalysisMutationResponse = {
	status?: string;
	message?: string;
	termsAnalyzed?: number;
	resultsSaved?: number;
	pendingReviews?: number;
};

function nowLabel() {
	return new Date().toLocaleString("zh-CN", {
		month: "2-digit",
		day: "2-digit",
		hour: "2-digit",
		minute: "2-digit",
	});
}

export function UploadLivePanel({ payload }: Props) {
	const [uploadState, setUploadState] = useState(
		payload.upload ?? {
			latestReportDate: "暂无导入",
			searchTerms: 0,
			campaigns: 0,
			snapshotCount: 0,
			recentSnapshots: [],
			recentCampaigns: [],
		},
	);
	const [activityLog, setActivityLog] = useState<string[]>([]);
	const [fileFailures, setFileFailures] = useState<
		Array<{ fileName?: string; reason?: string }>
	>([]);

	useEffect(() => {
		const latestCampaign = uploadState.recentCampaigns[0]?.name ?? null;
		const failedNames = fileFailures
			.slice(0, 2)
			.map((item) => item.fileName)
			.filter(Boolean)
			.join("、");
		writePageContext(payload.productId, "upload", {
			summary: `最近报表 ${uploadState.latestReportDate ?? "暂无"}，搜索词 ${uploadState.searchTerms ?? 0}，快照 ${uploadState.snapshotCount ?? 0}${latestCampaign ? `；最近活动 ${latestCampaign}` : ""}${failedNames ? `；失败文件 ${failedNames}` : ""}。`,
			campaigns: uploadState.campaigns ?? 0,
			snapshot_count: uploadState.snapshotCount ?? 0,
			failure_count: fileFailures.length,
			latest_campaign: latestCampaign,
			failed_names: failedNames,
		});
	}, [fileFailures, payload.productId, uploadState]);

	const historyItems = useMemo(() => {
		const snapshotItems = uploadState.recentSnapshots.map((item) => ({
			key: `snapshot-${item.id}`,
			kind: "snapshot" as const,
			title: `快照 ${item.id}`,
			detail: `形成 ${item.itemCount} 条结果`,
			timestamp: item.createdAt,
		}));
		const campaignItems = uploadState.recentCampaigns.map((item) => ({
			key: `campaign-${item.id}`,
			kind: "campaign" as const,
			title: item.name,
			detail: "导入活动已进入当前产品",
			timestamp: item.createdAt,
		}));
		return [...snapshotItems, ...campaignItems].slice(0, 8);
	}, [uploadState.recentCampaigns, uploadState.recentSnapshots]);

	function handleUploadComplete(response: UploadMutationResponse) {
		const stamp = nowLabel();
		setUploadState((current) => ({
			...current,
			latestReportDate: response.importedRows
				? stamp
				: current.latestReportDate,
			searchTerms: current.searchTerms + (response.importedRows ?? 0),
			campaigns: current.campaigns + (response.campaignsCreated ?? 0),
			snapshotCount:
				current.snapshotCount +
				((response.analysisState?.resultsSaved ?? 0) > 0 ? 1 : 0),
			recentCampaigns: [
				...(response.importedFiles ?? []).map((file, index) => ({
					id: Date.now() + index,
					name: file.campaignName ?? file.fileName ?? "导入活动",
					createdAt: stamp,
				})),
				...current.recentCampaigns,
			].slice(0, 4),
			recentSnapshots: response.analysisState?.resultsSaved
				? [
						{
							id: Date.now(),
							createdAt: stamp,
							itemCount: response.analysisState.resultsSaved ?? 0,
						},
						...current.recentSnapshots,
					].slice(0, 4)
				: current.recentSnapshots,
		}));
		setFileFailures(response.failedFiles ?? []);
		setActivityLog((current) =>
			[
				`已导入 ${(response.importedFiles ?? []).length} 个文件，新增 ${response.importedRows ?? 0} 条记录。`,
				...((response.failedFiles ?? []).length
					? [`有 ${(response.failedFiles ?? []).length} 个文件未导入成功。`]
					: []),
				...current,
			].slice(0, 4),
		);
		if (response.importedFiles?.length) {
			recordFrontendActivity(payload.productId, {
				label: "最近上传",
				title: `${response.importedFiles[0].campaignName ?? response.importedFiles[0].fileName ?? "导入文件"} 已导入`,
				detail: `新增 ${response.importedRows ?? 0} 条记录${response.failedFiles?.length ? `，${response.failedFiles.length} 个文件失败` : ""}。`,
				href: "/upload",
			});
		}
		if (response.analysisState?.resultsSaved) {
			recordFrontendActivity(payload.productId, {
				label: "最近分析",
				title: `最新快照已形成 ${response.analysisState.resultsSaved} 条建议动作`,
				detail: response.analysisState.message ?? "分析已自动运行。",
				href: "/analysis",
			});
		}
	}

	function handleAnalysisComplete(response: AnalysisMutationResponse) {
		const stamp = nowLabel();
		setUploadState((current) => ({
			...current,
			snapshotCount:
				current.snapshotCount + ((response.resultsSaved ?? 0) > 0 ? 1 : 0),
			recentSnapshots:
				(response.resultsSaved ?? 0) > 0
					? [
							{
								id: Date.now(),
								createdAt: stamp,
								itemCount: response.resultsSaved ?? 0,
							},
							...current.recentSnapshots,
						].slice(0, 4)
					: current.recentSnapshots,
		}));
		setActivityLog((current) =>
			[
				`${response.message ?? "分析完成"}，分析 ${response.termsAnalyzed ?? 0} 条词。`,
				...current,
			].slice(0, 4),
		);
		if (response.resultsSaved) {
			recordFrontendActivity(payload.productId, {
				label: "最近分析",
				title: `手动重跑后形成 ${response.resultsSaved} 条建议动作`,
				detail: `${response.message ?? "分析完成"}，分析 ${response.termsAnalyzed ?? 0} 条词。`,
				href: "/analysis",
			});
		}
	}

	const metricItems: Array<{ label: string; value: string; hint: string }> = [
		{
			label: "最近上传",
			value: uploadState.latestReportDate ?? "暂无导入",
			hint: /^\d/.test(uploadState.latestReportDate ?? "")
				? "最新报表时间"
				: "尚未导入任何报表",
		},
		{
			label: "搜索词",
			value: String(uploadState.searchTerms ?? 0),
			hint: "累计条数",
		},
		{
			label: "活动数",
			value: String(uploadState.campaigns ?? 0),
			hint: "已导入广告活动",
		},
		{
			label: "分析快照",
			value: String(uploadState.snapshotCount ?? 0),
			hint: "已生成快照版本",
		},
	];

	return (
		<div className="space-y-5">
			{/* ═══ 1. Metric cards row ═══ */}
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
							<div
								className={
									"font-bold text-fg leading-none " +
									(/^\d/.test(m.value)
										? "text-[20px] tabular-nums"
										: "text-[14px]")
								}
							>
								{m.value}
							</div>
							<span className="block text-[12px] text-fg-subtle mt-2">
								{m.hint}
							</span>
						</div>
					))}
				</div>
			</div>

			{/* ═══ 2. UPLOAD card ═══ */}
			<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
				<div className="flex items-center justify-between px-4 py-3 border-b border-border">
					<div className="flex items-baseline gap-3">
						<h2 className="text-fg">上传原始报表</h2>
						<span className="text-[12px] text-fg-muted">
							CSV / Excel · 自动识别表头
						</span>
					</div>
				</div>
				<div className="p-4">
					<UploadMutationPanel
						payload={payload}
						onUploadComplete={handleUploadComplete}
						onAnalysisComplete={handleAnalysisComplete}
					/>
				</div>
			</section>

			{/* ═══ 3. LOG（本次上传，conditional） ═══ */}
			{activityLog.length ? (
				<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
					<div className="flex items-center justify-between px-4 py-3 border-b border-border">
						<div className="flex items-baseline gap-3">
							<h2 className="text-fg">本次上传</h2>
							<span className="text-[12px] text-fg-muted">
								{activityLog.length} events
							</span>
						</div>
					</div>
					<ul className="divide-y divide-border">
						{activityLog.map((item, i) => (
							<li
								key={`${item}-${i}`}
								className="flex items-start gap-3 px-4 py-2.5"
							>
								<span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success-bg text-success-fg">
									<CheckCircle2 className="h-3 w-3" />
								</span>
								<span className="flex-1 text-[13px] text-fg leading-[1.5]">
									{item}
								</span>
							</li>
						))}
					</ul>
				</section>
			) : null}

			{/* ═══ 4. HISTORY（最近导入） ═══ */}
			<section className="bg-bg-elevated border border-border rounded-lg overflow-hidden">
				<div className="flex items-center justify-between px-4 py-3 border-b border-border">
					<div className="flex items-baseline gap-3">
						<h2 className="text-fg">最近导入</h2>
						<span className="text-[12px] text-fg-muted">
							{historyItems.length ? `${historyItems.length} items` : "empty"}
						</span>
					</div>
				</div>
				{historyItems.length ? (
					<ul className="divide-y divide-border">
						{historyItems.map((item) => {
							const Icon = item.kind === "snapshot" ? Camera : Layers;
							const toneClass =
								item.kind === "snapshot"
									? "bg-accent-bg text-accent-strong"
									: "bg-bg-subtle text-fg-muted";
							return (
								<li
									key={item.key}
									className="grid grid-cols-[auto_minmax(0,1fr)_120px] items-center gap-3 px-4 py-3 hover:bg-bg-subtle/40 transition-colors"
								>
									<span
										className={
											"inline-flex h-7 w-7 shrink-0 items-center justify-center rounded " +
											toneClass
										}
									>
										<Icon className="h-3.5 w-3.5" />
									</span>
									<div className="min-w-0">
										<div className="text-[13px] font-semibold text-fg truncate">
											{item.title}
										</div>
										<div className="text-[12px] text-fg-muted truncate">
											{item.detail}
										</div>
									</div>
									<span className="font-mono text-[12px] tabular-nums text-fg-subtle text-right">
										{item.timestamp}
									</span>
								</li>
							);
						})}
					</ul>
				) : (
					<div className="p-10 text-center text-[13px] text-fg-muted">
						当前还没有导入历史，点击上方上传区选择 CSV / Excel 开始。
					</div>
				)}
			</section>

			{/* ═══ 5. FAILED（失败文件，conditional） ═══ */}
			{fileFailures.length > 0 ? (
				<section className="bg-bg-elevated border-2 border-warning/40 rounded-lg overflow-hidden">
					<div className="flex items-center justify-between px-4 py-3 border-b border-warning/40 bg-warning-bg/30">
						<div className="flex items-center gap-2">
							<AlertTriangle className="h-4 w-4 text-warning-fg" />
							<h2 className="text-warning-fg">未成功文件</h2>
							<span className="text-[12px] text-warning-fg/80">
								{fileFailures.length} files
							</span>
						</div>
					</div>
					<ul className="divide-y divide-warning/20">
						{fileFailures.map((item, i) => (
							<li
								key={`${item.fileName}-${i}`}
								className="px-4 py-3 hover:bg-warning-bg/20 transition-colors"
							>
								<div className="font-mono text-[13px] font-semibold text-fg truncate">
									{item.fileName ?? "未知文件"}
								</div>
								<div className="mt-0.5 text-[12px] text-warning-fg leading-[1.5]">
									{item.reason ?? "未知原因"}
								</div>
							</li>
						))}
					</ul>
				</section>
			) : null}
		</div>
	);
}
