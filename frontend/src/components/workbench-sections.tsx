"use client";

import { ArrowUpRight } from "lucide-react";
import { useState } from "react";

import {
  analysisRows,
  executionBatches,
  executionEffect,
  opsTemplates,
  structureBuckets,
  topActions,
  trendBars,
  trendCards,
  workbenchStats,
} from "@/lib/mock-data";

function StatCard({ label, value, detail, className = "" }: { label: string; value: string; detail: string; className?: string }) {
  if (label === "最近一次分析") {
    const [date, time] = value.split(" · ");
    return (
      <article className={`rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm ${className}`.trim()}>
        <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">{label}</div>
        <div className="mt-4 flex items-end justify-between gap-3">
          <div className="whitespace-nowrap text-3xl font-bold tracking-tight text-zinc-950">{date}</div>
          <div className="pb-1 text-sm text-zinc-500">{time}</div>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-zinc-500">{detail}</p>
      </article>
    );
  }

  if (label === "当前阶段") {
    return (
      <article className={`rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm ${className}`.trim()}>
        <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">{label}</div>
        <div className="mt-4 max-w-[11ch] text-[1.75rem] font-semibold leading-tight tracking-tight text-zinc-950">{value}</div>
        <p className="mt-3 text-sm leading-relaxed text-zinc-500">{detail}</p>
      </article>
    );
  }

  const separator = value.includes(" · ") ? " · " : " ";
  const [primary, secondary] = value.split(separator);
  return (
    <article className={`rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm ${className}`.trim()}>
      <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">{label}</div>
      <div className="mt-4 flex items-end gap-2">
        <div className="text-3xl font-bold tracking-tight text-zinc-950">{primary}</div>
        {secondary ? <div className="pb-1 text-sm text-zinc-500">{secondary}</div> : null}
      </div>
      <p className="mt-3 text-sm leading-relaxed text-zinc-500">{detail}</p>
    </article>
  );
}

