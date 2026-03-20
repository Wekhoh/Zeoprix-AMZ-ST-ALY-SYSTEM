"""
UI页面模块
"""

from src.ui.pages.actions import render_actions
from src.ui.pages.analysis import render_analysis
from src.ui.pages.asin_analysis import render_asin_analysis
from src.ui.pages.home import render_home
from src.ui.pages.review import render_review  # v2.0: 相关性审核页面
from src.ui.pages.settings import render_settings
from src.ui.pages.upload import render_upload

__all__ = [
    "render_home",
    "render_upload",
    "render_analysis",
    "render_asin_analysis",
    "render_actions",
    "render_settings",
    "render_review",  # v2.0: 相关性审核页面
]
