"""产品默认配置种子与配置合并辅助函数。"""

from __future__ import annotations

import copy
import json
from pathlib import Path

DEFAULT_PRODUCT_CONFIG_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "fixtures"
    / "acceptance_product_config.json"
)


def load_default_product_config(template_path: str | Path | None = None) -> dict:
    """加载仓库内的默认产品配置模板。"""
    path = (
        Path(template_path).expanduser().resolve()
        if template_path is not None
        else DEFAULT_PRODUCT_CONFIG_TEMPLATE_PATH.resolve()
    )
    if not path.exists():
        raise FileNotFoundError(f"配置模板不存在: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"配置模板必须是 JSON object: {path}")

    return data


def merge_product_config(existing, template):
    """深度合并配置：保留现有标量，列表 union，字典递归补缺。"""
    if isinstance(existing, dict) and isinstance(template, dict):
        merged = copy.deepcopy(existing)
        for key, value in template.items():
            if key in merged:
                merged[key] = merge_product_config(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged

    if isinstance(existing, list) and isinstance(template, list):
        merged: list = []
        for item in existing + template:
            if item not in merged:
                merged.append(item)
        return merged

    if existing in (None, ""):
        return copy.deepcopy(template)

    return copy.deepcopy(existing)


def build_seeded_product_config(
    existing_config: dict | None = None,
    product_asin: str | None = None,
    template_path: str | Path | None = None,
) -> dict:
    """基于默认模板构建/补齐产品配置。"""
    template_config = load_default_product_config(template_path)
    merged_config = merge_product_config(existing_config or {}, template_config)

    own_asins = merged_config.get("own_asins", [])
    if not isinstance(own_asins, list):
        own_asins = []

    normalized_product_asin = (product_asin or "").strip().upper()
    if normalized_product_asin and normalized_product_asin not in own_asins:
        own_asins.append(normalized_product_asin)
    merged_config["own_asins"] = own_asins

    return merged_config
