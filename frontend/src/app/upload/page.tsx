import { getWorkbenchPayload } from "@/lib/backend";
import { DashboardShell } from "@/components/dashboard-shell";

export const dynamic = "force-dynamic";

export default async function UploadPage() {
  const payload = await getWorkbenchPayload();
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
          <p className="mt-3 text-sm leading-relaxed text-zinc-500">在正式重构版里，这里会承接原始报表导入、人工校准表导入、导入历史、数据健康分，以及“是否开始新一轮分析”的决策。</p>
          <div className="mt-6 rounded-2xl border border-dashed border-zinc-200 bg-zinc-50 p-10 text-center text-sm text-zinc-500">拖拽上传区域（重构首版预留）</div>
        </section>
        <section className="space-y-6">
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">AI Import Brief</div>
            <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">AI 导入摘要</h3>
            <p className="mt-3 text-sm leading-relaxed text-zinc-500">导入后自动告诉运营：这批数据够不够分析、和上次相比量级是否异常、下一步该去哪里。</p>
          </div>
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">History</div>
            <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">导入历史</h3>
            <p className="mt-3 text-sm leading-relaxed text-zinc-500">这里会列出每次导入的时间、文件数、行数、是否成功进入分析轮次。</p>
          </div>
        </section>
      </div>
    </DashboardShell>
  );
}
