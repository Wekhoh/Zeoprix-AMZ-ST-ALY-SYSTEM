"""
规则引擎核心模块
根据配置的规则分析搜索词数据
"""

import time
from dataclasses import dataclass, field

import pandas as pd

from src.config.logger import get_logger
from src.data.db import Database
from src.data.models import RelevanceLevel, ActionType

logger = get_logger(__name__)


# 置信度常量
class Confidence:
    """规则分析置信度常量"""

    FULL = 1.0  # 完全确定（规则直接匹配）
    AI_JUDGMENT = 0.7  # 需要AI判断
    DEFAULT = 0.5  # 默认值（无规则匹配）


@dataclass
class AnalysisResult:
    """分析结果"""

    term: str
    term_type: str
    triggered_rule: str
    suggested_action: str
    action_type: str
    confidence: float = 1.0
    need_ai_judgment: bool = False
    has_conflict: bool = False
    ai_reasoning: str = None
    # v2.0: 相关性人工审核
    relevance: str = None  # 相关性等级
    needs_review: bool = False  # 是否需要人工审核相关性
    data: dict = field(default_factory=dict)


@dataclass
class CampaignAnalysisResult:
    """按活动分析的结果（保留活动维度）"""

    term: str
    term_type: str
    campaign_id: int
    campaign_name: str
    triggered_rule: str
    suggested_action: str  # 主动作（如：手动精准）
    auto_action: str  # 在自动活动中的处理（keep/negate/observe）
    action_type: str
    confidence: float = 1.0
    need_ai_judgment: bool = False
    ai_reasoning: str = None
    # v2.0: 相关性人工审核
    relevance: str = None  # 相关性等级
    needs_review: bool = False  # 是否需要人工审核相关性

    # 该词在此活动的表现指标
    impressions: int = 0
    clicks: int = 0
    spend: float = 0.0
    orders: int = 0
    sales: float = 0.0
    acos: float = 0.0
    cvr: float = 0.0

    data: dict = field(default_factory=dict)


