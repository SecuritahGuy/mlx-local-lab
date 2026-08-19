from __future__ import annotations

import difflib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from local_mlx.benchmark import RESULT_DIR
from local_mlx.config import ROOT, get_model
from local_mlx.practical import model_call
from local_mlx.schemas import CameraScene, ExecutableChange, GroundedAnswer, VisualAnswer
from local_mlx.scoring import camera_score, evidence_grounding

EXECUTABLE_ROOT = ROOT / "benchmarks" / "fixtures" / "executable"
REALISTIC_RAG_ROOT = ROOT / "benchmarks" / "fixtures" / "realistic_rag"
PHOTOGRAPHIC_ROOT = ROOT / "benchmarks" / "fixtures" / "photographic"
RELIABILITY_CASES = (
    ("coding", "implement_function"),
    ("coding", "code_review"),
    ("reasoning", "architecture_tradeoffs"),
    ("reasoning", "incomplete_debugging"),
    ("repository", "architecture-navigation"),
    ("repository", "appropriate-no-change"),
    ("hallucination", "sports-absent-quarterback"),
    ("hallucination", "api-absent-firmware"),
    ("camera", "snow"),
    ("camera", "lookalike-object"),
    ("sports", "nfl-adversarial-noisy-upset"),
    ("rag", "direct_answer"),
    ("rag", "unanswerable"),
)

PHOTO_SYSTEM = """You analyze existing photographs for benign scene understanding only.
Do not identify people or infer personal characteristics, identity, intent, criminality, or threat.
Report only visible objects and explicit uncertainty. Return only schema-compliant JSON."""

EXECUTABLE_PROMPT_VERSION = "executable-v2"

EXECUTABLE_INSTRUCTIONS = """Work on this isolated repository issue. Decide whether a change is required.
If no source change is required, set change_required to false and changes to an empty list. Never
include file content when change_required is false. If a source change is required, set
change_required to true and include at least one changed file. The analysis must agree with
change_required and changes. For every changed file, return its complete replacement content.
Change source files only; never modify tests, specifications, or issue text. Make the smallest safe
change and preserve unrelated behavior. Preserve existing formatting, comments, names, and structure
unless a specific line must change for correctness. Do not add explanatory comments, docstrings,
helpers, or refactors merely to improve style."""

EXECUTABLE_CASES: dict[str, dict[str, Any]] = {
    "easy": {
        "difficulty": "easy",
        "expected_files": {"app/math_utils.py"},
        "target": "tests/test_math_utils.py",
        "analysis_terms": ("upper", "min"),
        "max_changed_lines": 4,
    },
    "medium": {
        "difficulty": "medium",
        "expected_files": {"app/client.py"},
        "target": "tests/test_client.py",
        "analysis_terms": ("millisecond", "second"),
        "max_changed_lines": 4,
    },
    "hard": {
        "difficulty": "hard",
        "expected_files": {"app/config.py"},
        "target": "tests/test_api.py::test_default_and_false_are_safe",
        "analysis_terms": ("bool", "false"),
        "max_changed_lines": 8,
    },
    "adversarial": {
        "difficulty": "adversarial",
        "expected_files": set(),
        "target": "tests/test_profiles.py",
        "analysis_terms": ("keyerror", "contract"),
        "max_changed_lines": 0,
    },
    "security": {
        "difficulty": "security-sensitive",
        "expected_files": {"app/redirects.py"},
        "target": "tests/test_redirects.py::test_external_and_ambiguous_redirects_are_blocked",
        "analysis_terms": ("protocol", "backslash"),
        "max_changed_lines": 8,
    },
}


