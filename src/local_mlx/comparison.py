from __future__ import annotations

import json
import math
import platform
import statistics
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

import psutil

from local_mlx.benchmark import RESULT_DIR
from local_mlx.config import get_model
from local_mlx.scoring import category_scores

PRACTICAL_PROFILES = ("vision", "camera", "sports", "hallucination", "agentic")
QUALITY_CATEGORIES = (
    "coding",
    "cybersecurity",
    "reasoning",
    "instruction_following",
    "rag",
    "structured_output",
    "vision",
    "camera",
    "sports",
    "hallucination",
    "agentic",
    "repository",
)
TIER_CATEGORIES = ("camera", "sports", "repository", "hallucination")
TIERS = ("easy", "medium", "hard", "adversarial")


def _read(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _latest(pattern: str, result_dir: Path = RESULT_DIR) -> Path | None:
    paths = sorted(result_dir.glob(pattern))
    return paths[-1] if paths else None


def load_model_results(alias: str, result_dir: Path = RESULT_DIR) -> tuple[list[dict], list[Path]]:
    rows: list[dict] = []
    paths: list[Path] = []
    for profile in PRACTICAL_PROFILES:
        path = _latest(f"*-{alias}-{profile}.jsonl", result_dir)
        if path:
            rows.extend(_read(path))
            paths.append(path)
    for context in sorted(result_dir.glob(f"*-{alias}-ctx2048.jsonl")):
        rows.extend(_read(context))
        paths.append(context)
    # Profiles can intentionally overlap; retain the newest occurrence of a logical case.
    deduped = {(row["benchmark"], row["test"]): row for row in rows}
    return list(deduped.values()), paths


def percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentile_value * len(ordered)) - 1)
    return ordered[index]


def performance(rows: list[dict]) -> dict[str, float | int | str | None]:
    active = [row for row in rows if row.get("supported") is not False]
    ttfts = [row["ttft_seconds"] for row in active if row.get("ttft_seconds") is not None]
    speeds = [row["tokens_per_second"] for row in active if row.get("tokens_per_second")]
    retrieval = [row["download_latency"] for row in active if row.get("retrieval")]
    memory = [row.get("memory", {}) for row in active]
    return {
        "startup_seconds": next((row.get("startup_seconds") for row in active if row.get("startup_seconds")), None),
        "median_ttft": statistics.median(ttfts) if ttfts else None,
        "p95_ttft": percentile(ttfts, 0.95),
        "max_ttft": max(ttfts, default=None),
        "median_tps": statistics.median(speeds) if speeds else None,
        "min_tps": min(speeds, default=None),
        "max_tps": max(speeds, default=None),
        "median_retrieval_ms": statistics.median(retrieval) * 1000 if retrieval else None,
        "peak_system_memory_gb": max((item.get("peak_system_used_gb") or 0 for item in memory), default=0),
        "peak_process_rss_gb": max((item.get("peak_process_rss_gb") or 0 for item in memory), default=0),
        "peak_swap_gb": max((item.get("peak_swap_used_gb") or 0 for item in memory), default=0),
        "worst_pressure": "critical" if any(item.get("worst_pressure") == "critical" for item in memory) else "warn" if any(item.get("worst_pressure") == "warn" for item in memory) else "normal",
        "model_failures": sum(row.get("model_success") is False for row in active),
        "schema_failures": sum(row.get("schema_valid") is False for row in active),
        "skipped": sum(row.get("supported") is False for row in rows),
    }


def difficulty_scores(rows: list[dict]) -> dict[tuple[str, str], float | None]:
    result = {}
    for category in TIER_CATEGORIES:
        for tier in TIERS:
            values = [row["quality_score"] for row in rows if row["benchmark"] == category
                      and row.get("difficulty") == tier and row.get("quality_score") is not None]
            result[(category, tier)] = round(sum(values) / len(values) * 100, 2) if values else None
    return result


