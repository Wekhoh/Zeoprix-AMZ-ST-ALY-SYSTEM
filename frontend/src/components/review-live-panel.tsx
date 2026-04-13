"use client";

import { useMemo, useState } from "react";

import { ReviewMutationPanel } from "@/components/review-mutation-panel";
import type { ReviewPayload } from "@/lib/mock-data";

type Props = {
  payload: ReviewPayload
  backendBaseUrl: string
}

type ReviewMutationResponse = {
  reviewId: number
  stats?: {
    total?: number
    reviewed?: number
    pending?: number
  }
}

export function ReviewLivePanel({ payload, backendBaseUrl }: Props) {
  const [reviewState, setReviewState] = useState(
    payload.review ?? { stats: { total: 0, reviewed: 0, pending: 0 }, pendingItems: [] },
  )

  const mutationPayload = useMemo(
    () => ({
      ...payload,
      review: reviewState,
    }),
    [payload, reviewState],
  )

  function handleDecisionSubmitted(term: string, response: ReviewMutationResponse) {
    setReviewState((current) => ({
      stats: {
        total: response.stats?.total ?? current.stats.total,
        reviewed: response.stats?.reviewed ?? current.stats.reviewed,
        pending: response.stats?.pending ?? Math.max(current.stats.pending - 1, 0),
      },
      pendingItems: current.pendingItems.filter((item) => item.term !== term),
    }))
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_0.95fr]">
      <ReviewMutationPanel
        payload={mutationPayload}
        backendBaseUrl={backendBaseUrl}
        onDecisionSubmitted={handleDecisionSubmitted}
      />
      <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Review Queue</div>
        <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">人工审核工作区</h3>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">总数</div><div className="mt-2 text-base font-semibold text-zinc-950">{reviewState.stats.total ?? 0}</div></div>
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">已审核</div><div className="mt-2 text-base font-semibold text-zinc-950">{reviewState.stats.reviewed ?? 0}</div></div>
          <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">待审核</div><div className="mt-2 text-base font-semibold text-zinc-950">{reviewState.stats.pending ?? 0}</div></div>
        </div>
        <div className="mt-5 space-y-3">
          {reviewState.pendingItems.length ? reviewState.pendingItems.map((item) => (
            <div key={`${item.term}-${item.campaignName}`} className="rounded-2xl bg-zinc-50 p-4">
              <div className="text-sm font-medium text-zinc-950">{item.term}</div>
              <div className="mt-1 text-sm text-zinc-500">{item.campaignName} ｜ {item.termType} ｜ {item.createdAt}</div>
            </div>
          )) : <p className="text-sm leading-relaxed text-zinc-500">当前没有待审核项。</p>}
        </div>
      </section>
      <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">AI Review Brief</div>
        <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">AI 审核建议</h3>
        <p className="mt-3 text-sm leading-relaxed text-zinc-500">当前待审核队列已接入真实后端数据，提交人工判断后会直接在当前页面收缩队列，不再整页刷新。</p>
      </section>
    </div>
  )
}
