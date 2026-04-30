import { CompetitorsLivePanel } from "@/components/competitors-live-panel";
import { DashboardShell } from "@/components/dashboard-shell";
import { getWorkbenchPayload } from "@/lib/backend";
import type { CompetitorPayload } from "@/lib/mock-data";

export const dynamic = "force-dynamic";

const BACKEND_BASE_URL =
	process.env.BACKEND_BASE_URL ??
	process.env.NEXT_PUBLIC_BACKEND_BASE_URL ??
	"http://127.0.0.1:8008";

const EMPTY_COMPETITORS: CompetitorPayload = {
	source: "empty",
	configuredCompetitorAsins: [],
	discoveredCompetitors: [],
	negativeAsinsCount: 0,
	watchAsinsCount: 0,
	insights: {
		totalCount: 0,
		totalSpend: 0,
		totalOrders: 0,
		avgAcos: 0,
		topPerformers: [],
		worstPerformers: [],
	},
};

async function getCompetitorsPayload(
	productId?: number,
): Promise<CompetitorPayload> {
	const params = productId ? `?product_id=${productId}` : "";
	try {
		const response = await fetch(
			`${BACKEND_BASE_URL}/frontend/competitors${params}`,
			{ cache: "no-store", next: { revalidate: 0 } },
		);
		if (!response.ok) {
			throw new Error(`competitors backend ${response.status}`);
		}
		return (await response.json()) as CompetitorPayload;
	} catch {
		return EMPTY_COMPETITORS;
	}
}

export default async function CompetitorsPage() {
	const [shell, competitors] = await Promise.all([
		getWorkbenchPayload(),
		getCompetitorsPayload(),
	]);
	return (
		<DashboardShell
			title="竞品监控"
			subtitle="把出现在自己搜索词里的对手 ASIN 拽出来给主人看，避免在不知情中持续投放高 ACOS 对手词。"
			productId={shell.productId}
			productContext={shell.productContext}
			aiCard={shell.aiCopilotCards[0]}
		>
			<CompetitorsLivePanel payload={competitors} />
		</DashboardShell>
	);
}
