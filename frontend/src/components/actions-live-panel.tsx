"use client";

import { useMemo, useState } from "react";

import { ActionsMutationPanel } from "@/components/actions-mutation-panel";
import { ExecutionBatchBoard } from "@/components/workbench-sections";
import type { ActionsPayload, ExecutionBatch } from "@/lib/mock-data";

type Props = {
  payload: ActionsPayload
  backendBaseUrl: string
}

type BatchMutationResponse = {
  id?: number
  batch_code?: string
  batch_type?: string
  status?: string
  summary?: {
    item_count?: number
    spend_total?: number
    sales_total?: number
  }
  verdict?: string
  effect_summary?: {
    status?: string
    summary?: string
    top_improving_terms?: string[]
    top_risky_terms?: string[]
  }
}

function normalizeBatch(response: BatchMutationResponse): ExecutionBatch {
  return {
    id: response.id,
    code: response.batch_code ?? "批次",
    type: response.batch_type ?? "执行批次",
    status: response.status ?? "draft",
    itemCount: response.summary?.item_count ?? 0,
    spend: `$${Number(response.summary?.spend_total ?? 0).toFixed(2)}`,
    sales: `$${Number(response.summary?.sales_total ?? 0).toFixed(2)}`,
    verdict: response.effect_summary?.status ?? response.verdict ?? "待观察",
    summary: response.effect_summary?.summary ?? "暂无批次说明。",
    improving: response.effect_summary?.top_improving_terms ?? [],
    risky: response.effect_summary?.top_risky_terms ?? [],
  }
}

function buildActionLog(line: string, previous: string[]) {
  return [line, ...previous].slice(0, 4)
}

export function ActionsLivePanel({ payload, backendBaseUrl }: Props) {
  const [executionBatches, setExecutionBatches] = useState<ExecutionBatch[]>(payload.executionBatches ?? [])
  const [actions, setActions] = useState(payload.actions ?? { negativeCount: 0, manualCount: 0, conflictCount: 0, latestBatchCode: null as string | null })
  const [activityLog, setActivityLog] = useState<string[]>([])

  const latestBatch = executionBatches[0]

  const mutationPanelPayload = useMemo(
    () => ({
      ...payload,
      actions,
      executionBatches,
    }),
    [actions, executionBatches, payload],
  )

  function handleBatchCreated(response: BatchMutationResponse, batchType: string) {
    const batch = normalizeBatch(response)
    setExecutionBatches((current) => [batch, ...current.filter((item) => item.id !== batch.id)].slice(0, 5))
    setActions((current) => ({
      ...current,
      latestBatchCode: batch.code,
    }))
    setActivityLog((current) =>
      buildActionLog(
        `${batchType === "negative" ? "已生成否词批次" : "已生成手动批次"} ${batch.code}，覆盖 ${batch.itemCount} 项。`,
        current,
      ),
    )
  }

  function handleBatchUpdated(response: BatchMutationResponse) {
    const batch = normalizeBatch(response)
    setExecutionBatches((current) => current.map((item) => (item.id === batch.id ? batch : item)))
    setActions((current) => ({
      ...current,
      latestBatchCode: batch.code,
    }))
    setActivityLog((current) => buildActionLog(`批次 ${batch.code} 已更新为 ${batch.status}。`, current))
  }

  return (
    <div className="space-y-6">
      <ActionsMutationPanel
        payload={mutationPanelPayload}
        backendBaseUrl={backendBaseUrl}
        onBatchCreated={handleBatchCreated}
        onBatchUpdated={handleBatchUpdated}
      />
      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Action Workbench</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">今日执行清单</h3>
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">当前待执行：否词 {actions.negativeCount} ｜ 手动补量 {actions.manualCount} ｜ 分歧词 {actions.conflictCount}。</p>
          {activityLog.length ? (
            <div className="mt-4 space-y-2">
              {activityLog.map((item) => (
                <div key={item} className="rounded-2xl bg-zinc-50 px-4 py-3 text-sm leading-relaxed text-zinc-500">{item}</div>
              ))}
            </div>
          ) : null}
        </div>
        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Execution Layer</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">批次状态推进</h3>
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">最近批次：{latestBatch?.code ?? actions.latestBatchCode ?? "暂无批次"}。所有动作现在都直接写回后端，并同步到当前页面。</p>
        </div>
      </section>
      <ExecutionBatchBoard executionBatches={executionBatches} />
    </div>
  )
}
