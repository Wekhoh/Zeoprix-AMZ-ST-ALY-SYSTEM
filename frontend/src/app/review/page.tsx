import { getReviewPayload } from "@/lib/backend";
import { DashboardShell } from "@/components/dashboard-shell";
import { ReviewLivePanel } from "@/components/review-live-panel";

export const dynamic = "force-dynamic";

export default async function ReviewPage() {
  const payload = await getReviewPayload();
  return (
    <DashboardShell
      title="审核中心"
      subtitle="把 AI 建议和人工拍板彻底分开。重构版会围绕相似词、采纳记录和风险提示提升审核效率。"
      productId={payload.productId}
      productContext={payload.productContext}
      aiCard={payload.aiCopilotCards[0]}
    >
      <ReviewLivePanel payload={payload} backendBaseUrl={process.env.BACKEND_BASE_URL ?? process.env.NEXT_PUBLIC_BACKEND_BASE_URL ?? "http://127.0.0.1:8000"} />
    </DashboardShell>
  );
}
