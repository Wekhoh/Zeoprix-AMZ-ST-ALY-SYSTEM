import { DashboardShell } from "@/components/dashboard-shell";
import { TemplatesCenter, WorkbenchOverview } from "@/components/workbench-sections";

export default function Page() {
  return (
    <DashboardShell
      title="Amazon 运营工作台"
      subtitle="把状态、优先级、趋势和最近执行效果收进一个更清晰的判断界面。"
    >
      <div className="space-y-8">
        <WorkbenchOverview />
        <TemplatesCenter />
      </div>
    </DashboardShell>
  );
}
