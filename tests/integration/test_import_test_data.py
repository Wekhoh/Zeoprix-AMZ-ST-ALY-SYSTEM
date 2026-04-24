"""集成测试：验收数据恢复脚本的产品配置注入。"""

import pandas as pd

from scripts.import_test_data import (
    DEFAULT_CONFIG_TEMPLATE_PATH,
    ensure_product_config,
    load_config_template,
)
from src.data.models import ActionType
from src.rules.engine import RuleEngine


class TestImportTestDataConfigSeed:
    """验证恢复脚本会补齐产品配置。"""

    def test_restore_seeds_template_into_empty_product_config(self, db):
        product_id = db.create_product(
            name="恢复验证产品",
            asin="B0REAL12345",
            config={},
        )

        template_config = load_config_template(DEFAULT_CONFIG_TEMPLATE_PATH)
        changed = ensure_product_config(
            db=db,
            product_id=product_id,
            product_asin="B0REAL12345",
            template_config=template_config,
        )

        product = db.get_product(product_id)
        config = product["config"]

        assert changed is True
        assert config["core_keywords"]
        assert "travel neck pillow for car" in config["core_keywords"]
        assert "microbead" in config["keyword_libraries"]["weak_category_keywords"]
        assert "microbead" not in config["keyword_libraries"]["irrelevant_keywords"]
        assert "travelon" in config["keyword_libraries"]["weak_category_keywords"]
        assert "B0FCSM9THX" in config["own_variants"]
        assert "B0REAL12345" in config["own_asins"]
        assert config["thresholds"]["min_clicks_for_analysis"] == 20

    def test_restore_preserves_existing_config_and_unions_lists(self, db):
        product_id = db.create_product(
            name="已有配置产品",
            asin="B0KEEP12345",
            config={
                "target_acos": 0.33,
                "core_keywords": ["custom core keyword"],
                "own_variants": ["B0CUSTOMVAR"],
                "keyword_libraries": {
                    "generic_keywords": ["already generic"],
                },
                "thresholds": {
                    "bad_cvr": 0.07,
                },
            },
        )

        template_config = load_config_template(DEFAULT_CONFIG_TEMPLATE_PATH)
        changed = ensure_product_config(
            db=db,
            product_id=product_id,
            product_asin="B0KEEP12345",
            template_config=template_config,
        )

        product = db.get_product(product_id)
        config = product["config"]

        assert changed is True
        assert config["target_acos"] == 0.33
        assert config["thresholds"]["bad_cvr"] == 0.07
        assert "custom core keyword" in config["core_keywords"]
        assert "travel pillow" in config["core_keywords"]
        assert "already generic" in config["keyword_libraries"]["generic_keywords"]
        assert "pillow" in config["keyword_libraries"]["generic_keywords"]
        assert "B0CUSTOMVAR" in config["own_variants"]
        assert "B0FCSM9THX" in config["own_variants"]
        assert "B0KEEP12345" in config["own_asins"]

    def test_seeded_config_contains_alignment_overrides(self, db):
        product_id = db.create_product(
            name="模板检查产品",
            asin="B0ALIGN1234",
            config={},
        )

        template_config = load_config_template(DEFAULT_CONFIG_TEMPLATE_PATH)
        ensure_product_config(
            db=db,
            product_id=product_id,
            product_asin="B0ALIGN1234",
            template_config=template_config,
        )

        config = db.get_product(product_id)["config"]
        libraries = config["keyword_libraries"]

        assert "microbead" in libraries["weak_category_keywords"]
        assert "microbead" not in libraries["irrelevant_keywords"]
        assert "airplane" not in libraries["irrelevant_keywords"]
        assert "cover" not in libraries["irrelevant_keywords"]
        assert "neck support" in libraries["weak_exact_keywords"]
        assert "cover neck pillow" in libraries["weak_exact_keywords"]
        assert "neck pillow cover" in libraries["weak_exact_keywords"]
        assert "pillow covers" in libraries["weak_exact_keywords"]
        assert "neck support office" in libraries["weak_exact_keywords"]
        assert "pillows for airplane" in config["core_keywords"]
        assert "travel pillows for airplanes" in config["core_keywords"]
        assert "neck travel" in config["related_keywords"]

    def test_seeded_config_drives_alignment_edge_cases(self, db):
        product_id = db.create_product(
            name="边界词对齐产品",
            asin="B0EDGE12345",
            config={},
        )

        template_config = load_config_template(DEFAULT_CONFIG_TEMPLATE_PATH)
        ensure_product_config(
            db=db,
            product_id=product_id,
            product_asin="B0EDGE12345",
            template_config=template_config,
        )

        engine = RuleEngine(db=db, product_id=product_id)
        df = pd.DataFrame(
            [
                {
                    "term": "microbead neck pillow",
                    "term_type": "keyword",
                    "total_clicks": 1,
                    "total_orders": 0,
                    "total_spend": 2.06,
                    "conversion_rate": 0.0,
                    "acos": 0.0,
                },
                {
                    "term": "neck support",
                    "term_type": "keyword",
                    "total_clicks": 2,
                    "total_orders": 0,
                    "total_spend": 6.42,
                    "conversion_rate": 0.0,
                    "acos": 0.0,
                },
                {
                    "term": "neck pillow airplane",
                    "term_type": "keyword",
                    "total_clicks": 20,
                    "total_orders": 2,
                    "total_spend": 40.0,
                    "conversion_rate": 0.10,
                    "acos": 0.6,
                },
                {
                    "term": "neck pillow with washable cover",
                    "term_type": "keyword",
                    "total_clicks": 2,
                    "total_orders": 1,
                    "total_spend": 6.98,
                    "conversion_rate": 0.5,
                    "acos": 0.29,
                },
                {
                    "term": "pillows for airplane",
                    "term_type": "keyword",
                    "total_clicks": 10,
                    "total_orders": 1,
                    "total_spend": 5.71,
                    "conversion_rate": 0.10,
                    "acos": 0.24,
                },
                {
                    "term": "travel pillows for airplanes",
                    "term_type": "keyword",
                    "total_clicks": 31,
                    "total_orders": 2,
                    "total_spend": 96.79,
                    "conversion_rate": 2 / 31,
                    "acos": 1.79,
                },
                {
                    "term": "cover neck pillow",
                    "term_type": "keyword",
                    "total_clicks": 2,
                    "total_orders": 0,
                    "total_spend": 6.0,
                    "conversion_rate": 0.0,
                    "acos": 0.0,
                },
                {
                    "term": "neck pillow cover",
                    "term_type": "keyword",
                    "total_clicks": 2,
                    "total_orders": 0,
                    "total_spend": 6.0,
                    "conversion_rate": 0.0,
                    "acos": 0.0,
                },
                {
                    "term": "neck support office",
                    "term_type": "keyword",
                    "total_clicks": 1,
                    "total_orders": 0,
                    "total_spend": 2.0,
                    "conversion_rate": 0.0,
                    "acos": 0.0,
                },
                {
                    "term": "pillow covers",
                    "term_type": "keyword",
                    "total_clicks": 1,
                    "total_orders": 0,
                    "total_spend": 2.0,
                    "conversion_rate": 0.0,
                    "acos": 0.0,
                },
                {
                    "term": "neck travel",
                    "term_type": "keyword",
                    "total_clicks": 1,
                    "total_orders": 1,
                    "total_spend": 3.49,
                    "conversion_rate": 1.0,
                    "acos": 0.15,
                },
            ]
        )

        results = {item.term: item for item in engine.analyze(df)}

        assert (
            results["microbead neck pillow"].action_type == ActionType.NEGATIVE_PHRASE
        )
        assert results["neck support"].action_type == ActionType.NEGATIVE_EXACT
        assert (
            results["neck pillow airplane"].action_type
            == ActionType.MANUAL_EXACT_NO_NEG
        )
        assert (
            results["neck pillow with washable cover"].action_type
            == ActionType.MANUAL_EXACT_NO_NEG
        )
        assert (
            results["pillows for airplane"].action_type
            == ActionType.MANUAL_EXACT_NO_NEG
        )
        assert (
            results["travel pillows for airplanes"].action_type
            == ActionType.MANUAL_EXACT_NO_NEG
        )
        assert results["cover neck pillow"].action_type == ActionType.NEGATIVE_EXACT
        assert results["neck pillow cover"].action_type == ActionType.NEGATIVE_EXACT
        assert results["neck support office"].action_type == ActionType.NEGATIVE_EXACT
        assert results["pillow covers"].action_type == ActionType.NEGATIVE_EXACT
        assert results["neck travel"].action_type == ActionType.MANUAL_EXACT_NO_NEG