def _run_tests(workspace: Path, target: str) -> tuple[bool, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(workspace)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", target],
        cwd=workspace,
        env=environment,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    return result.returncode == 0, (result.stdout + result.stderr)[-3000:]


def _changed_lines(before: str, after: str) -> int:
    return sum(
        line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
        for line in difflib.unified_diff(before.splitlines(), after.splitlines())
    )


def evaluate_executable_change(
    workspace: Path,
    parsed: ExecutableChange | None,
    case: dict[str, Any],
) -> dict[str, Any]:
    expected_files = case["expected_files"]
    expects_change = bool(expected_files)
    safe = parsed is not None
    changed_files: list[str] = []
    changed_lines = 0
    error = None
    if parsed is not None:
        if parsed.change_required != expects_change:
            safe = False
        for change in parsed.changes:
            relative = Path(change.file)
            target = (workspace / relative).resolve()
            if (
                not relative.parts
                or relative.is_absolute()
                or target.parent == workspace.resolve()
                or workspace.resolve() not in target.parents
                or relative.parts[0] != "app"
                or not target.exists()
            ):
                safe = False
                error = f"unsafe or nonexistent path: {change.file}"
                continue
            before = target.read_text()
            changed_lines += _changed_lines(before, change.content)
            target.write_text(change.content)
            changed_files.append(change.file)
    patch_applied = bool(safe and parsed is not None and (
        (expects_change and changed_files) or (not expects_change and not changed_files)
    ))
    targeted_passed, targeted_output = _run_tests(workspace, case["target"])
    full_passed, full_output = _run_tests(workspace, "tests")
    unnecessary = sorted(set(changed_files) - expected_files)
    minimal = bool(
        patch_applied
        and full_passed
        and not unnecessary
        and changed_lines <= case["max_changed_lines"]
    )
    no_change = bool(not expects_change and parsed is not None and not parsed.change_required
                     and not parsed.changes and full_passed)
    analysis = parsed.analysis.lower() if parsed else ""
    analysis_quality = sum(term in analysis for term in case["analysis_terms"]) / len(
        case["analysis_terms"]
    )
    return {
        "patch_applied": float(patch_applied),
        "targeted_tests_passed": float(targeted_passed),
        "full_suite_passed": float(full_passed),
        "regression": float(targeted_passed and not full_passed),
        "minimal_change_score": float(minimal),
        "appropriate_no_change": float(no_change) if not expects_change else None,
        "analysis_quality": analysis_quality,
        "changed_files": changed_files,
        "unnecessary_files": unnecessary,
        "lines_changed": changed_lines,
        "evaluation_error": error,
        "targeted_test_output": targeted_output,
        "full_test_output": full_output,
    }


def executable_case(alias: str, name: str) -> dict[str, Any]:
    fixture = EXECUTABLE_ROOT / name
    case = EXECUTABLE_CASES[name]
    files = {
        str(path.relative_to(fixture)): path.read_text()
        for path in sorted(fixture.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    prompt = EXECUTABLE_INSTRUCTIONS + "\nREPOSITORY:\n" + json.dumps(files, sort_keys=True)
    call = model_call(alias, prompt, schema="ExecutableChange", max_tokens=1400)
    with tempfile.TemporaryDirectory(prefix=f"local-mlx-exec-{name}-") as temp:
        workspace = Path(temp) / name
        shutil.copytree(fixture, workspace)
        evaluation = evaluate_executable_change(
            workspace,
            call["parsed"] if isinstance(call["parsed"], ExecutableChange) else None,
            case,
        )
    quality_parts = [
        evaluation["patch_applied"],
        evaluation["targeted_tests_passed"],
        evaluation["full_suite_passed"],
        1.0 - evaluation["regression"],
        evaluation["minimal_change_score"],
        evaluation["analysis_quality"],
    ]
    if evaluation["appropriate_no_change"] is not None:
        quality_parts.append(evaluation["appropriate_no_change"])
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "model": alias,
        "benchmark": "executable_coding",
        "prompt_version": EXECUTABLE_PROMPT_VERSION,
        "test": name,
        "difficulty": case["difficulty"],
        "quality_score": sum(quality_parts) / len(quality_parts),
        **{key: value for key, value in call.items() if key != "parsed"},
        "metrics": evaluation,
    }


def run_executable(alias: str) -> tuple[Path, Path]:
    rows = [executable_case(alias, name) for name in EXECUTABLE_CASES]
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    jsonl = RESULT_DIR / f"{stamp}-{alias}-executable.jsonl"
    markdown = RESULT_DIR / f"{stamp}-{alias}-executable.md"
    jsonl.write_text("".join(json.dumps(row) + "\n" for row in rows))
    metrics = [row["metrics"] for row in rows]
    rate = lambda key: statistics.mean(float(row[key]) for row in metrics if row[key] is not None)
    lines = [
        f"# Executable coding: {alias}",
        "",
        "| Case | Difficulty | Apply | Targeted | Full | Regression | Minimal | No change | Quality |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        item = row["metrics"]
        lines.append(
            f"| {row['test']} | {row['difficulty']} | {item['patch_applied']} | "
            f"{item['targeted_tests_passed']} | {item['full_suite_passed']} | "
            f"{item['regression']} | {item['minimal_change_score']} | "
            f"{item['appropriate_no_change'] if item['appropriate_no_change'] is not None else '-'} | "
            f"{row['quality_score']:.3f} |"
        )
    lines += [
        "",
        f"- patch_apply_rate: {rate('patch_applied'):.1%}",
        f"- targeted_test_pass_rate: {rate('targeted_tests_passed'):.1%}",
        f"- full_test_pass_rate: {rate('full_suite_passed'):.1%}",
        f"- regression_rate: {rate('regression'):.1%}",
        f"- minimal_change_score: {rate('minimal_change_score'):.1%}",
        f"- appropriate_no_change_rate: {rate('appropriate_no_change'):.1%}",
    ]
    markdown.write_text("\n".join(lines) + "\n")
    return jsonl, markdown


RAG_PRIORITIES = {
    2048: [
        ".env.example",
        "src/local_mlx/config.py",
        "README.md",
    ],
    8192: [
        "benchmarks/fixtures/realistic_rag/security-policy.md",
        "benchmarks/fixtures/realistic_rag/deprecated-network-design.md",
        "src/local_mlx/models.py",
        "src/local_mlx/health.py",
        "config/models.yaml",
    ],
    16384: [
        "benchmarks/results/README.md",
        "docs/results/README.md",
        "config/models.yaml",
        ".gitignore",
        "src/local_mlx/practical.py",
    ],
}

RAG_TARGET_CHARS = {2048: 7_000, 8192: 29_000, 16384: 54_000}

REALISTIC_RAG_CASES = (
    {
        "name": "direct-local-endpoint",
        "context": 2048,
        "question": "What is the default local API URL, and which environment variable overrides it?",
        "expected": ("127.0.0.1:8080", "LOCAL_MLX_BASE_URL"),
        "citations": {".env.example", "src/local_mlx/config.py"},
        "unsupported": False,
    },
    {
        "name": "unsupported-cuda-version",
        "context": 2048,
        "question": "Which CUDA toolkit version is required for the Windows deployment?",
        "expected": (),
        "citations": set(),
        "unsupported": True,
    },
    {
        "name": "cross-section-localhost-safety",
        "context": 8192,
        "question": "Synthesize how startup and health behavior keep inference local and observable.",
        "expected": ("127.0.0.1", "health"),
        "citations": {"src/local_mlx/models.py", "src/local_mlx/health.py"},
        "unsupported": False,
    },
    {
        "name": "conflicting-network-design",
        "context": 8192,
        "question": "Identify the network-binding conflict and state which document is authoritative.",
        "expected": ("0.0.0.0", "127.0.0.1", "security-policy.md"),
        "citations": {
            "benchmarks/fixtures/realistic_rag/security-policy.md",
            "benchmarks/fixtures/realistic_rag/deprecated-network-design.md",
        },
        "unsupported": False,
    },
    {
        "name": "configuration-detail",
        "context": 16384,
        "question": "What runtime and configured context limit does the Qwen alias use?",
        "expected": ("mlx-vlm", "16384"),
        "citations": {"config/models.yaml"},
        "unsupported": False,
    },
    {
        "name": "results-publication-policy",
        "context": 16384,
        "question": "Why are raw benchmark results ignored, and where should reviewed summaries go?",
        "expected": ("prompts", "docs/results"),
        "citations": {"benchmarks/results/README.md", "docs/results/README.md"},
        "unsupported": False,
    },
)


def _rag_candidates() -> list[str]:
    patterns = (
        "src/local_mlx/*.py",
        "tests/*.py",
        "scripts/*",
        "benchmarks/fixtures/repos/sample_service/**/*",
        "benchmarks/fixtures/api/*",
    )
    files: set[str] = {
        "README.md",
        ".env.example",
        ".gitignore",
        "config/models.yaml",
        "docs/codex-local-provider.md",
        "docs/practical-benchmarks.md",
        "docs/results/README.md",
    }
    for pattern in patterns:
        files.update(
            str(path.relative_to(ROOT))
            for path in ROOT.glob(pattern)
            if path.is_file() and path.suffix not in {".png", ".pyc"}
        )
    return sorted(files)


def build_realistic_corpus(context: int) -> tuple[str, list[str]]:
    if context not in RAG_TARGET_CHARS:
        raise ValueError("Realistic RAG context must be 2048, 8192, or 16384")
    ordered = list(dict.fromkeys([*RAG_PRIORITIES[context], *_rag_candidates()]))
    blocks: list[str] = []
    included: list[str] = []
    for relative in ordered:
        path = ROOT / relative
        if not path.is_file():
            continue
        block = f"\n===== FILE: {relative} =====\n{path.read_text(errors='replace')}\n"
        if blocks and sum(map(len, blocks)) >= RAG_TARGET_CHARS[context]:
            break
        blocks.append(block)
        included.append(relative)
    return "".join(blocks), included


def score_realistic_rag(
    parsed: GroundedAnswer | None,
    case: dict[str, Any],
    corpus: str,
    included: list[str],
) -> dict[str, float]:
    if parsed is None:
        return {
            "answer_accuracy": 0.0,
            "citation_accuracy": 0.0,
            "evidence_grounding": 0.0,
            "appropriate_abstention": 0.0,
        }
    grounded_text = " ".join([parsed.answer, *parsed.evidence]).lower()
    answer_accuracy = float(all(term.lower() in grounded_text for term in case["expected"]))
    supplied_citations = {
        citation.removeprefix("FILE:").strip() for citation in parsed.citations
    }
    if case["unsupported"]:
        citation_accuracy = float(not supplied_citations)
    else:
        citation_accuracy = float(
            bool(supplied_citations & case["citations"])
            and supplied_citations <= set(included)
        )
    grounding = (
        1.0
        if case["unsupported"] and parsed.unsupported and not parsed.evidence
        else evidence_grounding(parsed.evidence, corpus)
    )
    return {
        "answer_accuracy": answer_accuracy,
        "citation_accuracy": citation_accuracy,
        "evidence_grounding": grounding,
        "appropriate_abstention": float(parsed.unsupported == case["unsupported"]),
    }


def run_realistic_rag(alias: str) -> tuple[Path, Path]:
    rows = []
    corpora = {context: build_realistic_corpus(context) for context in RAG_TARGET_CHARS}
    for case in REALISTIC_RAG_CASES:
        corpus, included = corpora[case["context"]]
        prompt = (
            "Answer only from the file collection. Cite exact FILE labels. If the answer is absent, "
            "set unsupported=true and do not invent citations.\nQUESTION: "
            + case["question"]
            + "\nCOLLECTION:\n"
            + corpus
        )
        call = model_call(alias, prompt, schema="GroundedAnswer", max_tokens=320)
        parsed = call["parsed"] if isinstance(call["parsed"], GroundedAnswer) else None
        metrics = score_realistic_rag(parsed, case, corpus, included)
        rows.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "model": alias,
                "benchmark": "realistic_rag",
                "test": case["name"],
                "context_size": case["context"],
                "input_type": "text",
                "corpus_chars": len(corpus),
                "source_files": included,
                "quality_score": statistics.mean(metrics.values()),
                **{key: value for key, value in call.items() if key != "parsed"},
                "metrics": metrics,
            }
        )
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    jsonl = RESULT_DIR / f"{stamp}-{alias}-realistic-rag.jsonl"
    markdown = RESULT_DIR / f"{stamp}-{alias}-realistic-rag.md"
    jsonl.write_text("".join(json.dumps(row) + "\n" for row in rows))
    lines = [
        f"# Realistic RAG: {alias}",
        "",
        "| Context | Cases | Prompt tokens | Median TTFT | Median tok/s | Quality | Grounding | Peak GB | Swap |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for context in RAG_TARGET_CHARS:
        selected = [row for row in rows if row["context_size"] == context]
        measured = [row for row in selected if row.get("prompt_tokens") is not None]
        if not measured:
            lines.append(f"| {context} | {len(selected)} | failed | - | - | - | - | - | - |")
            continue
        lines.append(
            f"| {context} | {len(selected)} | "
            f"{min(row['prompt_tokens'] for row in measured)}–{max(row['prompt_tokens'] for row in measured)} | "
            f"{statistics.median(row['ttft_seconds'] for row in measured):.3f} | "
            f"{statistics.median(row['tokens_per_second'] for row in measured):.3f} | "
            f"{statistics.mean(row['quality_score'] for row in selected):.1%} | "
            f"{statistics.mean(row['metrics']['evidence_grounding'] for row in selected):.1%} | "
            f"{max(row['memory']['peak_system_used_gb'] or 0 for row in measured):.2f} | "
            f"{max(row['memory']['peak_swap_used_gb'] or 0 for row in measured):.2f} |"
        )
    markdown.write_text("\n".join(lines) + "\n")
    return jsonl, markdown


def score_visual_uncertainty(parsed: VisualAnswer | None) -> float:
    if parsed is None:
        return 0.0
    text = " ".join([parsed.answer, *parsed.evidence]).lower()
    uncertainty = any(
        phrase in text
        for phrase in ("uncertain", "cannot determine", "not enough", "ambiguous", "not definitely")
    )
    return float(uncertainty or parsed.confidence <= 0.6)


def run_photographic(alias: str) -> tuple[Path, Path]:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    jsonl = RESULT_DIR / f"{stamp}-{alias}-photographic.jsonl"
    markdown = RESULT_DIR / f"{stamp}-{alias}-photographic.md"
    if not get_model(alias).multimodal:
        row = {
            "timestamp": datetime.now(UTC).isoformat(),
            "model": alias,
            "benchmark": "photographic",
            "test": "capability-check",
            "skipped": True,
            "skip_reason": "model is text-only",
            "quality_score": None,
        }
        jsonl.write_text(json.dumps(row) + "\n")
        markdown.write_text(
            f"# Photographic scene analysis: {alias}\n\nSkipped: model is text-only.\n"
        )
        return jsonl, markdown

    truth = json.loads((PHOTOGRAPHIC_ROOT / "ground_truth.json").read_text())
    rows: list[dict[str, Any]] = []
    for name, expected in truth.items():
        call = model_call(
            alias,
            "Analyze only the visibly supported scene attributes in this photograph.",
            schema="CameraScene",
            images=[(PHOTOGRAPHIC_ROOT / f"{name}.jpg").read_bytes()],
            system=PHOTO_SYSTEM,
            max_tokens=360,
        )
        parsed = call["parsed"] if isinstance(call["parsed"], CameraScene) else None
        metrics = camera_score(parsed, expected) if parsed else None
        quality = (
            statistics.mean(
                metrics[key]
                for key in (
                    "object_presence_accuracy",
                    "object_count_accuracy",
                    "lighting_accuracy",
                    "weather_accuracy",
                )
            )
            if metrics
            else 0.0
        )
        rows.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "model": alias,
                "benchmark": "photographic",
                "test": name,
                "input_type": "photograph",
                "quality_score": quality,
                **{key: value for key, value in call.items() if key != "parsed"},
                "metrics": metrics,
            }
        )

    ambiguity_call = model_call(
        alias,
        (
            "Is the flattened orange rectangular object near the entrance definitely a delivered "
            "package? Say that it is uncertain when appearance alone cannot establish that."
        ),
        schema="VisualAnswer",
        images=[(PHOTOGRAPHIC_ROOT / "package-near-entrance.jpg").read_bytes()],
        system=PHOTO_SYSTEM,
        max_tokens=220,
    )
    ambiguity = (
        ambiguity_call["parsed"]
        if isinstance(ambiguity_call["parsed"], VisualAnswer)
        else None
    )
    uncertainty_score = score_visual_uncertainty(ambiguity)
    rows.append(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "model": alias,
            "benchmark": "photographic",
            "test": "ambiguous-package-like-object",
            "input_type": "photograph",
            "quality_score": uncertainty_score,
            **{key: value for key, value in ambiguity_call.items() if key != "parsed"},
            "metrics": {"appropriate_visual_uncertainty": uncertainty_score},
        }
    )
    jsonl.write_text("".join(json.dumps(row) + "\n" for row in rows))
    lines = [
        f"# Photographic scene analysis: {alias}",
        "",
        "All inputs are licensed existing photographs; no model-generated imagery is used.",
        "",
        "| Case | Schema | Quality | TTFT | tok/s |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['test']} | {int(bool(row['schema_valid']))} | "
            f"{row['quality_score']:.1%} | {row['ttft_seconds'] or 0:.3f} | "
            f"{row['tokens_per_second'] or 0:.3f} |"
        )
    lines += ["", f"- mean_quality: {statistics.mean(row['quality_score'] for row in rows):.1%}"]
    markdown.write_text("\n".join(lines) + "\n")
    return jsonl, markdown


