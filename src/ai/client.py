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

    def __init__(self, api_key: str = None, model: str = None):
        """
        初始化 Gemini 客户端

        Args:
            api_key: API密钥（默认从环境变量获取）
            model: 模型名称（默认 gemini-2.5-flash）
        """
        settings = Settings()
        # 显式检查 None，允许测试时传入空字符串
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model = model if model is not None else settings.gemini_model

        if not self.api_key:
            raise ValueError("未配置 GEMINI_API_KEY")

        # 初始化客户端
        self.client = genai.Client(api_key=self.api_key)
        logger.info(f"Gemini客户端初始化成功，模型: {self.model}")

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

    def __init__(self, client: GeminiClient, system_instruction: str = None):
        """
        初始化聊天会话

        Args:
            client: GeminiClient 实例
            system_instruction: 系统指令
        """
        self.gemini_client = client
        self.system_instruction = system_instruction
        self.history: list[dict[str, str]] = []

        # 创建 Gemini 聊天
        config = None
        if system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
            )

        self._chat = client.client.chats.create(
            model=client.model,
            config=config,
        )

        logger.debug("聊天会话已创建")

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

    def get_history(self) -> list[dict[str, str]]:
        """获取对话历史"""
        return self.history.copy()

    def clear_history(self) -> None:
        """清空对话历史并重建会话"""
        self.history.clear()

        # 重新创建聊天
        config = None
        if self.system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
            )

        self._chat = self.gemini_client.client.chats.create(
            model=self.gemini_client.model,
            config=config,
        )

        logger.debug("对话历史已清空")


def get_gemini_client(api_key: str = None) -> GeminiClient:
    """获取 Gemini 客户端实例"""
    return GeminiClient(api_key=api_key)
