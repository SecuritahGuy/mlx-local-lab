from __future__ import annotations

import json
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

import psutil
import yaml

from local_mlx.client import LocalLLM
from local_mlx.config import ROOT, get_model
from local_mlx.models import macos_memory_pressure, memory_snapshot, read_state
from local_mlx.schemas import SecurityReview

PROMPT_DIR = ROOT / "benchmarks" / "prompts"
DOCUMENT_DIR = ROOT / "benchmarks" / "documents"
RESULT_DIR = ROOT / "benchmarks" / "results"
LEGACY_CATEGORIES = (
    "coding",
    "cybersecurity",
    "instruction_following",
    "rag",
    "reasoning",
    "structured_output",
)

LEGACY_CHECKS: dict[str, list[tuple[str, ...]]] = {
    "implement_function": [("def merge_intervals",), ("valueerror",), ("pytest", "def test_"), ("o(n log n)", "complexity")],
    "fix_broken_function": [("yield",), ("valueerror",), ("n <= 0", "n < 1"), ("iter(", "iterator")],
    "code_review": [("mutable default", "cache={}"), ("race", "concurr"), ("timeout", "status")],
    "refactor": [("def ",), ("seen", "dict.fromkeys"), ("none",)],
    "explain_unfamiliar": [("reverse",), ("predicate",), ("default",), ("stopiteration", "next(")],
    "cloud_threat_model": [("trust bound",), ("rate limit", "abuse"), ("log", "detect"), ("least privilege",)],
    "sanitized_auth_logs": [("hypoth",), ("uncertain",), ("token",), ("203.0.113.8",)],
    "control_gaps": [("shared",), ("restore",), ("retention",), ("egress",)],
    "azure_architecture": [("managed identity", "key vault"), ("private", "public sql"), ("least privilege", "contributor"), ("diagnostic", "logging")],
    "technical_multistep": [("30",), ("600",), ("latency", "concurrency")],
    "architecture_tradeoffs": [("sqlite",), ("postgres",), ("audit", "append-only")],
    "constraint_satisfaction": [("a",), ("b",), ("c",), ("d",), ("schedule", "slot")],
    "incomplete_debugging": [("connection",), ("rank",), ("test",), ("uncertain", "missing")],
}


class MemorySampler:
    def __init__(self, pid: int | None):
        self.pid = pid
        self.samples: list[dict[str, Any]] = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        process = psutil.Process(self.pid) if self.pid else None
        while not self.stop_event.wait(0.25):
            row = memory_snapshot()
            if process:
                try:
                    row["process_rss_gb"] = round(process.memory_info().rss / 2**30, 3)
                except psutil.Error:
                    pass
            self.samples.append(row)

    def __enter__(self) -> Self:
        self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop_event.set()
        self.thread.join(1)

    def summary(self) -> dict[str, Any]:
        return {
            "peak_system_used_gb": max((s["used_gb"] for s in self.samples), default=None),
            "peak_process_rss_gb": max(
                (s.get("process_rss_gb", 0) for s in self.samples), default=None
            ),
            "peak_swap_used_gb": max((s["swap_used_gb"] for s in self.samples), default=None),
            "worst_pressure": next(
                (p for p in ("critical", "warn") if any(s["pressure"] == p for s in self.samples)),
                "normal",
            ),
        }


def load_cases(categories: list[str] | None = None) -> list[dict[str, Any]]:
    cases = []
    selected = categories or list(LEGACY_CATEGORIES)
    for category in selected:
        data = yaml.safe_load((PROMPT_DIR / f"{category}.yaml").read_text())
        for case in data["tests"]:
            if document_name := case.pop("document", None):
                document = (DOCUMENT_DIR / document_name).read_text().strip()
                case["prompt"] = case["prompt"].replace("{document}", document)
            cases.append({"benchmark": category, **case})
    return cases


