"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { ActionsPayload } from "@/lib/mock-data";

type Props = {
  payload: ActionsPayload
  backendBaseUrl: string
}

export function ActionsMutationPanel({ payload, backendBaseUrl }: Props) {
  const router = useRouter()
  const productId = payload.productId
  const [note, setNote] = useState("")
  const [message, setMessage] = useState<string | null>(null)
  const [pending, startTransition] = useTransition()

  const latestBatch = payload.executionBatches?.[0]

  async function createBatch(batchType: string) {
    if (!productId) return
    setMessage(null)
    startTransition(async () => {
      const response = await fetch(`${backendBaseUrl}/frontend/actions/execution-batches`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, batch_type: batchType, draft_note: note || undefined }),
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({ detail: "创建失败" }))
        setMessage(body.detail ?? "创建失败")
        return
      }
      setMessage(batchType === "negative" ? "否词执行批次已生成" : "手动投放批次已生成")
      router.refresh()
    })
  }

  async function advanceBatch(status: "executed" | "reviewed") {
    if (!latestBatch?.id) return
    setMessage(null)
    startTransition(async () => {
      const response = await fetch(`${backendBaseUrl}/frontend/actions/execution-batches/${latestBatch.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, execution_note: status === "executed" ? note || undefined : undefined, review_note: status === "reviewed" ? note || undefined : undefined }),
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({ detail: "更新失败" }))
        setMessage(body.detail ?? "更新失败")
        return
      }
      setMessage(status === "executed" ? "批次已标记为已执行" : "批次已标记为已复盘")
      router.refresh()
    })
  }

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Write Path</div>
      <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">执行操作</h3>
      <p className="mt-3 text-sm leading-relaxed text-zinc-500">直接从新前端创建执行批次，并推进最近批次的状态。</p>
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        className="mt-5 min-h-24 w-full rounded-2xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-900 outline-none placeholder:text-zinc-400"
        placeholder="填写这批动作的执行备注或复盘备注…"
      />
      <div className="mt-4 flex flex-wrap gap-3">
        <button disabled={pending || !productId} onClick={() => createBatch("negative")} className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50">
          生成否词批次
        </button>
        <button disabled={pending || !productId} onClick={() => createBatch("manual")} className="rounded-full border border-zinc-200 bg-white px-5 py-2.5 text-sm font-medium text-zinc-900 shadow-sm transition hover:bg-zinc-50 disabled:opacity-50">
          生成手动批次
        </button>
        <button disabled={pending || !latestBatch} onClick={() => advanceBatch("executed")} className="rounded-full border border-zinc-200 bg-white px-5 py-2.5 text-sm font-medium text-zinc-900 shadow-sm transition hover:bg-zinc-50 disabled:opacity-50">
          标记最近批次已执行
        </button>
        <button disabled={pending || !latestBatch} onClick={() => advanceBatch("reviewed")} className="rounded-full border border-zinc-200 bg-white px-5 py-2.5 text-sm font-medium text-zinc-900 shadow-sm transition hover:bg-zinc-50 disabled:opacity-50">
          标记最近批次已复盘
        </button>
      </div>
      {message ? <p className="mt-4 text-sm leading-relaxed text-zinc-500">{message}</p> : null}
    </section>
  )
}