def ttft_outliers(rows: list[dict], absolute_floor: float = 3.0) -> tuple[float | None, list[dict]]:
    candidates = [row for row in rows if row.get("ttft_seconds") is not None]
    if not candidates:
        return None, []
    median = statistics.median(row["ttft_seconds"] for row in candidates)
    threshold = max(3 * median, absolute_floor)
    prompt_median = statistics.median(row.get("prompt_tokens") or 0 for row in candidates)
    earliest = min(candidates, key=lambda row: row.get("timestamp", ""))
    outliers = []
    for row in candidates:
        if row["ttft_seconds"] <= threshold:
            continue
        evidence = []
        if row is earliest:
            evidence.append("first measured case after model startup; warm-up is plausible but not isolated")
        if row.get("input_type") == "multi-image":
            evidence.append("multi-image input required additional visual preprocessing")
        elif row.get("input_type") == "image":
            evidence.append("image input required visual preprocessing")
        if (row.get("prompt_tokens") or 0) > max(prompt_median * 2, 1000):
            evidence.append("prompt token count was more than twice the dataset median")
        if not evidence:
            evidence.append("no measured input or retrieval feature establishes a cause")
        outliers.append({
            "benchmark": row["benchmark"], "test": row["test"],
            "input_type": row.get("input_type", "unknown"),
            "prompt_tokens": row.get("prompt_tokens"), "output_tokens": row.get("output_tokens"),
            "ttft_seconds": row["ttft_seconds"], "total_seconds": row.get("model_latency", row.get("total_seconds")),
            "tokens_per_second": row.get("tokens_per_second"), "download_latency": row.get("download_latency"),
            "memory": row.get("memory"), "evidence_based_explanation": "; ".join(evidence),
        })
    return round(threshold, 4), outliers


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def meaningful_winner(a: float | None, b: float | None, *, higher: bool = True,
                      absolute_margin: float = 0.3) -> str:
    if a is None or b is None or abs(a - b) < absolute_margin:
        return "Tie"
    a_wins = a > b if higher else a < b
    return "A" if a_wins else "B"


def workload_winners(scores_a: dict[str, float], scores_b: dict[str, float],
                     alias_a: str, alias_b: str) -> dict[str, str]:
    result = {}
    for category in QUALITY_CATEGORIES:
        winner = meaningful_winner(scores_a.get(category), scores_b.get(category))
        result[category] = alias_a if winner == "A" else alias_b if winner == "B" else "Tie / no meaningful difference"
    return result


def system_metadata() -> dict[str, str]:
    try:
        chip = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        chip = platform.processor() or platform.machine()
    return {
        "chip": chip,
        "memory": f"{round(psutil.virtual_memory().total / 2**30)} GiB",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "mlx": version("mlx"),
        "mlx-lm": version("mlx-lm"),
        "mlx-vlm": version("mlx-vlm"),
        "executable": sys.executable,
    }


def grounding_summary(rows: list[dict]) -> dict[str, float | int | str | None]:
    hallucination = [row for row in rows if row["benchmark"] == "hallucination"]
    sports_evidence = [
        row["metrics"]["evidence_grounding"] for row in rows
        if row["benchmark"] == "sports" and row.get("metrics", {}).get("evidence_grounding") is not None
    ]
    schemas = [row for row in rows if row.get("schema_valid") is not None]
    return {
        "unsupported_claim_rate": (
            sum(row.get("quality_score") != 1 for row in hallucination) / len(hallucination) * 100
            if hallucination else None
        ),
        "appropriate_abstention_rate": (
            sum(row.get("quality_score") == 1 for row in hallucination) / len(hallucination) * 100
            if hallucination else None
        ),
        "mean_sports_evidence_grounding": (
            statistics.mean(sports_evidence) * 100 if sports_evidence else None
        ),
        "schema_valid": sum(row.get("schema_valid") is True for row in schemas),
        "schema_total": len(schemas),
    }


