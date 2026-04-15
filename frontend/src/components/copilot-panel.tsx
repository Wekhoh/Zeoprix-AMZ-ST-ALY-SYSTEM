"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { getPageContextKey, readPageContext } from "@/components/page-context";
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

type ActionLink = {
  label: string
  href: string
}

type CopilotResponse = {
  message?: string
  followUpPrompts?: string[]
  recommendedNextActions?: string[]
  actionLinks?: ActionLink[]
  contextLabel?: string | null
  warning?: string | null
}

type StoredCopilotState = {
  messages: ChatMessage[]
  prompts: string[]
  recommendedActions: string[]
  actionLinks: ActionLink[]
  contextLabel: string | null
  warning: string | null
}

function buildStorageKey(productId: number | null | undefined, pageKey: string) {
  return `zeoprix-copilot:${productId ?? "global"}:${pageKey}`
}

function deriveFallbackActionLinks(actions: string[], pageKey: string): ActionLink[] {
  const links = new Map<string, ActionLink>()

  for (const action of actions) {
    if (/(审核|拍板|分歧)/.test(action) && pageKey !== "review") {
      links.set("review", { label: "去审核中心", href: "/review" })
    }
    if (/(批次|执行|否词|手动投放|补量)/.test(action) && pageKey !== "actions") {
      links.set("actions", { label: "去操作清单", href: "/actions" })
    }
    if (/(导入|上传|重跑分析|重新运行分析)/.test(action) && pageKey !== "upload") {
      links.set("upload", { label: "去数据导入", href: "/upload" })
    }
    if (/(备份|恢复|清空|数据管理)/.test(action) && pageKey !== "settings") {
      links.set("settings", { label: "去数据管理", href: "/settings" })
    }
    if (/(筛选|结构|分布|趋势|搜索词分析)/.test(action) && pageKey !== "analysis") {
      links.set("analysis", { label: "去搜索词分析", href: "/analysis" })
    }
  }

  return Array.from(links.values()).slice(0, 3)
}

function readInitialState(storageKey: string, aiCard: AICopilotCard): StoredCopilotState {
  const fallbackActions: string[] = []
  const fallback = {
    messages: [{ role: "assistant" as const, content: aiCard.summary }],
    prompts: aiCard.prompts,
    recommendedActions: fallbackActions,
    actionLinks: deriveFallbackActionLinks(fallbackActions, "workbench"),
    contextLabel: aiCard.context,
    warning: null,
  }

  if (typeof window === "undefined") {
    return fallback
  }

  try {
    const raw = window.sessionStorage.getItem(storageKey)
    if (!raw) return fallback
    const parsed = JSON.parse(raw) as Partial<StoredCopilotState>
    return {
      messages: parsed.messages?.length ? parsed.messages : fallback.messages,
      prompts: parsed.prompts?.length ? parsed.prompts : fallback.prompts,
      recommendedActions: parsed.recommendedActions ?? [],
      actionLinks: parsed.actionLinks ?? [],
      contextLabel: parsed.contextLabel ?? fallback.contextLabel,
      warning: parsed.warning ?? null,
    }
  } catch {
    return fallback
  }
}

