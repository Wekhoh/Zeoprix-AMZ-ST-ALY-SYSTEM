import { getReviewPayload } from "@/lib/backend";
import { DashboardShell } from "@/components/dashboard-shell";
import { ReviewMutationPanel } from "@/components/review-mutation-panel";

export const dynamic = "force-dynamic";

export default async function ReviewPage() {
  const payload = await getReviewPayload();
  const review = payload.review ?? { stats: { total: 0, reviewed: 0, pending: 0 }, pendingItems: [] as Array<{ term: string; termType: string; campaignName: string; relevance: string; createdAt: string }> };
  return (
    <DashboardShell
      title="审核中心"
      subtitle="把 AI 建议和人工拍板彻底分开。重构版会围绕相似词、采纳记录和风险提示提升审核效率。"
      productContext={payload.productContext}
      aiCard={payload.aiCopilotCards[0]}
    >
      <div className="grid gap-6 xl:grid-cols-[1fr_0.95fr]">
        <ReviewMutationPanel payload={payload} backendBaseUrl={process.env.BACKEND_BASE_URL ?? process.env.NEXT_PUBLIC_BACKEND_BASE_URL ?? "http://127.0.0.1:8000"} />
        <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Review Queue</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">人工审核工作区</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">总数</div><div className="mt-2 text-base font-semibold text-zinc-950">{review.stats.total ?? 0}</div></div>
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">已审核</div><div className="mt-2 text-base font-semibold text-zinc-950">{review.stats.reviewed ?? 0}</div></div>
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">待审核</div><div className="mt-2 text-base font-semibold text-zinc-950">{review.stats.pending ?? 0}</div></div>
          </div>
          <div className="mt-5 space-y-3">
            {(review.pendingItems ?? []).length ? review.pendingItems.map((item) => (
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
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">当前待审核队列已接入真实后端数据，下一步会把人工采纳 / 驳回动作也直接接到这里。</p>
        </section>
      </div>
    </DashboardShell>
  );
}
