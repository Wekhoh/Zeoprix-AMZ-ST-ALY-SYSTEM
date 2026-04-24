import { getUploadPayload } from "@/lib/backend";
import { DashboardShell } from "@/components/dashboard-shell";
import { UploadLivePanel } from "@/components/upload-live-panel";

export const dynamic = "force-dynamic";

export default async function UploadPage() {
	const payload = await getUploadPayload();
	return (
		<DashboardShell
			title="数据导入"
			subtitle="把导入从技术动作重构成运营节奏的入口：先看数据健康，再决定是否建立新一轮分析。"
			productId={payload.productId}
			productContext={payload.productContext}
			aiCard={payload.aiCopilotCards[0]}
		>
			<UploadLivePanel payload={payload} />
		</DashboardShell>
	);
}