class RuleEngine:
    """规则引擎"""

    def __init__(self, db: Database, product_id: int = None):
        """
        初始化规则引擎

        Args:
            db: 数据库实例
            product_id: 产品ID（用于加载产品特定规则）
        """
        self.db = db
        self.product_id = product_id
        self.rules = self._load_rules()
        self.product_config = self._load_product_config()

    def _load_rules(self) -> list[dict]:
        """加载规则配置（按优先级排序）"""
        rules = self.db.get_rules(self.product_id)
        logger.debug(f"加载 {len(rules)} 条规则")
        return rules

    def _load_product_config(self) -> dict:
        """加载产品配置"""
        if self.product_id:
            product = self.db.get_product(self.product_id)
            if product:
                return product.get("config", {})
        return {}

    def analyze(self, df: pd.DataFrame) -> list[AnalysisResult]:
        """
        分析数据，返回分析结果列表

        Args:
            df: 聚合后的搜索词DataFrame

        Returns:
            分析结果列表
        """
        if df.empty:
            return []

        results = []

        for _, row in df.iterrows():
            result = self._analyze_row(row)
            if result:
                results.append(result)

        logger.info(f"分析完成，生成 {len(results)} 条结果")
        return results

    def _analyze_row(self, row: pd.Series) -> AnalysisResult | None:
        """
        分析单条数据

        使用 first-match-wins 策略：按优先级遍历规则，
        第一个匹配的规则生成结果，后续规则不再检查。
        """
        term = row.get("term", "")
        term_type = row.get("term_type", "keyword")

        # 按优先级遍历规则（优先级数值越小越先检查）
        for rule in self.rules:
            if self._match_rule(row, rule):
                logger.debug(
                    f"搜索词 '{term}' 匹配规则 '{rule.get('name')}' "
                    f"(优先级: {rule.get('priority')})"
                )
                return self._create_result(row, rule)

        # 没有匹配任何规则，标记为观察
        logger.debug(f"搜索词 '{term}' 无匹配规则，标记为观察")

        # v2.0: 获取相关性信息
        campaign_id = row.get("campaign_id")
        relevance = self._get_term_relevance(term, campaign_id=campaign_id)
        needs_review = relevance is None or relevance == RelevanceLevel.PENDING

        return AnalysisResult(
            term=term,
            term_type=term_type,
            triggered_rule="无匹配规则",
            suggested_action="观察",
            action_type="observe",
            confidence=Confidence.DEFAULT,
            relevance=relevance,
            needs_review=needs_review,
            data=row.to_dict(),
        )

    def _get_term_relevance(self, term: str, campaign_id: int = None) -> str:
        """
        判断搜索词的相关性等级

        检查顺序（优先级从高到低）：
        -1. 人工审核标记（最高优先级）
        0. 核心词精确匹配 - 用户明确标为强相关的词优先保留
        1. 泛词精确匹配 - 太泛的词（pillow, neck等）
        2. 弱相关精准词 - 明确需要精准否定的边界词（neck support 等）
        3. 不相关词检查 - 明显不相关词
        4. 弱相关类目词 - 完全不同类目（massager, blanket等）
        5. 汽车相关词 - car相关词
        6. 核心词子串匹配 - 包含核心词的长尾词

        例如: "travel neck pillow for car" 如果在core_keywords中有精确匹配
              则优先保留为STRONG，否则因为包含car归类为CAR

        Args:
            term: 搜索词
            campaign_id: 活动ID（用于查询Local标记）

        Returns:
            相关性等级
        """
        term_lower = term.lower().strip()

        # ==================== -1. 人工审核标记（最高优先级） ====================
        # v2.0: 人工标记的相关性优先于自动检测
        if self.product_id:
            manual_review = self.db.get_manual_review_relevance(
                product_id=self.product_id,
                term=term_lower,
                campaign_id=campaign_id,
            )
            if manual_review and manual_review.get("relevance"):
                manual_relevance = manual_review["relevance"]
                # 如果是pending，继续自动检测
                if manual_relevance != RelevanceLevel.PENDING:
                    return manual_relevance

        # 获取配置
        keyword_libraries = self.product_config.get("keyword_libraries", {})
        core_keywords = self.product_config.get("core_keywords", [])
        related_keywords = self.product_config.get("related_keywords", [])

        # ==================== 0. 核心词精确匹配（最高优先级） ====================
        # 用户明确标为强相关的词，即使包含其他特征词也优先保留
        if any(term_lower == k.lower() for k in core_keywords):
            return RelevanceLevel.STRONG

        if any(term_lower == k.lower() for k in related_keywords):
            return RelevanceLevel.STRONG

        # ==================== 1. 泛词精确匹配 ====================
        # 太泛的单词需要否定精准（如 pillow, pillows, neck, home）
        generic_keywords = keyword_libraries.get("generic_keywords", [])
        if any(term_lower == k.lower() for k in generic_keywords):
            return RelevanceLevel.GENERIC

        # ==================== 2. 弱相关精准词检查 ====================
        # 明确需要精准否定的边界词（neck support, pillow for neck 等）
        weak_exact_keywords = keyword_libraries.get("weak_exact_keywords", [])
        if any(term_lower == k.lower() for k in weak_exact_keywords):
            return "weak_exact"

        # ==================== 3. 不相关词检查 ====================
        # 明显不相关词（否定词组）
        irrelevant_keywords = keyword_libraries.get("irrelevant_keywords", [])
        if any(k.lower() in term_lower for k in irrelevant_keywords):
            return RelevanceLevel.IRRELEVANT

        # ==================== 4. 弱相关类目词检查 ====================
        # 弱相关词（massager, blanket, neck support等）→ 词组否定
        weak_category_keywords = keyword_libraries.get("weak_category_keywords", [])
        if any(k.lower() in term_lower for k in weak_category_keywords):
            return RelevanceLevel.WEAK

        # ==================== 5. 汽车相关词检查 ====================
        # car相关词 → 否定精准
        car_keywords = keyword_libraries.get("car_keywords", [])
        if any(k.lower() in term_lower for k in car_keywords):
            return RelevanceLevel.CAR

        # ==================== 6. 核心词子串匹配 ====================
        # 包含核心词的长尾词 → 强相关
        if any(
            k.lower() in term_lower or term_lower in k.lower() for k in core_keywords
        ):
            return RelevanceLevel.STRONG

        if any(
            k.lower() in term_lower or term_lower in k.lower() for k in related_keywords
        ):
            return RelevanceLevel.STRONG

        # 默认返回None（无法判断，可能需要AI辅助）
        return None

    def _match_rule(self, row: pd.Series, rule: dict) -> bool:
        """
        检查单条数据是否匹配规则

        Args:
            row: 数据行
            rule: 规则配置

        Returns:
            是否匹配
        """
        conditions = rule.get("conditions", {})
        term_type = row.get("term_type", "keyword")
        rule_type = rule.get("rule_type", "keyword")

        # 安全检查：空条件规则不应匹配任何数据
        if not conditions:
            logger.warning(f"规则 '{rule.get('name')}' 没有定义任何条件，跳过匹配")
            return False

        # 类型不匹配跳过
        if rule_type != term_type and rule_type != "all":
            return False

        # 检查各种条件
        spend = row.get("total_spend", row.get("spend", 0))
        orders = row.get("total_orders", row.get("orders", 0))
        acos = row.get("acos", 0)
        clicks = row.get("total_clicks", row.get("clicks", 0))

        # 新增指标支持
        impressions = row.get("total_impressions", row.get("impressions", 0))
        ctr = row.get("ctr", 0)
        cpc = row.get("cpc", 0)
        sales = row.get("total_sales", row.get("sales", 0))
        roas = row.get("roas", 0)

        # 计算CVR（转化率 = 订单/点击）
        cvr = row.get("conversion_rate", 0)
        if cvr == 0 and clicks > 0:
            cvr = orders / clicks

        # 计算CTR（如果未提供）
        if ctr == 0 and impressions > 0:
            ctr = clicks / impressions

        # 计算CPC（如果未提供）
        if cpc == 0 and clicks > 0:
            cpc = spend / clicks

        # 计算ROAS（如果未提供）
        if roas == 0 and spend > 0:
            roas = sales / spend

        term = row.get("term", "")
        campaign_id = row.get("campaign_id")  # 可能为None（汇总模式）

        # ==================== 花费条件 ====================
        if "spend_min" in conditions and spend < conditions["spend_min"]:
            return False
        if "spend_max" in conditions and spend > conditions["spend_max"]:
            return False

        # ==================== 订单条件 ====================
        if "orders_max" in conditions and orders > conditions["orders_max"]:
            return False
        if "orders_min" in conditions and orders < conditions["orders_min"]:
            return False

        # ==================== 点击条件 (新增) ====================
        if "clicks_min" in conditions and clicks < conditions["clicks_min"]:
            return False
        if "clicks_max" in conditions and clicks > conditions["clicks_max"]:
            return False

        # ==================== ACOS条件 ====================
        if "acos_min" in conditions and acos < conditions["acos_min"]:
            return False
        if "acos_max" in conditions and acos > conditions["acos_max"]:
            return False

        # ==================== CVR条件 ====================
        if "cvr_min" in conditions and cvr < conditions["cvr_min"]:
            return False
        if "cvr_max" in conditions and cvr > conditions["cvr_max"]:
            return False

        # ==================== 曝光条件 (新增) ====================
        if (
            "impressions_min" in conditions
            and impressions < conditions["impressions_min"]
        ):
            return False
        if (
            "impressions_max" in conditions
            and impressions > conditions["impressions_max"]
        ):
            return False

        # ==================== CTR条件 (新增) ====================
        if "ctr_min" in conditions and ctr < conditions["ctr_min"]:
            return False
        if "ctr_max" in conditions and ctr > conditions["ctr_max"]:
            return False

        # ==================== CPC条件 (新增) ====================
        if "cpc_min" in conditions and cpc < conditions["cpc_min"]:
            return False
        if "cpc_max" in conditions and cpc > conditions["cpc_max"]:
            return False

        # ==================== 销售额条件 (新增) ====================
        if "sales_min" in conditions and sales < conditions["sales_min"]:
            return False
        if "sales_max" in conditions and sales > conditions["sales_max"]:
            return False

        # ==================== ROAS条件 (新增) ====================
        if "roas_min" in conditions and roas < conditions["roas_min"]:
            return False
        if "roas_max" in conditions and roas > conditions["roas_max"]:
            return False

        # ==================== 相关性条件 ====================
        if "relevance" in conditions:
            required_relevance = conditions["relevance"]
            actual_relevance = self._get_term_relevance(term, campaign_id=campaign_id)
            # v2.0: 使用to_category将细分相关性（如strong_core）映射到大类（strong）进行匹配
            actual_category = (
                RelevanceLevel.to_category(actual_relevance)
                if actual_relevance
                else None
            )
            if actual_category != required_relevance:
                return False

        # ==================== 评估类规则保护 (v2.2) ====================
        # 强相关词应优先走 strong 专属规则，不被泛化“评估”规则抢走。
        if "评估" in rule.get("action", ""):
            actual_relevance = self._get_term_relevance(term, campaign_id=campaign_id)
            actual_category = (
                RelevanceLevel.to_category(actual_relevance)
                if actual_relevance
                else None
            )
            if actual_category == RelevanceLevel.STRONG:
                return False

        # ==================== 相关性排除条件 (v2.1新增) ====================
        # 用于规则如"低转化高花费"排除强相关词
        if "relevance_not" in conditions:
            excluded_relevance = conditions["relevance_not"]
            actual_relevance = self._get_term_relevance(term, campaign_id=campaign_id)
            actual_category = (
                RelevanceLevel.to_category(actual_relevance)
                if actual_relevance
                else None
            )
            if actual_category == excluded_relevance:
                return False  # 相关性与排除条件匹配，不适用此规则

        # ==================== 自家变体ASIN条件 (新增) ====================
        if conditions.get("is_own_variant"):
            own_variants = self.product_config.get("own_variants", [])
            # ASIN比较不区分大小写
            if term.upper() not in [v.upper() for v in own_variants]:
                return False

        # ==================== 需要AI判断的规则 ====================
        if conditions.get("need_ai_judgment"):
            # 检查是否在核心关键词列表中
            core_keywords = self.product_config.get("core_keywords", [])
            if term.lower() in [k.lower() for k in core_keywords]:
                return False  # 核心关键词不需要AI判断

        # ==================== 竞品ASIN条件 ====================
        if conditions.get("is_competitor"):
            own_asins = self.product_config.get("own_asins", [])
            own_variants = self.product_config.get("own_variants", [])
            # 自己的ASIN或变体不是竞品（不区分大小写）
            term_upper = term.upper()
            own_asins_upper = [a.upper() for a in own_asins]
            own_variants_upper = [v.upper() for v in own_variants]
            if term_upper in own_asins_upper or term_upper in own_variants_upper:
                return False

        return True

    def _create_result(self, row: pd.Series, rule: dict) -> AnalysisResult:
        """根据规则创建分析结果"""
        conditions = rule.get("conditions", {})
        need_ai = conditions.get("need_ai_judgment", False)

        # v2.0: 获取相关性信息
        term = row.get("term", "")
        campaign_id = row.get("campaign_id")
        relevance = self._get_term_relevance(term, campaign_id=campaign_id)
        needs_review = relevance is None or relevance == RelevanceLevel.PENDING

        # 如果需要审核，降低置信度
        if needs_review:
            confidence = Confidence.DEFAULT
        elif need_ai:
            confidence = Confidence.AI_JUDGMENT
        else:
            confidence = Confidence.FULL

        return AnalysisResult(
            term=term,
            term_type=row.get("term_type", "keyword"),
            triggered_rule=rule.get("name", ""),
            suggested_action=rule.get("action", ""),
            action_type=self._get_action_type(rule.get("action", "")),
            confidence=confidence,
            need_ai_judgment=need_ai,
            has_conflict=row.get("has_conflict", False)
            if "has_conflict" in row
            else False,
            relevance=relevance,
            needs_review=needs_review,
            data=row.to_dict(),
        )

    def _get_action_type(self, action: str) -> str:
        """
        根据建议动作确定动作类型

        动作类型细分:
        - negative_exact: 否定精准
        - negative_phrase: 否定词组
        - manual_exact: 手动精准
        - manual_product: 手动商品定位
        - manual_exact_no_neg: 手动精准测试 + 自动先不否
        - manual_exact_with_neg: 手动精准 + 自动否定
        - manual_product_no_neg: 手动商品定位 + 自动先不否
        - manual_product_with_neg: 手动商品定位 + 自动否定
        - observe: 观察
        - continue_observe: 继续观察
        - evaluate: 评估
        """
        action_lower = action.lower()

        # ==================== 组合动作：手动 + 是否否定 ====================
        # 优先检查组合动作（更具体的匹配优先）

        # 手动精准 + 自动否定
        if (
            "手动精准" in action and "否定" in action and "不否" not in action
        ) or "manual_exact_with_neg" in action_lower:
            return ActionType.MANUAL_EXACT_WITH_NEG

        # 手动精准 + 自动先不否
        if (
            "手动精准" in action and "不否" in action
        ) or "manual_exact_no_neg" in action_lower:
            return ActionType.MANUAL_EXACT_NO_NEG

        # 手动商品定位 + 自动否定
        if (
            ("手动商品" in action or "商品定位" in action)
            and "否定" in action
            and "不否" not in action
        ) or "manual_product_with_neg" in action_lower:
            return ActionType.MANUAL_PRODUCT_WITH_NEG

        # 手动商品定位 + 自动先不否
        if (
            ("手动商品" in action or "商品定位" in action) and "不否" in action
        ) or "manual_product_no_neg" in action_lower:
            return ActionType.MANUAL_PRODUCT_NO_NEG

        # ==================== 单一否定动作 ====================
        if "否定精准" in action or "negative_exact" in action_lower:
            return ActionType.NEGATIVE_EXACT
        elif (
            "否定词组" in action
            or "短语否定" in action
            or "negative_phrase" in action_lower
        ):
            return ActionType.NEGATIVE_PHRASE
        elif "否定" in action or "negative" in action_lower:
            # 默认否定为精准否定
            return ActionType.NEGATIVE_EXACT

        # ==================== 单一手动动作 ====================
        elif (
            "手动商品" in action
            or "商品定位" in action
            or "manual_product" in action_lower
        ):
            return ActionType.MANUAL_PRODUCT
        elif "手动精准" in action or "manual_exact" in action_lower:
            return ActionType.MANUAL_EXACT
        elif "手动" in action or "manual" in action_lower:
            # 默认手动为精准匹配
            return ActionType.MANUAL_EXACT

        # ==================== 观察类型 ====================
        elif "继续观察" in action or "continue_observe" in action_lower:
            return ActionType.CONTINUE_OBSERVE
        elif (
            "监控" in action
            or "观察" in action
            or "observe" in action_lower
            or "watch" in action_lower
        ):
            return ActionType.OBSERVE

        # ==================== 评估类型 ====================
        elif "评估" in action or "evaluate" in action_lower:
            return ActionType.EVALUATE

        else:
            return "other"

    def get_negative_keywords(
        self, results: list[AnalysisResult]
    ) -> list[AnalysisResult]:
        """获取需要否定的关键词（包括精准否定和词组否定）"""
        negative_types = [
            ActionType.NEGATIVE_EXACT,
            ActionType.NEGATIVE_PHRASE,
            "negative",
        ]
        return [r for r in results if r.action_type in negative_types]

    def get_negative_exact_keywords(
        self, results: list[AnalysisResult]
    ) -> list[AnalysisResult]:
        """获取需要精准否定的关键词"""
        return [r for r in results if r.action_type == ActionType.NEGATIVE_EXACT]

    def get_negative_phrase_keywords(
        self, results: list[AnalysisResult]
    ) -> list[AnalysisResult]:
        """获取需要词组否定的关键词"""
        return [r for r in results if r.action_type == ActionType.NEGATIVE_PHRASE]

    def get_manual_keywords(
        self, results: list[AnalysisResult]
    ) -> list[AnalysisResult]:
        """获取推荐手动投放的关键词（包括精准和商品定位）"""
        manual_types = [ActionType.MANUAL_EXACT, ActionType.MANUAL_PRODUCT, "manual"]
        return [r for r in results if r.action_type in manual_types]

    def get_manual_exact_keywords(
        self, results: list[AnalysisResult]
    ) -> list[AnalysisResult]:
        """获取推荐手动精准匹配的关键词"""
        return [r for r in results if r.action_type == ActionType.MANUAL_EXACT]

    def get_manual_product_keywords(
        self, results: list[AnalysisResult]
    ) -> list[AnalysisResult]:
        """获取推荐手动商品定位的ASIN"""
        return [r for r in results if r.action_type == ActionType.MANUAL_PRODUCT]

    def get_ai_pending(self, results: list[AnalysisResult]) -> list[AnalysisResult]:
        """获取需要AI判断的结果"""
        return [r for r in results if r.need_ai_judgment or r.has_conflict]

    # ==================== 按活动分析方法 ====================

    def analyze_by_campaign(self, df: pd.DataFrame) -> list[CampaignAnalysisResult]:
        """
        按活动分别分析数据，同一关键词在不同活动可有不同建议

        Args:
            df: 按活动+关键词聚合的DataFrame（来自aggregate_by_campaign_term）

        Returns:
            按活动分析结果列表
        """
        if df.empty:
            return []

        results = []

        for _, row in df.iterrows():
            result = self._analyze_campaign_row(row)
            if result:
                results.append(result)

        logger.info(f"按活动分析完成，生成 {len(results)} 条结果")
        return results

    def _analyze_campaign_row(self, row: pd.Series) -> CampaignAnalysisResult | None:
        """
        分析单条按活动数据

        与 _analyze_row 类似，但返回包含活动信息的 CampaignAnalysisResult，
        并且会根据该词在当前活动的表现决定 auto_action。
        """
        term = row.get("term", "")
        term_type = row.get("term_type", "keyword")
        campaign_id = row.get("campaign_id", 0)
        campaign_name = row.get("campaign_name", "")

        # 获取指标
        clicks = row.get("total_clicks", row.get("clicks", 0))
        orders = row.get("total_orders", row.get("orders", 0))
        spend = row.get("total_spend", row.get("spend", 0))
        sales = row.get("total_sales", row.get("sales", 0))
        impressions = row.get("total_impressions", row.get("impressions", 0))
        acos = row.get("acos", 0)
        cvr = row.get("conversion_rate", 0)
        if cvr == 0 and clicks > 0:
            cvr = orders / clicks

        # 按优先级遍历规则
        triggered_rule = "无匹配规则"
        suggested_action = "观察"
        action_type = ActionType.OBSERVE
        confidence = Confidence.DEFAULT
        need_ai = False

        for rule in self.rules:
            if self._match_rule(row, rule):
                triggered_rule = rule.get("name", "")
                suggested_action = rule.get("action", "")
                action_type = self._get_action_type(suggested_action)
                conditions = rule.get("conditions", {})
                need_ai = conditions.get("need_ai_judgment", False)
                confidence = Confidence.AI_JUDGMENT if need_ai else Confidence.FULL
                break

        # 决定自动活动中的处理方式
        auto_action = self._determine_auto_action(
            action_type=action_type, clicks=clicks, orders=orders, cvr=cvr, spend=spend
        )

        # v2.0: 获取相关性信息
        relevance = self._get_term_relevance(term, campaign_id=campaign_id)
        needs_review = relevance is None or relevance == RelevanceLevel.PENDING

        # 如果需要审核，降低置信度
        if needs_review and confidence == Confidence.FULL:
            confidence = Confidence.DEFAULT

        return CampaignAnalysisResult(
            term=term,
            term_type=term_type,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            triggered_rule=triggered_rule,
            suggested_action=suggested_action,
            auto_action=auto_action,
            action_type=action_type,
            confidence=confidence,
            need_ai_judgment=need_ai,
            relevance=relevance,
            needs_review=needs_review,
            impressions=impressions,
            clicks=clicks,
            spend=spend,
            orders=orders,
            sales=sales,
            acos=acos,
            cvr=cvr,
            data=row.to_dict(),
        )

    def _determine_auto_action(
        self, action_type: str, clicks: int, orders: int, cvr: float, spend: float
    ) -> str:
        """
        决定在自动广告活动中的处理方式

        基于用户逻辑：
        - 表现好（CVR >= 10%）：保留（keep）- 万一手动跑不好，自动还能续上
        - 表现差（clicks >= 20 且 orders = 0）：否定（negate）- 避免和手动抢预算
        - 样本不足或中等表现：观察（observe）- 继续积累数据

        注意：如果规则已明确指定否定策略（_WITH_NEG / _NO_NEG），
        则尊重规则意图，不再根据表现覆盖。

        Args:
            action_type: 主动作类型
            clicks: 点击数
            orders: 订单数
            cvr: 转化率
            spend: 花费

        Returns:
            自动活动处理方式: "keep" / "negate" / "observe" / None
        """
        # ==================== 规则已明确指定策略的，直接遵循 ====================
        # 规则指定"手动+自动否定"
        if action_type in [
            ActionType.MANUAL_EXACT_WITH_NEG,
            ActionType.MANUAL_PRODUCT_WITH_NEG,
        ]:
            return "negate"

        # 规则指定"手动+自动先不否"
        if action_type in [
            ActionType.MANUAL_EXACT_NO_NEG,
            ActionType.MANUAL_PRODUCT_NO_NEG,
        ]:
            return "keep"

        # ==================== 纯手动动作，根据表现计算 ====================
        if action_type not in [ActionType.MANUAL_EXACT, ActionType.MANUAL_PRODUCT]:
            return None

        # 获取阈值配置
        thresholds = self.product_config.get("thresholds", {})
        min_clicks_for_analysis = thresholds.get("min_clicks_for_analysis", 20)
        good_cvr = thresholds.get("good_cvr", 0.10)

        # 表现好：保留
        if cvr >= good_cvr and orders >= 1:
            return "keep"

        # 表现差：否定（样本充足+零转化）
        if clicks >= min_clicks_for_analysis and orders == 0:
            return "negate"

        # 其他情况：观察
        return "observe"

    def get_campaign_results_by_term(
        self, results: list[CampaignAnalysisResult], term: str
    ) -> list[CampaignAnalysisResult]:
        """获取特定关键词在各活动的分析结果"""
        return [r for r in results if r.term == term]

    def get_terms_with_multiple_campaigns(
        self, results: list[CampaignAnalysisResult]
    ) -> dict[str, list[CampaignAnalysisResult]]:
        """获取出现在多个活动中的关键词及其各活动结果"""
        from collections import defaultdict

        term_results = defaultdict(list)
        for r in results:
            term_results[r.term].append(r)
        return {term: res for term, res in term_results.items() if len(res) > 1}


