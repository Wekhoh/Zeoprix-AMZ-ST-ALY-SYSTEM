import { DashboardShell } from "@/components/dashboard-shell";

export default function ReviewPage() {
  return (
    <DashboardShell title="审核中心" subtitle="把 AI 建议和人工拍板彻底分开。重构版会围绕相似词、采纳记录和风险提示提升审核效率。">
      <div className="grid gap-6 xl:grid-cols-[1fr_0.95fr]">
        <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Review Queue</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">人工审核工作区</h3>
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">这里会围绕相似词、AI 建议采纳、风险提示和批量审核效率做重构，不再是传统表单页。</p>
        </section>
        <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">AI Review Brief</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">AI 审核建议</h3>
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">先解释为什么这么判，再决定是否采纳。后续会在这里直接记录 accepted / rejected / ignored。</p>
        </section>
      </div>
    </DashboardShell>
  );
}