def compare_models(alias_a: str, alias_b: str, result_dir: Path = RESULT_DIR) -> tuple[Path, dict]:
    rows_a, paths_a = load_model_results(alias_a, result_dir)
    rows_b, paths_b = load_model_results(alias_b, result_dir)
    if not rows_a or not rows_b:
        raise ValueError("Both models need practical profiles and a 2048-context baseline before comparison")
    scores_a, scores_b = category_scores(rows_a), category_scores(rows_b)
    perf_a, perf_b = performance(rows_a), performance(rows_b)
    grounding_a, grounding_b = grounding_summary(rows_a), grounding_summary(rows_b)
    tiers_a, tiers_b = difficulty_scores(rows_a), difficulty_scores(rows_b)
    winners = workload_winners(scores_a, scores_b, alias_a, alias_b)
    cases_a = {(row["benchmark"], row["test"]): row for row in rows_a}
    cases_b = {(row["benchmark"], row["test"]): row for row in rows_b}
    regressions = []
    for key in sorted(cases_a.keys() & cases_b.keys()):
        a, b = cases_a[key], cases_b[key]
        qa, qb = a.get("quality_score"), b.get("quality_score")
        if qa is not None and qb is not None and abs(qa - qb) >= 0.25:
            expected = {
                "snow": "schema-valid camera output with weather_visible=snow",
                "camera-absent-person": "explicitly state that no person/evidence is visible",
                "sports-absent-quarterback": "abstain because injury information is absent",
                "api-absent-firmware": "abstain because firmware is absent",
                "nfl-adversarial-noisy-upset": "ignore vanity statistics, acknowledge missing injuries, and calibrate probability",
                "architecture-navigation": "schema-valid answer naming app/auth.py and app/api.py",
                "mixed-json-text-image": "extract HTTP 503 and exact request ID demo-7f3a",
            }.get(key[1], "satisfy the deterministic checks recorded by the case evaluator")
            regressions.append({"category": key[0], "test": key[1], "difficulty": a.get("difficulty"),
                                "expected": expected,
                                alias_a: qa, alias_b: qb, "delta": qb - qa,
                                f"{alias_a}_output": a.get("output", "")[:500],
                                f"{alias_b}_output": b.get("output", "")[:500]})
    threshold_a, outliers_a = ttft_outliers(rows_a)
    threshold_b, outliers_b = ttft_outliers(rows_b)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    output = result_dir / f"{stamp}-{alias_a}-vs-{alias_b}-comparison.md"
    system = system_metadata()
    lines = [f"# {alias_a} vs {alias_b}", "", "## Hardware and runtime", "",
             f"- Chip: {system['chip']}", f"- Unified memory: {system['memory']}",
             f"- Platform: {system['platform']}", f"- Python: {system['python']}",
             f"- MLX: {system['mlx']}; mlx-lm: {system['mlx-lm']}; mlx-vlm: {system['mlx-vlm']}",
             "", "## Model metadata", "",
             "| Model | ID | Runtime | Multimodal | Responses API | Estimated disk GB |",
             "|---|---|---|---|---|---:|"]
    for alias in (alias_a, alias_b):
        cfg = get_model(alias)
        lines.append(f"| {alias} | {cfg.model_id} | {cfg.runtime} | {cfg.multimodal} | {cfg.responses_api} | {cfg.estimated_download_gb} |")
    lines += ["", "## Quality summary", "", f"| Metric / Category | {alias_a} | {alias_b} | Delta ({alias_b}-{alias_a}) | Winner |", "|---|---:|---:|---:|---|"]
    for category in QUALITY_CATEGORIES:
        a, b = scores_a.get(category), scores_b.get(category)
        winner = winners[category]
        lines.append(f"| {category} | {_fmt(a)} | {_fmt(b)} | {_fmt(b - a) if a is not None and b is not None else 'N/A'} | {winner} |")
    performance_metrics = [
        ("startup_seconds", False, 0.5), ("median_ttft", False, 0.15),
        ("p95_ttft", False, 0.25), ("max_ttft", False, 0.5),
        ("median_tps", True, 0.75), ("peak_system_memory_gb", False, 0.5),
        ("peak_swap_gb", False, 0.1),
    ]
    lines += ["", "## Performance", "", f"| Metric | {alias_a} | {alias_b} | Delta | Winner |", "|---|---:|---:|---:|---|"]
    for metric, higher, margin in performance_metrics:
        a, b = perf_a[metric], perf_b[metric]
        mark = meaningful_winner(a, b, higher=higher, absolute_margin=margin) if isinstance(a, (int, float)) and isinstance(b, (int, float)) else "Tie"
        winner = alias_a if mark == "A" else alias_b if mark == "B" else "Tie"
        lines.append(f"| {metric} | {_fmt(a)} | {_fmt(b)} | {_fmt(b - a) if isinstance(a, (int, float)) and isinstance(b, (int, float)) else 'N/A'} | {winner} |")
    lines += ["", "### Additional performance and reliability", "",
              f"| Metric | {alias_a} | {alias_b} |", "|---|---:|---:|",
              f"| throughput_range_tok_s | {_fmt(perf_a['min_tps'])}–{_fmt(perf_a['max_tps'])} | {_fmt(perf_b['min_tps'])}–{_fmt(perf_b['max_tps'])} |",
              f"| median_http_retrieval_ms | {_fmt(perf_a['median_retrieval_ms'])} | {_fmt(perf_b['median_retrieval_ms'])} |",
              f"| peak_process_rss_gb | {_fmt(perf_a['peak_process_rss_gb'])} | {_fmt(perf_b['peak_process_rss_gb'])} |",
              f"| worst_memory_pressure | {perf_a['worst_pressure']} | {perf_b['worst_pressure']} |",
              f"| model_failures | {perf_a['model_failures']} | {perf_b['model_failures']} |",
              f"| schema_failures | {perf_a['schema_failures']} | {perf_b['schema_failures']} |"]
    lines += ["", "## Grounding and abstention", "",
              f"| Metric | {alias_a} | {alias_b} |", "|---|---:|---:|",
              f"| unsupported_claim_rate | {_fmt(grounding_a['unsupported_claim_rate'])}% | {_fmt(grounding_b['unsupported_claim_rate'])}% |",
              f"| appropriate_abstention_rate | {_fmt(grounding_a['appropriate_abstention_rate'])}% | {_fmt(grounding_b['appropriate_abstention_rate'])}% |",
              f"| mean_sports_evidence_grounding | {_fmt(grounding_a['mean_sports_evidence_grounding'])}% | {_fmt(grounding_b['mean_sports_evidence_grounding'])}% |",
              f"| schema_valid | {grounding_a['schema_valid']}/{grounding_a['schema_total']} | {grounding_b['schema_valid']}/{grounding_b['schema_total']} |"]
    lines += ["", "## Difficulty breakdown", "", f"| Category / Difficulty | {alias_a} | {alias_b} | Winner |", "|---|---:|---:|---|"]
    for category in TIER_CATEGORIES:
        for tier in TIERS:
            a, b = tiers_a[(category, tier)], tiers_b[(category, tier)]
            mark = meaningful_winner(a, b, absolute_margin=3.0)
            winner = alias_a if mark == "A" else alias_b if mark == "B" else "Tie"
            lines.append(f"| {category} / {tier} | {_fmt(a)} | {_fmt(b)} | {winner} |")
    lines += ["", "## Case-level material differences", ""]
    if regressions:
        for item in regressions:
            lines += [f"### {item['category']} / {item['test']} ({item['difficulty']})", "",
                      f"- {alias_a}: {item[alias_a]}", f"- {alias_b}: {item[alias_b]}",
                      f"- Expected: {item['expected']}",
                      f"- Delta ({alias_b}-{alias_a}): {item['delta']:.3f}",
                      f"- {alias_a} output: `{item[f'{alias_a}_output']}`",
                      f"- {alias_b} output: `{item[f'{alias_b}_output']}`", ""]
    else:
        lines.append("No case differed by the material threshold of 0.25 quality points.")
    lines += ["", "## TTFT outliers", "",
              f"Rule: TTFT > max(3 × model median, 3.0 seconds). {alias_a} threshold={threshold_a}; {alias_b} threshold={threshold_b}."]
    for alias, items in ((alias_a, outliers_a), (alias_b, outliers_b)):
        lines += ["", f"### {alias}", ""]
        if not items:
            lines.append("No flagged cases.")
        for item in items:
            lines.append(f"- `{item['benchmark']}/{item['test']}`: {item['input_type']}, prompt={item['prompt_tokens']} tokens, output={item['output_tokens']} tokens, TTFT={item['ttft_seconds']}s, runtime={item['total_seconds']}s, throughput={item['tokens_per_second']} tok/s. Evidence: {item['evidence_based_explanation']}.")
    lines += ["", "## Workload routing", "", "A quality-score difference below 0.30/10 is a tie; difficulty-tier differences below 3 percentage points are ties."]
    lines.extend(f"- {category}: {winner}" for category, winner in winners.items())
    lines += ["", "## Aggregate methodology finding", "",
              "The earlier Qwen 8.41/10 was intentional, not a scoring bug. It was the unweighted mean of six high quality categories plus speed (5.05) and system-wide memory efficiency (3.75). Unsupported categories are omitted; model failures score zero; infrastructure failures are not assigned model-quality scores.",
              "", "## Source result files", ""]
    lines.extend(f"- {path}" for path in paths_a + paths_b)
    output.write_text("\n".join(lines) + "\n")
    data = {"system": system, "scores": {alias_a: scores_a, alias_b: scores_b},
            "performance": {alias_a: perf_a, alias_b: perf_b},
            "grounding": {alias_a: grounding_a, alias_b: grounding_b},
            "difficulty": {alias_a: tiers_a, alias_b: tiers_b},
            "regressions": regressions, "outliers": {alias_a: outliers_a, alias_b: outliers_b},
            "winners": winners}
    return output, data
