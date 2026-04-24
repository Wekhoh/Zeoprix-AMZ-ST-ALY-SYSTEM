import { getSettingsPayload } from "@/lib/backend";
import { DashboardShell } from "@/components/dashboard-shell";
import { SettingsLivePanel } from "@/components/settings-live-panel";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
	const payload = await getSettingsPayload();
	return (
		<DashboardShell
			title="数据管理与系统设置"
			subtitle="把长期配置和运行时数据操作彻底分开：一边是规则和词库，一边是清空、备份、恢复。"
			productId={payload.productId}
			productContext={payload.productContext}
			aiCard={payload.aiCopilotCards[0]}
		>
			<SettingsLivePanel payload={payload} />
		</DashboardShell>
	);
}
