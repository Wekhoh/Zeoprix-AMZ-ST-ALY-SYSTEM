-- Migration: 002_add_relevance_fields
-- Date: 2026-01-15
-- Description: 添加相关性人工审核功能所需字段
-- Author: AMZ搜索词分析系统

-- Step 1: 添加相关性字段
ALTER TABLE manual_reviews ADD COLUMN relevance TEXT;
ALTER TABLE manual_reviews ADD COLUMN relevance_notes TEXT;

-- Step 2: 添加范围控制字段
ALTER TABLE manual_reviews ADD COLUMN scope TEXT DEFAULT 'local';

-- Step 3: 添加ASIN竞争力评估字段
ALTER TABLE manual_reviews ADD COLUMN competition_level TEXT;
ALTER TABLE manual_reviews ADD COLUMN competition_notes TEXT;

-- Step 4: 添加AI辅助字段
ALTER TABLE manual_reviews ADD COLUMN ai_suggestion TEXT;
ALTER TABLE manual_reviews ADD COLUMN ai_confidence REAL;

-- Step 5: 创建新索引
CREATE INDEX IF NOT EXISTS idx_manual_reviews_relevance ON manual_reviews(product_id, relevance);
CREATE INDEX IF NOT EXISTS idx_manual_reviews_scope ON manual_reviews(product_id, scope);
CREATE INDEX IF NOT EXISTS idx_manual_reviews_reviewed ON manual_reviews(product_id, reviewed);

-- Step 6: 将现有reviewed=1的记录标记为待确认相关性
-- 已审核但无相关性标记的记录设为pending
UPDATE manual_reviews
SET relevance = 'pending'
WHERE reviewed = 1 AND relevance IS NULL;

-- 相关性等级说明:
-- strong_core: 强相关核心词（产品核心关键词）
-- strong_longtail: 强相关长尾词（长尾但相关）
-- weak: 弱相关（关联度低）
-- generic: 太泛（泛词不精准）
-- irrelevant: 不相关（完全无关）
-- pending: 待定（未审核）

-- 范围说明:
-- local: 仅当前活动生效（默认）
-- global: 同步到该ASIN下所有活动

-- 竞争力等级说明（ASIN专用）:
-- can_compete: 可竞争（有竞争优势）
-- cannot_compete: 不可竞争（无竞争力）
-- need_observe: 待观察（样本不足）
