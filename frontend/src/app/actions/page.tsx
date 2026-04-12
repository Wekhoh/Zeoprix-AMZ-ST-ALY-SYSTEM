import { getActionsPayload } from "@/lib/backend";
import { ActionsMutationPanel } from "@/components/actions-mutation-panel";
import { DashboardShell } from "@/components/dashboard-shell";
import { ExecutionBatchBoard } from "@/components/workbench-sections";

export const dynamic = "force-dynamic";

export default async function ActionsPage() {
  const payload = await getActionsPayload();
  const actions = payload.actions ?? { negativeCount: 0, manualCount: 0, conflictCount: 0, latestBatchCode: null };
  return (
    <DashboardShell
      title="操作清单与执行批次"
      subtitle="把建议、执行、复盘收进同一条工作流：先生成批次，再标记执行，最后在这里看 verdict 与 Top changes。"
      productContext={payload.productContext}
      aiCard={payload.aiCopilotCards[0]}
    >
      <div className="space-y-6">
        <ActionsMutationPanel payload={payload} backendBaseUrl={process.env.BACKEND_BASE_URL ?? process.env.NEXT_PUBLIC_BACKEND_BASE_URL ?? "http://127.0.0.1:8000"} />
        <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Action Workbench</div>
            <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">今日执行清单</h3>
            <p className="mt-3 text-sm leading-relaxed text-zinc-500">当前待执行：否词 {actions.negativeCount} ｜ 手动补量 {actions.manualCount} ｜ 分歧词 {actions.conflictCount}。</p>
          </div>
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Execution Layer</div>
            <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">批次状态推进</h3>
            <p className="mt-3 text-sm leading-relaxed text-zinc-500">最近批次：{actions.latestBatchCode ?? '暂无批次'}。后续会在这个页面继续接入真正的创建 / 标记执行写操作。</p>
          </div>
        </section>
        <ExecutionBatchBoard executionBatches={payload.executionBatches} />
      </div>
    </DashboardShell>
  );
}
