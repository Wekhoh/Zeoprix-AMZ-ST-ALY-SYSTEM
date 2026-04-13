import { getWorkbenchPayload } from "@/lib/backend";
import { DashboardShell } from "@/components/dashboard-shell";
import { TemplatesCenter, WorkbenchOverview } from "@/components/workbench-sections";

export const dynamic = "force-dynamic";

export default async function Page() {
  const payload = await getWorkbenchPayload();
  return (
    <DashboardShell
      title="Amazon 运营工作台"
      subtitle="把状态、优先级、趋势和最近执行效果收进一个更清晰的判断界面。"
      productId={payload.productId}
      productContext={payload.productContext}
      aiCard={payload.aiCopilotCards[0]}
    >
      <div className="space-y-8">
        <WorkbenchOverview
          workbenchStats={payload.workbenchStats}
          topActions={payload.topActions}
          trendCards={payload.trendCards}
          trendBars={payload.trendBars}
          structureBuckets={payload.structureBuckets}
          executionEffect={payload.executionEffect}
        />
        <TemplatesCenter opsTemplates={payload.opsTemplates} />
      </div>
    </DashboardShell>
  );
}
