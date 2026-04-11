import { DashboardShell } from "@/components/dashboard-shell";

export default function ReviewPage() {
  return (
    <DashboardShell title="审核中心" subtitle="把 AI 建议和人工拍板彻底分开。重构版会围绕相似词、采纳记录和风险提示提升审核效率。">
      <div className="grid gap-6 xl:grid-cols-[1fr_0.95fr]">
        <section className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
          <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Review Queue</div>
          <h3 className="mt-2 text-2xl font-semibold text-white">人工审核工作区</h3>
          <p className="mt-3 text-sm leading-7 text-slate-400">这里会围绕相似词、AI 建议采纳、风险提示和批量审核效率做重构，不再是传统表单页。</p>
        </section>
        <section className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
          <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">AI Review Brief</div>
          <h3 className="mt-2 text-2xl font-semibold text-white">AI 审核建议</h3>
          <p className="mt-3 text-sm leading-7 text-slate-400">先解释为什么这么判，再决定是否采纳。后续会在这里直接记录 accepted / rejected / ignored。</p>
        </section>
      </div>
    </DashboardShell>
  );
}
