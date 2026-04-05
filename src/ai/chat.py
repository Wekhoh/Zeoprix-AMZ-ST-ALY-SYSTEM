"""
AI 对话助手模块
提供多轮对话和引导式交互功能
"""

from dataclasses import dataclass, field
from enum import Enum

from src.ai.client import GeminiClient
from src.config.logger import get_logger
from src.data.models import ActionType
from src.data.db import Database
from src.rules.engine import analyze_search_terms

logger = get_logger(__name__)


class MessageRole(Enum):
    """消息角色"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ChatMessage:
    """聊天消息"""

    role: MessageRole
    content: str
    timestamp: str = None
    metadata: dict = field(default_factory=dict)


@dataclass
class GuidedOption:
    """引导选项"""

    id: str
    label: str
    description: str = ""
    action: str = None  # 可选的后续动作标识
    data: dict = field(default_factory=dict)


@dataclass
class ChatResponse:
    """聊天响应"""

    message: str
    options: list[GuidedOption] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    action_required: bool = False
    action_type: str = None


class ChatAssistant:
    """AI 对话助手"""

    SYSTEM_PROMPT = """你是一个专业的亚马逊广告优化助手，帮助卖家分析搜索词数据并优化广告投放。

你的核心能力：
1. 分析搜索词表现，识别高价值词和需否定的词
2. 解答亚马逊广告相关问题
3. 提供数据驱动的优化建议
4. 帮助用户理解数据背后的含义

交互风格：
- 专业但友好
- 回答简洁明了
- 主动提供可操作的建议
- 必要时提供引导选项

当用户询问数据相关问题时，优先使用数据库查询结果来回答。
"""

    def __init__(
        self,
        client: GeminiClient = None,
        db: Database = None,
        product_id: int = None,
    ):
        """
        初始化对话助手

        Args:
            client: GeminiClient 实例
            db: 数据库实例（用于查询数据）
            product_id: 当前产品ID
        """
        self.client = client or GeminiClient()
        self.db = db
        self.product_id = product_id

        # 创建聊天会话
        self.chat_session = self.client.create_chat(
            system_instruction=self.SYSTEM_PROMPT
        )

        # 上下文信息
        self.context: dict = {}

        logger.info("对话助手已初始化")

    def set_context(self, **kwargs) -> None:
        """
        设置对话上下文

        Args:
            **kwargs: 上下文键值对
        """
        self.context.update(kwargs)

    def process_message(
        self,
        message: str,
        include_data: bool = True,
    ) -> ChatResponse:
        """
        处理用户消息

        Args:
            message: 用户消息
            include_data: 是否包含数据库数据

        Returns:
            ChatResponse
        """
        # 检测意图并获取相关数据
        intent = self._detect_intent(message)
        data_context = ""

        if include_data and self.db and self.product_id:
            data_context = self._get_relevant_data(intent, message)

        # 构建增强提示
        enhanced_message = message
        if data_context:
            enhanced_message = f"""用户问题：{message}

相关数据：
{data_context}

