import { DashboardShell } from "@/components/dashboard-shell";
import { TemplatesCenter, WorkbenchOverview } from "@/components/workbench-sections";

export default function Page() {
  return (
    <DashboardShell
      title="Amazon 运营工作台"
      subtitle="重构后的首页不再只是数据概览，而是把状态、优先级、趋势、结构、执行效果和运营模板收进同一个判断中枢。"
    >
      <div className="space-y-8">
        <WorkbenchOverview />
        <TemplatesCenter />
      </div>
    </DashboardShell>
  );
}