export function WorkbenchOverview() {
  return (
    <div className="space-y-8">
      <section className="grid gap-6 lg:grid-cols-3">
        <StatCard label={workbenchStats[0].label} value={workbenchStats[0].value} detail={workbenchStats[0].detail} className="lg:col-span-1" />
        <StatCard label={workbenchStats[1].label} value={workbenchStats[1].value} detail={workbenchStats[1].detail} className="lg:col-span-1" />
        <StatCard label={workbenchStats[2].label} value={workbenchStats[2].value} detail={workbenchStats[2].detail} className="lg:col-span-1" />
        <StatCard label={workbenchStats[3].label} value={workbenchStats[3].value} detail={workbenchStats[3].detail} className="lg:col-span-1" />
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <article className="rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm lg:col-span-2">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Action Radar</div>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-950">今日最优先 3 个动作</h2>
            </div>
            <span className="rounded-full bg-zinc-100 px-3 py-1.5 text-sm font-medium text-zinc-900">按优先级排序</span>
          </div>

          <div className="grid gap-4">
            {topActions.map((action) => (
              <article key={action.title} className="rounded-2xl bg-zinc-50 p-5">
                <div className="flex items-center justify-between">
                  <span className="rounded-full bg-white px-3 py-1 text-[11px] font-medium text-zinc-700 ring-1 ring-zinc-200/80">
                    {action.tag}
                  </span>
                  <ArrowUpRight className="h-4 w-4 text-indigo-700" />
                </div>
                <h3 className="mt-4 text-[1.05rem] font-medium tracking-tight text-zinc-900">{action.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-zinc-500">{action.description}</p>
              </article>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm lg:col-span-1 lg:self-start">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Execution Review</div>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-950">最近执行效果</h2>
            </div>
            <span className="rounded-full bg-indigo-50 px-3 py-1.5 text-sm font-medium text-indigo-700">{executionEffect.status}</span>
          </div>
          <p className="mt-4 text-sm leading-relaxed text-zinc-500">{executionEffect.summary}</p>
          <div className="mt-5 flex flex-wrap gap-2">
            {executionEffect.chips.map((chip) => (
              <span key={chip} className="rounded-full bg-zinc-100 px-3 py-1.5 text-sm font-medium text-zinc-900">{chip}</span>
            ))}
          </div>
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            <div className="rounded-2xl bg-zinc-50 p-5">
              <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">改善线索</div>
              <ul className="mt-3 space-y-2 text-sm text-zinc-900">
                {executionEffect.improving.map((term) => (
                  <li key={term}>{term}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl bg-zinc-50 p-5">
              <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">仍需关注</div>
              <ul className="mt-3 space-y-2 text-sm text-zinc-900">
                {executionEffect.risky.map((term) => (
                  <li key={term}>{term}</li>
                ))}
              </ul>
            </div>
          </div>
        </article>
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <article className="rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm lg:col-span-2">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Trend Pulse</div>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-950">近 30 天趋势概览</h2>
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {trendCards.map((card) => (
              <div key={card.label} className="rounded-2xl bg-zinc-50 p-4">
                <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-zinc-500">{card.label}</div>
                <div className="mt-3 text-[15px] font-semibold text-zinc-900">{card.value}</div>
                <div className="mt-2 text-[12px] leading-relaxed text-zinc-500">{card.detail}</div>
              </div>
            ))}
          </div>
          <div className="mt-6 rounded-2xl bg-zinc-50 p-6">
            <div className="flex items-end gap-4 border-t border-zinc-200 pt-5">
              {trendBars.map((bar, index) => (
                <div key={bar.label} className="flex flex-1 flex-col items-center gap-2">
                  <div
                    className={`rounded-full ${index === trendBars.length - 1 ? "bg-indigo-600" : "bg-zinc-200"}`}
                    style={{ width: index === trendBars.length - 1 ? 10 : 8, height: `${bar.value * 1.2}px` }}
                  />
                  <span className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">{bar.label}</span>
                </div>
              ))}
            </div>
          </div>
        </article>

        <article className="rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm lg:col-span-1">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Structure Lens</div>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-950">搜索词结构概览</h2>
          </div>
          <div className="mt-6 space-y-3">
            {structureBuckets.map((bucket) => (
              <div key={bucket.label} className="grid grid-cols-[96px_1fr_40px] items-center gap-4 rounded-2xl bg-zinc-50 px-4 py-3">
                <div className="text-[13px] font-medium text-zinc-900">{bucket.label}</div>
                <div className="h-2 rounded-full bg-zinc-200">
                  <div className="h-2 rounded-full bg-zinc-950" style={{ width: bucket.ratio === '<1%' ? '4%' : bucket.ratio }} />
                </div>
                <div className="text-right text-[12px] text-zinc-500">{bucket.count}</div>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}

export function TemplatesCenter() {
  const [activeTab, setActiveTab] = useState<"boss_summary" | "handoff_note" | "weekly_review">("boss_summary");
  const tabMeta = {
    boss_summary: { label: "老板摘要模板" },
    handoff_note: { label: "执行交接模板" },
    weekly_review: { label: "周度复盘模板" },
  };

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm">
      <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Delivery Layer</div>
      <h2 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-950">运营模板中心</h2>
      <div className="mt-6 flex flex-wrap gap-2">
        {(Object.entries(tabMeta) as Array<[keyof typeof tabMeta, (typeof tabMeta)[keyof typeof tabMeta]]>).map(([key, item]) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`rounded-full px-4 py-2 text-sm font-medium transition ${
              activeTab === key ? "bg-indigo-50 text-indigo-700" : "bg-zinc-100 text-zinc-900 hover:bg-zinc-50"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="mt-6 rounded-2xl bg-zinc-50 p-8">
        <div className="whitespace-pre-wrap text-base leading-relaxed text-zinc-500">{opsTemplates[activeTab]}</div>
      </div>
    </section>
  );
}

export function AnalysisTable() {
  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm">
      <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Analysis Table</div>
      <h2 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-950">搜索词分析总览</h2>
      <div className="mt-6 overflow-hidden rounded-2xl border border-zinc-200">
        <table className="w-full border-collapse text-left text-[13px] text-zinc-900">
          <thead className="bg-white text-[11px] font-medium uppercase tracking-[0.16em] text-zinc-500">
            <tr>
              <th className="px-4 py-3">关键词</th>
              <th className="px-4 py-3">类型</th>
              <th className="px-4 py-3">规则</th>
              <th className="px-4 py-3">动作</th>
              <th className="px-4 py-3">花费</th>
              <th className="px-4 py-3">订单</th>
              <th className="px-4 py-3">置信度</th>
            </tr>
          </thead>
          <tbody>
            {analysisRows.map((row) => (
              <tr key={row.term} className="border-t border-zinc-200 bg-zinc-50/60">
                <td className="px-4 py-4 font-medium text-zinc-900">{row.term}</td>
                <td className="px-4 py-4 text-zinc-500">{row.type}</td>
                <td className="px-4 py-4 text-zinc-500">{row.rule}</td>
                <td className="px-4 py-4"><span className="rounded-full bg-zinc-100 px-3 py-1 text-sm font-medium text-zinc-900">{row.action}</span></td>
                <td className="px-4 py-4">{row.spend}</td>
                <td className="px-4 py-4">{row.orders}</td>
                <td className="px-4 py-4">{row.confidence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function ExecutionBatchBoard() {
  return (
    <section className="space-y-5">
      {executionBatches.map((batch) => (
        <article key={batch.code} className="rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full bg-zinc-100 px-3 py-1 text-sm text-zinc-500">{batch.code}</span>
            <span className="rounded-full bg-zinc-100 px-3 py-1 text-sm text-zinc-500">{batch.type}</span>
            <span className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-700">{batch.status}</span>
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
            <div className="space-y-4">
              <div className="rounded-2xl bg-zinc-50 p-5">
                <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">批次摘要</div>
                <div className="mt-3 text-base font-semibold tracking-tight text-zinc-950">{batch.verdict}</div>
                <p className="mt-3 text-sm leading-relaxed text-zinc-500">{batch.summary}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl bg-zinc-50 p-4">
                  <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">覆盖项数</div>
                  <div className="mt-2 text-base font-semibold text-zinc-950">{batch.itemCount}</div>
                </div>
                <div className="rounded-2xl bg-zinc-50 p-4">
                  <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">总花费 / 总销售</div>
                  <div className="mt-2 text-base font-semibold text-zinc-950">{batch.spend} / {batch.sales}</div>
                </div>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl bg-zinc-50 p-5">
                <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">改善最多的词</div>
                <ul className="mt-3 space-y-2 text-sm text-zinc-900">
                  {batch.improving.map((term) => (
                    <li key={term}>{term}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl bg-zinc-50 p-5">
                <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">仍需重点关注</div>
                <ul className="mt-3 space-y-2 text-sm text-zinc-900">
                  {batch.risky.map((term) => (
                    <li key={term}>{term}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </article>
      ))}
    </section>
  );
}
