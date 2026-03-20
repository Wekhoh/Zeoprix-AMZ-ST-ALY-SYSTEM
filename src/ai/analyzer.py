"""
AI 分析器模块
使用 Gemini AI 进行关键词相关性判断和分歧解决
"""

import threading
import time
from dataclasses import dataclass

from src.ai.client import GeminiClient
from src.config.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """令牌桶限流器"""

    def __init__(self, rate: float = 10.0, capacity: int = 20):
        """
        初始化限流器

        Args:
            rate: 每秒生成的令牌数（默认10个/秒）
            capacity: 桶的最大容量（默认20个）
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1, timeout: float = 30.0) -> bool:
        """
        获取令牌

        Args:
            tokens: 需要的令牌数
            timeout: 最大等待时间（秒）

        Returns:
            是否成功获取
        """
        start_time = time.time()

        while True:
            with self._lock:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

            # 计算等待时间
            wait_time = (tokens - self.tokens) / self.rate
            if time.time() - start_time + wait_time > timeout:
                logger.warning(f"获取令牌超时（需要{tokens}个，当前{self.tokens}个）")
                return False

            # 等待一小段时间后重试
            time.sleep(min(wait_time, 0.1))

    def _refill(self):
        """补充令牌"""
        now = time.time()
        elapsed = now - self.last_update
        new_tokens = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_update = now


# 全局限流器实例（每秒10次请求，最大突发20次）
_global_rate_limiter = RateLimiter(rate=10.0, capacity=20)


@dataclass
class RelevanceResult:
    """相关性判断结果"""

    keyword: str
    relevance: str  # high, medium, low
    confidence: float
    reason: str
    suggested_action: str


@dataclass
class RelevanceSuggestion:
    """相关性建议结果（v2.0人工审核用）"""

    term: str
    suggested_relevance: str  # strong_core, strong_longtail, weak, generic, irrelevant
    confidence: float  # 0.0-1.0
    reasoning: str
    suggested_action: str  # 建议的后续动作


@dataclass
class ConflictResult:
    """分歧解决结果"""

    keyword: str
    suggestion: str
    reasoning: str
    confidence: float
    campaign_analysis: list[dict]


class AIAnalyzer:
    """AI 分析器"""

    def __init__(self, client: GeminiClient = None, rate_limiter: RateLimiter = None):
        """
        初始化 AI 分析器

        Args:
            client: GeminiClient 实例（可选，默认自动创建）
            rate_limiter: 限流器实例（可选，默认使用全局限流器）
        """
        self.client = client or GeminiClient()
        self.rate_limiter = rate_limiter or _global_rate_limiter

    def _wait_for_rate_limit(self, tokens: int = 1) -> bool:
        """等待速率限制"""
        if not self.rate_limiter.acquire(tokens):
            logger.error("API调用被限流，请稍后重试")
            return False
        return True

    def judge_relevance(
        self,
        keyword: str,
        product_context: dict,
        performance_data: dict = None,
    ) -> RelevanceResult:
        """
        判断关键词与产品的相关性

        Args:
            keyword: 搜索词
            product_context: 产品上下文信息
                - name: 产品名称
                - category: 产品类目
                - core_keywords: 核心关键词列表
                - description: 产品描述（可选）
            performance_data: 表现数据（可选）
                - impressions, clicks, spend, orders, acos

        Returns:
            RelevanceResult
        """
        system_instruction = """你是一个亚马逊广告专家，专门分析搜索词与产品的相关性。
你需要根据产品信息判断搜索词是否与产品相关。

请返回JSON格式：
{
    "relevance": "high" | "medium" | "low",
    "confidence": 0.0-1.0,
    "reason": "简短解释",
    "suggested_action": "建议动作"
}

相关性判断标准：
- high: 搜索词直接描述产品核心功能或属性
- medium: 搜索词与产品有关联但不是核心需求
- low: 搜索词与产品几乎无关或是竞品/其他品类

建议动作：
- high: "保留投放"
- medium: "观察表现"
- low: "建议否定"
"""

        prompt = f"""请分析以下搜索词与产品的相关性：

搜索词: {keyword}

产品信息:
- 名称: {product_context.get("name", "未知")}
- 类目: {product_context.get("category", "未知")}
- 核心关键词: {", ".join(product_context.get("core_keywords", []))}
- 描述: {product_context.get("description", "无")}
"""

        if performance_data:
            prompt += f"""
