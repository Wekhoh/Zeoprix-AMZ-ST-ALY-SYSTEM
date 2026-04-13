import { getAnalysisPayload } from "@/lib/backend";
import { DashboardShell } from "@/components/dashboard-shell";
import { AnalysisTable } from "@/components/workbench-sections";

export const dynamic = "force-dynamic";

export default async function AnalysisPage() {
  const payload = await getAnalysisPayload();
  const analysis = payload.analysis ?? { rowCount: 0, typeCounts: {} as Record<string, number>, actionCounts: {} as Record<string, number> };
  return (
    <DashboardShell
      title="搜索词分析"
      subtitle="汇总、按活动、按 ASIN 三种视角放进同一套分析页面，而不是拆成零散页面。"
      productId={payload.productId}
      productContext={payload.productContext}
      aiCard={payload.aiCopilotCards[0]}
    >
      <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
        <AnalysisTable analysisRows={payload.analysisRows} />
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
    </DashboardShell>
  );
}
