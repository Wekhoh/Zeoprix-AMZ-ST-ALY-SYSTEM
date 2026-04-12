"use client";

import { useState, useTransition } from "react";

import { BACKEND_BASE_URL } from "@/lib/backend";
import type { UploadPayload } from "@/lib/mock-data";

type Props = {
  payload: UploadPayload
}

export function UploadMutationPanel({ payload }: Props) {
  const productId = payload.productId
  const [message, setMessage] = useState<string | null>(null)
  const [autoAnalyze, setAutoAnalyze] = useState(true)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [pending, startTransition] = useTransition()

  async function uploadFiles(files: File[]) {
    if (!productId || !files.length) return
    setMessage(null)
    startTransition(async () => {
      const formData = new FormData()
      formData.append("product_id", String(productId))
      formData.append("auto_analyze", String(autoAnalyze))
      for (const file of files) {
        formData.append("files", file)
      }

      const response = await fetch(`${BACKEND_BASE_URL}/frontend/upload/files`, {
        method: "POST",
        body: formData,
      })
      const body = await response.json().catch(() => ({ message: "上传失败" }))
      if (!response.ok) {
        setMessage(body.detail ?? body.message ?? "上传失败")
        return
      }
      const analysisMessage = body.analysisState?.message ? `；${body.analysisState.message}` : ""
      setMessage(`已导入 ${body.campaignsCreated ?? 0} 个活动，${body.importedRows ?? 0} 条记录${analysisMessage}`)
      window.location.reload()
    })
  }

  async function rerunAnalysis() {
    if (!productId) return
    setMessage(null)
    startTransition(async () => {
      const response = await fetch(`${BACKEND_BASE_URL}/frontend/upload/run-analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId }),
      })
      const body = await response.json().catch(() => ({ message: "分析执行失败" }))
      if (!response.ok) {
        setMessage(body.detail ?? body.message ?? "分析执行失败")
        return
      }
      setMessage(`${body.message ?? '分析完成'}（分析词数 ${body.termsAnalyzed ?? 0}，建议 ${body.resultsSaved ?? 0} 条）`)
      window.location.reload()
    })
  }

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Write Path</div>
      <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">上传后动作</h3>
      <p className="mt-3 text-sm leading-relaxed text-zinc-500">在新前端里直接重跑规则分析，形成新的快照和建议结果。</p>
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
      <div className="mt-5 flex flex-wrap gap-3">
        <button disabled={pending || !productId || !selectedFiles.length} onClick={() => uploadFiles(selectedFiles)} className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50">
          上传原始报表
        </button>
        <button disabled={pending || !productId} onClick={rerunAnalysis} className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50">
          重新运行分析
        </button>
      </div>
      {message ? <p className="mt-4 text-sm leading-relaxed text-zinc-500">{message}</p> : null}
    </section>
  )
}
