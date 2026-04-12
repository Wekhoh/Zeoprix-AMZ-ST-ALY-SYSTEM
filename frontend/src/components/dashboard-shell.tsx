"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowUpRight, Bot } from "lucide-react";
import type { ReactNode } from "react";

import { aiCopilotCards, navItems, productContext } from "@/lib/mock-data";

export function DashboardShell({ children, title, subtitle }: { children: ReactNode; title: string; subtitle: string }) {
  const pathname = usePathname();
  const primaryCard = aiCopilotCards[0];

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      <div className="border-b border-zinc-200/70 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-6 lg:px-10">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-3">
              <div className="h-7 w-7 rounded-full bg-zinc-900" />
              <div>
                <div className="font-display text-[16px] font-semibold tracking-[-0.05em] text-zinc-900">Zeoprix</div>
                <div className="text-[11px] text-zinc-500">Amazon Ads Workbench</div>
              </div>
            </Link>
            <nav className="hidden items-center gap-1 md:flex">
              {navItems.map((item) => {
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`rounded-full px-3 py-2 text-[13px] font-medium transition ${
                      active ? "bg-zinc-100 text-zinc-900" : "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden rounded-full bg-zinc-100 px-3 py-1.5 text-[12px] font-medium text-zinc-700 sm:inline-flex">
              {productContext.role}
            </span>
            <button className="rounded-full bg-zinc-900 px-4 py-2 text-[13px] font-medium text-white shadow-sm transition hover:bg-zinc-800">
              数据管理
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-[1440px] px-6 py-8 lg:px-10 lg:py-10">
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_300px]">
          <main className="space-y-8">
            <section className="rounded-[36px] border border-zinc-200/60 bg-white px-8 py-10 shadow-sm lg:px-10">
              <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_248px] lg:items-end">
                <div className="max-w-3xl">
                  <div className="text-[11px] font-medium uppercase tracking-[0.24em] text-zinc-500">运营工作台</div>
                  <h1 className="mt-4 whitespace-nowrap font-display text-[2.1rem] font-semibold tracking-[-0.08em] text-zinc-900 lg:text-[2.35rem]">
                    {title}
                  </h1>
                  <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-zinc-700 font-normal">{subtitle}</p>
                </div>

                <div className="space-y-3">
                  <div className="rounded-[24px] bg-zinc-50 px-5 py-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">当前产品</div>
                    <div className="mt-2 text-[15px] font-medium text-zinc-900">{productContext.name}</div>
                    <div className="mt-1 text-sm text-zinc-500">{productContext.workspace}</div>
                  </div>
                  <div className="rounded-[24px] bg-zinc-50 px-5 py-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">最近更新</div>
                    <div className="mt-2 text-sm font-medium text-zinc-900">分析 {productContext.lastAnalysisAt}</div>
                    <div className="mt-1 text-sm text-zinc-500">备份 {productContext.lastBackupAt}</div>
                  </div>
                </div>
              </div>
            </section>

            {children}
          </main>

          <aside className="space-y-4 xl:sticky xl:top-8 xl:self-start">
            <section className="rounded-[28px] border border-zinc-200/60 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="rounded-2xl bg-indigo-50 p-2 text-indigo-600">
                  <Bot className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-500">Copilot</div>
                  <div className="font-display text-[15px] font-semibold tracking-[-0.03em] text-zinc-900">AI 运营副驾驶</div>
                </div>
              </div>

              <div className="mt-5 text-[12px] font-medium text-zinc-500">聚焦：止损与补量</div>
              <p className="mt-3 text-sm leading-relaxed text-zinc-700">{primaryCard.summary}</p>

              <div className="mt-5 flex flex-wrap gap-2">
                {primaryCard.prompts.slice(0, 2).map((prompt) => (
                  <button key={prompt} className="rounded-full bg-zinc-100 px-3 py-2 text-[12px] font-medium text-zinc-700 transition hover:bg-zinc-200">
                    {prompt}
                  </button>
                ))}
                <button className="rounded-full bg-indigo-50 px-3 py-2 text-[12px] font-medium text-indigo-700 transition hover:bg-indigo-100">
                  生成老板摘要
                </button>
              </div>

              <button className="mt-5 inline-flex items-center gap-2 text-[13px] font-medium text-zinc-900 transition hover:text-indigo-600">
                打开完整 Copilot <ArrowUpRight className="h-4 w-4 text-indigo-600" />
              </button>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}
