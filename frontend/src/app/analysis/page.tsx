import { getAnalysisPayload } from "@/lib/backend";
import { AnalysisLivePanel } from "@/components/analysis-live-panel";
import { DashboardShell } from "@/components/dashboard-shell";

export const dynamic = "force-dynamic";

export default async function AnalysisPage() {
	const payload = await getAnalysisPayload();
	return (
		<DashboardShell
			title="搜索词分析"
			subtitle="汇总、按活动、按 ASIN 三种视角放进同一套分析页面，而不是拆成零散页面。"
			productId={payload.productId}
			productContext={payload.productContext}
			aiCard={payload.aiCopilotCards[0]}
		>
			<AnalysisLivePanel payload={payload} />
		</DashboardShell>
	);
}
