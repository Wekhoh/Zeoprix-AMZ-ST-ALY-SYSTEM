"use client";

import { useMemo, useState } from "react";

import type { AnalysisPayload, AnalysisRow } from "@/lib/mock-data";
import { AnalysisTable } from "@/components/workbench-sections";

type Props = {
  payload: AnalysisPayload
}

export function AnalysisLivePanel({ payload }: Props) {
  const analysis = payload.analysis ?? { rowCount: 0, typeCounts: {} as Record<string, number>, actionCounts: {} as Record<string, number> }
  const [typeFilter, setTypeFilter] = useState<string>("all")
  const [actionFilter, setActionFilter] = useState<string>("all")

  const filteredRows = useMemo(() => {
    return (payload.analysisRows ?? []).filter((row: AnalysisRow) => {
      const typePass = typeFilter === "all" || row.type === typeFilter
      const actionPass = actionFilter === "all" || row.action === actionFilter
      return typePass && actionPass
    })
  }, [payload.analysisRows, typeFilter, actionFilter])

  const typeOptions = useMemo(() => ["all", ...Object.keys(analysis.typeCounts ?? {})], [analysis.typeCounts])
  const actionOptions = useMemo(() => ["all", ...Object.keys(analysis.actionCounts ?? {})], [analysis.actionCounts])

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
      <div className="space-y-6">
        <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Interactive Filters</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">筛选与切换</h3>
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">先按词类型和建议动作过滤，再看明细表，避免一次盯太多信息。</p>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-2 text-sm text-zinc-500">
              <span className="font-medium text-zinc-900">词类型</span>
              <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="rounded-2xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none">
                {typeOptions.map((option) => (
                  <option key={option} value={option}>{option === 'all' ? '全部' : option}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-2 text-sm text-zinc-500">
              <span className="font-medium text-zinc-900">建议动作</span>
              <select value={actionFilter} onChange={(e) => setActionFilter(e.target.value)} className="rounded-2xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none">
                {actionOptions.map((option) => (
                  <option key={option} value={option}>{option === 'all' ? '全部' : option}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="mt-4 text-sm text-zinc-500">当前显示 {filteredRows.length} / {analysis.rowCount ?? 0} 条结果</div>
        </section>
        <AnalysisTable analysisRows={filteredRows} />
      </div>

      <section className="space-y-6">
        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">AI Brief</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">AI 汇总简报</h3>
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">当前真实分析结果共 {analysis.rowCount ?? 0} 行，主要动作分布和类型分布已经开始从后端同步。</p>
        </div>
        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">View Modes</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">实时分布</h3>
          <div className="mt-5 grid gap-3">
            <div className="rounded-2xl bg-zinc-50 p-4">
              <div className="text-sm font-semibold tracking-tight text-zinc-950">动作分布</div>
              <div className="mt-2 text-sm leading-relaxed text-zinc-500">{Object.entries(analysis.actionCounts ?? {}).map(([k, v]) => `${k} ${v}`).join(' ｜ ') || '暂无'}</div>
            </div>
            <div className="rounded-2xl bg-zinc-50 p-4">
              <div className="text-sm font-semibold tracking-tight text-zinc-950">类型分布</div>
              <div className="mt-2 text-sm leading-relaxed text-zinc-500">{Object.entries(analysis.typeCounts ?? {}).map(([k, v]) => `${k} ${v}`).join(' ｜ ') || '暂无'}</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
