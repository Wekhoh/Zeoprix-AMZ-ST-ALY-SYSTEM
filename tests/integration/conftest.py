"""
集成测试共享 fixtures
提供内存数据库、测试数据等共用资源
"""

import os
import shutil
import uuid
from pathlib import Path

import pandas as pd
import pytest
from _pytest import pathlib as pytest_pathlib
from _pytest import tmpdir as pytest_tmpdir

from src.data.db import Database


TEST_TEMP_ROOT = Path.home() / ".codex" / "memories" / "amz_pytest_tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)

PYTEST_DEBUG_ROOT = TEST_TEMP_ROOT / f"pytest_root_{uuid.uuid4().hex}"
PYTEST_DEBUG_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["PYTEST_DEBUG_TEMPROOT"] = str(PYTEST_DEBUG_ROOT)

_ORIGINAL_CLEANUP_DEAD_SYMLINKS = pytest_pathlib.cleanup_dead_symlinks
_ORIGINAL_FIND_PREFIXED = pytest_pathlib.find_prefixed
_ORIGINAL_GETBASETEMP = pytest_tmpdir.TempPathFactory.getbasetemp


def _safe_cleanup_dead_symlinks(root: Path) -> None:
    """忽略当前 Windows 沙箱下 basetemp 目录的误报权限异常。"""
    try:
        _ORIGINAL_CLEANUP_DEAD_SYMLINKS(root)
    except PermissionError:
        return


def _safe_find_prefixed(root: Path, prefix: str):
    """在 OneDrive/沙箱目录被占用时，允许 pytest 回退为创建新的编号目录。"""
    try:
        yield from _ORIGINAL_FIND_PREFIXED(root, prefix)
    except PermissionError:
        return


def _safe_getbasetemp(self):
    """跳过 pytest 默认的 numbered dir 流程，避免 Windows/OneDrive 下的 basetemp 权限异常。"""
    if self._basetemp is None and self._given_basetemp is None:
        basetemp = TEST_TEMP_ROOT / f"basetemp_{uuid.uuid4().hex}"
        basetemp.mkdir(parents=True, exist_ok=False)
        self._basetemp = basetemp.resolve()
    return _ORIGINAL_GETBASETEMP(self)


pytest_pathlib.cleanup_dead_symlinks = _safe_cleanup_dead_symlinks
pytest_tmpdir.cleanup_dead_symlinks = _safe_cleanup_dead_symlinks
pytest_pathlib.find_prefixed = _safe_find_prefixed
pytest_tmpdir.TempPathFactory.getbasetemp = _safe_getbasetemp


@pytest.fixture
def temp_db_path():
    """创建临时数据库文件路径"""
    tmpdir = TEST_TEMP_ROOT / f"db_{uuid.uuid4().hex}"
    tmpdir.mkdir(parents=True, exist_ok=False)
    try:
        yield str(tmpdir / "test.db")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def db(temp_db_path):
    """创建已初始化的数据库实例"""
    database = Database(temp_db_path)
    database.init_schema()
    database.init_default_rules()
    yield database
    database.close()


@pytest.fixture
def product_id(db):
    """创建测试产品并返回ID"""
    pid = db.create_product(
        name="旅行枕",
        asin="B0TEST12345",
        category="Home & Kitchen",
    )
    # 配置核心关键词和自有ASIN
    db.update_product_config(
        pid,
        {
            "core_keywords": ["travel pillow", "neck pillow", "travel neck pillow"],
            "related_keywords": ["airplane pillow", "flight pillow"],
            "own_asins": ["B0TEST12345"],
            "keyword_libraries": {
                "generic_keywords": ["pillow", "pillows"],
                "irrelevant_keywords": ["massager", "blanket"],
                "weak_category_keywords": ["neck support", "cushion"],
                "car_keywords": ["car", "automotive"],
            },
            "thresholds": {
                "spend_threshold": 10.0,
                "min_clicks_for_analysis": 20,
                "good_cvr": 0.10,
            },
        },
    )
    return pid


@pytest.fixture
def sample_search_terms_df():
    """创建模拟的搜索词DataFrame（模拟解析后的数据）"""
    return pd.DataFrame(
        [
            # 高花费零转化 → 应否定
            {
                "term": "neck massager",
                "impressions": 500,
                "clicks": 30,
                "spend": 15.0,
                "orders": 0,
                "sales": 0.0,
                "acos": 0.0,
                "term_type": "keyword",
            },
            # 高转化 → 应手动投放
            {
                "term": "travel pillow for airplane",
                "impressions": 1000,
                "clicks": 50,
                "spend": 25.0,
                "orders": 8,
                "sales": 120.0,
                "acos": 0.208,
                "term_type": "keyword",
            },
            # 核心词低转化 → 继续观察
            {
                "term": "travel neck pillow",
                "impressions": 200,
                "clicks": 5,
                "spend": 2.5,
                "orders": 1,
                "sales": 15.0,
                "acos": 0.167,
                "term_type": "keyword",
            },
            # 竞品ASIN → 监控
            {
                "term": "B0COMPET001",
                "impressions": 100,
                "clicks": 10,
                "spend": 5.0,
                "orders": 0,
                "sales": 0.0,
                "acos": 0.0,
                "term_type": "asin",
            },
            # 泛词 → 否定
            {
                "term": "pillow",
                "impressions": 2000,
                "clicks": 100,
                "spend": 50.0,
                "orders": 2,
                "sales": 30.0,
                "acos": 1.667,
                "term_type": "keyword",
            },
            # 汽车词 → 否定
            {
                "term": "car neck pillow",
                "impressions": 300,
                "clicks": 20,
                "spend": 10.0,
                "orders": 0,
                "sales": 0.0,
                "acos": 0.0,
                "term_type": "keyword",
            },
            # 正常表现词
            {
                "term": "memory foam travel pillow",
                "impressions": 800,
                "clicks": 40,
                "spend": 20.0,
                "orders": 5,
                "sales": 75.0,
                "acos": 0.267,
                "term_type": "keyword",
            },
        ]
    )


@pytest.fixture
def campaign_id(db, product_id):
    """创建测试广告活动并返回ID"""
    return db.get_or_create_campaign(
        product_id=product_id,
        name="BLK-Auto-Broad",
        match_type="auto",
    )


@pytest.fixture
def db_with_data(db, product_id, campaign_id, sample_search_terms_df):
    """创建带有测试数据的数据库"""
    db.save_search_terms(sample_search_terms_df, campaign_id)
    return db
