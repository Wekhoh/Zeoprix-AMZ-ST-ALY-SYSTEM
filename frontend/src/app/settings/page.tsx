import { getSettingsPayload } from "@/lib/backend";
import { DashboardShell } from "@/components/dashboard-shell";
import { SettingsMutationPanel } from "@/components/settings-mutation-panel";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const payload = await getSettingsPayload();
  const settings = payload.settings ?? {
    ruleVersionCount: 0,
    strategyProfileCount: 0,
    keywordLibraryCounts: { irrelevant: 0, weak: 0, generic: 0, car: 0, variants: 0 },
    backupSummary: { searchTerms: 0, analysisResults: 0, manualReviews: 0, snapshots: 0, executionBatches: 0 },
  };
  const libs = settings.keywordLibraryCounts;
  const backup = settings.backupSummary;
  return (
    <DashboardShell
      title="数据管理与系统设置"
      subtitle="把长期配置和运行时数据操作彻底分开：一边是规则和词库，一边是清空、备份、恢复。"
      productId={payload.productId}
      productContext={payload.productContext}
      aiCard={payload.aiCopilotCards[0]}
    >
      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <SettingsMutationPanel payload={payload} />
        <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Configuration</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">规则与产品配置</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">规则版本</div><div className="mt-2 text-base font-semibold text-zinc-950">{settings.ruleVersionCount ?? 0}</div></div>
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">策略组合</div><div className="mt-2 text-base font-semibold text-zinc-950">{settings.strategyProfileCount ?? 0}</div></div>
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">不相关词库</div><div className="mt-2 text-base font-semibold text-zinc-950">{libs.irrelevant ?? 0}</div></div>
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">弱相关 / 泛词</div><div className="mt-2 text-base font-semibold text-zinc-950">{(libs.weak ?? 0) + (libs.generic ?? 0)}</div></div>
          </div>
        </section>
        <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Data Management</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">清空、备份、恢复</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">搜索词</div><div className="mt-2 text-base font-semibold text-zinc-950">{backup.searchTerms ?? 0}</div></div>
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">分析结果</div><div className="mt-2 text-base font-semibold text-zinc-950">{backup.analysisResults ?? 0}</div></div>
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">审核记录</div><div className="mt-2 text-base font-semibold text-zinc-950">{backup.manualReviews ?? 0}</div></div>
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">执行批次</div><div className="mt-2 text-base font-semibold text-zinc-950">{backup.executionBatches ?? 0}</div></div>
          </div>
        </section>
      </div>
    </DashboardShell>
  );
}