广告表现数据:
- 展示: {performance_data.get("impressions", 0)}
- 点击: {performance_data.get("clicks", 0)}
- 花费: ${performance_data.get("spend", 0):.2f}
- 订单: {performance_data.get("orders", 0)}
- ACOS: {performance_data.get("acos", 0):.2%}
"""

        # 速率限制
        if not self._wait_for_rate_limit():
            return RelevanceResult(
                keyword=keyword,
                relevance="medium",
                confidence=0.5,
                reason="API调用被限流",
                suggested_action="观察表现",
            )

        result = self.client.generate_json(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.3,
        )

        if not result:
            logger.warning(f"相关性判断失败: {keyword}")
            return RelevanceResult(
                keyword=keyword,
                relevance="medium",
                confidence=0.5,
                reason="AI分析失败，默认中等相关",
                suggested_action="观察表现",
            )

        return RelevanceResult(
            keyword=keyword,
            relevance=result.get("relevance", "medium"),
            confidence=result.get("confidence", 0.5),
            reason=result.get("reason", ""),
            suggested_action=result.get("suggested_action", "观察表现"),
        )

    def suggest_relevance(
        self,
        term: str,
        product_context: dict,
        performance_data: dict = None,
    ) -> RelevanceSuggestion:
        """
        建议搜索词的相关性等级（v2.0人工审核用）

        使用新的6级相关性系统：
        - strong_core: 强相关核心词（产品核心关键词）
        - strong_longtail: 强相关长尾词（长尾但相关）
        - weak: 弱相关（关联度低）
        - generic: 太泛（泛词不精准）
        - irrelevant: 不相关（完全无关）

        Args:
            term: 搜索词
            product_context: 产品上下文信息
            performance_data: 表现数据（可选）

        Returns:
            RelevanceSuggestion
        """
        system_instruction = """你是一个亚马逊广告专家，需要判断搜索词与产品的相关性等级。

请返回JSON格式：
{
    "relevance": "strong_core" | "strong_longtail" | "weak" | "generic" | "irrelevant",
    "confidence": 0.0-1.0,
    "reasoning": "判断理由（简短）",
    "suggested_action": "建议动作"
}

相关性等级定义：
- strong_core: 产品核心关键词，直接描述产品主要功能/特性（如"旅行枕头"对应旅行枕产品）
- strong_longtail: 长尾但相关的词，与产品有明确关联（如"飞机颈枕"对应旅行枕产品）
- weak: 弱相关，有一定关联但不是目标需求（如"颈部按摩器"与旅行枕产品）
- generic: 太泛，搜索意图不明确（如"pillow"这种大词）
- irrelevant: 完全不相关（如"汽车配件"与旅行枕产品）

建议动作：
- strong_core/strong_longtail: 优先手动精准投放
- weak: 否定词组
- generic: 否定精准
- irrelevant: 否定词组
"""

        prompt = f"""请分析以下搜索词与产品的相关性等级：

搜索词: {term}

产品信息:
- 名称: {product_context.get("name", "未知")}
- 类目: {product_context.get("category", "未知")}
- 核心关键词: {", ".join(product_context.get("core_keywords", []))}
"""

        if performance_data:
            prompt += f"""
广告表现数据:
- 点击: {performance_data.get("clicks", 0)}
- 花费: ${performance_data.get("spend", 0):.2f}
- 订单: {performance_data.get("orders", 0)}
"""

        # 速率限制
        if not self._wait_for_rate_limit():
            return RelevanceSuggestion(
                term=term,
                suggested_relevance="pending",
                confidence=0.0,
                reasoning="API调用被限流",
                suggested_action="需人工判断",
            )

        result = self.client.generate_json(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.3,
        )

        if not result:
            logger.warning(f"相关性建议失败: {term}")
            return RelevanceSuggestion(
                term=term,
                suggested_relevance="pending",
                confidence=0.0,
                reasoning="AI分析失败",
                suggested_action="需人工判断",
            )

        return RelevanceSuggestion(
            term=term,
            suggested_relevance=result.get("relevance", "pending"),
            confidence=result.get("confidence", 0.5),
            reasoning=result.get("reasoning", ""),
            suggested_action=result.get("suggested_action", "需人工判断"),
        )

    def batch_suggest_relevance(
        self,
        terms: list[str],
        product_context: dict,
    ) -> list[RelevanceSuggestion]:
        """
        批量建议搜索词的相关性等级

        Args:
            terms: 搜索词列表
            product_context: 产品上下文

        Returns:
            RelevanceSuggestion 列表
        """
        system_instruction = """你是一个亚马逊广告专家，需要批量判断搜索词与产品的相关性等级。

