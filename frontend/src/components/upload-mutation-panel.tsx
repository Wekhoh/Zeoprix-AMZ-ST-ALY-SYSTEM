"use client";
/**
 * upload-mutation-panel — Ops Terminal 方向
 * 内联拖放区 + 操作行 + 进度条 + 消息行，无大卡包裹
 */
import { useRef, useState } from "react";
import { Upload, X, FileText } from "lucide-react";

import { BACKEND_BASE_URL } from "@/lib/backend";
import type { UploadPayload } from "@/lib/mock-data";
import { Button } from "@/components/ui/button";

type Props = {
	payload: UploadPayload;
	onUploadComplete?: (response: UploadMutationResponse) => void;
	onAnalysisComplete?: (response: AnalysisMutationResponse) => void;
};

type AnalysisMutationResponse = {
	status?: string;
	message?: string;
	termsAnalyzed?: number;
	resultsSaved?: number;
	pendingReviews?: number;
};

type UploadMutationResponse = {
	status?: string;
	message?: string;
	importedFiles?: Array<{
		fileName?: string;
		campaignName?: string;
		rows?: number;
	}>;
	failedFiles?: Array<{ fileName?: string; reason?: string }>;
	importedRows?: number;
	campaignsCreated?: number;
	analysisState?: AnalysisMutationResponse | null;
};

function uploadWithProgress(
	url: string,
	formData: FormData,
	onProgress: (percent: number) => void,
): Promise<{
	ok: boolean;
	status: number;
	body: UploadMutationResponse & { detail?: string };
}> {
	return new Promise((resolve) => {
		const xhr = new XMLHttpRequest();
		xhr.open("POST", url);
		xhr.upload.onprogress = (event) => {
			if (!event.lengthComputable) return;
			onProgress(
				Math.max(
					5,
					Math.min(100, Math.round((event.loaded / event.total) * 100)),
				),
			);
		};
		xhr.onload = () => {
			let body: UploadMutationResponse & { detail?: string } = {
				message: "上传失败",
			};
			try {
				body = JSON.parse(xhr.responseText || "{}");
			} catch {
				body = { message: "上传失败" };
			}
			resolve({
				ok: xhr.status >= 200 && xhr.status < 300,
				status: xhr.status,
				body,
			});
		};
		xhr.onerror = () =>
			resolve({ ok: false, status: xhr.status, body: { message: "上传失败" } });
		xhr.send(formData);
	});
}