def apply_context(case: dict[str, Any], context_size: int) -> dict[str, Any]:
    case = dict(case)
    if case["benchmark"] != "rag":
        return case
    prompt = case["prompt"]
    question_at = prompt.rfind("Question:")
    prefix, question = (prompt[:question_at], prompt[question_at:]) if question_at >= 0 else (prompt, "")
    target_chars = max(0, int((context_size - 450) * 4.25) - len(prompt))
    notes = []
    index = 1
    while sum(len(note) for note in notes) < target_chars:
        notes.append(
            f"[A{index:05d}] Archive padding note {index}: this synthetic tokenizer-length record "
            "contains no facts about Project Cedar, deployment schedules, people, approvals, "
            "thresholds, hosting providers, or cloud regions. Ignore it when answering.\n"
        )
        index += 1
    case["prompt"] = prefix + "\n[BEGIN IRRELEVANT ARCHIVE PADDING]\n" + "".join(notes) + "[END IRRELEVANT ARCHIVE PADDING]\n" + question
    case["context_target"] = context_size
    case["approximate_input_chars"] = len(case["prompt"])
    return case


def score_legacy(case: dict[str, Any], output: str, schema_valid: bool | None) -> float:
    lowered = output.lower()
    name = case["name"]
    if case.get("schema") == "SecurityReview":
        return float(schema_valid is True)
    if name == "exact_format":
        return float(output.strip().splitlines() == ["alpha", "beta", "gamma"])
    if name == "conflicting_untrusted_text":
        words = output.split()
        return (float(len(words) <= 20) + float("secret" not in lowered) + float("migration" in lowered)) / 3
    if name == "constrained_answer":
        count = len(output.split())
        return (float(25 <= count <= 35) + float("latency" in lowered) + float("durability" in lowered) + float("always" not in lowered and "never" not in lowered)) / 4
    if case["benchmark"] == "rag":
        if name == "direct_answer":
            return sum(("tuesday" in lowered, "15:00" in lowered, "p1" in lowered)) / 3
        if name == "combine_passages":
            return sum(("priya" in lowered, "service owner" in lowered, "sre" in lowered, "p2" in lowered, "p3" in lowered)) / 5
        if name == "unanswerable":
            return float("not in document" in lowered)
    checks = LEGACY_CHECKS.get(name)
    if not checks:
        return float(bool(output.strip()))
    return sum(any(option in lowered for option in alternatives) for alternatives in checks) / len(checks)


def run_case(client: LocalLLM, alias: str, case: dict[str, Any], context_size: int) -> dict:
    model = get_model(alias)
    state = read_state()
    if not state or state["alias"] != alias:
        raise RuntimeError(f"Start {alias} before benchmarking it")
    if macos_memory_pressure() in {"warn", "critical"}:
        raise RuntimeError("Memory pressure is already elevated; benchmark aborted")
    start = time.perf_counter()
    first_token: float | None = None
    text_parts: list[str] = []
    usage = None
    error = None
    sampler = MemorySampler(state["pid"])
    try:
        with sampler:
            stream = client.stream(
                case["prompt"], temperature=model.temperature, max_tokens=case.get("max_tokens", 512)
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    if first_token is None:
                        first_token = time.perf_counter()
                    text_parts.append(delta)
                if getattr(chunk, "usage", None):
                    usage = chunk.usage
                if macos_memory_pressure() == "critical":
                    raise RuntimeError("Critical macOS memory pressure during inference")
        success = True
    except Exception as exc:  # noqa: BLE001 - failures are benchmark data, not control flow
        success = False
        error = f"{type(exc).__name__}: {exc}"
    end = time.perf_counter()
    output = "".join(text_parts)
    schema_valid: bool | None = None
    if case.get("schema") == "SecurityReview":
        try:
            SecurityReview.model_validate_json(output)
            schema_valid = True
        except ValueError:
            schema_valid = False
    output_tokens = getattr(usage, "completion_tokens", None)
    elapsed = end - start
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "model": alias,
        "model_id": model.model_id,
        "runtime": model.runtime,
        "benchmark": case["benchmark"],
        "test": case["name"],
        "difficulty": case.get("difficulty", "medium"),
        "input_type": "text",
        "context_size": context_size,
        "context_target": case.get("context_target"),
        "approximate_input_chars": case.get("approximate_input_chars", len(case["prompt"])),
        "temperature": model.temperature,
        "max_tokens": case.get("max_tokens", 512),
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": output_tokens,
        "total_tokens": getattr(usage, "total_tokens", None),
        "ttft_seconds": round(first_token - start, 4) if first_token else None,
        "total_seconds": round(elapsed, 4),
        "tokens_per_second": round(output_tokens / elapsed, 3) if output_tokens else None,
        "success": success,
        "schema_valid": schema_valid,
        "quality_score": score_legacy(case, output, schema_valid) if success else 0.0,
        "memory": sampler.summary(),
        "output": output,
        "error": error,
    }