请基于以上数据回答用户问题。"""

        # 获取AI响应
        try:
            response_text = self.chat_session.send_message(enhanced_message)
        except Exception as e:
            logger.error(f"对话失败: {e}")
            return ChatResponse(
                message="抱歉，处理您的请求时出现错误。请稍后再试。",
                options=self._get_default_options(),
            )

        # 生成引导选项
        options = self._generate_options(intent, response_text)

        return ChatResponse(
            message=response_text,
            options=options,
            data={"intent": intent},
        )

    def _detect_intent(self, message: str) -> str:
        """
        检测用户意图

        Args:
            message: 用户消息

        Returns:
            意图标识
        """
        message_lower = message.lower()

        # 否词相关
        if any(kw in message_lower for kw in ["否定", "否词", "negative", "屏蔽"]):
            return "negative_keywords"

        # 高转化词相关
        if any(kw in message_lower for kw in ["高转化", "好词", "优质", "表现好"]):
            return "high_conversion"

        # ACOS相关
        if any(kw in message_lower for kw in ["acos", "广告成本", "投入产出"]):
            return "acos_analysis"

        # 竞品相关
        if any(kw in message_lower for kw in ["竞品", "asin", "竞争对手"]):
            return "competitor_analysis"

        # 数据概览
        if any(kw in message_lower for kw in ["概览", "总体", "汇总", "统计"]):
            return "overview"

        # 建议相关
        if any(kw in message_lower for kw in ["建议", "优化", "怎么办", "应该"]):
            return "recommendations"

        return "general"

    def _get_relevant_data(self, intent: str, message: str) -> str:
        """
        获取与意图相关的数据

        Args:
            intent: 用户意图
            message: 原始消息

        Returns:
            格式化的数据字符串
        """
        if not self.db or not self.product_id:
            return ""

        try:
            if intent == "negative_keywords":
                return self._get_negative_keywords_data()
            elif intent == "high_conversion":
                return self._get_high_conversion_data()
            elif intent == "overview":
                return self._get_overview_data()
            elif intent == "acos_analysis":
                return self._get_acos_data()
            elif intent == "competitor_analysis":
                return self._get_competitor_data()
            else:
                return self._get_overview_data()
        except Exception as e:
            logger.warning(f"获取数据失败: {e}")
            return ""

    def _get_negative_keywords_data(self) -> str:
        """获取需否定的关键词数据（使用实时分析）"""
        # 使用实时分析结果（与搜索词分析页面保持一致）
        analysis_results = analyze_search_terms(self.db, self.product_id)
        negative_results = [r for r in analysis_results if ActionType.is_negative(r.action_type)]

        if not negative_results:
            return "当前没有需要否定的关键词。"

        lines = ["需要否定的关键词（Top 10）："]
        for r in negative_results[:10]:
            spend = r.data.get("total_spend", r.data.get("spend", 0))
            orders = r.data.get("total_orders", r.data.get("orders", 0))
            lines.append(
                f"- {r.term}: 花费${spend:.2f}, 订单{orders}, 规则={r.triggered_rule}"
            )

        return "\n".join(lines)

    def _get_high_conversion_data(self) -> str:
        """获取高转化关键词数据（使用实时分析）"""
        # 使用实时分析结果（与搜索词分析页面保持一致）
        analysis_results = analyze_search_terms(self.db, self.product_id)
        manual_results = [r for r in analysis_results if ActionType.is_manual(r.action_type)]

        if not manual_results:
            return "当前没有识别到高转化关键词。"

        lines = ["高转化关键词（Top 10）："]
        for r in manual_results[:10]:
            spend = r.data.get("total_spend", r.data.get("spend", 0))
            sales = r.data.get("total_sales", r.data.get("sales", 0))
            orders = r.data.get("total_orders", r.data.get("orders", 0))
            acos = spend / sales if sales > 0 else 0
            lines.append(
                f"- {r.term}: ACOS={acos:.2%}, 订单{orders}, 销售额${sales:.2f}"
            )

        return "\n".join(lines)

    def _get_overview_data(self) -> str:
        """获取数据概览"""
        # 获取搜索词统计 - 通过campaigns表关联product_id
        cursor = self.db.execute(
            """
            SELECT
                COUNT(DISTINCT st.term) as term_count,
                SUM(st.spend) as total_spend,
                SUM(st.orders) as total_orders,
                SUM(st.sales) as total_sales
            FROM search_terms st
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE c.product_id = ?
            """,
            (self.product_id,),
        )
        row = cursor.fetchone()

        if not row or row["term_count"] == 0:
            return "当前没有搜索词数据。"

        total_spend = row["total_spend"] or 0
        total_sales = row["total_sales"] or 0
        overall_acos = total_spend / total_sales if total_sales > 0 else 0

        return f"""数据概览：
