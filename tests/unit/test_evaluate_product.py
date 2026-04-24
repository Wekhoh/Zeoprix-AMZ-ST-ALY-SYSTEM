from scripts.evaluate_product import (
    compute_objective_score,
    parse_alignment_summary,
    parse_pytest_summary,
    summarize_llm_scores,
)


def test_parse_pytest_summary_extracts_counts_and_pass_rate():
    text = "269 passed, 10 skipped, 2 warnings in 50.03s"

    summary = parse_pytest_summary(text)

    assert summary["passed"] == 269
    assert summary["skipped"] == 10
    assert summary["warnings"] == 2
    assert summary["failed"] == 0
    assert summary["pass_rate"] == 100.0


def test_parse_alignment_summary_extracts_dual_rates_and_conflicts():
    text = """
=== 广告组级对齐 ===
对齐率: 107/107 = 100.0%

=== 汇总级对齐 ===
对齐率: 398/398 = 100.0%
源数据冲突标记: 5
"""

    summary = parse_alignment_summary(text)

    assert summary["campaign_rate"] == 100.0
    assert summary["aggregate_rate"] == 100.0
    assert summary["source_conflicts"] == 5


def test_parse_alignment_summary_tolerates_garbled_non_utf8_labels():
    text = (
        """\n=== 乱码一 ===\n字段甲: 107\n对齐率: 107/107 = 100.0%\n\n=== 乱码二 ===\n字段乙: 398\n对齐率: 398/398 = 100.0%\n乱七八糟: 5\n""".replace(
            "对齐率", "乱码率"
        )
        .replace("字段甲", "错别字")
        .replace("字段乙", "再错")
    )

    summary = parse_alignment_summary(text)

    assert summary["campaign_rate"] == 100.0
    assert summary["aggregate_rate"] == 100.0
    assert summary["source_conflicts"] == 5


def test_parse_alignment_summary_marks_missing_section_rate_as_none():
    text = """
=== 广告组级对齐 ===
期望行数: 3
系统结果数: 461
没有可用于对齐的结果。

=== 汇总级对齐 ===
期望行数: 398
系统结果数: 398
对齐率: 398/398 = 100.0%
剩余不匹配: 0
未命中系统结果: 0
源数据冲突标记: 5
"""

    summary = parse_alignment_summary(text)

    assert summary["campaign_rate"] is None
    assert summary["aggregate_rate"] == 100.0
    assert summary["source_conflicts"] == 5


def test_compute_objective_score_and_llm_average_remain_high_for_clean_baseline():
    pytest_summary = {"pass_rate": 100.0, "warnings": 2}
    alignment_summary = {
        "campaign_rate": 100.0,
        "aggregate_rate": 100.0,
        "source_conflicts": 5,
    }
    llm_summary = summarize_llm_scores({"ux": 92, "workflow": 94, "governance": 91})

    objective = compute_objective_score(pytest_summary, alignment_summary)

    assert objective >= 99.0
    assert llm_summary["average"] == 92.33


def test_compute_objective_score_uses_available_alignment_rates_only():
    pytest_summary = {"pass_rate": 100.0, "warnings": 2}
    alignment_summary = {
        "campaign_rate": None,
        "aggregate_rate": 100.0,
        "source_conflicts": 5,
    }

    objective = compute_objective_score(pytest_summary, alignment_summary)

    assert objective >= 99.0