def write_results(alias: str, rows: list[dict[str, Any]], context_size: int | None = None) -> tuple[Path, Path]:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    suffix = f"-ctx{context_size}" if context_size else ""
    jsonl = RESULT_DIR / f"{stamp}-{alias}{suffix}.jsonl"
    summary = RESULT_DIR / f"{stamp}-{alias}{suffix}.md"
    jsonl.write_text("".join(json.dumps(row) + "\n" for row in rows))
    ok = sum(row["success"] for row in rows)
    lines = [
        f"# Benchmark: {alias}",
        "",
        f"Successful: {ok}/{len(rows)}",
        "",
        "| Category | Test | Tier | TTFT (s) | tok/s | Quality | Prompt tokens | Schema | Peak RSS GB |",
        "|---|---|---|---:|---:|---:|---:|---|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['benchmark']} | {row['test']} | {row['difficulty']} | {row['ttft_seconds'] or '-'} | "
            f"{row['tokens_per_second'] or '-'} | {row['quality_score']} | {row['prompt_tokens'] or '-'} | "
            f"{row['schema_valid'] if row['schema_valid'] is not None else '-'} | "
            f"{row['memory']['peak_process_rss_gb'] or '-'} |"
        )
    lines += ["", "Qualitative scoring is intentionally left to human review of the JSONL outputs."]
    summary.write_text("\n".join(lines) + "\n")
    return jsonl, summary


def run_suite(alias: str, context_size: int, categories: list[str] | None = None) -> tuple[Path, Path]:
    if context_size not in {2048, 8192, 16384}:
        raise ValueError("Context size must be 2048, 8192, or 16384")
    client = LocalLLM()
    rows = [run_case(client, alias, apply_context(case, context_size), context_size) for case in load_cases(categories)]
    return write_results(alias, rows, context_size)


def comparison_report(paths: list[Path]) -> Path:
    rows = [json.loads(line) for path in paths for line in path.read_text().splitlines()]
    by_model: dict[str, list[dict]] = {}
    for row in rows:
        by_model.setdefault(row["model"], []).append(row)
    out = RESULT_DIR / f"{datetime.now(UTC):%Y%m%d-%H%M%S}-comparison.md"
    lines = [
        "# Model comparison",
        "",
        "| Model | Success | Median tok/s | Median TTFT | Peak RSS GB |",
        "|---|---:|---:|---:|---:|",
    ]
    for model, items in by_model.items():
        speeds = sorted(x["tokens_per_second"] for x in items if x["tokens_per_second"])
        ttfts = sorted(x["ttft_seconds"] for x in items if x["ttft_seconds"])
        median = lambda xs: xs[len(xs) // 2] if xs else "-"
        peak = max((x["memory"]["peak_process_rss_gb"] or 0 for x in items), default=0)
        lines.append(f"| {model} | {sum(x['success'] for x in items)}/{len(items)} | {median(speeds)} | {median(ttfts)} | {peak} |")
    lines += ["", "## Selection worksheet", "", "Review outputs and record the winner for everyday assistant, coding, cybersecurity, structured output, RAG, speed, and memory efficiency. Quality rankings are not inferred from speed alone."]
    out.write_text("\n".join(lines) + "\n")
    return out