def analyze_search_terms(db: Database, product_id: int = None) -> list[AnalysisResult]:
    """便捷函数：分析搜索词（汇总模式，跨活动聚合）"""
    from src.analysis.truth_replay import apply_reviewed_truth
    from src.data.aggregator import DataAggregator

    # 获取聚合数据
    aggregator = DataAggregator(db)
    df = aggregator.aggregate_by_term(product_id)

    # 规则分析
    engine = RuleEngine(db, product_id)
    return apply_reviewed_truth(db, product_id, engine.analyze(df))


def analyze_search_terms_by_campaign(
    db: Database, product_id: int = None
) -> list[CampaignAnalysisResult]:
    """
    便捷函数：按活动分析搜索词

    同一关键词在不同活动中会有不同的分析结果。

    Args:
        db: 数据库实例
        product_id: 产品ID（可选）

    Returns:
        按活动分析结果列表
    """
    from src.analysis.truth_replay import apply_reviewed_truth
    from src.data.aggregator import DataAggregator

    # 获取按活动+关键词聚合的数据
    aggregator = DataAggregator(db)
    df = aggregator.aggregate_by_campaign_term(product_id)

    # 规则分析
    engine = RuleEngine(db, product_id)
    return apply_reviewed_truth(db, product_id, engine.analyze_by_campaign(df))


