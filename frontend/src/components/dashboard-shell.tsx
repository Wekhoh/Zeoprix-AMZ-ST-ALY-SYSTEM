"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { aiCopilotCards, navItems, productContext as defaultProductContext, type AICopilotCard, type ProductContext } from "@/lib/mock-data";
import { CopilotPanel } from "@/components/copilot-panel";

export function DashboardShell({
  children,
  title,
  subtitle,
  productContext,
  productId,
  aiCard,
}: {
  children: ReactNode
  title: string
  subtitle: string
  productContext?: ProductContext | null
  productId?: number | null
  aiCard?: AICopilotCard | null
}) {
  const pathname = usePathname();
  const currentProduct = productContext ?? defaultProductContext
  const primaryCard = aiCard ?? aiCopilotCards[0];

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      <header className="border-b border-zinc-200/60 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-6 lg:px-10">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-3">
              <div className="h-7 w-7 rounded-full bg-zinc-950" />
              <div>
                <div className="text-[16px] font-semibold tracking-tight text-zinc-950">Zeoprix</div>
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
                      active ? "bg-zinc-100 text-zinc-950" : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900"
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
              {currentProduct.role}
            </span>
            <button className="rounded-full bg-zinc-950 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800">
              数据管理
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1440px] px-6 py-8 lg:px-10 lg:py-10">
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_320px]">
          <main className="space-y-8">
            <section className="relative overflow-hidden rounded-2xl border border-zinc-200 bg-white px-8 py-10 shadow-sm lg:px-10">
              <div className="absolute inset-0 opacity-40 [background-image:linear-gradient(to_right,rgba(161,161,170,0.12)_1px,transparent_1px),linear-gradient(to_bottom,rgba(161,161,170,0.12)_1px,transparent_1px)] [background-size:64px_64px]" />
              <div className="pointer-events-none absolute inset-x-24 bottom-0 h-40 -z-0 bg-gradient-to-r from-cyan-300/30 via-violet-300/30 to-fuchsia-300/30 blur-[100px]" />
              <div className="relative z-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_272px] lg:items-end">
                <div className="max-w-3xl">
                  <div className="text-[11px] font-medium uppercase tracking-[0.24em] text-zinc-500">运营工作台</div>
                  <h1 className="mt-4 whitespace-nowrap text-4xl font-semibold tracking-tight text-zinc-950">{title}</h1>
                  <p className="mt-4 max-w-xl text-base leading-relaxed text-zinc-500">{subtitle}</p>
                  <div className="mt-8 flex flex-wrap gap-3">
                    <button className="rounded-full bg-zinc-950 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800">
                      查看今日动作
                    </button>
                    <button className="rounded-full border border-zinc-200 bg-white px-6 py-2.5 text-sm font-medium text-zinc-900 shadow-sm transition hover:bg-zinc-50">
                      打开数据管理
                    </button>
                  </div>
                </div>

                <div className="grid gap-3">
                  <div className="rounded-2xl bg-zinc-50 p-5">
                    <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">当前产品</div>
                    <div className="mt-2 text-[15px] font-medium text-zinc-900">{currentProduct.name}</div>
                    <div className="mt-1 text-sm text-zinc-500">{currentProduct.workspace}</div>
                  </div>
                  <div className="rounded-2xl bg-zinc-50 p-5">
                    <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">最近更新</div>
                    <div className="mt-2 text-sm font-medium text-zinc-900">分析 {currentProduct.lastAnalysisAt}</div>
                    <div className="mt-1 text-sm text-zinc-500">备份 {currentProduct.lastBackupAt}</div>
                  </div>
                </div>
              </div>
            </section>

            {children}
          </main>

          <aside className="space-y-4 xl:sticky xl:top-8 xl:self-start">
            <CopilotPanel
              productId={productId ?? null}
              pageKey={pathname === "/" ? "workbench" : pathname.replace("/", "")}
              pageTitle={title}
              aiCard={primaryCard}
            />
          </aside>
        </div>
      </div>
    </div>
  );
}