- 搜索词总数: {row["term_count"]}
- 总花费: ${total_spend:.2f}
- 总订单: {row["total_orders"] or 0}
- 总销售额: ${total_sales:.2f}
- 整体ACOS: {overall_acos:.2%}"""

    def _get_acos_data(self) -> str:
        """获取ACOS相关数据"""
        # 通过campaigns表关联product_id
        cursor = self.db.execute(
            """
            SELECT st.term, st.spend, st.orders, st.sales,
                   CASE WHEN st.sales > 0 THEN st.spend / st.sales ELSE 0 END as acos
            FROM search_terms st
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE c.product_id = ? AND st.spend > 0
            ORDER BY acos DESC
            LIMIT 10
            """,
            (self.product_id,),
        )
        rows = cursor.fetchall()

        if not rows:
            return "当前没有ACOS数据。"

        lines = ["ACOS最高的搜索词（Top 10）："]
        for r in rows:
            lines.append(
                f"- {r['term']}: ACOS={r['acos']:.2%}, "
                f"花费${r['spend']:.2f}, 订单{r['orders']}"
            )

        return "\n".join(lines)

    def _get_competitor_data(self) -> str:
        """获取竞品ASIN数据"""
        # 通过campaigns表关联product_id
        cursor = self.db.execute(
            """
            SELECT st.term, st.spend, st.orders, st.clicks
            FROM search_terms st
            JOIN campaigns c ON st.campaign_id = c.id
            WHERE c.product_id = ? AND st.term_type = 'asin'
            ORDER BY st.spend DESC
            LIMIT 10
            """,
            (self.product_id,),
        )
        rows = cursor.fetchall()

        if not rows:
            return "当前没有竞品ASIN数据。"

        lines = ["竞品ASIN投放情况（Top 10）："]
        for r in rows:
            lines.append(
                f"- {r['term']}: 花费${r['spend']:.2f}, "
                f"订单{r['orders']}, 点击{r['clicks']}"
            )

        return "\n".join(lines)

    def _generate_options(self, intent: str, response: str) -> list[GuidedOption]:
        """
        根据意图生成引导选项

        Args:
            intent: 用户意图
            response: AI响应

        Returns:
            引导选项列表
        """
        if intent == "negative_keywords":
            return [
                GuidedOption(
                    id="export_negative",
                    label="导出否词表",
                    description="下载需要否定的关键词列表",
                    action="export_negative",
                ),
                GuidedOption(
                    id="view_details",
                    label="查看详情",
                    description="查看每个否词的具体数据",
                    action="view_negative_details",
                ),
                GuidedOption(
                    id="ask_more",
                    label="继续提问",
                    description="询问更多问题",
                ),
            ]

        elif intent == "high_conversion":
            return [
                GuidedOption(
                    id="export_manual",
                    label="导出手动词",
                    description="下载推荐手动投放的关键词",
                    action="export_manual",
                ),
                GuidedOption(
                    id="view_details",
                    label="查看详情",
                    description="查看每个高转化词的数据",
                    action="view_manual_details",
                ),
                GuidedOption(
                    id="ask_more",
                    label="继续提问",
                    description="询问更多问题",
                ),
            ]

        elif intent == "overview":
            return [
                GuidedOption(
                    id="view_negative",
                    label="查看否词",
                    description="哪些词需要否定？",
                    action="view_negative",
                ),
                GuidedOption(
                    id="view_manual",
                    label="查看优质词",
                    description="哪些词值得手动投放？",
                    action="view_manual",
                ),
                GuidedOption(
                    id="export_report",
                    label="导出报告",
                    description="生成完整分析报告",
                    action="export_report",
                ),
            ]

        else:
            return self._get_default_options()

    def _get_default_options(self) -> list[GuidedOption]:
        """获取默认引导选项"""
        return [
            GuidedOption(
                id="overview",
                label="数据概览",
                description="查看搜索词整体表现",
            ),
            GuidedOption(
                id="negative",
                label="否词分析",
                description="哪些词需要否定？",
            ),
            GuidedOption(
                id="manual",
                label="优质词推荐",
                description="哪些词值得手动投放？",
            ),
            GuidedOption(
                id="help",
                label="使用帮助",
                description="了解如何使用助手",
            ),
        ]

    def get_welcome_message(self) -> ChatResponse:
        """获取欢迎消息"""
        message = """你好！我是你的亚马逊广告优化助手。

我可以帮你：
• 分析搜索词表现
• 识别需要否定的关键词
• 推荐高转化关键词
• 解答广告优化问题

你想从哪里开始？"""

        return ChatResponse(
            message=message,
            options=self._get_default_options(),
        )

    def handle_option(self, option_id: str) -> ChatResponse:
        """
        处理用户选择的选项

        Args:
            option_id: 选项ID

        Returns:
            ChatResponse
        """
        option_messages = {
            "overview": "请给我展示数据概览",
            "negative": "哪些词需要否定？",
            "manual": "哪些词值得手动投放？",
            "help": "如何使用这个助手？",
            "view_negative": "显示需要否定的关键词详情",
            "view_manual": "显示推荐手动投放的关键词详情",
        }

        message = option_messages.get(option_id, f"处理选项: {option_id}")
        return self.process_message(message)

    def reset(self) -> None:
        """重置对话"""
        self.chat_session = self.client.create_chat(
            system_instruction=self.SYSTEM_PROMPT
        )
        self.context.clear()
        logger.info("对话已重置")


def get_chat_assistant(
    client: GeminiClient = None,
    db: Database = None,
    product_id: int = None,
) -> ChatAssistant:
    """获取对话助手实例"""
    return ChatAssistant(client, db, product_id)
