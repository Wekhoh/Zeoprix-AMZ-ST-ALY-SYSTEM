"""
Gemini API 客户端模块
封装 Google Gemini API 调用
"""

import time
from typing import Any

from google import genai
from google.genai import types

from src.config.logger import get_logger
from src.config.settings import Settings

logger = get_logger(__name__)


class GeminiClient:
    """Gemini API 客户端"""

    # 默认超时设置（秒）
    DEFAULT_TIMEOUT = 60.0

    def __init__(self, api_key: str = None, model: str = None, timeout: float = None):
        """
        初始化 Gemini 客户端

        Args:
            api_key: API密钥（默认从环境变量获取）
            model: 模型名称（默认 gemini-2.5-flash）
            timeout: 默认超时时间（秒）
        """
        settings = Settings()
        # 显式检查 None，允许测试时传入空字符串
        self.api_key = api_key if api_key is not None else settings.gemini_api_key

        # 动态模型选择：优先使用 session_state 中的模型，否则用默认配置
        if model is not None:
            self.model = model
        else:
            try:
                import streamlit as st
                if hasattr(st, 'session_state') and "selected_gemini_model" in st.session_state:
                    self.model = st.session_state.selected_gemini_model
                else:
                    self.model = settings.gemini_model
            except Exception:
                # 非Streamlit环境下使用配置文件中的模型
                self.model = settings.gemini_model
        self.default_timeout = timeout or self.DEFAULT_TIMEOUT

        if not self.api_key:
            raise ValueError("未配置 GEMINI_API_KEY")

        # 初始化客户端，配置HTTP选项（通过client_args传递timeout给httpx）
        http_options = types.HttpOptions(
            client_args={'timeout': self.default_timeout}
        )
        self.client = genai.Client(api_key=self.api_key, http_options=http_options)
        logger.info(f"Gemini客户端初始化成功，模型: {self.model}, 超时: {self.default_timeout}s")

    def generate(
        self,
        prompt: str,
        system_instruction: str = None,
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> str:
        """
        生成文本响应

        Args:
            prompt: 用户提示词
            system_instruction: 系统指令
            temperature: 生成温度（0-1）
            max_output_tokens: 最大输出token数
            timeout: 超时时间（秒）
            max_retries: 最大重试次数

        Returns:
            生成的文本
        """
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            system_instruction=system_instruction,
        )

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )

                if response.text:
                    logger.debug(f"生成成功，响应长度: {len(response.text)}")
                    return response.text
                else:
                    logger.warning("响应为空")
                    return ""

            except Exception as e:
                logger.warning(f"生成失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"生成失败，已达最大重试次数: {e}")
                    raise

    def generate_json(
        self,
        prompt: str,
        system_instruction: str = None,
        temperature: float = 0.3,
        max_retries: int = 3,
    ) -> dict | list | None:
        """
        生成JSON格式响应

        Args:
            prompt: 用户提示词
            system_instruction: 系统指令
            temperature: 生成温度（更低以保证格式稳定）
            max_retries: 最大重试次数

        Returns:
            解析后的JSON对象
        """
        import json

        # 添加JSON格式要求
        json_instruction = (system_instruction or "") + "\n\n请只返回有效的JSON格式，不要包含其他文字。"

        response = self.generate(
            prompt=prompt,
            system_instruction=json_instruction,
            temperature=temperature,
            max_retries=max_retries,
        )

        # 尝试解析JSON
        try:
            # 清理可能的markdown代码块
            text = response.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}\n原始响应: {response}")
            return None

    def create_chat(self, system_instruction: str = None) -> "ChatSession":
        """
        创建聊天会话

        Args:
            system_instruction: 系统指令

        Returns:
            ChatSession 实例
        """
        return ChatSession(self, system_instruction)


