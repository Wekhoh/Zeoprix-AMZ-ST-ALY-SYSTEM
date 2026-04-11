import { DashboardShell } from "@/components/dashboard-shell";
import { ExecutionBatchBoard } from "@/components/workbench-sections";

export default function ActionsPage() {
  return (
    <DashboardShell
      title="操作清单与执行批次"
      subtitle="把建议、执行、复盘收进同一条工作流：先生成批次，再标记执行，最后在这里看 verdict 与 Top changes。"
    >
      <div className="space-y-6">
        <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <div className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Action Workbench</div>
            <h3 className="mt-2 text-2xl font-semibold text-white">今日执行清单</h3>
            <p className="mt-3 text-sm leading-7 text-slate-400">否词和手动投放不再只是导出按钮，而是可以先生成执行批次，再记录执行与复盘。</p>
          </div>
          <div className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Execution Layer</div>
            <h3 className="mt-2 text-2xl font-semibold text-white">批次状态推进</h3>
            <p className="mt-3 text-sm leading-7 text-slate-400">先准备、再执行、再复盘。重构版会把每一批动作看成一个真正的可追踪对象，而不是 Excel 导出动作。</p>
          </div>
        </section>
        <ExecutionBatchBoard />
      </div>
    </DashboardShell>
  );
}