请返回JSON数组格式：
[
    {
        "term": "搜索词",
        "relevance": "strong_core" | "strong_longtail" | "weak" | "generic" | "irrelevant",
        "confidence": 0.0-1.0,
        "reasoning": "判断理由（简短）",
        "suggested_action": "建议动作"
    },
    ...
]
"""

        terms_str = "\n".join([f"- {t}" for t in terms])

        prompt = f"""请批量分析以下搜索词与产品的相关性等级：

产品信息:
- 名称: {product_context.get("name", "未知")}
- 类目: {product_context.get("category", "未知")}
- 核心关键词: {", ".join(product_context.get("core_keywords", []))}

待分析搜索词:
{terms_str}
"""

        # 速率限制
        tokens_needed = max(1, len(terms) // 10)
        if not self._wait_for_rate_limit(tokens_needed):
            return [
                RelevanceSuggestion(
                    term=t,
                    suggested_relevance="pending",
                    confidence=0.0,
                    reasoning="API调用被限流",
                    suggested_action="需人工判断",
                )
                for t in terms
            ]

        result = self.client.generate_json(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.3,
        )

        if not result or not isinstance(result, list):
            logger.warning("批量相关性建议失败")
            return [
                RelevanceSuggestion(
                    term=t,
                    suggested_relevance="pending",
                    confidence=0.0,
                    reasoning="批量分析失败",
                    suggested_action="需人工判断",
                )
                for t in terms
            ]

        results = []
        for item in result:
            results.append(
                RelevanceSuggestion(
                    term=item.get("term", ""),
                    suggested_relevance=item.get("relevance", "pending"),
                    confidence=item.get("confidence", 0.5),
                    reasoning=item.get("reasoning", ""),
                    suggested_action=item.get("suggested_action", "需人工判断"),
                )
            )

        return results

    def resolve_conflict(
        self,
        keyword: str,
        campaign_data: list[dict],
        product_context: dict = None,
    ) -> ConflictResult:
        """
        解决同一关键词在不同活动中的表现分歧

        Args:
            keyword: 搜索词
            campaign_data: 各活动表现数据列表
                [{"campaign": str, "acos": float, "orders": int, "spend": float, ...}, ...]
            product_context: 产品上下文（可选）

        Returns:
            ConflictResult
        """
        system_instruction = """你是一个亚马逊广告优化专家，专门分析关键词在不同广告活动中的表现差异。

当同一个搜索词在不同活动中表现差异很大时，你需要分析原因并给出综合建议。

请返回JSON格式：
{
    "suggestion": "综合建议",
    "reasoning": "详细分析",
    "confidence": 0.0-1.0,
    "campaign_analysis": [
        {"campaign": "活动名", "assessment": "评价", "recommendation": "建议"}
    ]
}

分析维度：
1. 匹配类型差异（广泛匹配 vs 精确匹配）
2. 出价策略差异
3. 广告位置差异
4. 受众定位差异
5. 季节/时间因素

常见建议：
- 在表现好的活动中加大投放
- 在表现差的活动中否定
- 调整匹配类型
- 统一竞价策略
"""

        # 构建活动数据表格
        campaign_table = "| 活动 | ACOS | 订单 | 花费 | 点击 |\n|------|------|------|------|------|\n"
        for data in campaign_data:
            acos = data.get("acos", 0)
            acos_str = f"{acos:.2%}" if acos > 0 else "N/A"
            campaign_table += f"| {data.get('campaign', '未知')} | {acos_str} | {data.get('orders', 0)} | ${data.get('spend', 0):.2f} | {data.get('clicks', 0)} |\n"

        prompt = f"""请分析以下搜索词在不同活动中的表现分歧：

搜索词: {keyword}

各活动表现:
{campaign_table}
"""

        if product_context:
            prompt += f"""
产品信息:
- 名称: {product_context.get("name", "未知")}
- 类目: {product_context.get("category", "未知")}
"""

        # 速率限制
        if not self._wait_for_rate_limit():
            return ConflictResult(
                keyword=keyword,
                suggestion="需要进一步人工分析",
                reasoning="API调用被限流",
                confidence=0.3,
                campaign_analysis=[],
            )

        result = self.client.generate_json(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.4,
        )

        if not result:
            logger.warning(f"分歧解决失败: {keyword}")
            return ConflictResult(
                keyword=keyword,
                suggestion="需要进一步人工分析",
                reasoning="AI分析失败",
                confidence=0.3,
                campaign_analysis=[],
            )

        return ConflictResult(
            keyword=keyword,
            suggestion=result.get("suggestion", ""),
            reasoning=result.get("reasoning", ""),
            confidence=result.get("confidence", 0.5),
            campaign_analysis=result.get("campaign_analysis", []),
        )

    def batch_judge_relevance(
        self,
        keywords: list[str],
        product_context: dict,
    ) -> list[RelevanceResult]:
        """
        批量判断关键词相关性

        Args:
            keywords: 搜索词列表
            product_context: 产品上下文

        Returns:
            RelevanceResult 列表
        """
        system_instruction = """你是一个亚马逊广告专家，需要批量判断多个搜索词与产品的相关性。

