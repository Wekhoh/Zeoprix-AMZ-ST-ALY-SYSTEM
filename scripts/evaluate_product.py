from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_PYTEST_COUNT_RE = re.compile(r"(?P<count>\d+) (?P<label>passed|failed|errors|skipped|warnings)")
_ALIGNMENT_RATE_RE = re.compile(r"=\s*(?P<rate>\d+(?:\.\d+)?)%")
_TRAILING_COUNT_RE = re.compile(r":\s*(?P<count>\d+)\s*$", re.MULTILINE)
_SECTION_RE = re.compile(
    r"^===\s*(?P<title>.+?)\s*===\s*$\n(?P<body>.*?)(?=^===\s*.+?\s*===\s*$|\Z)",
    re.MULTILINE | re.DOTALL,
)


def parse_pytest_summary(text: str) -> dict[str, Any]:
    counts = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "warnings": 0,
    }
    for match in _PYTEST_COUNT_RE.finditer(text):
        counts[match.group("label")] = int(match.group("count"))

    executed = counts["passed"] + counts["failed"] + counts["errors"]
    pass_rate = round((counts["passed"] / executed) * 100, 2) if executed else 0.0
    return {**counts, "executed": executed, "pass_rate": pass_rate}


def parse_alignment_summary(text: str) -> dict[str, Any]:
    campaign_rate: float | None = None
    aggregate_rate: float | None = None
    source_conflicts = 0

    section_matches = list(_SECTION_RE.finditer(text))
    if section_matches:
        for match in section_matches:
            title = match.group("title")
            body = match.group("body")
            rate_match = _ALIGNMENT_RATE_RE.search(body)
            rate = float(rate_match.group("rate")) if rate_match else None
            if "广告组" in title:
                campaign_rate = rate
            elif "汇总" in title:
                aggregate_rate = rate
                trailing_counts = [int(item.group("count")) for item in _TRAILING_COUNT_RE.finditer(body)]
                source_conflicts = trailing_counts[-1] if trailing_counts else 0

    if campaign_rate is None and aggregate_rate is None:
        rates = [float(match.group("rate")) for match in _ALIGNMENT_RATE_RE.finditer(text)]
        campaign_rate = rates[0] if len(rates) >= 1 else None
        aggregate_rate = rates[1] if len(rates) >= 2 else None
        trailing_counts = [int(match.group("count")) for match in _TRAILING_COUNT_RE.finditer(text)]
        source_conflicts = trailing_counts[-1] if trailing_counts else 0

    return {
        "campaign_rate": campaign_rate,
        "aggregate_rate": aggregate_rate,
        "source_conflicts": source_conflicts,
    }


def summarize_llm_scores(scores: dict[str, float]) -> dict[str, Any]:
    normalized = {key: round(float(value), 2) for key, value in scores.items()}
    average = round(sum(normalized.values()) / len(normalized), 2) if normalized else 0.0
    return {"scores": normalized, "average": average}


def compute_objective_score(
    pytest_summary: dict[str, Any], alignment_summary: dict[str, Any]
) -> float:
    test_score = float(pytest_summary.get("pass_rate", 0.0))
    available_alignment_rates = [
        float(rate)
        for rate in (
            alignment_summary.get("campaign_rate"),
            alignment_summary.get("aggregate_rate"),
        )
        if rate is not None
    ]
    alignment_score = (
        sum(available_alignment_rates) / len(available_alignment_rates)
        if available_alignment_rates
        else 0.0
    )
    warning_penalty = min(float(pytest_summary.get("warnings", 0)) * 0.25, 5.0)
    conflict_penalty = max(float(alignment_summary.get("source_conflicts", 0)) - 5.0, 0.0) * 0.2
    objective = (test_score * 0.55) + (alignment_score * 0.45) - warning_penalty - conflict_penalty
    return round(max(objective, 0.0), 2)


def compute_total_score(objective_score: float, llm_average: float) -> float:
    return round((objective_score * 0.6) + (llm_average * 0.4), 2)


def _run_command(command: list[str], cwd: Path, extra_env: dict[str, str] | None = None) -> str:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        raise RuntimeError(f"命令执行失败: {' '.join(command)}\n{output}")
    return output


def _append_history(history_file: Path, payload: dict[str, Any]) -> None:
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with history_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _parse_llm_scores(raw_scores: list[str]) -> dict[str, float]:
    parsed: dict[str, float] = {}
    for item in raw_scores:
        if "=" not in item:
            raise ValueError(f"LLM 评分参数格式错误: {item}，应为 维度=分数")
        key, value = item.split("=", 1)
        parsed[key.strip()] = float(value)
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行产品化评估并输出总分。")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--llm-score", action="append", default=[], help="传入 LLM 评审分数，格式如 ux=92")
    parser.add_argument("--llm-review-file", help="包含 LLM 评审分数 JSON 的文件路径")
    parser.add_argument("--history-file", default="tasks/eval_history.jsonl")
    parser.add_argument("--change-note", default="", help="记录本轮改动摘要")
    parser.add_argument("--json", action="store_true", help="只输出 JSON 结果")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    pytest_output = _run_command([sys.executable, "-m", "pytest", "-q"], repo_root, extra_env={"DEBUG": "true"})
    alignment_output = _run_command([sys.executable, "analyze_mismatches.py"], repo_root)

    pytest_summary = parse_pytest_summary(pytest_output)
    alignment_summary = parse_alignment_summary(alignment_output)

    llm_scores = _parse_llm_scores(args.llm_score)
    if args.llm_review_file:
        llm_scores.update(json.loads(Path(args.llm_review_file).read_text(encoding="utf-8")))
    llm_summary = summarize_llm_scores(llm_scores)

    objective_score = compute_objective_score(pytest_summary, alignment_summary)
    total_score = compute_total_score(objective_score, llm_summary["average"])

    result = {
        "pytest": pytest_summary,
        "alignment": alignment_summary,
        "llm_review": llm_summary,
        "scores": {
            "objective": objective_score,
            "total": total_score,
        },
        "thresholds": {
            "total_over_90": total_score > 90.0,
            "llm_average_over_90": llm_summary["average"] > 90.0,
        },
        "change_note": args.change_note,
    }

    _append_history(repo_root / args.history_file, result)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Objective score: {objective_score:.2f}")
        print(f"LLM review average: {llm_summary['average']:.2f}")
        print(f"Total score: {total_score:.2f}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