export function CopilotPanel({ productId, pageKey, pageTitle, aiCard }: Props) {
  const router = useRouter()
  const storageKey = useMemo(() => buildStorageKey(productId, pageKey), [pageKey, productId])
  const pageContextKey = useMemo(() => getPageContextKey(productId, pageKey), [pageKey, productId])
  const initialState = useMemo(() => readInitialState(storageKey, aiCard), [aiCard, storageKey])

  const [messages, setMessages] = useState<ChatMessage[]>(initialState.messages)
  const [input, setInput] = useState("")
  const [prompts, setPrompts] = useState<string[]>(initialState.prompts)
  const [recommendedActions, setRecommendedActions] = useState<string[]>(initialState.recommendedActions)
  const [actionLinks, setActionLinks] = useState<ActionLink[]>(initialState.actionLinks)
  const [contextLabel, setContextLabel] = useState<string | null>(initialState.contextLabel)
  const [warning, setWarning] = useState<string | null>(initialState.warning)
  const [pageContext, setPageContext] = useState<Record<string, unknown>>(() => readPageContext(productId, pageKey))
  const [pending, startTransition] = useTransition()

  useEffect(() => {
    try {
      window.sessionStorage.setItem(
        storageKey,
        JSON.stringify({ messages, prompts, recommendedActions, actionLinks, contextLabel, warning }),
      )
    } catch {
      // ignore storage failures
    }
  }, [actionLinks, contextLabel, messages, prompts, recommendedActions, storageKey, warning])

  useEffect(() => {
    const syncPageContext = () => {
      setPageContext(readPageContext(productId, pageKey))
    }
    syncPageContext()

    const handle = (event: Event) => {
      const custom = event as CustomEvent<{ key?: string }>
      if (!custom.detail?.key || custom.detail.key === pageContextKey) {
        syncPageContext()
      }
    }

    window.addEventListener("zeoprix:page-context-updated", handle as EventListener)
    window.addEventListener("storage", syncPageContext)
    return () => {
      window.removeEventListener("zeoprix:page-context-updated", handle as EventListener)
      window.removeEventListener("storage", syncPageContext)
    }
  }, [pageContextKey, pageKey, productId])

  function clearConversation() {
    const resetMessages = [{ role: "assistant" as const, content: aiCard.summary }]
    setMessages(resetMessages)
    setPrompts(aiCard.prompts)
    setRecommendedActions([])
    setActionLinks([])
    setContextLabel(aiCard.context)
    setWarning(null)
    setInput("")
  }

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
          page_context: pageContext,
          user_message: trimmed,
          history: nextMessages.slice(-6),
        }),
      })
      const body = (await response.json().catch(() => ({ message: "AI 助手当前不可用。" }))) as CopilotResponse
      const nextActions = body.recommendedNextActions ?? []
      setMessages((current) => [...current, { role: "assistant", content: body.message ?? "AI 助手当前不可用。" }])
      setPrompts(body.followUpPrompts?.length ? body.followUpPrompts : aiCard.prompts)
      setRecommendedActions(nextActions)
      setActionLinks(body.actionLinks?.length ? body.actionLinks : deriveFallbackActionLinks(nextActions, pageKey))
      setContextLabel(body.contextLabel ?? aiCard.context)
      setWarning(body.warning ?? null)
    })
  }

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-indigo-50 p-2 text-indigo-700">
            <span className="block h-4 w-4 rounded-full bg-current opacity-90" />
          </div>
          <div>
            <div className="text-[11px] font-medium uppercase tracking-[0.22em] text-zinc-500">Copilot</div>
            <div className="text-[15px] font-semibold tracking-tight text-zinc-950">AI 运营副驾驶</div>
          </div>
        </div>
        <button onClick={clearConversation} className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-600 shadow-sm transition hover:bg-zinc-50 hover:text-zinc-900">
          重置
        </button>
      </div>

      {contextLabel ? (
        <div className="mt-5 inline-flex items-center rounded-full bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-700">
          {contextLabel}
        </div>
      ) : null}

      {Object.keys(pageContext).length ? (
        <div className="mt-3 rounded-2xl bg-zinc-50 px-4 py-3 text-sm leading-relaxed text-zinc-500">
          {String(pageContext.summary ?? "")}
        </div>
      ) : null}

      <div className="mt-4 space-y-3">
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

      {recommendedActions.length ? (
        <div className="mt-4 rounded-2xl bg-zinc-50 p-4">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Recommended next</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {recommendedActions.slice(0, 3).map((action) => (
              <button key={action} onClick={() => sendMessage(action)} className="rounded-full bg-white px-4 py-2 text-sm font-medium text-zinc-700 shadow-sm ring-1 ring-zinc-200 transition hover:bg-zinc-100 hover:text-zinc-900">
                {action}
              </button>
            ))}
          </div>
          {actionLinks.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {actionLinks.map((link) => (
                <button key={link.href} onClick={() => router.push(link.href)} className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-600 shadow-sm transition hover:bg-zinc-50 hover:text-zinc-900">
                  {link.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

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