@dataclass
class ASINAnalysisResult:
    """按ASIN分析的结果（ASIN级别聚合）"""

    term: str
    term_type: str
    asin_identifier: str  # 如 BLK, DBL
    triggered_rule: str
    suggested_action: str
    auto_action: str
    action_type: str
    confidence: float = 1.0
    need_ai_judgment: bool = False
    ai_reasoning: str = None

    # 该词在此ASIN的表现指标
    impressions: int = 0
    clicks: int = 0
    spend: float = 0.0
    orders: int = 0
    sales: float = 0.0
    acos: float = 0.0
    cvr: float = 0.0

    data: dict = field(default_factory=dict)


def analyze_search_terms_by_asin(
    db: Database, product_id: int = None
) -> list[ASINAnalysisResult]:
    """
    便捷函数：按ASIN分析搜索词

    同一关键词在不同ASIN（如BLK、DBL）中会有不同的分析结果。
    ASIN标识从活动名称提取（第一个"-"前的部分）。

    Args:
        db: 数据库实例
        product_id: 产品ID（可选）

    Returns:
        按ASIN分析结果列表
    """
    from src.analysis.truth_replay import apply_reviewed_truth
    from src.data.aggregator import DataAggregator

    # 获取按ASIN+关键词聚合的数据
    aggregator = DataAggregator(db)
    df = aggregator.aggregate_by_asin_term(product_id)

    if df.empty:
        return []

    # 规则分析
    engine = RuleEngine(db, product_id)
    results = []

    for _, row in df.iterrows():
        term = row.get("term", "")
        term_type = row.get("term_type", "keyword")
        asin_identifier = row.get("asin_identifier", "UNKNOWN")

        # 获取指标
        clicks = row.get("total_clicks", 0)
        orders = row.get("total_orders", 0)
        spend = row.get("total_spend", 0)
        sales = row.get("total_sales", 0)
        impressions = row.get("total_impressions", 0)
        acos = row.get("acos", 0)
        cvr = row.get("conversion_rate", 0)

        # 按优先级遍历规则
        triggered_rule = "无匹配规则"
        suggested_action = "观察"
        action_type = ActionType.OBSERVE
        confidence = Confidence.DEFAULT
        need_ai = False

        for rule in engine.rules:
            if engine._match_rule(row, rule):
                triggered_rule = rule.get("name", "")
                suggested_action = rule.get("action", "")
                action_type = engine._get_action_type(suggested_action)
                conditions = rule.get("conditions", {})
                need_ai = conditions.get("need_ai_judgment", False)
                confidence = Confidence.AI_JUDGMENT if need_ai else Confidence.FULL
                break

        # 决定自动活动中的处理方式
        auto_action = engine._determine_auto_action(
            action_type=action_type, clicks=clicks, orders=orders, cvr=cvr, spend=spend
        )

        results.append(
            ASINAnalysisResult(
                term=term,
                term_type=term_type,
                asin_identifier=asin_identifier,
                triggered_rule=triggered_rule,
                suggested_action=suggested_action,
                auto_action=auto_action or "",
                action_type=action_type,
                confidence=confidence,
                need_ai_judgment=need_ai,
                impressions=impressions,
                clicks=clicks,
                spend=spend,
                orders=orders,
                sales=sales,
                acos=acos,
                cvr=cvr,
                data=row.to_dict(),
            )
        )

    logger.info(f"按ASIN分析完成，生成 {len(results)} 条结果")
    return apply_reviewed_truth(db, product_id, results)


