"use client";

import { useState, useTransition } from "react";

import { BACKEND_BASE_URL } from "@/lib/backend";
import type { SettingsPayload } from "@/lib/mock-data";

type Props = {
  payload: SettingsPayload
}

export function SettingsMutationPanel({ payload }: Props) {
  const productId = payload.productId
  const [message, setMessage] = useState<string | null>(null)
  const [pending, startTransition] = useTransition()

  async function clearRuntime() {
    if (!productId) return
    setMessage(null)
    startTransition(async () => {
      const response = await fetch(`${BACKEND_BASE_URL}/frontend/settings/clear-runtime`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId }),
      })
      const body = await response.json().catch(() => ({ message: "清空失败" }))
      if (!response.ok) {
        setMessage(body.detail ?? body.message ?? "清空失败")
        return
      }
      setMessage(body.message ?? "运行数据已清空")
      window.location.reload()
    })
  }

  async function downloadBackup() {
    if (!productId) return
    setMessage(null)
    startTransition(async () => {
      const response = await fetch(`${BACKEND_BASE_URL}/frontend/settings/full-backup?product_id=${productId}`)
      const body = await response.json().catch(() => ({ detail: "导出失败" }))
      if (!response.ok) {
        setMessage(body.detail ?? "导出失败")
        return
      }
      const blob = new Blob([body.content], { type: body.mime ?? 'application/json' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = body.fileName ?? 'backup.json'
      anchor.click()
      URL.revokeObjectURL(url)
      setMessage(`完整备份已导出：${body.fileName}`)
    })
  }

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Write Path</div>
      <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">数据管理操作</h3>
      <p className="mt-3 text-sm leading-relaxed text-zinc-500">从新前端直接触发清空运行数据和完整备份导出。</p>
      <div className="mt-5 flex flex-wrap gap-3">
        <button disabled={pending || !productId} onClick={downloadBackup} className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50">
          导出完整备份
        </button>
        <button disabled={pending || !productId} onClick={clearRuntime} className="rounded-full border border-zinc-200 bg-white px-5 py-2.5 text-sm font-medium text-zinc-900 shadow-sm transition hover:bg-zinc-50 disabled:opacity-50">
          清空运行数据
        </button>
      </div>
      {message ? <p className="mt-4 text-sm leading-relaxed text-zinc-500">{message}</p> : null}
    </section>
  )
}
