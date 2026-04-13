"use client";

import { useState, useTransition } from "react";

import { BACKEND_BASE_URL } from "@/lib/backend";
import type { AICopilotCard } from "@/lib/mock-data";

type Props = {
  productId?: number | null
  pageKey: string
  pageTitle: string
  aiCard: AICopilotCard
}

type ChatMessage = {
  role: "assistant" | "user"
  content: string
}

export function CopilotPanel({ productId, pageKey, pageTitle, aiCard }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([{ role: "assistant", content: aiCard.summary }])
  const [input, setInput] = useState("")
  const [prompts, setPrompts] = useState<string[]>(aiCard.prompts)
  const [warning, setWarning] = useState<string | null>(null)
  const [pending, startTransition] = useTransition()

  async function sendMessage(message: string) {
    const trimmed = message.trim()
    if (!trimmed) return
    const nextMessages = [...messages, { role: "user" as const, content: trimmed }]
    setMessages(nextMessages)
    setInput("")
    setWarning(null)

    startTransition(async () => {
      const response = await fetch(`${BACKEND_BASE_URL}/frontend/copilot/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: productId ?? null,
          page_key: pageKey,
          page_title: pageTitle,
          user_message: trimmed,
          history: nextMessages.slice(-6),
        }),
      })
      const body = await response.json().catch(() => ({ message: "AI 助手当前不可用。" }))
      setMessages((current) => [...current, { role: "assistant", content: body.message ?? "AI 助手当前不可用。" }])
      setPrompts((body.followUpPrompts as string[] | undefined) ?? aiCard.prompts)
      setWarning(body.warning ?? null)
    })
  }

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="rounded-full bg-indigo-50 p-2 text-indigo-700">
          <span className="block h-4 w-4 rounded-full bg-current opacity-90" />
        </div>
        <div>
          <div className="text-[11px] font-medium uppercase tracking-[0.22em] text-zinc-500">Copilot</div>
          <div className="text-[15px] font-semibold tracking-tight text-zinc-950">AI 运营副驾驶</div>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {messages.slice(-4).map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={message.role === "assistant" ? "rounded-2xl bg-zinc-50 p-4 text-sm leading-relaxed text-zinc-700" : "rounded-2xl bg-zinc-950 p-4 text-sm leading-relaxed text-white"}
          >
            {message.content}
          </div>
        ))}
        {pending ? <div className="rounded-2xl bg-zinc-50 p-4 text-sm leading-relaxed text-zinc-500">AI 正在思考…</div> : null}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {prompts.slice(0, 3).map((prompt) => (
          <button key={prompt} onClick={() => sendMessage(prompt)} className="rounded-full border border-zinc-200 bg-white px-5 py-2.5 text-sm font-medium text-zinc-900 shadow-sm transition hover:bg-zinc-50">
            {prompt}
          </button>
        ))}
      </div>

      <div className="mt-5 rounded-2xl border border-zinc-200 bg-zinc-50 p-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="继续追问当前页面…"
          className="min-h-24 w-full resize-none bg-transparent text-sm leading-relaxed text-zinc-900 outline-none placeholder:text-zinc-400"
        />
        <div className="mt-3 flex items-center justify-between gap-3">
          <span className="text-[12px] text-zinc-500">{pageTitle}</span>
          <button disabled={pending || !input.trim()} onClick={() => sendMessage(input)} className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50">
            发送
          </button>
        </div>
      </div>
      {warning ? <p className="mt-4 text-sm leading-relaxed text-zinc-500">{warning}</p> : null}
    </section>
  )
}
