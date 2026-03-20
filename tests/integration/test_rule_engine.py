"""
集成测试：规则引擎
测试 聚合→规则分析→结果验证 + 人工审核覆盖
"""


class TestRuleEngineIntegration:
    """规则引擎集成测试"""

    def test_analyze_produces_results_for_all_terms(self, db_with_data, product_id):
        """测试分析覆盖所有搜索词"""
        from src.rules.engine import analyze_search_terms

        results = analyze_search_terms(db_with_data, product_id)

        assert len(results) == 7  # 7条搜索词应全部有结果
        terms = [r.term for r in results]
        assert "neck massager" in terms
        assert "travel pillow for airplane" in terms
        assert "pillow" in terms

    def test_irrelevant_terms_get_negative_action(self, db_with_data, product_id):
        """测试不相关词被标记为否定"""
        from src.rules.engine import analyze_search_terms

        results = analyze_search_terms(db_with_data, product_id)

        massager_result = next(r for r in results if r.term == "neck massager")
        # massager 在 irrelevant_keywords 中，应被标记为否定类
        assert "negative" in massager_result.action_type

    def test_generic_terms_get_negative_action(self, db_with_data, product_id):
        """测试泛词被标记为否定"""
        from src.rules.engine import analyze_search_terms

        results = analyze_search_terms(db_with_data, product_id)

        pillow_result = next(r for r in results if r.term == "pillow")
        assert "negative" in pillow_result.action_type

    def test_car_terms_get_negative_action(self, db_with_data, product_id):
        """测试汽车词被标记为否定"""
        from src.rules.engine import analyze_search_terms

        results = analyze_search_terms(db_with_data, product_id)

        car_result = next(r for r in results if r.term == "car neck pillow")
        assert "negative" in car_result.action_type

    def test_core_keywords_are_protected(self, db_with_data, product_id):
        """测试核心关键词不被误否定"""
        from src.rules.engine import analyze_search_terms

        results = analyze_search_terms(db_with_data, product_id)

        core_result = next(r for r in results if r.term == "travel neck pillow")
        # 核心词不应被否定
        assert "negative" not in core_result.action_type

    def test_relevance_levels_are_assigned(self, db_with_data, product_id):
        """测试相关性等级正确分配"""
        from src.data.models import RelevanceLevel
        from src.rules.engine import RuleEngine

        engine = RuleEngine(db_with_data, product_id)

        # 核心词应为STRONG
        rel = engine._get_term_relevance("travel pillow")
        assert rel == RelevanceLevel.STRONG

        # 泛词应为GENERIC
        rel = engine._get_term_relevance("pillow")
        assert rel == RelevanceLevel.GENERIC

        # 不相关词应为IRRELEVANT
        rel = engine._get_term_relevance("neck massager")
        assert rel == RelevanceLevel.IRRELEVANT

        # 汽车词应为CAR
        rel = engine._get_term_relevance("car neck pillow")
        assert rel == RelevanceLevel.CAR

    def test_manual_review_overrides_auto_relevance(self, db_with_data, product_id):
        """测试人工审核覆盖自动检测的相关性"""
        from src.data.models import RelevanceLevel
        from src.rules.engine import RuleEngine

        # "neck massager" 自动检测为 IRRELEVANT
        engine = RuleEngine(db_with_data, product_id)
        auto_rel = engine._get_term_relevance("neck massager")
        assert auto_rel == RelevanceLevel.IRRELEVANT

        # 人工标记为强相关核心词
        db_with_data.upsert_manual_review(
            product_id=product_id,
            term="neck massager",
            relevance="strong_core",
            scope="global",
            relevance_notes="test override",
        )

        # 重新加载引擎，人工标记应覆盖自动检测
        engine2 = RuleEngine(db_with_data, product_id)
        manual_rel = engine2._get_term_relevance("neck massager")
        assert manual_rel == "strong_core"

    def test_confidence_levels_vary_by_rule_match(self, db_with_data, product_id):
        """测试置信度根据规则匹配类型变化"""
        from src.rules.engine import analyze_search_terms, Confidence

        results = analyze_search_terms(db_with_data, product_id)

        for result in results:
            if result.need_ai_judgment:
                assert result.confidence <= Confidence.AI_JUDGMENT
            elif result.triggered_rule == "无匹配规则":
                assert result.confidence == Confidence.DEFAULT

    def test_action_type_categorization(self, db_with_data, product_id):
        """测试动作类型正确分类"""
        from src.rules.engine import analyze_search_terms

        results = analyze_search_terms(db_with_data, product_id)

        action_types = {r.action_type for r in results}
        # 至少应包含否定类和观察类
        has_negative = any("negative" in at for at in action_types)
        has_observe_or_other = any(
            at in ("observe", "evaluate", "continue_observe", "other") or "manual" in at
            for at in action_types
        )
        assert has_negative, f"应有否定类动作，实际: {action_types}"
        assert has_observe_or_other, f"应有观察/手动类动作，实际: {action_types}"

    def test_campaign_analysis_preserves_campaign_dimension(
        self, db_with_data, product_id
    ):
        """测试按活动分析保留活动维度"""
        from src.rules.engine import analyze_search_terms_by_campaign

        results = analyze_search_terms_by_campaign(db_with_data, product_id)

        assert len(results) > 0
        # 每条结果应有campaign_id和campaign_name
        for r in results:
            assert r.campaign_id is not None
            assert r.campaign_name != ""
        # 手动类动作应有auto_action; 否定/观察类auto_action为None（设计如此）
        manual_results = [r for r in results if "manual" in r.action_type]
        for r in manual_results:
            assert r.auto_action is not None
