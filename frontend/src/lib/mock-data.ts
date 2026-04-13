export type NavItem = {
  href: string
  label: string
  eyebrow: string
}

export type ProductContext = {
  name: string
  role: string
  workspace: string
  lastAnalysisAt: string
  lastBackupAt: string
}

export type WorkbenchStat = { label: string; value: string; detail: string }
export type TopAction = { tag: string; title: string; description: string }
export type TrendCard = { label: string; value: string; detail: string }
export type TrendBar = { label: string; value: number }
export type StructureBucket = { label: string; count: number; ratio: string }
export type ExecutionEffect = {
  status: string
  summary: string
  chips: string[]
  improving: string[]
  risky: string[]
  batchCode: string | null
  batchStatus: string | null
}
export type OpsTemplates = {
  boss_summary: string
  handoff_note: string
  weekly_review: string
}
export type AICopilotCard = {
  title: string
  context: string
  summary: string
  prompts: string[]
}
export type AnalysisRow = {
  term: string
  type: string
  rule: string
  action: string
  spend: string
  orders: number
  confidence: string
}
export type ExecutionBatchItemPreview = {
  term: string
  action: string
  spend: string
}

export type ExecutionBatch = {
  id?: number
  code: string
  type: string
  status: string
  itemCount: number
  spend: string
  sales: string
  verdict: string
  summary: string
  improving: string[]
  risky: string[]
  itemsPreview?: ExecutionBatchItemPreview[]
}
export type WorkbenchPayload = {
  source?: string
  productId?: number | null
  productContext: ProductContext | null
  workbenchStats: WorkbenchStat[]
  topActions: TopAction[]
  trendCards: TrendCard[]
  trendBars: TrendBar[]
  structureBuckets: StructureBucket[]
  executionEffect: ExecutionEffect
  opsTemplates: OpsTemplates
  aiCopilotCards: AICopilotCard[]
  analysisRows: AnalysisRow[]
  executionBatches: ExecutionBatch[]
}

export type UploadSnapshotItem = {
  id: number
  createdAt: string
  itemCount: number
}

export type UploadCampaignItem = {
  id: number
  name: string
  createdAt: string
}

export type UploadPayload = WorkbenchPayload & {
  upload?: {
    latestReportDate: string
    searchTerms: number
    campaigns: number
    snapshotCount: number
    recentSnapshots: UploadSnapshotItem[]
    recentCampaigns: UploadCampaignItem[]
  }
}

export type AnalysisPayload = WorkbenchPayload & {
  analysis?: {
    rowCount: number
    typeCounts: Record<string, number>
    actionCounts: Record<string, number>
  }
}

export type ActionsPayload = WorkbenchPayload & {
  actions?: {
    negativeCount: number
    manualCount: number
    conflictCount: number
    latestBatchCode?: string | null
  }
}

export type ReviewPendingItem = {
  term: string
  termType: string
  campaignName: string
  campaignId?: number | null
  relevance: string
  createdAt: string
}

export type ReviewPayload = WorkbenchPayload & {
  review?: {
    stats: {
      total: number
      reviewed: number
      pending: number
    }
    pendingItems: ReviewPendingItem[]
  }
}

export type SettingsPayload = WorkbenchPayload & {
  settings?: {
    ruleVersionCount: number
    strategyProfileCount: number
    keywordLibraryCounts: {
      irrelevant: number
      weak: number
      generic: number
      car: number
      variants: number
    }
    backupSummary: {
      searchTerms: number
      analysisResults: number
      manualReviews: number
      snapshots: number
      executionBatches: number
    }
  }
}

export const navItems: NavItem[] = [
  { href: '/', label: '运营工作台', eyebrow: 'Home' },
  { href: '/upload', label: '数据导入', eyebrow: 'Import' },
  { href: '/analysis', label: '搜索词分析', eyebrow: 'Analysis' },
  { href: '/actions', label: '操作清单', eyebrow: 'Execution' },
  { href: '/review', label: '审核中心', eyebrow: 'Review' },
  { href: '/settings', label: '数据管理', eyebrow: 'Data' },
]

export const productContext = {
  name: '桌面验收产品',
  role: 'Admin',
  workspace: '桌面验收产品工作区',
  lastAnalysisAt: '2026-04-11 12:34',
  lastBackupAt: '2026-04-11 09:10',
}

export const workbenchStats = [
  { label: '当前阶段', value: '待执行优化动作', detail: '先止损，再补量。' },
  { label: '最近一次分析', value: '2026-04-11 · 12:34', detail: 'latest snapshot 已形成。' },
  { label: '历史沉淀', value: '4 个分析快照', detail: '646 条人工审核、3 个执行批次。' },
  { label: '数据规模', value: '316 条词 · 6 个活动', detail: '当前已形成 98 条建议动作。' },
]

export const topActions = [
  {
    tag: '止损优先',
    title: '优先止损 37 个高花费词',
    description: '先处理 travel pillow、soft neck support 这类高花费低产出词。',
  },
  {
    tag: '补量机会',
    title: '补量 11 个高转化词',
    description: 'best neck pillow、airplane pillow case 适合先做手动精准。',
  },
  {
    tag: '风险处理',
    title: '拍板 18 个分歧词',
    description: '这批词跨 ASIN / 跨活动结论不稳定，执行前应先人工拍板。',
  },
]

