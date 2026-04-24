"""全局测试 fixtures。

在当前 Windows + OneDrive + 沙箱环境下，pytest 与标准库 ``tempfile`` 默认使用
的临时目录可能出现权限异常。这里统一把测试临时目录重定向到可写、可清理的
工作区路径，避免 ``tmp_path`` / ``TemporaryDirectory`` 在回收时触发误报。
"""

import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest


TEST_TEMP_ROOT = Path.home() / ".codex" / "memories" / "amz_pytest_tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)

# 统一标准库 tempfile 的根目录，覆盖 TemporaryDirectory/NamedTemporaryFile 等场景。
for _temp_var in ("TMP", "TEMP", "TMPDIR"):
    os.environ[_temp_var] = str(TEST_TEMP_ROOT)
tempfile.tempdir = str(TEST_TEMP_ROOT)


class SafeTemporaryDirectory:
    """在当前 Windows 环境下替代标准库 TemporaryDirectory。

    Python 3.14 在当前环境中创建的 TemporaryDirectory 目录可见但不可写，导致
    测试与上传 helper 落盘失败。这里直接使用 Path.mkdir 创建可写目录，并保持
    与 TemporaryDirectory 主要上下文管理接口兼容。
    """

    def __init__(
        self,
        suffix: str | None = None,
        prefix: str | None = None,
        dir: str | os.PathLike[str] | None = None,
        ignore_cleanup_errors: bool = False,
        *,
        delete: bool = True,
    ) -> None:
        self._base_dir = Path(dir) if dir else TEST_TEMP_ROOT
        self._suffix = suffix or ""
        self._prefix = prefix or "tmp"
        self._ignore_cleanup_errors = ignore_cleanup_errors
        self._delete = delete
        self.name = str(self._create_dir())

    def _create_dir(self) -> Path:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        while True:
            candidate = (
                self._base_dir / f"{self._prefix}{uuid.uuid4().hex}{self._suffix}"
            )
            try:
                candidate.mkdir(parents=True, exist_ok=False)
                return candidate
            except FileExistsError:
                continue

    def __enter__(self) -> str:
        return self.name

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        if not self._delete or not self.name:
            return
        target = Path(self.name)
        if not target.exists():
            return
        if self._ignore_cleanup_errors:
            shutil.rmtree(target, ignore_errors=True)
            return
        shutil.rmtree(target)


tempfile.TemporaryDirectory = SafeTemporaryDirectory


@pytest.fixture
def tmp_path() -> Path:
    """提供可写的临时目录，避免 pytest 默认 basetemp 在当前环境下拒绝访问。"""
    path = TEST_TEMP_ROOT / f"tmp_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
