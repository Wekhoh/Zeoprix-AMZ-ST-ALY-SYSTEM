"use client";

import { useEffect, useState } from "react";

import { recordFrontendActivity } from "@/components/live-activity";
import { writePageContext } from "@/components/page-context";
import { SettingsConfigPanel } from "@/components/settings-config-panel";
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

type ConfigMutationResponse = {
  status?: string
  message?: string
  ruleVersionCount?: number
  recentRuleVersions?: Array<{
    version: number
    createdAt: string
    description: string
  }>
  configEditor?: {
    coreKeywords: string[]
    relatedKeywords: string[]
    competitorAsins: string[]
    ownVariants: string[]
  }
}

type SettingsState = NonNullable<SettingsPayload["settings"]>

function buildInitialSettingsState(payload: SettingsPayload): SettingsState {
  return payload.settings ?? {
    ruleVersionCount: 0,
    strategyProfileCount: 0,
    keywordLibraryCounts: { irrelevant: 0, weak: 0, generic: 0, car: 0, variants: 0 },
    backupSummary: { searchTerms: 0, analysisResults: 0, manualReviews: 0, snapshots: 0, executionBatches: 0 },
    configEditor: { coreKeywords: [], relatedKeywords: [], competitorAsins: [], ownVariants: [] },
    recentRuleVersions: [],
  }
}

export function SettingsLivePanel({ payload }: Props) {
  const [settingsState, setSettingsState] = useState<SettingsState>(() => buildInitialSettingsState(payload))
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
      core_keywords: settingsState.configEditor.coreKeywords.join("、"),
    })
  }, [activityLog, backup.searchTerms, payload.productId, settingsState])

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

  function handleConfigSaved(response: ConfigMutationResponse) {
    const configEditor = response.configEditor
    if (!configEditor) return
    setSettingsState((current) => ({
      ...current,
      configEditor,
      ruleVersionCount: response.ruleVersionCount ?? current.ruleVersionCount,
      recentRuleVersions: response.recentRuleVersions ?? current.recentRuleVersions,
      keywordLibraryCounts: {
        ...current.keywordLibraryCounts,
        variants: configEditor.ownVariants.length,
      },
    }))
    const line = `已保存配置：核心词 ${configEditor.coreKeywords.length} 个，竞品 ASIN ${configEditor.competitorAsins.length} 个。`
    setActivityLog((current) => [line, ...current].slice(0, 4))
    recordFrontendActivity(payload.productId, {
      label: "最近配置",
      title: "规则与词库配置已更新",
      detail: line,
      href: "/settings",
    })
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
      <div className="space-y-6">
        <SettingsMutationPanel payload={payload} onRuntimeCleared={handleRuntimeCleared} onBackupRestored={handleBackupRestored} />
        <SettingsConfigPanel payload={{ ...payload, settings: settingsState }} onConfigSaved={handleConfigSaved} />
      </div>
      <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Configuration</div>
        <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">规则与产品配置</h3>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">规则版本</div><div className="mt-2 text-base font-semibold text-zinc-950">{settingsState.ruleVersionCount ?? 0}</div></div>
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">策略组合</div><div className="mt-2 text-base font-semibold text-zinc-950">{settingsState.strategyProfileCount ?? 0}</div></div>
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">不相关词库</div><div className="mt-2 text-base font-semibold text-zinc-950">{libs.irrelevant ?? 0}</div></div>
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">弱相关 / 泛词</div><div className="mt-2 text-base font-semibold text-zinc-950">{(libs.weak ?? 0) + (libs.generic ?? 0)}</div></div>
        </div>
        {settingsState.recentRuleVersions.length ? (
          <div className="mt-5 rounded-2xl bg-zinc-50 p-4">
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">最近配置版本</div>
            <div className="mt-3 space-y-2 text-sm leading-relaxed text-zinc-500">
              {settingsState.recentRuleVersions.slice(0, 3).map((item) => (
                <div key={`rule-version-${item.version}`} className="rounded-2xl bg-white px-4 py-3 ring-1 ring-zinc-200/80">
                  <div className="font-medium text-zinc-950">v{item.version} · {item.createdAt}</div>
                  <div className="mt-1">{item.description}</div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
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
