"use client";

import { useState } from "react";

import { BACKEND_BASE_URL } from "@/lib/backend";
import type { UploadPayload } from "@/lib/mock-data";

type Props = {
  payload: UploadPayload
  onUploadComplete?: (response: UploadMutationResponse) => void
  onAnalysisComplete?: (response: AnalysisMutationResponse) => void
}

type AnalysisMutationResponse = {
  status?: string
  message?: string
  termsAnalyzed?: number
  resultsSaved?: number
  pendingReviews?: number
}

type UploadMutationResponse = {
  status?: string
  message?: string
  importedFiles?: Array<{ fileName?: string; campaignName?: string; rows?: number }>
  failedFiles?: Array<{ fileName?: string; reason?: string }>
  importedRows?: number
  campaignsCreated?: number
  analysisState?: AnalysisMutationResponse | null
}

function uploadWithProgress(
  url: string,
  formData: FormData,
  onProgress: (percent: number) => void,
): Promise<{ ok: boolean; status: number; body: UploadMutationResponse & { detail?: string } }> {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest()
    xhr.open("POST", url)
    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) return
      onProgress(Math.max(5, Math.min(100, Math.round((event.loaded / event.total) * 100))))
    }
    xhr.onload = () => {
      let body: UploadMutationResponse & { detail?: string } = { message: "上传失败" }
      try {
        body = JSON.parse(xhr.responseText || "{}")
      } catch {
        body = { message: "上传失败" }
      }
      resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status, body })
    }
    xhr.onerror = () => resolve({ ok: false, status: xhr.status, body: { message: "上传失败" } })
    xhr.send(formData)
  })
}

export function UploadMutationPanel({ payload, onUploadComplete, onAnalysisComplete }: Props) {
  const productId = payload.productId
  const [message, setMessage] = useState<string | null>(null)
  const [autoAnalyze, setAutoAnalyze] = useState(true)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [pendingAction, setPendingAction] = useState<"upload" | "analysis" | null>(null)
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)

  async function uploadFiles(files: File[]) {
    if (!productId || !files.length) return
    setMessage(`正在上传 ${files.length} 个文件…`)
    setPendingAction("upload")
    setUploadProgress(0)

    const formData = new FormData()
    formData.append("product_id", String(productId))
    formData.append("auto_analyze", String(autoAnalyze))
    for (const file of files) {
      formData.append("files", file)
    }

    const result = await uploadWithProgress(`${BACKEND_BASE_URL}/frontend/upload/files`, formData, setUploadProgress)
    if (!result.ok) {
      setMessage(result.body.detail ?? result.body.message ?? "上传失败")
      setPendingAction(null)
      setUploadProgress(null)
      return
    }

    const body = result.body
    const importedMessage = `已导入 ${body.campaignsCreated ?? 0} 个活动，${body.importedRows ?? 0} 条记录`
    const failureMessage = body.failedFiles?.length ? `；${body.failedFiles.length} 个文件失败` : ""
    const analysisMessage = body.analysisState?.message ? `；${body.analysisState.message}` : ""
    setMessage(`${importedMessage}${failureMessage}${analysisMessage}`)
    onUploadComplete?.(body)
    if (body.analysisState) {
      onAnalysisComplete?.(body.analysisState)
    }
    setSelectedFiles([])
    setPendingAction(null)
    setUploadProgress(100)
    window.setTimeout(() => setUploadProgress(null), 800)
  }

  async function rerunAnalysis() {
    if (!productId) return
    setMessage("正在重新运行分析…")
    setPendingAction("analysis")

    const response = await fetch(`${BACKEND_BASE_URL}/frontend/upload/run-analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: productId }),
    })
    const body = (await response.json().catch(() => ({ message: "分析执行失败" }))) as AnalysisMutationResponse & { detail?: string }
    if (!response.ok) {
      setMessage(body.detail ?? body.message ?? "分析执行失败")
      setPendingAction(null)
      return
    }
    setMessage(`${body.message ?? "分析完成"}（分析词数 ${body.termsAnalyzed ?? 0}，建议 ${body.resultsSaved ?? 0} 条）`)
    onAnalysisComplete?.(body)
    setPendingAction(null)
  }

  const isUploading = pendingAction === "upload"
  const isAnalyzing = pendingAction === "analysis"

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Write Path</div>
      <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">上传后动作</h3>
      <p className="mt-3 text-sm leading-relaxed text-zinc-500">在新前端里直接导入原始报表或重跑规则分析，形成新的快照和建议结果。</p>
      <label className="mt-5 flex cursor-pointer flex-col gap-3 rounded-2xl bg-zinc-50 p-4 text-sm text-zinc-500">
        <span className="font-medium text-zinc-900">上传原始报表</span>
        <span>支持 CSV / Excel，多文件时会自动按文件名创建活动。</span>
        <div className="flex items-center gap-2">
          <input checked={autoAnalyze} onChange={(e) => setAutoAnalyze(e.target.checked)} type="checkbox" />
          <span>上传后自动运行分析</span>
        </div>
        <input
          type="file"
          multiple
          accept=".csv,.xlsx,.xls"
          onChange={(e) => {
            const files = Array.from(e.target.files ?? [])
            setSelectedFiles(files)
          }}
          className="text-sm text-zinc-900"
        />
        {selectedFiles.length ? (
          <div className="text-sm text-zinc-500">{selectedFiles.map((file) => file.name).join(" ｜ ")}</div>
        ) : null}
      </label>
      {uploadProgress !== null ? (
        <div className="mt-4 rounded-2xl bg-zinc-50 p-4">
          <div className="flex items-center justify-between text-sm text-zinc-500">
            <span>{isUploading ? "上传进度" : "最近上传"}</span>
            <span className="tabular-nums">{uploadProgress}%</span>
          </div>
          <div className="mt-3 h-2 rounded-full bg-zinc-100">
            <div className="h-2 rounded-full bg-zinc-900 transition-all" style={{ width: `${uploadProgress}%` }} />
          </div>
        </div>
      ) : null}
      <div className="mt-5 flex flex-wrap gap-3">
        <button disabled={pendingAction !== null || !productId || !selectedFiles.length} onClick={() => void uploadFiles(selectedFiles)} className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50">
          {isUploading ? "上传中…" : "上传原始报表"}
        </button>
        <button disabled={pendingAction !== null || !productId} onClick={() => void rerunAnalysis()} className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50">
          {isAnalyzing ? "分析中…" : "重新运行分析"}
        </button>
      </div>
      {message ? <p className="mt-4 text-sm leading-relaxed text-zinc-500">{message}</p> : null}
    </section>
  )
}
