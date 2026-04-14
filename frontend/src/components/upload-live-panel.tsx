"use client";

import { useMemo, useState } from "react";

import { recordFrontendActivity } from "@/components/live-activity";
import { UploadMutationPanel } from "@/components/upload-mutation-panel";
import type { UploadPayload } from "@/lib/mock-data";

type Props = {
  payload: UploadPayload
}

type UploadMutationResponse = {
  importedFiles?: Array<{ fileName?: string; campaignName?: string; rows?: number }>
  failedFiles?: Array<{ fileName?: string; reason?: string }>
  importedRows?: number
  campaignsCreated?: number
  analysisState?: {
    status?: string
    message?: string
    termsAnalyzed?: number
    resultsSaved?: number
    pendingReviews?: number
  } | null
}

type AnalysisMutationResponse = {
  status?: string
  message?: string
  termsAnalyzed?: number
  resultsSaved?: number
  pendingReviews?: number
}

function nowLabel() {
  return new Date().toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
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
  )
  const [activityLog, setActivityLog] = useState<string[]>([])
  const [fileFailures, setFileFailures] = useState<Array<{ fileName?: string; reason?: string }>>([])

  const historyItems = useMemo(() => {
    const snapshotItems = uploadState.recentSnapshots.map((item) => ({
      key: `snapshot-${item.id}`,
      title: item.createdAt,
      detail: `快照 ${item.id} · ${item.itemCount} 条结果`,
    }))
    const campaignItems = uploadState.recentCampaigns.map((item) => ({
      key: `campaign-${item.id}`,
      title: item.name,
      detail: `创建于 ${item.createdAt}`,
    }))
    return [...snapshotItems, ...campaignItems].slice(0, 6)
  }, [uploadState.recentCampaigns, uploadState.recentSnapshots])

  function handleUploadComplete(response: UploadMutationResponse) {
    const stamp = nowLabel()
    setUploadState((current) => ({
      ...current,
      latestReportDate: response.importedRows ? stamp : current.latestReportDate,
      searchTerms: current.searchTerms + (response.importedRows ?? 0),
      campaigns: current.campaigns + (response.campaignsCreated ?? 0),
      snapshotCount: current.snapshotCount + ((response.analysisState?.resultsSaved ?? 0) > 0 ? 1 : 0),
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
            { id: Date.now(), createdAt: stamp, itemCount: response.analysisState.resultsSaved ?? 0 },
            ...current.recentSnapshots,
          ].slice(0, 4)
        : current.recentSnapshots,
    }))
    setFileFailures(response.failedFiles ?? [])
    setActivityLog((current) => [
      `已导入 ${(response.importedFiles ?? []).length} 个文件，新增 ${response.importedRows ?? 0} 条记录。`,
      ...((response.failedFiles ?? []).length ? [`有 ${(response.failedFiles ?? []).length} 个文件未导入成功。`] : []),
      ...current,
    ].slice(0, 4))
    if (response.importedFiles?.length) {
      recordFrontendActivity(payload.productId, {
        label: "最近上传",
        title: `${response.importedFiles[0].campaignName ?? response.importedFiles[0].fileName ?? "导入文件"} 已导入`,
        detail: `新增 ${response.importedRows ?? 0} 条记录${response.failedFiles?.length ? `，${response.failedFiles.length} 个文件失败` : ""}。`,
        href: "/upload",
      })
    }
    if (response.analysisState?.resultsSaved) {
      recordFrontendActivity(payload.productId, {
        label: "最近分析",
        title: `最新快照已形成 ${response.analysisState.resultsSaved} 条建议动作`,
        detail: response.analysisState.message ?? "分析已自动运行。",
        href: "/analysis",
      })
    }
  }

  function handleAnalysisComplete(response: AnalysisMutationResponse) {
    const stamp = nowLabel()
    setUploadState((current) => ({
      ...current,
      snapshotCount: current.snapshotCount + ((response.resultsSaved ?? 0) > 0 ? 1 : 0),
      recentSnapshots: (response.resultsSaved ?? 0) > 0
        ? [{ id: Date.now(), createdAt: stamp, itemCount: response.resultsSaved ?? 0 }, ...current.recentSnapshots].slice(0, 4)
        : current.recentSnapshots,
    }))
    setActivityLog((current) => [
      `${response.message ?? "分析完成"}，分析 ${response.termsAnalyzed ?? 0} 条词。`,
      ...current,
    ].slice(0, 4))
    if (response.resultsSaved) {
      recordFrontendActivity(payload.productId, {
        label: "最近分析",
        title: `手动重跑后形成 ${response.resultsSaved} 条建议动作`,
        detail: `${response.message ?? "分析完成"}，分析 ${response.termsAnalyzed ?? 0} 条词。`,
        href: "/analysis",
      })
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <UploadMutationPanel payload={payload} onUploadComplete={handleUploadComplete} onAnalysisComplete={handleAnalysisComplete} />
      <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Import Center</div>
        <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">导入与批次建立</h3>
        <p className="mt-3 text-sm leading-relaxed text-zinc-500">当前真实数据已经接入：这里会优先提示最近导入日期、搜索词规模和最近形成的分析快照。</p>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">最近报表</div><div className="mt-2 text-base font-semibold text-zinc-950">{uploadState.latestReportDate ?? "暂无导入"}</div></div>
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">搜索词</div><div className="mt-2 text-base font-semibold text-zinc-950">{uploadState.searchTerms ?? 0}</div></div>
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">分析快照</div><div className="mt-2 text-base font-semibold text-zinc-950">{uploadState.snapshotCount ?? 0}</div></div>
        </div>
      </section>
      <section className="space-y-6">
        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">AI Import Brief</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">AI 导入摘要</h3>
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">最近导入后已经形成 {uploadState.snapshotCount ?? 0} 个分析快照，当前共有 {uploadState.campaigns ?? 0} 个活动可供分析。</p>
          {activityLog.length ? (
            <ul className="mt-4 space-y-2 text-sm leading-relaxed text-zinc-500">
              {activityLog.map((item) => (
                <li key={item} className="rounded-2xl bg-zinc-50 px-4 py-3">{item}</li>
              ))}
            </ul>
          ) : null}
          {fileFailures.length ? (
            <div className="mt-4 rounded-2xl bg-zinc-50 p-4">
              <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Failed files</div>
              <ul className="mt-3 space-y-2 text-sm leading-relaxed text-zinc-500">
                {fileFailures.map((item) => (
                  <li key={`${item.fileName}-${item.reason}`}>
                    <span className="font-medium text-zinc-900">{item.fileName}</span>：{item.reason}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">History</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">导入历史</h3>
          <div className="mt-4 space-y-3">
            {historyItems.length ? historyItems.map((item) => (
              <div key={item.key} className="rounded-2xl bg-zinc-50 p-4">
                <div className="text-sm font-medium text-zinc-950">{item.title}</div>
                <div className="mt-1 text-sm text-zinc-500">{item.detail}</div>
              </div>
            )) : <p className="text-sm leading-relaxed text-zinc-500">当前还没有导入历史快照。</p>}
          </div>
        </div>
      </section>
    </div>
  )
}
