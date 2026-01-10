"""
UI页面模块
"""

from src.ui.pages.home import render_home
from src.ui.pages.upload import render_upload
from src.ui.pages.analysis import render_analysis
from src.ui.pages.actions import render_actions
from src.ui.pages.settings import render_settings

__all__ = [
    "render_home",
    "render_upload",
    "render_analysis",
    "render_actions",
    "render_settings",
]
