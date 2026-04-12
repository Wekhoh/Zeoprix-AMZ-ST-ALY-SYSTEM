import { getUploadPayload } from "@/lib/backend";
import { DashboardShell } from "@/components/dashboard-shell";

export const dynamic = "force-dynamic";

export default async function UploadPage() {
  const payload = await getUploadPayload();
  const upload = payload.upload ?? {
    latestReportDate: "暂无导入",
    searchTerms: 0,
    campaigns: 0,
    snapshotCount: 0,
    recentSnapshots: [],
    recentCampaigns: [],
  };
  const snapshots = upload.recentSnapshots;
  const campaigns = upload.recentCampaigns;
  return (
    <DashboardShell
      title="数据导入"
      subtitle="把导入从技术动作重构成运营节奏的入口：先看数据健康，再决定是否建立新一轮分析。"
      productContext={payload.productContext}
      aiCard={payload.aiCopilotCards[0]}
    >
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Import Center</div>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">导入与批次建立</h3>
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">当前真实数据已经接入：这里会优先提示最近导入日期、搜索词规模和最近形成的分析快照。</p>
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">最近报表</div><div className="mt-2 text-base font-semibold text-zinc-950">{upload.latestReportDate ?? "暂无导入"}</div></div>
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">搜索词</div><div className="mt-2 text-base font-semibold text-zinc-950">{upload.searchTerms ?? 0}</div></div>
            <div className="rounded-2xl bg-zinc-50 p-4"><div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">分析快照</div><div className="mt-2 text-base font-semibold text-zinc-950">{upload.snapshotCount ?? 0}</div></div>
          </div>
        </section>
        <section className="space-y-6">
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">AI Import Brief</div>
            <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">AI 导入摘要</h3>
            <p className="mt-3 text-sm leading-relaxed text-zinc-500">最近导入后已经形成 {upload.snapshotCount ?? 0} 个分析快照，当前共有 {upload.campaigns ?? 0} 个活动可供分析。</p>
          </div>
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">History</div>
            <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">导入历史</h3>
            <div className="mt-4 space-y-3">
              {snapshots.length ? snapshots.map((item) => (
                <div key={item.id} className="rounded-2xl bg-zinc-50 p-4">
                  <div className="text-sm font-medium text-zinc-950">{item.createdAt}</div>
                  <div className="mt-1 text-sm text-zinc-500">快照 {item.id} · {item.itemCount} 条结果</div>
                </div>
              )) : <p className="text-sm leading-relaxed text-zinc-500">当前还没有导入历史快照。</p>}
              {campaigns.length ? campaigns.map((item) => (
                <div key={item.id} className="rounded-2xl bg-zinc-50 p-4">
                  <div className="text-sm font-medium text-zinc-950">{item.name}</div>
                  <div className="mt-1 text-sm text-zinc-500">创建于 {item.createdAt}</div>
                </div>
              )) : null}
            </div>
          </div>
        </section>
      </div>
    </DashboardShell>
  );
}