class ChatSession:
    """聊天会话，支持多轮对话"""

    # 默认最大历史轮数（每轮包含用户消息和AI回复）
    DEFAULT_MAX_HISTORY_TURNS = 20

    def __init__(
        self,
        client: GeminiClient,
        system_instruction: str = None,
        max_history_turns: int = None,
    ):
        """
        初始化聊天会话

        Args:
            client: GeminiClient 实例
            system_instruction: 系统指令
            max_history_turns: 最大历史轮数（每轮含user+assistant消息）
        """
        self.gemini_client = client
        self.system_instruction = system_instruction
        self.max_history_turns = max_history_turns or self.DEFAULT_MAX_HISTORY_TURNS
        self.history: list[dict[str, str]] = []

        # 创建 Gemini 聊天
        self._chat = self._create_chat()

        logger.debug(
            f"聊天会话已创建，最大历史轮数: {self.max_history_turns}"
        )

    def _create_chat(self):
        """创建 Gemini 聊天对象"""
        config = None
        if self.system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
            )

        return self.gemini_client.client.chats.create(
            model=self.gemini_client.model,
            config=config,
        )

    def send_message(
        self,
        message: str,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> str:
        """
        发送消息并获取回复

        Args:
            message: 用户消息
            temperature: 生成温度
            max_retries: 最大重试次数

        Returns:
            AI 回复
        """
        for attempt in range(max_retries):
            try:
                response = self._chat.send_message(message)

                if response.text:
                    # 记录对话历史
                    self.history.append({"role": "user", "content": message})
                    self.history.append({"role": "assistant", "content": response.text})

                    # 检查并裁剪历史（滑动窗口）
                    self._trim_history_if_needed()

                    logger.debug(f"对话回复成功，长度: {len(response.text)}")
                    return response.text
                else:
                    return ""

            except Exception as e:
                logger.warning(f"对话失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    logger.error(f"对话失败，已达最大重试次数: {e}")
                    raise

    def _trim_history_if_needed(self) -> None:
        """
        滑动窗口：如果历史超过限制，裁剪并重建聊天会话

        每轮对话包含2条消息（user + assistant），所以最大消息数 = max_history_turns * 2
        """
        max_messages = self.max_history_turns * 2

        if len(self.history) <= max_messages:
            return

        # 计算需要移除的消息数（保留最近的 max_messages 条）
        remove_count = len(self.history) - max_messages
        # 确保移除偶数条消息（完整的对话轮次）
        remove_count = (remove_count // 2) * 2

        if remove_count <= 0:
            return

        logger.info(
            f"对话历史超限，裁剪 {remove_count // 2} 轮对话 "
            f"(当前 {len(self.history) // 2} 轮，限制 {self.max_history_turns} 轮)"
        )

        # 裁剪历史
        self.history = self.history[remove_count:]

        # 重建 Gemini 聊天并重放历史
        self._rebuild_chat_with_history()

    def _rebuild_chat_with_history(self) -> None:
        """重建聊天会话并重放历史记录"""
        self._chat = self._create_chat()

        # 重放历史记录到新会话
        # 注意：以 user/assistant 对的方式重放
        for i in range(0, len(self.history), 2):
            if i + 1 < len(self.history):
                user_msg = self.history[i]["content"]
                assistant_msg = self.history[i + 1]["content"]
                try:
                    # 发送用户消息并忽略响应（我们有自己的历史记录）
                    # 使用 Gemini 的历史注入方式
                    self._chat.send_message(user_msg)
                except Exception as e:
                    logger.warning(f"重放历史消息失败: {e}")
                    # 如果重放失败，保留已有历史但停止重放
                    break

        logger.debug(f"聊天会话已重建，历史 {len(self.history) // 2} 轮")

    def get_history(self) -> list[dict[str, str]]:
        """获取对话历史"""
        return self.history.copy()

    def clear_history(self) -> None:
        """清空对话历史并重建会话"""
        self.history.clear()
        self._chat = self._create_chat()
        logger.debug("对话历史已清空")


def get_gemini_client(api_key: str = None) -> GeminiClient:
    """获取 Gemini 客户端实例"""
    return GeminiClient(api_key=api_key)
