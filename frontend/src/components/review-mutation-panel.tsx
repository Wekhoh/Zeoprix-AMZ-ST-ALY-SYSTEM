"use client";

import { useState, useTransition } from "react";

import type { ReviewPayload } from "@/lib/mock-data";

type Props = {
  payload: ReviewPayload
  backendBaseUrl: string
  onDecisionSubmitted?: (itemKey: string, response: ReviewMutationResponse, decisionLabel: string) => void
}

type ReviewMutationResponse = {
  reviewId: number
  stats?: {
    total?: number
    reviewed?: number
    pending?: number
  }
}

function buildReviewKey(item: NonNullable<ReviewPayload["review"]>["pendingItems"][number]) {
  return `${item.term}::${item.campaignName}::${item.createdAt}`
}

function formatDecisionLabel(relevance: string) {
  switch (relevance) {
    case "strong_core":
      return "强相关"
    case "generic":
      return "泛词"
    case "irrelevant":
      return "不相关"
    default:
      return relevance
  }
}

export function ReviewMutationPanel({ payload, backendBaseUrl, onDecisionSubmitted }: Props) {
  const review = payload.review
  const productId = payload.productId
  const [notes, setNotes] = useState<Record<string, string>>({})
  const [message, setMessage] = useState<string | null>(null)
  const [pending, startTransition] = useTransition()

  async function submitDecision(item: NonNullable<ReviewPayload["review"]>["pendingItems"][number], relevance: string) {
    if (!productId) return
    setMessage(null)
    startTransition(async () => {
      const response = await fetch(`${backendBaseUrl}/frontend/review/manual-reviews`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: productId,
          term: item.term,
          term_type: item.termType,
          campaign_id: item.campaignId ?? null,
          relevance,
          notes: notes[item.term] || undefined,
        }),
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({ detail: "提交失败" }))
        setMessage(body.detail ?? "提交失败")
        return
      }
      const body = (await response.json().catch(() => ({}))) as ReviewMutationResponse
      setMessage(`已提交 ${item.term} 的人工审核：${formatDecisionLabel(relevance)}`)
      onDecisionSubmitted?.(buildReviewKey(item), body, formatDecisionLabel(relevance))
      setNotes((current) => {
        const next = { ...current }
        delete next[item.term]
        return next
      })
    })
  }

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Write Path</div>
      <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">审核操作</h3>
      <p className="mt-3 text-sm leading-relaxed text-zinc-500">直接在新前端里提交人工相关性判断，刷新后队列会减少。</p>
      <div className="mt-5 space-y-4">
        {(review?.pendingItems ?? []).slice(0, 5).map((item) => (
          <div key={buildReviewKey(item)} className="rounded-2xl bg-zinc-50 p-4">
            <div className="text-sm font-medium text-zinc-950">{item.term}</div>
            <div className="mt-1 text-sm text-zinc-500">{item.campaignName} ｜ {item.termType}</div>
            <textarea
              value={notes[item.term] ?? ""}
              onChange={(e) => setNotes((current) => ({ ...current, [item.term]: e.target.value }))}
              className="mt-3 min-h-20 w-full rounded-2xl border border-zinc-200 bg-white p-3 text-sm text-zinc-900 outline-none placeholder:text-zinc-400"
              placeholder="补充人工判断备注（可选）"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <button disabled={pending} onClick={() => submitDecision(item, "strong_core")} className="rounded-full bg-zinc-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50">标记强相关</button>
              <button disabled={pending} onClick={() => submitDecision(item, "generic")} className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-900 shadow-sm transition hover:bg-zinc-50 disabled:opacity-50">标记泛词</button>
              <button disabled={pending} onClick={() => submitDecision(item, "irrelevant")} className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-900 shadow-sm transition hover:bg-zinc-50 disabled:opacity-50">标记不相关</button>
            </div>
          </div>
        ))}
      </div>
      {message ? <p className="mt-4 text-sm leading-relaxed text-zinc-500">{message}</p> : null}
    </section>
  )
}
