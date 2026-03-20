"""
应用配置模块
从.env文件加载配置，提供全局配置访问
"""

import os
import warnings
from pathlib import Path

from dotenv import load_dotenv

# 可用的Gemini模型列表 (model_id, display_name)
# 注意：Gemini 3 系列需要使用 -preview 后缀
AVAILABLE_GEMINI_MODELS = [
    ("gemini-2.5-flash", "Gemini 2.5 Flash (推荐)"),
    ("gemini-2.5-pro", "Gemini 2.5 Pro"),
    ("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite"),
    ("gemini-3-flash-preview", "Gemini 3 Flash Preview (最新)"),
    ("gemini-3-pro-preview", "Gemini 3 Pro Preview (最新)"),
]


class Settings:
    """应用配置类"""

    def __init__(self, env_path: str = None):
        """
        初始化配置

        Args:
            env_path: .env文件路径，默认为项目根目录
        """
        # 确定项目根目录
        self.project_root = Path(__file__).parent.parent.parent

        # 加载.env文件 (override=True确保新配置能覆盖旧值)
        if env_path:
            load_dotenv(env_path, override=True)
        else:
            load_dotenv(self.project_root / ".env", override=True)

        # ==================== Gemini API 配置 ====================
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        # ==================== 数据库配置 ====================
        self.database_path = os.getenv("DATABASE_PATH", "data/db/app.db")
        # 转换为绝对路径
        if not os.path.isabs(self.database_path):
            self.database_path = str(self.project_root / self.database_path)

        # ==================== 应用配置 ====================
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        # ==================== 验证必要配置 ====================
        self._validate()

    def _validate(self) -> None:
        """验证必要配置是否存在"""
        errors = []

        if not self.gemini_api_key or self.gemini_api_key == "your_gemini_api_key_here":
            errors.append("GEMINI_API_KEY 未配置或无效，请在 .env 文件中设置")

        if errors:
            # 开发模式下只警告，不报错
            if self.debug:
                for error in errors:
                    warnings.warn(error, stacklevel=2)
            else:
                raise ValueError("\n".join(errors))

    @property
    def is_api_configured(self) -> bool:
        """检查API是否已配置"""
        return bool(
            self.gemini_api_key and self.gemini_api_key != "your_gemini_api_key_here"
        )

    def __repr__(self) -> str:
        return (
            f"Settings(\n"
            f"  gemini_model={self.gemini_model},\n"
            f"  database_path={self.database_path},\n"
            f"  debug={self.debug},\n"
            f"  log_level={self.log_level},\n"
            f"  is_api_configured={self.is_api_configured}\n"
            f")"
        )


# 全局配置实例
_settings = None


def get_settings() -> Settings:
    """获取全局配置实例（单例模式）"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