function formatBytes(bytes: number): string {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
	return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadMutationPanel({
	payload,
	onUploadComplete,
	onAnalysisComplete,
}: Props) {
	const productId = payload.productId;
	const [message, setMessage] = useState<string | null>(null);
	const [messageTone, setMessageTone] = useState<"info" | "success" | "error">(
		"info",
	);
	const [autoAnalyze, setAutoAnalyze] = useState(true);
	const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
	const [pendingAction, setPendingAction] = useState<
		"upload" | "analysis" | null
	>(null);
	const [uploadProgress, setUploadProgress] = useState<number | null>(null);
	const [isDragOver, setIsDragOver] = useState(false);
	const fileInputRef = useRef<HTMLInputElement>(null);

	function addFiles(newFiles: File[]) {
		if (!newFiles.length) return;
		const allowed = newFiles.filter((f) => /\.(csv|xlsx|xls)$/i.test(f.name));
		setSelectedFiles((current) => {
			const seen = new Set(current.map((f) => `${f.name}-${f.size}`));
			const merged = [...current];
			for (const f of allowed) {
				const key = `${f.name}-${f.size}`;
				if (!seen.has(key)) {
					merged.push(f);
					seen.add(key);
				}
			}
			return merged;
		});
	}

	function removeFile(index: number) {
		setSelectedFiles((current) => current.filter((_, i) => i !== index));
	}

	async function uploadFiles(files: File[]) {
		if (!productId || !files.length) return;
		setMessage(`正在上传 ${files.length} 个文件…`);
		setMessageTone("info");
		setPendingAction("upload");
		setUploadProgress(0);

		const formData = new FormData();
		formData.append("product_id", String(productId));
		formData.append("auto_analyze", String(autoAnalyze));
		for (const file of files) {
			formData.append("files", file);
		}

		const result = await uploadWithProgress(
			`${BACKEND_BASE_URL}/frontend/upload/files`,
			formData,
			setUploadProgress,
		);
		if (!result.ok) {
			setMessage(result.body.detail ?? result.body.message ?? "上传失败");
			setMessageTone("error");
			setPendingAction(null);
			setUploadProgress(null);
			return;
		}

		const body = result.body;
		const importedMessage = `已导入 ${body.campaignsCreated ?? 0} 个活动，${body.importedRows ?? 0} 条记录`;
		const failureMessage = body.failedFiles?.length
			? `；${body.failedFiles.length} 个文件失败`
			: "";
		const analysisMessage = body.analysisState?.message
			? `；${body.analysisState.message}`
			: "";
		setMessage(`${importedMessage}${failureMessage}${analysisMessage}`);
		setMessageTone(body.failedFiles?.length ? "error" : "success");
		onUploadComplete?.(body);
		if (body.analysisState) {
			onAnalysisComplete?.(body.analysisState);
		}
		setSelectedFiles([]);
		setPendingAction(null);
		setUploadProgress(100);
		window.setTimeout(() => setUploadProgress(null), 1200);
	}

	async function rerunAnalysis() {
		if (!productId) return;
		setMessage("正在重新运行分析…");
		setMessageTone("info");
		setPendingAction("analysis");

		const response = await fetch(
			`${BACKEND_BASE_URL}/frontend/upload/run-analysis`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ product_id: productId }),
			},
		);
		const body = (await response.json().catch(() => ({
			message: "分析执行失败",
		}))) as AnalysisMutationResponse & { detail?: string };
		if (!response.ok) {
			setMessage(body.detail ?? body.message ?? "分析执行失败");
			setMessageTone("error");
			setPendingAction(null);
			return;
		}
		setMessage(
			`${body.message ?? "分析完成"}（分析词数 ${body.termsAnalyzed ?? 0}，建议 ${body.resultsSaved ?? 0} 条）`,
		);
		setMessageTone("success");
		onAnalysisComplete?.(body);
		setPendingAction(null);
	}

	const isUploading = pendingAction === "upload";
	const isAnalyzing = pendingAction === "analysis";
	const canUpload = productId !== null && selectedFiles.length > 0;

	return (
		<div className="space-y-5">
			{/* ═══ 拖放区 ═══ */}
			<label
				htmlFor="upload-file-input"
				onDragOver={(e) => {
					e.preventDefault();
					setIsDragOver(true);
				}}
				onDragLeave={() => setIsDragOver(false)}
				onDrop={(e) => {
					e.preventDefault();
					setIsDragOver(false);
					const files = Array.from(e.dataTransfer.files ?? []);
					addFiles(files);
				}}
				className={
					"group relative flex flex-col items-center justify-center gap-3 " +
					"rounded-md border-2 border-dashed px-6 py-10 cursor-pointer transition-colors " +
					(isDragOver
						? "border-accent bg-accent-bg"
						: "border-border bg-bg-subtle/30 hover:border-fg-subtle hover:bg-bg-subtle/60")
				}
			>
				<input
					ref={fileInputRef}
					id="upload-file-input"
					type="file"
					multiple
					accept=".csv,.xlsx,.xls"
					onChange={(e) => {
						const files = Array.from(e.target.files ?? []);
						addFiles(files);
						e.target.value = "";
					}}
					className="sr-only"
				/>
				<Upload
					className={
						"h-6 w-6 transition-colors " +
						(isDragOver ? "text-accent-fg" : "text-fg-subtle")
					}
				/>
				<div className="text-center">
					<div className="text-[14px] font-medium text-fg">
						{isDragOver ? "松开即可添加" : "拖放文件到这里，或点击选择"}
					</div>
					<div className="mt-1 text-[12px] text-fg-muted">
						支持 CSV / Excel · 多文件时自动按文件名创建活动
					</div>
				</div>
			</label>

			{/* ═══ 已选文件 chip 列表 ═══ */}
			{selectedFiles.length > 0 ? (
				<div className="space-y-1.5">
					<div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-fg-subtle">
						<span>selected</span>
						<span className="tabular-nums">{selectedFiles.length}</span>
					</div>
					<ul className="space-y-1">
						{selectedFiles.map((file, idx) => (
							<li
								key={`${file.name}-${file.size}-${idx}`}
								className="flex items-center gap-3 rounded border border-border bg-bg-elevated px-3 py-2"
							>
								<FileText className="h-3.5 w-3.5 shrink-0 text-fg-subtle" />
								<span className="flex-1 truncate font-mono text-[13px] text-fg">
									{file.name}
								</span>
								<span className="shrink-0 font-mono text-[12px] tabular-nums text-fg-muted">
									{formatBytes(file.size)}
								</span>
								<button
									type="button"
									onClick={() => removeFile(idx)}
									className="shrink-0 rounded p-1 text-fg-subtle hover:bg-bg-subtle hover:text-fg transition-colors"
									aria-label="移除"
								>
									<X className="h-3 w-3" />
								</button>
							</li>
						))}
					</ul>
				</div>
			) : null}

			{/* ═══ 操作行 ═══ */}
			<div className="flex flex-wrap items-center gap-x-5 gap-y-3">
				<label className="flex items-center gap-2 cursor-pointer">
					<input
						type="checkbox"
						checked={autoAnalyze}
						onChange={(e) => setAutoAnalyze(e.target.checked)}
						className="h-4 w-4 rounded border-border accent-accent cursor-pointer"
					/>
					<span className="text-[13px] font-medium text-fg">
						上传后自动运行分析
					</span>
				</label>
				<div className="ml-auto flex items-center gap-2">
					<Button
						variant="secondary"
						size="md"
						disabled={pendingAction !== null || !productId}
						onClick={() => void rerunAnalysis()}
						loading={isAnalyzing}
					>
						{isAnalyzing ? "分析中" : "仅重跑分析"}
					</Button>
					<Button
						variant="primary"
						size="md"
						disabled={pendingAction !== null || !canUpload}
						onClick={() => void uploadFiles(selectedFiles)}
						loading={isUploading}
					>
						{isUploading ? "上传中" : "上传原始报表"}
					</Button>
				</div>
			</div>

			{/* ═══ 进度条 ═══ */}
			{uploadProgress !== null ? (
				<div className="space-y-1.5">
					<div className="flex items-center justify-between text-[12px]">
						<span className="font-mono uppercase tracking-[0.14em] text-fg-subtle">
							{uploadProgress >= 100 ? "completed" : "uploading"}
						</span>
						<span className="font-mono tabular-nums font-semibold text-fg">
							{uploadProgress}%
						</span>
					</div>
					<div className="h-1 w-full overflow-hidden rounded-full bg-bg-subtle">
						<div
							className={
								"h-full rounded-full transition-all duration-300 " +
								(uploadProgress >= 100 ? "bg-success" : "bg-fg")
							}
							style={{ width: `${uploadProgress}%` }}
						/>
					</div>
				</div>
			) : null}

			{/* ═══ 消息行 ═══ */}
			{message ? (
				<div
					className={
						"flex items-start gap-2 border-t border-border pt-3 text-[13px] leading-[1.6] font-medium " +
						(messageTone === "error"
							? "text-error-fg"
							: messageTone === "success"
								? "text-success-fg"
								: "text-fg-muted")
					}
				>
					<span className="font-mono text-[11px] mt-0.5 shrink-0">
						{messageTone === "error"
							? "✗"
							: messageTone === "success"
								? "✓"
								: "›"}
					</span>
					<span className="flex-1">{message}</span>
				</div>
			) : null}
		</div>
	);
}
