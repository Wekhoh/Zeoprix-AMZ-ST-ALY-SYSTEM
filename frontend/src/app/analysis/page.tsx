import { DashboardShell } from "@/components/dashboard-shell";
import { AnalysisTable } from "@/components/workbench-sections";

export default function AnalysisPage() {
  return (
    <DashboardShell
      title="搜索词分析"
      subtitle="汇总、按活动、按 ASIN 三种视角放进同一套分析页面，而不是拆成零散页面。重构版会让 AI 卡片、diff、导出和过滤条件都共享同一个分析心智。"
    >
      <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
        <AnalysisTable />
        <section className="space-y-6">
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">AI Brief</div>
            <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">AI 汇总简报</h3>
            <p className="mt-3 text-sm leading-relaxed text-zinc-500">当前最大的经营问题仍然是泛词和高花费词混杂，建议先止损 travel pillow，再补量 best neck pillow。</p>
          </div>
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">View Modes</div>
            <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">三种分析视角</h3>
            <div className="mt-5 grid gap-3">
              {[
                ['汇总', '先定今日最优先的经营动作。'],
                ['按活动', '看哪个活动最差、最值得补量。'],
                ['按 ASIN', '看问题更像词问题还是页面问题。'],
              ].map(([title, desc]) => (
                <div key={title} className="rounded-2xl bg-zinc-50 p-4">
                  <div className="text-base font-semibold tracking-tight text-zinc-950">{title}</div>
                  <div className="mt-2 text-sm leading-relaxed text-zinc-500">{desc}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </DashboardShell>
  );
}
