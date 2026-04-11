import { DashboardShell } from "@/components/dashboard-shell";

export default function UploadPage() {
  return (
    <DashboardShell
      title="数据导入"
      subtitle="把导入从技术动作重构成运营节奏的入口：先看数据健康，再决定是否建立新一轮分析。"
    >
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
          <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Import Center</div>
          <h3 className="mt-2 text-2xl font-semibold text-white">导入与批次建立</h3>
          <p className="mt-3 text-sm leading-7 text-slate-400">在正式重构版里，这里会承接原始报表导入、人工校准表导入、导入历史、数据健康分，以及“是否开始新一轮分析”的决策。</p>
          <div className="mt-6 rounded-3xl border border-dashed border-white/12 bg-[#0A1018] p-10 text-center text-sm text-slate-500">拖拽上传区域（重构首版预留）</div>
        </section>
        <section className="space-y-6">
          <div className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">AI Import Brief</div>
            <h3 className="mt-2 text-2xl font-semibold text-white">AI 导入摘要</h3>
            <p className="mt-3 text-sm leading-7 text-slate-400">导入后自动告诉运营：这批数据够不够分析、和上次相比量级是否异常、下一步该去哪里。</p>
          </div>
          <div className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">History</div>
            <h3 className="mt-2 text-2xl font-semibold text-white">导入历史</h3>
            <p className="mt-3 text-sm leading-7 text-slate-400">这里会列出每次导入的时间、文件数、行数、是否成功进入分析轮次。</p>
          </div>
        </section>
      </div>
    </DashboardShell>
  );
}
