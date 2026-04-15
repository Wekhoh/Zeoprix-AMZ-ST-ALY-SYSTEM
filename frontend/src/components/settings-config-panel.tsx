"use client";

import { useState, useTransition } from "react";

import { BACKEND_BASE_URL } from "@/lib/backend";
import type { SettingsPayload } from "@/lib/mock-data";

type Props = {
  payload: SettingsPayload
  onConfigSaved?: (response: ConfigMutationResponse) => void
}

type ConfigMutationResponse = {
  status?: string
  message?: string
  configEditor?: {
    coreKeywords: string[]
    relatedKeywords: string[]
    competitorAsins: string[]
    ownVariants: string[]
  }
}

function splitLines(value: string) {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

export function SettingsConfigPanel({ payload, onConfigSaved }: Props) {
  const productId = payload.productId
  const editor = payload.settings?.configEditor ?? { coreKeywords: [], relatedKeywords: [], competitorAsins: [], ownVariants: [] }
  const [coreKeywords, setCoreKeywords] = useState(editor.coreKeywords.join("\n"))
  const [relatedKeywords, setRelatedKeywords] = useState(editor.relatedKeywords.join("\n"))
  const [competitorAsins, setCompetitorAsins] = useState(editor.competitorAsins.join("\n"))
  const [ownVariants, setOwnVariants] = useState(editor.ownVariants.join("\n"))
  const [message, setMessage] = useState<string | null>(null)
  const [pending, startTransition] = useTransition()

  function saveConfig() {
    if (!productId) return
    setMessage(null)
    startTransition(async () => {
      const response = await fetch(`${BACKEND_BASE_URL}/frontend/settings/product-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: productId,
          core_keywords: splitLines(coreKeywords),
          related_keywords: splitLines(relatedKeywords),
          competitor_asins: splitLines(competitorAsins),
          own_variants: splitLines(ownVariants),
        }),
      })
      const body = (await response.json().catch(() => ({ message: "保存失败" }))) as ConfigMutationResponse & { detail?: string }
      if (!response.ok) {
        setMessage(body.detail ?? body.message ?? "保存失败")
        return
      }
      setMessage(body.message ?? "配置已保存。")
      if (body.configEditor) {
        setCoreKeywords(body.configEditor.coreKeywords.join("\n"))
        setRelatedKeywords(body.configEditor.relatedKeywords.join("\n"))
        setCompetitorAsins(body.configEditor.competitorAsins.join("\n"))
        setOwnVariants(body.configEditor.ownVariants.join("\n"))
      }
      onConfigSaved?.(body)
    })
  }

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Config Editor</div>
      <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">快速配置编辑</h3>
      <p className="mt-3 text-sm leading-relaxed text-zinc-500">先把核心词、相关词、竞品 ASIN 和自家变体在这里维护好，再让分析和 Copilot 继续引用。</p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-2 text-sm text-zinc-500">
          <span className="font-medium text-zinc-900">核心词</span>
          <textarea value={coreKeywords} onChange={(e) => setCoreKeywords(e.target.value)} className="min-h-28 rounded-2xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-900 outline-none placeholder:text-zinc-400" placeholder="每行一个核心词" />
        </label>
        <label className="flex flex-col gap-2 text-sm text-zinc-500">
          <span className="font-medium text-zinc-900">相关词</span>
          <textarea value={relatedKeywords} onChange={(e) => setRelatedKeywords(e.target.value)} className="min-h-28 rounded-2xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-900 outline-none placeholder:text-zinc-400" placeholder="每行一个相关词" />
        </label>
        <label className="flex flex-col gap-2 text-sm text-zinc-500">
          <span className="font-medium text-zinc-900">竞品 ASIN</span>
          <textarea value={competitorAsins} onChange={(e) => setCompetitorAsins(e.target.value)} className="min-h-28 rounded-2xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-900 outline-none placeholder:text-zinc-400" placeholder="每行一个竞品 ASIN" />
        </label>
        <label className="flex flex-col gap-2 text-sm text-zinc-500">
          <span className="font-medium text-zinc-900">自家变体 ASIN</span>
          <textarea value={ownVariants} onChange={(e) => setOwnVariants(e.target.value)} className="min-h-28 rounded-2xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-900 outline-none placeholder:text-zinc-400" placeholder="每行一个自家变体 ASIN" />
        </label>
      </div>
      <div className="mt-5 flex items-center gap-3">
        <button disabled={pending || !productId} onClick={saveConfig} className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50">
          {pending ? "保存中…" : "保存配置"}
        </button>
        {message ? <span className="text-sm leading-relaxed text-zinc-500">{message}</span> : null}
      </div>
    </section>
  )
}
