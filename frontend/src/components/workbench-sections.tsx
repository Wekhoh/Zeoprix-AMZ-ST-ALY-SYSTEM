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
    <div className="space-y-10">
      <section className="grid gap-4 lg:grid-cols-4">
        {workbenchStats.map((card) => (
          <div key={card.label} className="rounded-[28px] border border-black/6 bg-white p-6 shadow-[0_24px_50px_rgba(15,23,42,0.06)]">
            <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">{card.label}</div>
            <div className="mt-3 text-[1.35rem] font-semibold tracking-[-0.03em] text-[#111111]">{card.value}</div>
            <p className="mt-3 text-[14px] leading-7 text-black/48">{card.detail}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.12fr_0.88fr]">
        <div className="rounded-[32px] border border-black/6 bg-white p-7 shadow-[0_26px_60px_rgba(15,23,42,0.06)]">
          <div className="mb-7 flex items-center justify-between">
            <div>
              <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">Action Radar</div>
              <h3 className="mt-3 text-[2rem] font-semibold tracking-[-0.05em] text-[#111111]">今日最优先 3 个动作</h3>
            </div>
            <div className="rounded-full border border-black/8 bg-[#fafaf7] px-3 py-1 text-[12px] text-black/55">今日优先级</div>
          </div>
          <div className="space-y-4">
            {topActions.map((action) => (
              <div key={action.title} className="rounded-[28px] border border-black/6 bg-[#fbfbf8] p-5 transition hover:border-black/12 hover:bg-white">
                <div className="flex items-center justify-between">
                  <div className="text-[11px] uppercase tracking-[0.22em] text-black/40">{action.tag}</div>
                  <ArrowUpRight className="h-4 w-4 text-black/25" />
                </div>
                <div className="mt-3 text-[1.05rem] font-semibold leading-7 tracking-[-0.03em] text-[#111111]">{action.title}</div>
                <p className="mt-3 text-[14px] leading-7 text-black/50">{action.description}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <section className="rounded-[32px] border border-black/6 bg-white p-7 shadow-[0_26px_60px_rgba(15,23,42,0.06)]">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">Trend Pulse</div>
                <h3 className="mt-3 text-[2rem] font-semibold tracking-[-0.05em] text-[#111111]">近 30 天趋势概览</h3>
              </div>
              <TrendingUp className="h-5 w-5 text-black/30" />
            </div>
            <div className="mt-6 grid gap-3">
              {trendCards.map((card) => (
                <div key={card.label} className="rounded-[24px] border border-black/6 bg-[#fbfbf8] p-4">
                  <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">{card.label}</div>
                  <div className="mt-2 text-[1.05rem] font-semibold text-[#111111]">{card.value}</div>
                  <div className="mt-2 text-[13px] leading-6 text-black/48">{card.detail}</div>
                </div>
              ))}
            </div>
            <div className="mt-6 flex items-end gap-3 rounded-[28px] border border-black/6 bg-[#fbfbf8] px-4 py-5">
              {trendBars.map((bar) => (
                <div key={bar.label} className="flex flex-1 flex-col items-center gap-2">
                  <div className="w-full rounded-full bg-[linear-gradient(to_top,#111111,#6b7280)]" style={{ height: `${bar.value * 1.6}px` }} />
                  <span className="text-[11px] uppercase tracking-[0.16em] text-black/35">{bar.label}</span>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <div className="rounded-[32px] border border-black/6 bg-white p-7 shadow-[0_26px_60px_rgba(15,23,42,0.06)]">
          <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">Structure Lens</div>
          <h3 className="mt-3 text-[2rem] font-semibold tracking-[-0.05em] text-[#111111]">搜索词结构概览</h3>
          <p className="mt-4 text-[14px] leading-7 text-black/50">先看流量是被哪些结构占据：泛词过多通常意味着浪费，核心词与高质量长尾越多，结构越健康。</p>
          <div className="mt-6 grid gap-3">
            {structureBuckets.map((bucket) => (
              <div key={bucket.label} className="flex items-center justify-between rounded-[24px] border border-black/6 bg-[#fbfbf8] px-4 py-3">
                <div>
                  <div className="text-[14px] font-medium text-[#111111]">{bucket.label}</div>
                  <div className="text-[11px] uppercase tracking-[0.16em] text-black/35">{bucket.ratio}</div>
                </div>
                <div className="text-[1.05rem] font-semibold text-[#111111]">{bucket.count}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[32px] border border-black/6 bg-white p-7 shadow-[0_26px_60px_rgba(15,23,42,0.06)]">
          <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">Execution Review</div>
          <h3 className="mt-3 text-[2rem] font-semibold tracking-[-0.05em] text-[#111111]">最近执行效果</h3>
          <p className="mt-4 text-[14px] leading-7 text-black/50">{executionEffect.summary}</p>
          <div className="mt-5 flex flex-wrap gap-2">
            <span className="rounded-full border border-black/8 bg-[#111111] px-3 py-1 text-[12px] text-white">{executionEffect.status}</span>
            {executionEffect.chips.map((chip) => (
              <span key={chip} className="rounded-full border border-black/8 bg-[#fbfbf8] px-3 py-1 text-[12px] text-black/65">{chip}</span>
            ))}
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-[24px] border border-black/6 bg-[#fbfbf8] p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-black/35">改善线索</div>
              <ul className="mt-3 space-y-2 text-[14px] text-black/75">
                {executionEffect.improving.map((term) => (
                  <li key={term}>• {term}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-[24px] border border-black/6 bg-[#fbfbf8] p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-black/35">仍需关注</div>
              <ul className="mt-3 space-y-2 text-[14px] text-black/75">
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
    <section className="rounded-[32px] border border-black/6 bg-white p-7 shadow-[0_26px_60px_rgba(15,23,42,0.06)]">
      <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">Delivery Layer</div>
      <h3 className="mt-3 text-[2rem] font-semibold tracking-[-0.05em] text-[#111111]">运营模板中心</h3>
      <p className="mt-4 text-[14px] leading-7 text-black/50">把首页已经整理好的判断直接转成可交付文本，减少你再手工整理日报、交接和周度复盘摘要的时间。</p>

      <div className="mt-6 grid gap-3 md:grid-cols-3">
        {[
          ['老板摘要模板', '给老板 / 管理者快速同步当日重点'],
          ['执行交接模板', '给执行同事或助理的操作说明'],
          ['周度复盘模板', '整理一周变化、动作与风险'],
        ].map(([title, desc]) => (
          <div key={title} className="rounded-[24px] border border-black/6 bg-[#fbfbf8] p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-black/35">模板用途</div>
            <div className="mt-2 text-[15px] font-semibold text-[#111111]">{title}</div>
            <div className="mt-2 text-[13px] leading-6 text-black/48">{desc}</div>
          </div>
        ))}
      </div>

      <div className="mt-6 border-t border-black/6 pt-6">
        <div className="flex gap-2 overflow-x-auto pb-2">
          {['老板摘要模板', '执行交接模板', '周度复盘模板'].map((title, index) => (
            <button
              key={title}
              className={`rounded-full px-4 py-2 text-[13px] font-medium ${index === 0 ? 'bg-[#111111] text-white' : 'border border-black/8 bg-[#fbfbf8] text-black/65'}`}
            >
              {title}
            </button>
          ))}
        </div>
        <div className="mt-5 grid gap-4 xl:grid-cols-3">
          {[
            ['老板摘要模板', opsTemplates.boss_summary],
            ['执行交接模板', opsTemplates.handoff_note],
            ['周度复盘模板', opsTemplates.weekly_review],
          ].map(([title, content]) => (
            <div key={title} className="rounded-[28px] border border-black/6 bg-[#fbfbf8] p-5">
              <div className="text-[11px] uppercase tracking-[0.18em] text-black/35">{title}</div>
              <div className="mt-4 whitespace-pre-wrap text-[14px] leading-7 text-black/72">{content}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export function AnalysisTable() {
  return (
    <section className="rounded-[32px] border border-black/6 bg-white p-7 shadow-[0_26px_60px_rgba(15,23,42,0.06)]">
      <div className="text-[11px] uppercase tracking-[0.22em] text-black/35">Analysis Table</div>
      <h3 className="mt-3 text-[2rem] font-semibold tracking-[-0.05em] text-[#111111]">搜索词分析总览</h3>
      <div className="mt-6 overflow-hidden rounded-[28px] border border-black/6 bg-[#fbfbf8]">
        <table className="w-full border-collapse text-left text-[14px] text-black/72">
          <thead className="bg-white text-[11px] uppercase tracking-[0.18em] text-black/35">
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
              <tr key={row.term} className="border-t border-black/6 bg-[#fbfbf8]">
                <td className="px-4 py-4 font-medium text-[#111111]">{row.term}</td>
                <td className="px-4 py-4 text-black/48">{row.type}</td>
                <td className="px-4 py-4 text-black/48">{row.rule}</td>
                <td className="px-4 py-4"><span className="rounded-full border border-black/8 bg-white px-3 py-1 text-[12px] text-black/70">{row.action}</span></td>
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
        <article key={batch.code} className="rounded-[32px] border border-black/6 bg-white p-7 shadow-[0_26px_60px_rgba(15,23,42,0.06)]">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full border border-black/8 bg-[#fbfbf8] px-3 py-1 text-[12px] text-black/65">{batch.code}</span>
            <span className="rounded-full border border-black/8 bg-[#fbfbf8] px-3 py-1 text-[12px] text-black/65">{batch.type}</span>
            <span className="rounded-full bg-[#111111] px-3 py-1 text-[12px] text-white">{batch.status}</span>
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-[0.92fr_1.08fr]">
            <div className="space-y-4">
              <div className="rounded-[24px] border border-black/6 bg-[#fbfbf8] p-5">
                <div className="text-[11px] uppercase tracking-[0.18em] text-black/35">批次摘要</div>
                <div className="mt-3 text-[1.15rem] font-semibold text-[#111111]">{batch.verdict}</div>
                <p className="mt-3 text-[14px] leading-7 text-black/50">{batch.summary}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-[20px] border border-black/6 bg-[#fbfbf8] p-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-black/35">覆盖项数</div>
                  <div className="mt-2 text-[1rem] font-semibold text-[#111111]">{batch.itemCount}</div>
                </div>
                <div className="rounded-[20px] border border-black/6 bg-[#fbfbf8] p-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-black/35">总花费 / 总销售</div>
                  <div className="mt-2 text-[1rem] font-semibold text-[#111111]">{batch.spend} / {batch.sales}</div>
                </div>
              </div>
            </div>
            <div className="space-y-4">
              <div className="rounded-[24px] border border-black/6 bg-[#fbfbf8] p-5">
                <div className="text-[11px] uppercase tracking-[0.18em] text-black/35">改善最多的词</div>
                <ul className="mt-3 space-y-2 text-[14px] text-black/72">
                  {batch.improving.map((term) => (
                    <li key={term}>• {term}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-[24px] border border-black/6 bg-[#fbfbf8] p-5">
                <div className="text-[11px] uppercase tracking-[0.18em] text-black/35">仍需重点关注</div>
                <ul className="mt-3 space-y-2 text-[14px] text-black/72">
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