export const trendCards = [
  { label: '最近 7 天', value: '$5,803.51', detail: '订单 88 ｜ 销售额 $2,386.02 ｜ ACOS 243.23%' },
  { label: '最近 14 天', value: '$6,904.27', detail: '订单 101 ｜ 销售额 $2,998.40 ｜ ACOS 230.27%' },
  { label: '最近 30 天', value: '$11,884.22', detail: '订单 156 ｜ 销售额 $5,622.14 ｜ ACOS 211.39%' },
]

export const trendBars = [
  { label: '04-02', value: 38 },
  { label: '04-04', value: 42 },
  { label: '04-06', value: 61 },
  { label: '04-08', value: 57 },
  { label: '04-10', value: 74 },
]

export const structureBuckets = [
  { label: '核心词', count: 138, ratio: '44%' },
  { label: '其它 ASIN', count: 110, ratio: '35%' },
  { label: '其它长尾', count: 49, ratio: '16%' },
  { label: '相关词', count: 11, ratio: '3%' },
  { label: '泛词', count: 7, ratio: '2%' },
  { label: '自家变体 ASIN', count: 1, ratio: '<1%' },
]

export const executionEffect = {
  status: '出现改善信号',
  summary: '最近一批执行后，止损压力下降，手动放量机会开始浮现。',
  chips: ['建议否定 -2', '手动投放 +1', '分歧词 -1'],
  improving: ['travel pillow', 'airplane pillow case'],
  risky: ['massager', 'soft neck support'],
  batchCode: 'NEG-20260411-120000-ABC123',
  batchStatus: 'reviewed',
}

export const opsTemplates = {
  boss_summary:
    '桌面验收产品当前处于「待执行优化动作」。最近执行效果判断为「出现改善信号」，建议今天优先处理高花费词止损、补量高转化词，并尽快拍板分歧词。',
  handoff_note:
    '【执行交接】先去操作清单执行否词批次 NEG-20260411-120000-ABC123，再处理 11 个手动补量词。执行后 3 天回看最近执行效果与 verdict。',
  weekly_review:
    '【周度复盘】本周首页趋势显示花费上升但结构开始收敛，最近执行效果为“出现改善信号”。改善最多的词为 travel pillow，仍需关注 massager。',
}

export const aiCopilotCards = [
  {
    title: 'AI 汇总简报',
    context: '当前产品：桌面验收产品 · 上下文：最近一次分析结果',
    summary: '泛词与高花费词仍然混杂，今天应先止损再补量。',
    prompts: ['解释 ACOS 为什么高', '给我 3 个最优先动作', '生成老板摘要'],
  },
  {
    title: 'AI 执行说明',
    context: '当前产品：桌面验收产品 · 上下文：执行批次 NEG-20260411-120000-ABC123',
    summary: '这批动作适合今天执行，执行后 3 天内观察手动机会是否继续增加。',
    prompts: ['整理执行备注', '给我更保守建议', '生成交接模板'],
  },
]

export const analysisRows = [
  {
    term: 'travel pillow',
    type: '核心词',
    rule: '高点击无转化',
    action: '否定精准',
    spend: '$24.00',
    orders: 0,
    confidence: '高',
  },
  {
    term: 'best neck pillow',
    type: '长尾机会',
    rule: '高转化补量',
    action: '手动精准',
    spend: '$8.00',
    orders: 2,
    confidence: '高',
  },
  {
    term: 'massager',
    type: '泛词风险',
    rule: '低相关 + 高花费',
    action: '否定词组',
    spend: '$17.50',
    orders: 0,
    confidence: '中',
  },
]

export const executionBatches = [
  {
    code: 'NEG-20260411-120000-ABC123',
    type: '否词批次',
    status: '已复盘',
    itemCount: 37,
    spend: '$241.50',
    sales: '$96.00',
    verdict: '出现改善信号',
    summary: '执行后，建议否定和分歧词数量下降，手动机会开始增加。',
    improving: ['travel pillow', 'airplane pillow case'],
    risky: ['massager', 'soft neck support'],
    itemsPreview: [
      { term: 'travel pillow', action: '否定精准', spend: '$24.00' },
      { term: 'soft neck support', action: '否定词组', spend: '$17.50' },
      { term: 'massager', action: '否定词组', spend: '$16.20' },
    ],
  },
  {
    code: 'MAN-20260410-184500-FD220A',
    type: '手动投放批次',
    status: '已执行',
    itemCount: 11,
    spend: '$88.00',
    sales: '$220.00',
    verdict: '继续观察',
    summary: '执行后还没有形成新的分析快照，建议 3 天后再回来复盘。',
    improving: [],
    risky: ['memory foam pillow'],
    itemsPreview: [
      { term: 'best neck pillow', action: '手动精准', spend: '$8.00' },
      { term: 'airplane pillow case', action: '手动精准', spend: '$6.50' },
    ],
  },
]

export const mockWorkbenchPayload: WorkbenchPayload = {
  source: "mock",
  productId: null,
  productContext,
  workbenchStats,
  topActions,
  trendCards,
  trendBars,
  structureBuckets,
  executionEffect,
  opsTemplates,
  aiCopilotCards,
  analysisRows,
  executionBatches,
}
