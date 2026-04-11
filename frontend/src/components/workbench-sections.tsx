import { ArrowUpRight, TrendingUp } from "lucide-react";

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

export function WorkbenchOverview() {
  return (
    <div className="space-y-8">
      <section className="grid gap-4 lg:grid-cols-4">
        {workbenchStats.map((card) => (
          <div key={card.label} className="rounded-3xl border border-white/8 bg-white/[0.03] p-5 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{card.label}</div>
            <div className="mt-3 text-xl font-semibold text-white">{card.value}</div>
            <p className="mt-3 text-sm leading-6 text-slate-400">{card.detail}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Action Radar</div>
              <h3 className="mt-2 text-2xl font-semibold text-white">今日最优先 3 个动作</h3>
            </div>
            <div className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-200">今日优先级</div>
          </div>
          <div className="space-y-4">
            {topActions.map((action) => (
              <div key={action.title} className="rounded-3xl border border-white/8 bg-[#0A1018] p-5 transition hover:border-cyan-300/30 hover:bg-[#0D1420]">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-[0.18em] text-cyan-300/70">{action.tag}</div>
                  <ArrowUpRight className="h-4 w-4 text-slate-500" />
                </div>
                <div className="mt-3 text-lg font-semibold text-white">{action.title}</div>
                <p className="mt-3 text-sm leading-6 text-slate-400">{action.description}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <section className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Trend Pulse</div>
                <h3 className="mt-2 text-2xl font-semibold text-white">近 30 天趋势概览</h3>
              </div>
              <TrendingUp className="h-5 w-5 text-cyan-300" />
            </div>
            <div className="mt-6 grid gap-3">
              {trendCards.map((card) => (
                <div key={card.label} className="rounded-2xl border border-white/8 bg-[#0A1018] p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{card.label}</div>
                  <div className="mt-2 text-lg font-semibold text-white">{card.value}</div>
                  <div className="mt-2 text-sm leading-6 text-slate-400">{card.detail}</div>
                </div>
              ))}
            </div>
            <div className="mt-6 flex items-end gap-3 rounded-3xl border border-white/8 bg-[#070B12] px-4 py-5">
              {trendBars.map((bar) => (
                <div key={bar.label} className="flex flex-1 flex-col items-center gap-2">
                  <div className="w-full rounded-full bg-gradient-to-t from-cyan-400 to-sky-500" style={{ height: `${bar.value * 1.6}px` }} />
                  <span className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{bar.label}</span>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <div className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
          <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Structure Lens</div>
          <h3 className="mt-2 text-2xl font-semibold text-white">搜索词结构概览</h3>
          <p className="mt-3 text-sm leading-6 text-slate-400">先看流量是被哪些结构占据：泛词过多通常意味着浪费，核心词与高质量长尾越多，结构越健康。</p>
          <div className="mt-6 grid gap-3">
            {structureBuckets.map((bucket) => (
              <div key={bucket.label} className="flex items-center justify-between rounded-2xl border border-white/8 bg-[#0A1018] px-4 py-3">
                <div>
                  <div className="text-sm font-medium text-white">{bucket.label}</div>
                  <div className="text-xs uppercase tracking-[0.16em] text-slate-500">{bucket.ratio}</div>
                </div>
                <div className="text-lg font-semibold text-cyan-200">{bucket.count}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
          <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Execution Review</div>
          <h3 className="mt-2 text-2xl font-semibold text-white">最近执行效果</h3>
          <p className="mt-3 text-sm leading-6 text-slate-400">{executionEffect.summary}</p>
          <div className="mt-5 flex flex-wrap gap-2">
            <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-200">{executionEffect.status}</span>
            {executionEffect.chips.map((chip) => (
              <span key={chip} className="rounded-full border border-white/8 bg-white/5 px-3 py-1 text-xs font-medium text-slate-300">{chip}</span>
            ))}
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/8 bg-[#0A1018] p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">改善线索</div>
              <ul className="mt-3 space-y-2 text-sm text-slate-200">
                {executionEffect.improving.map((term) => (
                  <li key={term}>• {term}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-white/8 bg-[#0A1018] p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">仍需关注</div>
              <ul className="mt-3 space-y-2 text-sm text-slate-200">
                {executionEffect.risky.map((term) => (
                  <li key={term}>• {term}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

export function TemplatesCenter() {
  return (
    <section className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Delivery Layer</div>
      <h3 className="mt-2 text-2xl font-semibold text-white">运营模板中心</h3>
      <p className="mt-3 text-sm leading-6 text-slate-400">把首页已经整理好的判断直接转成可交付文本，减少你再手工整理日报、交接和周度复盘摘要的时间。</p>

      <div className="mt-6 grid gap-3 md:grid-cols-3">
        {[
          ['老板摘要模板', '给老板 / 管理者快速同步当日重点'],
          ['执行交接模板', '给执行同事或助理的操作说明'],
          ['周度复盘模板', '整理一周变化、动作与风险'],
        ].map(([title, desc]) => (
          <div key={title} className="rounded-2xl border border-white/8 bg-[#0A1018] p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">模板用途</div>
            <div className="mt-2 text-base font-semibold text-white">{title}</div>
            <div className="mt-2 text-sm leading-6 text-slate-400">{desc}</div>
          </div>
        ))}
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-3">
        {[
          ['老板摘要模板', opsTemplates.boss_summary],
          ['执行交接模板', opsTemplates.handoff_note],
          ['周度复盘模板', opsTemplates.weekly_review],
        ].map(([title, content]) => (
          <div key={title} className="rounded-3xl border border-white/8 bg-[#070B12] p-5">
            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{title}</div>
            <div className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-200">{content}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

export function AnalysisTable() {
  return (
    <section className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Analysis Table</div>
      <h3 className="mt-2 text-2xl font-semibold text-white">搜索词分析总览</h3>
      <div className="mt-6 overflow-hidden rounded-3xl border border-white/8">
        <table className="w-full border-collapse text-left text-sm text-slate-200">
          <thead className="bg-white/5 text-xs uppercase tracking-[0.18em] text-slate-500">
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
              <tr key={row.term} className="border-t border-white/8 bg-[#0A1018]">
                <td className="px-4 py-4 font-medium text-white">{row.term}</td>
                <td className="px-4 py-4 text-slate-400">{row.type}</td>
                <td className="px-4 py-4 text-slate-400">{row.rule}</td>
                <td className="px-4 py-4"><span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-100">{row.action}</span></td>
                <td className="px-4 py-4">{row.spend}</td>
                <td className="px-4 py-4">{row.orders}</td>
                <td className="px-4 py-4">{row.confidence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export function ExecutionBatchBoard() {
  return (
    <section className="space-y-5">
      {executionBatches.map((batch) => (
        <article key={batch.code} className="rounded-[28px] border border-white/8 bg-white/[0.03] p-6 shadow-[0_24px_60px_rgba(7,12,20,0.35)]">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full border border-white/8 bg-white/5 px-3 py-1 text-xs text-slate-300">{batch.code}</span>
            <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-100">{batch.type}</span>
            <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs text-emerald-100">{batch.status}</span>
          </div>
          <div className="mt-5 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
            <div className="space-y-4">
              <div className="rounded-2xl border border-white/8 bg-[#0A1018] p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">批次摘要</div>
                <div className="mt-3 text-lg font-semibold text-white">{batch.verdict}</div>
                <p className="mt-2 text-sm leading-6 text-slate-400">{batch.summary}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/8 bg-[#0A1018] p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">覆盖项数</div>
                  <div className="mt-2 text-lg font-semibold text-white">{batch.itemCount}</div>
                </div>
                <div className="rounded-2xl border border-white/8 bg-[#0A1018] p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">总花费 / 总销售</div>
                  <div className="mt-2 text-lg font-semibold text-white">{batch.spend} / {batch.sales}</div>
                </div>
              </div>
            </div>
            <div className="space-y-4">
              <div className="rounded-2xl border border-white/8 bg-[#0A1018] p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">改善最多的词</div>
                <ul className="mt-3 space-y-2 text-sm text-slate-200">
                  {batch.improving.map((term) => (
                    <li key={term}>• {term}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl border border-white/8 bg-[#0A1018] p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">仍需重点关注</div>
                <ul className="mt-3 space-y-2 text-sm text-slate-200">
                  {batch.risky.map((term) => (
                    <li key={term}>• {term}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </article>
      ))}
    </section>
  )
}
