"use client";

import { useEffect, useState } from "react";

import { recordFrontendActivity } from "@/components/live-activity";
import { writePageContext } from "@/components/page-context";
import { SettingsMutationPanel } from "@/components/settings-mutation-panel";
import type { SettingsPayload } from "@/lib/mock-data";

type Props = {
  payload: SettingsPayload
}

type RestoreBackupResponse = {
  status?: string
  restoredProductId?: number
  productName?: string
}

export function SettingsLivePanel({ payload }: Props) {
  const [settingsState, setSettingsState] = useState(
    payload.settings ?? {
      ruleVersionCount: 0,
      strategyProfileCount: 0,
      keywordLibraryCounts: { irrelevant: 0, weak: 0, generic: 0, car: 0, variants: 0 },
      backupSummary: { searchTerms: 0, analysisResults: 0, manualReviews: 0, snapshots: 0, executionBatches: 0 },
    },
  )
  const [activityLog, setActivityLog] = useState<string[]>([])

  const libs = settingsState.keywordLibraryCounts
  const backup = settingsState.backupSummary

  useEffect(() => {
    const latestActivity = activityLog[0] ?? null
    writePageContext(payload.productId, "settings", {
      summary: `规则 ${settingsState.ruleVersionCount ?? 0} 个版本，策略 ${settingsState.strategyProfileCount ?? 0} 组，当前备份包含 ${backup.searchTerms ?? 0} 条搜索词${latestActivity ? `；最近操作：${latestActivity}` : ""}。`,
      rule_versions: settingsState.ruleVersionCount ?? 0,
      strategy_profiles: settingsState.strategyProfileCount ?? 0,
      backup_terms: backup.searchTerms ?? 0,
      latest_activity: latestActivity,
    })
  }, [activityLog, backup.searchTerms, payload.productId, settingsState.ruleVersionCount, settingsState.strategyProfileCount])

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
    }))
    setActivityLog((current) => ["已清空当前产品的运行数据。", ...current].slice(0, 4))
    recordFrontendActivity(payload.productId, {
      label: "最近数据管理",
      title: "运行数据已清空",
      detail: "当前产品的搜索词、分析结果、审核记录与执行批次都已清空。",
      href: "/settings",
    })
  }

  function handleBackupRestored(response: RestoreBackupResponse, restoreAsNew: boolean) {
    const line = `${restoreAsNew ? "已恢复为新产品副本" : "已恢复到当前产品"}：${response.productName ?? "恢复产品"}`
    setActivityLog((current) => [line, ...current].slice(0, 4))
    recordFrontendActivity(payload.productId, {
      label: "最近数据管理",
      title: restoreAsNew ? "完整备份已恢复为新副本" : "完整备份已恢复到当前产品",
      detail: line,
      href: "/settings",
    })
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
      <SettingsMutationPanel payload={payload} onRuntimeCleared={handleRuntimeCleared} onBackupRestored={handleBackupRestored} />
      <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Configuration</div>
        <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">规则与产品配置</h3>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">规则版本</div><div className="mt-2 text-base font-semibold text-zinc-950">{settingsState.ruleVersionCount ?? 0}</div></div>
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">策略组合</div><div className="mt-2 text-base font-semibold text-zinc-950">{settingsState.strategyProfileCount ?? 0}</div></div>
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">不相关词库</div><div className="mt-2 text-base font-semibold text-zinc-950">{libs.irrelevant ?? 0}</div></div>
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">弱相关 / 泛词</div><div className="mt-2 text-base font-semibold text-zinc-950">{(libs.weak ?? 0) + (libs.generic ?? 0)}</div></div>
        </div>
      </section>
      <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Data Management</div>
        <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">清空、备份、恢复</h3>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">搜索词</div><div className="mt-2 text-base font-semibold text-zinc-950">{backup.searchTerms ?? 0}</div></div>
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">分析结果</div><div className="mt-2 text-base font-semibold text-zinc-950">{backup.analysisResults ?? 0}</div></div>
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">审核记录</div><div className="mt-2 text-base font-semibold text-zinc-950">{backup.manualReviews ?? 0}</div></div>
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">执行批次</div><div className="mt-2 text-base font-semibold text-zinc-950">{backup.executionBatches ?? 0}</div></div>
        </div>
        {activityLog.length ? (
          <div className="mt-5 space-y-2">
            {activityLog.map((item) => (
              <div key={item} className="rounded-2xl bg-zinc-50 px-4 py-3 text-sm leading-relaxed text-zinc-500">{item}</div>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  )
}
