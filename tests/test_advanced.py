from pathlib import Path

from local_mlx.advanced import (
    EXECUTABLE_CASES,
    EXECUTABLE_INSTRUCTIONS,
    EXECUTABLE_PROMPT_VERSION,
    EXECUTABLE_SCORER_VERSION,
    RAG_TARGET_CHARS,
    _winner,
    build_realistic_corpus,
    distribution,
    evaluate_executable_change,
    score_realistic_rag,
    score_visual_uncertainty,
)
from local_mlx.schemas import ExecutableChange, FileReplacement, GroundedAnswer, VisualAnswer


def test_executable_prompt_defines_consistent_no_change_contract() -> None:
    normalized = " ".join(EXECUTABLE_INSTRUCTIONS.split())
    assert "change_required to false and changes to an empty list" in normalized
    assert "Never include file content when change_required is false" in normalized
    assert "analysis must agree with change_required and changes" in normalized
    assert "Do not add explanatory comments, docstrings, helpers, or refactors" in normalized
    assert EXECUTABLE_PROMPT_VERSION == "executable-v2"
    assert EXECUTABLE_SCORER_VERSION == "minimality-v2"


def test_no_change_case_rewards_restraint(tmp_path: Path) -> None:
    fixture = Path("benchmarks/fixtures/executable/adversarial")
    workspace = tmp_path / "fixture"
    import shutil

    shutil.copytree(fixture, workspace)
    change = ExecutableChange(
        change_required=False,
        changes=[],
        analysis="KeyError is required by the explicit contract.",
        confidence=1,
    )
    result = evaluate_executable_change(workspace, change, EXECUTABLE_CASES["adversarial"])
    assert result["appropriate_no_change"] == 1
    assert result["full_suite_passed"] == 1


def test_unsafe_test_modification_is_rejected(tmp_path: Path) -> None:
    fixture = Path("benchmarks/fixtures/executable/easy")
    workspace = tmp_path / "fixture"
    import shutil

    shutil.copytree(fixture, workspace)
    change = ExecutableChange(
        change_required=True,
        changes=[FileReplacement(file="tests/test_math_utils.py", content="")],
        analysis="upper min",
        confidence=1,
    )
    result = evaluate_executable_change(workspace, change, EXECUTABLE_CASES["easy"])
    assert result["patch_applied"] == 0


def test_minimality_reports_efficiency_and_added_comments(tmp_path: Path) -> None:
    fixture = Path("benchmarks/fixtures/executable/easy")
    workspace = tmp_path / "fixture"
    import shutil

    shutil.copytree(fixture, workspace)
    target = workspace / "app/math_utils.py"
    content = target.read_text().replace(
        "return max(upper, max(lower, value))",
        "# The upper bound must cap the value.\n    return min(upper, max(lower, value))",
    )
    change = ExecutableChange(
        change_required=True,
        changes=[FileReplacement(file="app/math_utils.py", content=content)],
        analysis="Use min instead of the upper value.",
        confidence=1,
    )
    result = evaluate_executable_change(workspace, change, EXECUTABLE_CASES["easy"])
    assert result["full_suite_passed"] == 1
    assert result["added_comment_lines"] == 1
    assert result["reference_changed_lines"] == 2
    assert result["edit_efficiency"] < 1
    assert result["minimal_change_score"] == 0


def test_empty_file_path_is_rejected_without_crashing(tmp_path: Path) -> None:
    fixture = Path("benchmarks/fixtures/executable/easy")
    workspace = tmp_path / "fixture"
    import shutil

    shutil.copytree(fixture, workspace)
    change = ExecutableChange(
        change_required=True,
        changes=[FileReplacement(file="", content="")],
        analysis="upper min",
        confidence=1,
    )
    result = evaluate_executable_change(workspace, change, EXECUTABLE_CASES["easy"])
    assert result["patch_applied"] == 0


def test_realistic_corpora_use_repository_files_without_padding() -> None:
    for context, target in RAG_TARGET_CHARS.items():
        corpus, files = build_realistic_corpus(context)
        assert len(corpus) >= target
        assert files
        assert "synthetic tokenizer-length" not in corpus


def test_realistic_rag_unsupported_answer() -> None:
    case = {"expected": (), "citations": set(), "unsupported": True}
    answer = GroundedAnswer(
        answer="The collection does not specify that deployment.",
        citations=[],
        evidence=[],
        unsupported=True,
        confidence=1,
    )
    metrics = score_realistic_rag(answer, case, "source", ["source.md"])
    assert metrics["appropriate_abstention"] == 1
    assert metrics["citation_accuracy"] == 1
    assert metrics["evidence_grounding"] == 1


def test_realistic_rag_accepts_requested_file_label_prefix() -> None:
    case = {
        "expected": ("127.0.0.1",),
        "citations": {"policy.md"},
        "unsupported": False,
    }
    answer = GroundedAnswer(
        answer="Loopback is required.",
        citations=["FILE: policy.md"],
        evidence=["Bind to 127.0.0.1"],
        unsupported=False,
        confidence=1,
    )
    metrics = score_realistic_rag(answer, case, "Bind to 127.0.0.1", ["policy.md"])
    assert metrics["answer_accuracy"] == 1
    assert metrics["citation_accuracy"] == 1


def test_photographic_fixtures_have_truth_and_provenance() -> None:
    root = Path("benchmarks/fixtures/photographic")
    import json

    truth = json.loads((root / "ground_truth.json").read_text())
    assert len(truth) == 7
    assert all((root / f"{name}.jpg").is_file() for name in truth)
    provenance = (root / "PROVENANCE.md").read_text()
    assert all(f"`{name}.jpg`" in provenance for name in [*truth, "package-near-entrance"])


def test_visual_uncertainty_accepts_low_confidence() -> None:
    answer = VisualAnswer(answer="It resembles a parcel.", confidence=0.4, evidence=[])
    assert score_visual_uncertainty(answer) == 1


def test_distribution_preserves_variance() -> None:
    result = distribution([1.0, 2.0, 3.0])
    assert result == {"mean": 2.0, "median": 2.0, "stdev": 1.0, "min": 1.0, "max": 3.0}


def test_routing_winner_requires_practical_margin() -> None:
    assert _winner(0.80, 0.77) == "No meaningful difference"
    assert _winner(0.90, 0.80) == "Qwen"
