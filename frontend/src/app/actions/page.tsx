import { getWorkbenchPayload } from "@/lib/backend";
import { DashboardShell } from "@/components/dashboard-shell";
import { ExecutionBatchBoard } from "@/components/workbench-sections";

export const dynamic = "force-dynamic";

export default async function ActionsPage() {
  const payload = await getWorkbenchPayload();
  return (
    <DashboardShell
      title="操作清单与执行批次"
      subtitle="把建议、执行、复盘收进同一条工作流：先生成批次，再标记执行，最后在这里看 verdict 与 Top changes。"
      productContext={payload.productContext}
      aiCard={payload.aiCopilotCards[0]}
    >
      <div className="space-y-6">
        <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Action Workbench</div>
            <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">今日执行清单</h3>
            <p className="mt-3 text-sm leading-relaxed text-zinc-500">否词和手动投放不再只是导出按钮，而是可以先生成执行批次，再记录执行与复盘。</p>
          </div>
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Execution Layer</div>
            <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">批次状态推进</h3>
            <p className="mt-3 text-sm leading-relaxed text-zinc-500">先准备、再执行、再复盘。重构版会把每一批动作看成一个真正的可追踪对象，而不是 Excel 导出动作。</p>
          </div>
        </section>
        <ExecutionBatchBoard executionBatches={payload.executionBatches} />
      </div>
    </DashboardShell>
  );
}
