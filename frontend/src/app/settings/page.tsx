import { getWorkbenchPayload } from "@/lib/backend";
import { DashboardShell } from "@/components/dashboard-shell";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const payload = await getWorkbenchPayload();
  return (
    <DashboardShell
      title="数据管理与系统设置"
      subtitle="把长期配置和运行时数据操作彻底分开：一边是规则和词库，一边是清空、备份、恢复。"
      productContext={payload.productContext}
      aiCard={payload.aiCopilotCards[0]}
    >
      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Configuration</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">规则与产品配置</h3>
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">这里会承接规则阈值、关键词库、产品信息、AI 配置等长期设置项。</p>
        </section>
        <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Data Management</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">清空、备份、恢复</h3>
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">这里会明确展示最近一次分析、最近一次备份、最近一次恢复，以及所有危险操作会影响哪些资产。</p>
        </section>
      </div>
    </DashboardShell>
  );
}
