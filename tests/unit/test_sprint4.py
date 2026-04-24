"""
Sprint 4 单元测试
测试 AI 集成模块（客户端、分析器、对话助手）
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# 真实 API 测试需要同时满足：
# 1. 配置了 GEMINI_API_KEY
# 2. 显式开启 RUN_LIVE_GEMINI_TESTS=1
# 默认 CI / 沙箱环境不出网时应自动跳过，避免把网络策略误判成业务失败。
HAS_API_KEY = bool(os.getenv("GEMINI_API_KEY"))
RUN_LIVE_GEMINI_TESTS = os.getenv("RUN_LIVE_GEMINI_TESTS") == "1"
HAS_LIVE_GEMINI = HAS_API_KEY and RUN_LIVE_GEMINI_TESTS


class TestGeminiClient:
    """T24: Gemini 客户端测试"""

    def test_client_init_without_key(self):
        """测试无API Key时初始化失败"""
        from src.ai.client import GeminiClient

        # 使用明确的空值测试
        with pytest.raises(ValueError, match="未配置 GEMINI_API_KEY"):
            GeminiClient(api_key="")

    @pytest.mark.skipif(
        not HAS_LIVE_GEMINI,
        reason="需要 GEMINI_API_KEY 且显式开启 RUN_LIVE_GEMINI_TESTS=1",
    )
    def test_client_init_with_key(self):
        """测试有API Key时初始化成功"""
        from src.ai.client import GeminiClient

        client = GeminiClient()
        assert client.client is not None
        # 模型名称可能因环境变量GEMINI_MODEL而不同
        assert client.model is not None
        assert "gemini" in client.model.lower()

    @pytest.mark.skipif(
        not HAS_LIVE_GEMINI,
        reason="需要 GEMINI_API_KEY 且显式开启 RUN_LIVE_GEMINI_TESTS=1",
    )
    def test_generate_simple(self):
        """测试简单文本生成"""
        from src.ai.client import GeminiClient

        client = GeminiClient()
        response = client.generate("Say 'Hello' in one word")

        assert response is not None
        assert len(response) > 0

    @pytest.mark.skipif(
        not HAS_LIVE_GEMINI,
        reason="需要 GEMINI_API_KEY 且显式开启 RUN_LIVE_GEMINI_TESTS=1",
    )
    def test_generate_json(self):
        """测试JSON格式生成"""
        from src.ai.client import GeminiClient

        client = GeminiClient()
        result = client.generate_json(
            prompt="Return a JSON object with keys 'name' and 'value'",
            system_instruction="Always return valid JSON",
        )

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.skipif(
        not HAS_LIVE_GEMINI,
        reason="需要 GEMINI_API_KEY 且显式开启 RUN_LIVE_GEMINI_TESTS=1",
    )
    def test_create_chat(self):
        """测试创建聊天会话"""
        from src.ai.client import GeminiClient, ChatSession

        client = GeminiClient()
        chat = client.create_chat()

        assert isinstance(chat, ChatSession)
        assert chat.history == []

    @pytest.mark.skipif(
        not HAS_LIVE_GEMINI,
        reason="需要 GEMINI_API_KEY 且显式开启 RUN_LIVE_GEMINI_TESTS=1",
    )
    def test_chat_session(self):
        """测试聊天会话交互"""
        from src.ai.client import GeminiClient

        client = GeminiClient()
        chat = client.create_chat()

        response = chat.send_message("Say 'Hi'")

        assert response is not None
        assert len(chat.history) == 2  # user + assistant


class TestAIAnalyzer:
    """T25-T26: AI 分析器测试"""

    @pytest.mark.skipif(
        not HAS_LIVE_GEMINI,
        reason="需要 GEMINI_API_KEY 且显式开启 RUN_LIVE_GEMINI_TESTS=1",
    )
    def test_judge_relevance(self):
        """测试相关性判断"""
        from src.ai.analyzer import AIAnalyzer

        analyzer = AIAnalyzer()
        result = analyzer.judge_relevance(
            keyword="wireless charger",
            product_context={
                "name": "Fast Wireless Charger",
                "category": "Electronics",
                "core_keywords": ["wireless charger", "fast charging"],
            },
        )

        assert result.keyword == "wireless charger"
        assert result.relevance in ["high", "medium", "low"]
        assert 0 <= result.confidence <= 1
        assert len(result.reason) > 0

    @pytest.mark.skipif(
        not HAS_LIVE_GEMINI,
        reason="需要 GEMINI_API_KEY 且显式开启 RUN_LIVE_GEMINI_TESTS=1",
    )
    def test_judge_relevance_low(self):
        """测试低相关性判断"""
        from src.ai.analyzer import AIAnalyzer

        analyzer = AIAnalyzer()
        result = analyzer.judge_relevance(
            keyword="iphone cable",
            product_context={
                "name": "Android Wireless Charger",
                "category": "Electronics",
                "core_keywords": ["wireless charger", "android"],
            },
        )

        assert result.keyword == "iphone cable"
        # 这个词应该被判断为低相关或中相关
        assert result.relevance in ["low", "medium"]

    @pytest.mark.skipif(
        not HAS_LIVE_GEMINI,
        reason="需要 GEMINI_API_KEY 且显式开启 RUN_LIVE_GEMINI_TESTS=1",
    )
    def test_resolve_conflict(self):
        """测试分歧解决"""
        from src.ai.analyzer import AIAnalyzer

        analyzer = AIAnalyzer()
        campaign_data = [
            {
                "campaign": "Campaign A - Broad",
                "acos": 0.15,
                "orders": 10,
                "spend": 50,
                "clicks": 100,
            },
            {
                "campaign": "Campaign B - Exact",
                "acos": 0.80,
                "orders": 2,
                "spend": 80,
                "clicks": 50,
            },
        ]

        result = analyzer.resolve_conflict(
            keyword="wireless charger",
            campaign_data=campaign_data,
        )

        assert result.keyword == "wireless charger"
        assert len(result.suggestion) > 0
        assert len(result.reasoning) > 0

    @pytest.mark.skipif(
        not HAS_LIVE_GEMINI,
        reason="需要 GEMINI_API_KEY 且显式开启 RUN_LIVE_GEMINI_TESTS=1",
    )
    def test_batch_judge_relevance(self):
        """测试批量相关性判断"""
        from src.ai.analyzer import AIAnalyzer

        analyzer = AIAnalyzer()
        keywords = ["wireless charger", "phone stand", "car holder"]
        product_context = {
            "name": "Wireless Charger Stand",
            "category": "Electronics",
            "core_keywords": ["wireless charger", "phone stand"],
        }

        results = analyzer.batch_judge_relevance(keywords, product_context)

        assert len(results) == 3
        for result in results:
            assert result.relevance in ["high", "medium", "low"]


class TestChatAssistant:
    """T27-T28: 对话助手测试"""

    @pytest.fixture
    def db_with_data(self):
        """创建带数据的测试数据库"""
        from src.data.db import Database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = Database(db_path)
        db.init_schema()
        db.init_default_rules()

        # 创建测试产品
        product_id = db.create_product(
            name="测试产品",
            asin="B0TESTPROD",
            config={"core_keywords": ["test"]},
        )

        # 创建测试活动
        campaign_id = db.create_campaign(
            product_id=product_id,
            name="Test Campaign",
            match_type="broad",
        )

        # 添加搜索词数据（直接SQL插入）
        import pandas as pd

        test_data = pd.DataFrame(
            [
                {
                    "term": "good keyword",
                    "term_type": "keyword",
                    "match_type": "broad",
                    "impressions": 1000,
                    "clicks": 50,
                    "spend": 10.0,
                    "orders": 5,
                    "sales": 100.0,
                },
                {
                    "term": "bad keyword",
                    "term_type": "keyword",
                    "match_type": "broad",
                    "impressions": 500,
                    "clicks": 20,
                    "spend": 15.0,
                    "orders": 0,
                    "sales": 0,
                },
            ]
        )
        db.save_search_terms(test_data, campaign_id)

        yield db, product_id

        db.close()
        os.unlink(db_path)

    def test_chat_assistant_init(self, db_with_data):
        """测试对话助手初始化（使用Mock）"""
        from src.ai.chat import ChatAssistant

        db, product_id = db_with_data

        # 使用Mock客户端
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_client.create_chat.return_value = mock_chat

        assistant = ChatAssistant(client=mock_client, db=db, product_id=product_id)

        assert assistant.db == db
        assert assistant.product_id == product_id

    def test_welcome_message(self, db_with_data):
        """测试欢迎消息"""
        from src.ai.chat import ChatAssistant

        db, product_id = db_with_data

        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_client.create_chat.return_value = mock_chat

        assistant = ChatAssistant(client=mock_client, db=db, product_id=product_id)
        response = assistant.get_welcome_message()

        assert "亚马逊广告" in response.message
        assert len(response.options) > 0

    def test_detect_intent(self, db_with_data):
        """测试意图检测"""
        from src.ai.chat import ChatAssistant

        db, product_id = db_with_data

        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_client.create_chat.return_value = mock_chat

        assistant = ChatAssistant(client=mock_client, db=db, product_id=product_id)

        assert assistant._detect_intent("哪些词需要否定？") == "negative_keywords"
        assert assistant._detect_intent("高转化词有哪些？") == "high_conversion"
        assert assistant._detect_intent("ACOS太高了怎么办？") == "acos_analysis"
        assert assistant._detect_intent("竞品ASIN表现如何？") == "competitor_analysis"
        assert assistant._detect_intent("给我一个数据概览") == "overview"
        assert assistant._detect_intent("你好") == "general"

    def test_guided_options(self, db_with_data):
        """测试引导选项生成"""
        from src.ai.chat import ChatAssistant

        db, product_id = db_with_data

        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_client.create_chat.return_value = mock_chat

        assistant = ChatAssistant(client=mock_client, db=db, product_id=product_id)

        # 测试否词意图的选项
        options = assistant._generate_options("negative_keywords", "回复内容")
        assert len(options) > 0
        assert any(opt.id == "export_negative" for opt in options)

        # 测试高转化意图的选项
        options = assistant._generate_options("high_conversion", "回复内容")
        assert any(opt.id == "export_manual" for opt in options)

    @pytest.mark.skipif(
        not HAS_LIVE_GEMINI,
        reason="需要 GEMINI_API_KEY 且显式开启 RUN_LIVE_GEMINI_TESTS=1",
    )
    def test_process_message(self, db_with_data):
        """测试消息处理（真实API）"""
        from src.ai.chat import ChatAssistant

        db, product_id = db_with_data

        assistant = ChatAssistant(db=db, product_id=product_id)
        response = assistant.process_message("数据概览")

        assert response.message is not None
        assert len(response.message) > 0


class TestGuidedConversation:
    """T28: 引导式对话测试"""

    def test_guided_option_dataclass(self):
        """测试 GuidedOption 数据类"""
        from src.ai.chat import GuidedOption

        option = GuidedOption(
            id="test_option",
            label="测试选项",
            description="这是一个测试选项",
            action="test_action",
            data={"key": "value"},
        )

        assert option.id == "test_option"
        assert option.label == "测试选项"
        assert option.action == "test_action"
        assert option.data["key"] == "value"

    def test_chat_response_dataclass(self):
        """测试 ChatResponse 数据类"""
        from src.ai.chat import ChatResponse, GuidedOption

        options = [
            GuidedOption(id="opt1", label="选项1"),
            GuidedOption(id="opt2", label="选项2"),
        ]

        response = ChatResponse(
            message="测试消息",
            options=options,
            data={"intent": "test"},
        )

        assert response.message == "测试消息"
        assert len(response.options) == 2
        assert response.data["intent"] == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