# ========== TTL 缓存（Sprint 1.3 启动性能优化）==========
# 缓存 key 使用 SQLite PRAGMA data_version：每次 DB 写入自动 +1，读取不变。
# 上传文件 / 规则修改 / 审核变动后自动失效，无需手动 invalidate。
_CACHE_TTL_SECONDS = 120.0
_MAX_CACHE_ENTRIES = 8
_analysis_cache: dict = {}


def _get_db_data_version(db: Database) -> int:
    """读取 SQLite data_version；失败返回 -1（退回无缓存调用）。"""
    try:
        row = db.conn.execute("PRAGMA data_version").fetchone()
        return int(row[0]) if row else -1
    except Exception as exc:
        logger.debug("PRAGMA data_version 失败，缓存键 fallback: %s", exc)
        return -1


def _cache_put(key: tuple, value: list) -> None:
    """写入缓存并做最小容量控制（保留最近 8 条，防内存膨胀）。"""
    _analysis_cache[key] = (value, time.time())
    if len(_analysis_cache) > _MAX_CACHE_ENTRIES:
        oldest_key = min(_analysis_cache.items(), key=lambda kv: kv[1][1])[0]
        _analysis_cache.pop(oldest_key, None)


def analyze_search_terms_cached(
    db: Database, product_id: int = None
) -> list[AnalysisResult]:
    """analyze_search_terms 的 TTL 缓存版本（供 /frontend/workbench 等热路径使用）。"""
    version = _get_db_data_version(db)
    if version < 0:
        return analyze_search_terms(db, product_id)
    key = ("flat", product_id, version)
    cached = _analysis_cache.get(key)
    if cached is not None and (time.time() - cached[1]) < _CACHE_TTL_SECONDS:
        return cached[0]
    results = analyze_search_terms(db, product_id)
    _cache_put(key, results)
    return results


def analyze_search_terms_by_asin_cached(
    db: Database, product_id: int = None
) -> list[ASINAnalysisResult]:
    """analyze_search_terms_by_asin 的 TTL 缓存版本。"""
    version = _get_db_data_version(db)
    if version < 0:
        return analyze_search_terms_by_asin(db, product_id)
    key = ("asin", product_id, version)
    cached = _analysis_cache.get(key)
    if cached is not None and (time.time() - cached[1]) < _CACHE_TTL_SECONDS:
        return cached[0]
    results = analyze_search_terms_by_asin(db, product_id)
    _cache_put(key, results)
    return results