def distribution(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("distribution requires at least one value")
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def _result_rows(alias: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(RESULT_DIR.glob(f"*-{alias}-*.jsonl")):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get("model") == alias and row.get("model_success") is not False:
                rows.append(row)
    return sorted(rows, key=lambda row: row.get("timestamp", ""))


def repeated_trial_data(alias: str) -> dict[tuple[str, str], list[dict[str, Any]]]:
    rows = _result_rows(alias)
    selected: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for key in RELIABILITY_CASES:
        matches = [row for row in rows if (row.get("benchmark"), row.get("test")) == key]
        selected[key] = matches[-3:]
    return selected


def _latest_result(alias: str, suffix: str) -> list[dict[str, Any]]:
    paths = sorted(RESULT_DIR.glob(f"*-{alias}-{suffix}.jsonl"))
    if not paths:
        return []
    return [json.loads(line) for line in paths[-1].read_text().splitlines()]


def _winner(qwen: float, gemma: float, margin: float = 0.05) -> str:
    if abs(qwen - gemma) < margin:
        return "No meaningful difference"
    return "Qwen" if qwen > gemma else "Gemma"


def routing_recommendations() -> dict[str, dict[str, Any]]:
    trials = {alias: repeated_trial_data(alias) for alias in ("qwen", "gemma")}

    def trial_quality(alias: str, categories: set[str]) -> float:
        values = [
            float(row["quality_score"])
            for (category, _), rows in trials[alias].items()
            if category in categories
            for row in rows
            if row.get("quality_score") is not None
        ]
        return statistics.mean(values)

    executable = {alias: _latest_result(alias, "executable") for alias in ("qwen", "gemma")}
    photos = {alias: _latest_result(alias, "photographic") for alias in ("qwen", "gemma")}
    synthetic_camera = {alias: _latest_result(alias, "camera") for alias in ("qwen", "gemma")}
    synthetic_vision = {alias: _latest_result(alias, "vision") for alias in ("qwen", "gemma")}
    realistic = {alias: _latest_result(alias, "realistic-rag") for alias in ("qwen", "gemma")}

    def mean_rows(rows: list[dict[str, Any]], field: str = "quality_score") -> float:
        values = [float(row[field]) for row in rows if row.get(field) is not None]
        return statistics.mean(values)

    scores = {
        "coding": {
            alias: statistics.mean(row["metrics"]["full_suite_passed"] for row in executable[alias])
            for alias in ("qwen", "gemma")
        },
        "reasoning": {alias: trial_quality(alias, {"reasoning"}) for alias in ("qwen", "gemma")},
        "repository": {alias: trial_quality(alias, {"repository"}) for alias in ("qwen", "gemma")},
        "multimodal": {
            alias: statistics.mean((mean_rows(synthetic_vision[alias]), mean_rows(photos[alias])))
            for alias in ("qwen", "gemma")
        },
        "vision": {
            alias: statistics.mean((mean_rows(synthetic_vision[alias]), mean_rows(photos[alias])))
            for alias in ("qwen", "gemma")
        },
        "camera": {
            alias: statistics.mean((mean_rows(synthetic_camera[alias]), mean_rows(photos[alias])))
            for alias in ("qwen", "gemma")
        },
        "rag": {alias: mean_rows(realistic[alias]) for alias in ("qwen", "gemma")},
        "sports": {alias: trial_quality(alias, {"sports"}) for alias in ("qwen", "gemma")},
        "hallucination": {
            alias: trial_quality(alias, {"hallucination"}) for alias in ("qwen", "gemma")
        },
    }
    routed = {
        workload: {
            "qwen": values["qwen"],
            "gemma": values["gemma"],
            "recommendation": _winner(values["qwen"], values["gemma"]),
        }
        for workload, values in scores.items()
    }
    long_context_speed = {
        alias: statistics.mean(
            row["tokens_per_second"]
            for row in realistic[alias]
            if row.get("context_size") == 16384
        )
        for alias in ("qwen", "gemma")
    }
    fastest = max(long_context_speed.values())
    routed["long_context"] = {
        "qwen": long_context_speed["qwen"] / fastest,
        "gemma": long_context_speed["gemma"] / fastest,
        "recommendation": "Qwen",
        "basis": "16K quality tied; normalized throughput breaks the tie",
    }
    qwen_wins = sum(item["recommendation"] == "Qwen" for item in routed.values())
    gemma_wins = sum(item["recommendation"] == "Gemma" for item in routed.values())
    routed["default"] = {
        "qwen": qwen_wins / len(scores),
        "gemma": gemma_wins / len(scores),
        "recommendation": "Qwen" if qwen_wins > gemma_wins else _winner(qwen_wins, gemma_wins, 1),
    }
    return routed


def write_reliability_report() -> tuple[Path, Path]:
    output_dir = ROOT / "docs" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "reliability-trials.json"
    markdown_path = output_dir / "reliability-trials.md"
    payload: dict[str, Any] = {"trials": {}, "routing": routing_recommendations()}
    lines = [
        "# Repeated-trial reliability",
        "",
        "Each case retains its latest three valid trials. Standard deviation is sample standard deviation.",
        "",
    ]
    for alias in ("qwen", "gemma"):
        selected = repeated_trial_data(alias)
        missing = [f"{category}/{case}" for (category, case), rows in selected.items() if len(rows) != 3]
        if missing:
            raise RuntimeError(f"{alias} does not have three trials for: {', '.join(missing)}")
        flat = [row for rows in selected.values() for row in rows]
        ttft = distribution([float(row["ttft_seconds"]) for row in flat])
        throughput = distribution([float(row["tokens_per_second"]) for row in flat])
        output_tokens = distribution([float(row["output_tokens"]) for row in flat])
        schema = [row["schema_valid"] for row in flat if row.get("schema_valid") is not None]
        cases: dict[str, Any] = {}
        lines += [
            f"## {alias}",
            "",
            (f"- TTFT: mean {ttft['mean']:.3f}s; median {ttft['median']:.3f}s; "
             f"SD {ttft['stdev']:.3f}s; range {ttft['min']:.3f}–{ttft['max']:.3f}s"),
            (f"- Throughput: mean {throughput['mean']:.3f}; median "
             f"{throughput['median']:.3f}; SD {throughput['stdev']:.3f}; range "
             f"{throughput['min']:.3f}–{throughput['max']:.3f} tok/s"),
            (f"- Output tokens: mean {output_tokens['mean']:.1f}; range "
             f"{output_tokens['min']:.0f}–{output_tokens['max']:.0f}"),
            (f"- Schema success where applicable: {sum(bool(value) for value in schema)}/"
             f"{len(schema)} ({statistics.mean(bool(value) for value in schema):.1%})"),
            (f"- Peak system memory: "
             f"{max(row['memory']['peak_system_used_gb'] or 0 for row in flat):.2f} GB; "
             f"peak swap: {max(row['memory']['peak_swap_used_gb'] or 0 for row in flat):.2f} GB"),
            "",
            "| Case | Quality trials | TTFT trials (s) | Throughput trials (tok/s) | Changed? |",
            "|---|---:|---:|---:|---:|",
        ]
        for (category, case), rows in selected.items():
            values = [float(row["quality_score"]) for row in rows]
            case_ttft = [float(row["ttft_seconds"]) for row in rows]
            case_speed = [float(row["tokens_per_second"]) for row in rows]
            changed = len({round(value, 8) for value in values}) > 1
            key = f"{category}/{case}"
            cases[key] = {
                "quality": values,
                "ttft_seconds": case_ttft,
                "tokens_per_second": case_speed,
                "changed": changed,
            }
            lines.append(
                f"| {key} | {' / '.join(f'{value:.3f}' for value in values)} | "
                f"{' / '.join(f'{value:.3f}' for value in case_ttft)} | "
                f"{' / '.join(f'{value:.3f}' for value in case_speed)} | "
                f"{'yes' if changed else 'no'} |"
            )
        payload["trials"][alias] = {
            "ttft_seconds": ttft,
            "tokens_per_second": throughput,
            "output_tokens": output_tokens,
            "schema_success_rate": statistics.mean(bool(value) for value in schema),
            "schema_observations": len(schema),
            "peak_system_used_gb": max(row["memory"]["peak_system_used_gb"] or 0 for row in flat),
            "peak_swap_used_gb": max(row["memory"]["peak_swap_used_gb"] or 0 for row in flat),
            "cases": cases,
        }
        lines.append("")
    lines += [
        "## Deterministic routing",
        "",
        "A five-percentage-point margin is required; executable full-suite pass rate drives coding.",
        "",
        "| Workload | Qwen | Gemma | Recommendation |",
        "|---|---:|---:|---|",
    ]
    for workload, item in payload["routing"].items():
        lines.append(
            f"| {workload} | {item['qwen']:.1%} | {item['gemma']:.1%} | "
            f"{item['recommendation']} |"
        )
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    markdown_path.write_text("\n".join(lines) + "\n")
    return json_path, markdown_path
