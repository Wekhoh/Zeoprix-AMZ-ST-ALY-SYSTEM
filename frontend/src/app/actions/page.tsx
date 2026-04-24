import { getActionsPayload } from "@/lib/backend";
import { ActionsLivePanel } from "@/components/actions-live-panel";
import { DashboardShell } from "@/components/dashboard-shell";

export const dynamic = "force-dynamic";

export default async function ActionsPage() {
	const payload = await getActionsPayload();
	return (
		<DashboardShell
			title="操作清单与执行批次"
			subtitle="把建议、执行、复盘收进同一条工作流：先生成批次，再标记执行，最后在这里看 verdict 与 Top changes。"
			productId={payload.productId}
			productContext={payload.productContext}
			aiCard={payload.aiCopilotCards[0]}
		>
			<ActionsLivePanel
				payload={payload}
				backendBaseUrl={
					process.env.BACKEND_BASE_URL ??
					process.env.NEXT_PUBLIC_BACKEND_BASE_URL ??
					"http://127.0.0.1:8000"
				}
			/>
		</DashboardShell>
	);
}
