"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Bot,
  Database,
  FolderUp,
  LayoutDashboard,
  ListChecks,
  Settings2,
  ShieldCheck,
} from "lucide-react";
import type { ReactNode } from "react";

import { aiCopilotCards, navItems, productContext } from "@/lib/mock-data";

const iconMap: Record<string, ReactNode> = {
  "/": <LayoutDashboard className="h-4 w-4" />,
  "/upload": <FolderUp className="h-4 w-4" />,
  "/analysis": <BarChart3 className="h-4 w-4" />,
  "/actions": <ListChecks className="h-4 w-4" />,
  "/review": <ShieldCheck className="h-4 w-4" />,
  "/settings": <Database className="h-4 w-4" />,
};

export function DashboardShell({ children, title, subtitle }: { children: ReactNode; title: string; subtitle: string }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[#fbfbf8] text-[#111111]">
      <div className="mx-auto grid min-h-screen max-w-[1600px] grid-cols-[260px_minmax(0,1fr)_320px]">
        <aside className="border-r border-black/6 bg-white px-6 py-6">
          <div className="mb-10">
            <div className="mb-4 text-[11px] font-medium uppercase tracking-[0.24em] text-black/40">Amazon Ops OS</div>
            <h1 className="font-display text-[1.28rem] leading-[1.1] font-semibold tracking-[-0.035em] text-[#111111]">Zeoprix Ops Workbench</h1>
            <p className="mt-4 max-w-[17rem] text-[12px] leading-6 text-black/46">把搜索词分析、执行批次、复盘与 AI 副驾驶收进同一个运营工作台。</p>
          </div>

          <div className="mb-8 rounded-[24px] border border-black/8 bg-[#fafaf7] p-4">
            <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">当前工作区</div>
            <div className="mt-3 text-[14px] font-medium text-[#111111]">{productContext.workspace}</div>
            <div className="mt-1 text-[12px] text-black/46">{productContext.name}</div>
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full border border-black/8 bg-white px-3 py-1 text-[12px] text-black/70">{productContext.role}</span>
              <span className="rounded-full border border-black/8 bg-white px-3 py-1 text-[12px] text-black/60">最近分析 {productContext.lastAnalysisAt}</span>
            </div>
          </div>

          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`group flex items-center justify-between rounded-2xl px-4 py-3 transition ${
                    active ? "bg-[#111111] text-white" : "text-black/60 hover:bg-black/[0.04] hover:text-black"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={active ? "text-white" : "text-black/35"}>{iconMap[item.href]}</span>
                    <div>
                      <div className={`text-[10px] uppercase tracking-[0.22em] ${active ? "text-white/55" : "text-black/35"}`}>{item.eyebrow}</div>
                      <div className="text-[13px] font-medium">{item.label}</div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </nav>

          <div className="mt-8 rounded-[24px] border border-black/8 bg-[#f6f7f4] p-4">
            <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">最近备份</div>
            <div className="mt-2 text-[13px] font-medium text-[#111111]">{productContext.lastBackupAt}</div>
            <p className="mt-3 text-[12px] leading-6 text-black/46">建议切换新类目前，先导出完整备份并标记恢复点。</p>
          </div>
        </aside>

        <main className="relative overflow-hidden border-r border-black/6 bg-[#fcfcfa] px-10 py-8">
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(15,23,42,0.04)_1px,transparent_1px),linear-gradient(to_bottom,rgba(15,23,42,0.04)_1px,transparent_1px)] bg-[size:88px_88px] opacity-80" />
          <div className="relative z-10">
            <header className="mb-10 flex items-start justify-between gap-8 border-b border-black/6 pb-8">
              <div className="max-w-4xl">
                <div className="text-[11px] uppercase tracking-[0.24em] text-black/35">运营工作台</div>
                <h2 className="mt-4 max-w-[12ch] font-display text-[3rem] leading-[1] font-semibold tracking-[-0.05em] text-[#111111]">{title}</h2>
                <p className="mt-5 max-w-3xl text-[15px] leading-7 text-black/48">{subtitle}</p>
              </div>
              <div className="rounded-[28px] border border-black/8 bg-white px-5 py-4 text-right shadow-[0_12px_30px_rgba(15,23,42,0.06)]">
                <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">今天建议先做</div>
                <div className="mt-3 max-w-[14rem] text-[12px] leading-6 font-medium text-[#111111]">先止损，再补量，最后复盘分歧词</div>
              </div>
            </header>
            {children}
          </div>
        </main>

        <aside className="bg-[#f6f7f4] px-6 py-6">
          <div className="mb-6 flex items-center gap-3">
            <div className="rounded-2xl border border-black/8 bg-white p-2 text-black/70"><Bot className="h-5 w-5" /></div>
            <div>
              <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">Copilot</div>
              <div className="text-[14px] font-medium text-[#111111]">AI 运营副驾驶</div>
            </div>
          </div>

          <div className="mb-4 rounded-[24px] border border-black/8 bg-white p-4">
            <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">当前上下文</div>
            <div className="mt-2 text-[13px] font-medium text-[#111111]">{productContext.name}</div>
            <p className="mt-2 text-[12px] leading-6 text-black/46">基于最近一次分析结果、执行批次与审核沉淀生成建议。</p>
          </div>

          <div className="space-y-4">
            {aiCopilotCards.map((card) => (
              <section key={card.title} className="rounded-[24px] border border-black/8 bg-white p-4">
                <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">{card.title}</div>
                <div className="mt-3 text-[13px] leading-6 font-medium text-[#111111]">{card.summary}</div>
                <p className="mt-2 text-[12px] leading-6 text-black/46">{card.context}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {card.prompts.map((prompt) => (
                    <button key={prompt} className="rounded-full border border-black/8 bg-[#fafaf7] px-3 py-1.5 text-[12px] text-black/70 transition hover:border-black/15 hover:bg-black/[0.03]">{prompt}</button>
                  ))}
                </div>
              </section>
            ))}
          </div>

          <div className="mt-6 rounded-[24px] border border-black/8 bg-white p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">准备提问</div>
                <div className="mt-1 text-[12px] text-black/46">用副驾驶把结果解释成可执行动作</div>
              </div>
              <Settings2 className="h-4 w-4 text-black/35" />
            </div>
            <div className="mt-4 rounded-[20px] border border-black/8 bg-[#fafaf7] p-3 text-[12px] text-black/42">“帮我基于当前批次，生成老板摘要和执行备注”</div>
            <button className="mt-4 w-full rounded-[20px] bg-[#111111] px-4 py-3 text-[13px] font-medium text-white transition hover:bg-black">打开 AI 助手</button>
          </div>
        </aside>
      </div>
    </div>
  )
}
