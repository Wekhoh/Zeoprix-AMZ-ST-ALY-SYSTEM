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
    <div className="min-h-screen bg-[#090E16] text-slate-100">
      <div className="mx-auto grid min-h-screen max-w-[1600px] grid-cols-[280px_minmax(0,1fr)_340px] gap-0">
        <aside className="border-r border-white/10 bg-[linear-gradient(180deg,#0E1626_0%,#0A1220_100%)] px-5 py-6">
          <div className="mb-8">
            <div className="mb-3 inline-flex rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-200">
              Amazon Ops OS
            </div>
            <h1 className="font-display text-2xl font-semibold tracking-tight text-white">Zeoprix Ops Workbench</h1>
            <p className="mt-3 text-sm leading-6 text-slate-400">把搜索词分析、执行批次、复盘与 AI 副驾驶收进同一个运营工作台。</p>
          </div>

          <div className="mb-6 rounded-2xl border border-white/8 bg-white/5 p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">当前工作区</div>
            <div className="mt-2 text-sm font-semibold text-white">{productContext.workspace}</div>
            <div className="mt-1 text-sm text-slate-400">{productContext.name}</div>
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-3 py-1 text-xs text-amber-100">{productContext.role}</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">最近分析 {productContext.lastAnalysisAt}</span>
            </div>
          </div>

          <nav className="space-y-2">
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`group flex items-center justify-between rounded-2xl px-4 py-3 transition ${
                    active ? "bg-white text-slate-950 shadow-[0_10px_30px_rgba(255,255,255,0.08)]" : "text-slate-300 hover:bg-white/6 hover:text-white"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={active ? "text-sky-600" : "text-slate-500"}>{iconMap[item.href]}</span>
                    <div>
                      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{item.eyebrow}</div>
                      <div className="text-sm font-medium">{item.label}</div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </nav>

          <div className="mt-8 rounded-2xl border border-emerald-400/15 bg-emerald-400/8 p-4 text-sm text-emerald-100">
            <div className="mb-2 text-xs uppercase tracking-[0.18em] text-emerald-200/70">最近备份</div>
            <div className="font-medium">{productContext.lastBackupAt}</div>
            <p className="mt-2 text-emerald-100/70">建议切换新类目前，先导出完整备份并标记恢复点。</p>
          </div>
        </aside>

        <main className="bg-[radial-gradient(circle_at_top_left,rgba(76,201,240,0.10),transparent_28%),linear-gradient(180deg,#0A111C_0%,#0C1422_100%)] px-8 py-8">
          <header className="mb-8 flex items-start justify-between gap-6">
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">运营工作台</div>
              <h2 className="mt-3 font-display text-4xl font-semibold tracking-tight text-white">{title}</h2>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-400">{subtitle}</p>
            </div>
            <div className="rounded-2xl border border-white/8 bg-white/5 px-4 py-3 text-right">
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">今天建议先做</div>
              <div className="mt-2 text-sm font-medium text-white">先止损，再补量，最后复盘分歧词</div>
            </div>
          </header>
          {children}
        </main>

        <aside className="border-l border-white/10 bg-[linear-gradient(180deg,#0B111C_0%,#0A1019_100%)] px-5 py-6">
          <div className="mb-5 flex items-center gap-3">
            <div className="rounded-2xl bg-white/8 p-2 text-cyan-200"><Bot className="h-5 w-5" /></div>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Copilot</div>
              <div className="font-medium text-white">AI 运营副驾驶</div>
            </div>
          </div>

          <div className="mb-4 rounded-2xl border border-white/8 bg-white/5 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">当前上下文</div>
            <div className="mt-2 text-sm font-medium text-white">{productContext.name}</div>
            <p className="mt-2 text-sm leading-6 text-slate-400">基于最近一次分析结果、执行批次与审核沉淀生成建议。</p>
          </div>

          <div className="space-y-4">
            {aiCopilotCards.map((card) => (
              <section key={card.title} className="rounded-2xl border border-white/8 bg-white/5 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{card.title}</div>
                <div className="mt-2 text-sm font-semibold text-white">{card.summary}</div>
                <p className="mt-2 text-sm leading-6 text-slate-400">{card.context}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {card.prompts.map((prompt) => (
                    <button key={prompt} className="rounded-full border border-white/10 bg-white/6 px-3 py-1.5 text-xs text-slate-200 transition hover:border-cyan-300/40 hover:bg-cyan-300/10">{prompt}</button>
                  ))}
                </div>
              </section>
            ))}
          </div>

          <div className="mt-6 rounded-2xl border border-white/8 bg-white/5 p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">准备提问</div>
                <div className="mt-1 text-sm text-slate-300">用副驾驶把结果解释成可执行动作</div>
              </div>
              <Settings2 className="h-4 w-4 text-slate-500" />
            </div>
            <div className="mt-4 rounded-2xl border border-white/10 bg-[#070B12] p-3 text-sm text-slate-500">“帮我基于当前批次，生成老板摘要和执行备注”</div>
            <button className="mt-4 w-full rounded-2xl bg-white px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-100">打开 AI 助手</button>
          </div>
        </aside>
      </div>
    </div>
  );
}