请返回JSON数组格式：
[
    {
        "keyword": "搜索词",
        "relevance": "high" | "medium" | "low",
        "confidence": 0.0-1.0,
        "reason": "简短解释",
        "suggested_action": "建议动作"
    },
    ...
]
"""

        keywords_str = "\n".join([f"- {kw}" for kw in keywords])

        prompt = f"""请批量分析以下搜索词与产品的相关性：

产品信息:
- 名称: {product_context.get("name", "未知")}
- 类目: {product_context.get("category", "未知")}
- 核心关键词: {", ".join(product_context.get("core_keywords", []))}

待分析搜索词:
{keywords_str}
"""

        # 速率限制（批量请求消耗更多令牌）
        tokens_needed = max(1, len(keywords) // 10)  # 每10个关键词消耗1个令牌
        if not self._wait_for_rate_limit(tokens_needed):
            return [
                RelevanceResult(
                    keyword=kw,
                    relevance="medium",
                    confidence=0.5,
                    reason="API调用被限流",
                    suggested_action="观察表现",
                )
                for kw in keywords
            ]

        result = self.client.generate_json(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.3,
        )

        if not result or not isinstance(result, list):
            logger.warning("批量相关性判断失败")
            return [
                RelevanceResult(
                    keyword=kw,
                    relevance="medium",
                    confidence=0.5,
                    reason="批量分析失败",
                    suggested_action="观察表现",
                )
                for kw in keywords
            ]

        results = []
        for item in result:
            results.append(
                RelevanceResult(
                    keyword=item.get("keyword", ""),
                    relevance=item.get("relevance", "medium"),
                    confidence=item.get("confidence", 0.5),
                    reason=item.get("reason", ""),
                    suggested_action=item.get("suggested_action", "观察表现"),
                )
            )

        return results

    def analyze_competitor_asin(
        self,
        asin: str,
        performance_data: dict,
        product_context: dict = None,
    ) -> dict:
        """
        分析竞品ASIN的投放价值

        Args:
            asin: 竞品ASIN
            performance_data: 表现数据
            product_context: 自有产品上下文

        Returns:
            分析结果字典
        """
        system_instruction = """你是一个亚马逊广告专家，专门分析竞品ASIN投放策略。

当广告出现在竞品商品页面时，你需要分析这种投放是否有价值。

请返回JSON格式：
{
    "value": "high" | "medium" | "low",
    "reasoning": "分析原因",
    "recommendation": "建议动作",
    "confidence": 0.0-1.0
}

分析维度：
1. 转化效果（有订单 = 有价值）
2. ACOS水平（低ACOS = 高价值）
3. 点击成本（是否划算）
4. 竞争策略（是否值得持续投放）
"""

        prompt = f"""请分析以下竞品ASIN的投放价值：

竞品ASIN: {asin}

投放表现:
- 展示: {performance_data.get("impressions", 0)}
- 点击: {performance_data.get("clicks", 0)}
- 花费: ${performance_data.get("spend", 0):.2f}
- 订单: {performance_data.get("orders", 0)}
- ACOS: {performance_data.get("acos", 0):.2%}
"""

        if product_context:
            prompt += f"""
自有产品信息:
- 名称: {product_context.get("name", "未知")}
- 类目: {product_context.get("category", "未知")}
"""

        # 速率限制
        if not self._wait_for_rate_limit():
            return {
                "value": "medium",
                "reasoning": "API调用被限流",
                "recommendation": "观察表现",
                "confidence": 0.3,
            }

        result = self.client.generate_json(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.3,
        )

        if not result:
            return {
                "value": "medium",
                "reasoning": "AI分析失败",
                "recommendation": "观察表现",
                "confidence": 0.3,
            }

        return result


def get_ai_analyzer(client: GeminiClient = None) -> AIAnalyzer:
    """获取 AI 分析器实例"""
    return AIAnalyzer(client)
