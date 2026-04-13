"use client";

import { useMemo, useState } from "react";

import type { AnalysisPayload, AnalysisRow } from "@/lib/mock-data";
import { AnalysisTable } from "@/components/workbench-sections";

type Props = {
  payload: AnalysisPayload
}

type SortKey = "spend-desc" | "orders-desc" | "confidence-desc" | "term-asc"
type FocusMode = "all" | "stoploss" | "scale" | "review"

function parseCurrency(value: string) {
  return Number(value.replace(/[^\d.-]/g, "")) || 0
}

function parseConfidence(value: string) {
  const normalized = value.replace("%", "")
  return Number(normalized) || 0
}

function passesFocusMode(row: AnalysisRow, focusMode: FocusMode) {
  if (focusMode === "all") return true
  if (focusMode === "stoploss") return /否定|negative/i.test(row.action)
  if (focusMode === "scale") return /手动|补量|manual/i.test(row.action)
  if (focusMode === "review") return parseConfidence(row.confidence) < 100 || /冲突|审核|conflict/i.test(row.action)
  return true
}

export function AnalysisLivePanel({ payload }: Props) {
  const analysis = payload.analysis ?? { rowCount: 0, typeCounts: {} as Record<string, number>, actionCounts: {} as Record<string, number> }
  const [typeFilter, setTypeFilter] = useState<string>("all")
  const [actionFilter, setActionFilter] = useState<string>("all")
  const [query, setQuery] = useState("")
  const [sortKey, setSortKey] = useState<SortKey>("spend-desc")
  const [focusMode, setFocusMode] = useState<FocusMode>("all")

  const filteredRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    const base = (payload.analysisRows ?? []).filter((row: AnalysisRow) => {
      const typePass = typeFilter === "all" || row.type === typeFilter
      const actionPass = actionFilter === "all" || row.action === actionFilter
      const queryPass = !normalizedQuery || [row.term, row.type, row.rule, row.action].some((value) => value.toLowerCase().includes(normalizedQuery))
      const focusPass = passesFocusMode(row, focusMode)
      return typePass && actionPass && queryPass && focusPass
    })

    return [...base].sort((left, right) => {
      switch (sortKey) {
        case "orders-desc":
          return right.orders - left.orders
        case "confidence-desc":
          return parseConfidence(right.confidence) - parseConfidence(left.confidence)
        case "term-asc":
          return left.term.localeCompare(right.term, "zh-CN")
        case "spend-desc":
        default:
          return parseCurrency(right.spend) - parseCurrency(left.spend)
      }
    })
  }, [actionFilter, focusMode, payload.analysisRows, query, sortKey, typeFilter])

  const typeOptions = useMemo(() => ["all", ...Object.keys(analysis.typeCounts ?? {})], [analysis.typeCounts])
  const actionOptions = useMemo(() => ["all", ...Object.keys(analysis.actionCounts ?? {})], [analysis.actionCounts])
  const visibleActionCounts = useMemo(() => {
    return filteredRows.reduce<Record<string, number>>((acc, row) => {
      acc[row.action] = (acc[row.action] ?? 0) + 1
      return acc
    }, {})
  }, [filteredRows])
  const visibleTypeCounts = useMemo(() => {
    return filteredRows.reduce<Record<string, number>>((acc, row) => {
      acc[row.type] = (acc[row.type] ?? 0) + 1
      return acc
    }, {})
  }, [filteredRows])

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
      <div className="space-y-6">
        <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Interactive Filters</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">筛选与排序</h3>
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">先选一个视角，再按词类型、建议动作和关键词过滤，最后按花费、订单或置信度排序。</p>
          <div className="mt-5 flex flex-wrap gap-2">
            {[
              ["all", "全部视角"],
              ["stoploss", "止损优先"],
              ["scale", "补量机会"],
              ["review", "待人工拍板"],
            ].map(([value, label]) => (
              <button
                key={value}
                onClick={() => setFocusMode(value as FocusMode)}
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  focusMode === value ? "bg-zinc-950 text-white" : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <label className="flex flex-col gap-2 text-sm text-zinc-500 xl:col-span-2">
              <span className="font-medium text-zinc-900">搜索词 / 规则 / 动作</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索关键词、规则或动作…"
                className="rounded-2xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none placeholder:text-zinc-400"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-zinc-500">
              <span className="font-medium text-zinc-900">词类型</span>
              <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="rounded-2xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none">
                {typeOptions.map((option) => (
                  <option key={option} value={option}>{option === "all" ? "全部" : option}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-2 text-sm text-zinc-500">
              <span className="font-medium text-zinc-900">建议动作</span>
              <select value={actionFilter} onChange={(e) => setActionFilter(e.target.value)} className="rounded-2xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none">
                {actionOptions.map((option) => (
                  <option key={option} value={option}>{option === "all" ? "全部" : option}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
            <div className="flex flex-wrap gap-2">
              {Object.entries(visibleActionCounts).slice(0, 4).map(([action, count]) => (
                <span key={action} className="rounded-full bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-700">{action} {count}</span>
              ))}
            </div>
            <label className="flex flex-col gap-2 text-sm text-zinc-500 sm:min-w-40">
              <span className="font-medium text-zinc-900">排序方式</span>
              <select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)} className="rounded-2xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 outline-none">
                <option value="spend-desc">按花费降序</option>
                <option value="orders-desc">按订单降序</option>
                <option value="confidence-desc">按置信度降序</option>
                <option value="term-asc">按关键词排序</option>
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
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">当前真实分析结果共 {analysis.rowCount ?? 0} 行，筛选后还有 {filteredRows.length} 行。你可以先缩小到一个动作，再回到右侧 Copilot 追问为什么。</p>
        </div>
        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">View Modes</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">实时分布</h3>
          <div className="mt-5 grid gap-3">
            <div className="rounded-2xl bg-zinc-50 p-4">
              <div className="text-sm font-semibold tracking-tight text-zinc-950">动作分布</div>
              <div className="mt-2 text-sm leading-relaxed text-zinc-500">{Object.entries(visibleActionCounts).map(([k, v]) => `${k} ${v}`).join(" ｜ ") || "暂无"}</div>
            </div>
            <div className="rounded-2xl bg-zinc-50 p-4">
              <div className="text-sm font-semibold tracking-tight text-zinc-950">类型分布</div>
              <div className="mt-2 text-sm leading-relaxed text-zinc-500">{Object.entries(visibleTypeCounts).map(([k, v]) => `${k} ${v}`).join(" ｜ ") || "暂无"}</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
