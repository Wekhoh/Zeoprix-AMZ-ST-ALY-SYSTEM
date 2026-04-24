"""
后端数据库基础设施测试。
"""

from __future__ import annotations

from sqlalchemy import text

from src.backend.database import (
    create_engine_for_url,
    create_session_factory,
    get_backend_database_url,
)


def test_get_backend_database_url_defaults_to_local_sqlite(tmp_path, monkeypatch):
    """未配置环境变量时，应回退到本地 sqlite 数据库。"""
    monkeypatch.delenv("AMZ_BACKEND_DATABASE_URL", raising=False)
    monkeypatch.setenv("AMZ_BACKEND_SQLITE_PATH", str(tmp_path / "backend.db"))

    url = get_backend_database_url()

    assert url.startswith("sqlite:///")
    assert str((tmp_path / "backend.db").as_posix()) in url


def test_session_factory_executes_simple_query_against_sqlite(tmp_path):
    """会话工厂应可用于最小 SQL 执行，作为后续 ORM 与迁移地基。"""
    db_path = tmp_path / "smoke.db"
    engine = create_engine_for_url(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        result = session.execute(text("select 1")).scalar_one()

    assert result == 1
