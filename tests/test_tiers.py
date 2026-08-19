import json
from unittest.mock import MagicMock, patch

from local_mlx.config import get_model
from local_mlx.practical import (
    DIFFICULTIES,
    HALLUCINATION_GUARDRAILED_POLICY,
    HALLUCINATION_GUARDRAILED_PROMPT_VERSION,
    HALLUCINATION_NATURAL_POLICY,
    HALLUCINATION_NATURAL_PROMPT_VERSION,
    repository_tier_cases,
    run_practical,
)
from local_mlx.schemas import ChangeDecision, RepositoryAnswer


def test_required_categories_cover_every_difficulty() -> None:
    prefixes = {
        "camera": ["empty-day", "package-obscured", "lookalike-object", "ambiguous-object-abstention"],
        "sports": ["nfl-historical-matchup", "nba-historical-matchup", "mlb-historical-matchup", "nfl-adversarial-noisy-upset"],
        "repository": ["architecture-navigation", "cross-file-retry-localization", "config-logic-test-interaction", "appropriate-no-change"],
        "hallucination": ["camera-absent-person", "sports-absent-quarterback", "api-absent-firmware", "false-premise-conflicting-data"],
    }
    for tests in prefixes.values():
        assert {DIFFICULTIES[test] for test in tests} == {"easy", "medium", "hard", "adversarial"}


def test_hallucination_prompts_separate_natural_and_guardrailed_contracts() -> None:
    assert HALLUCINATION_NATURAL_PROMPT_VERSION == "hallucination-natural-v1"
    assert HALLUCINATION_GUARDRAILED_PROMPT_VERSION == "hallucination-guardrailed-v1"
    assert "INSUFFICIENT_EVIDENCE" not in HALLUCINATION_NATURAL_POLICY
    assert "Missing fields are unknown" in HALLUCINATION_GUARDRAILED_POLICY
    assert "INSUFFICIENT_EVIDENCE" in HALLUCINATION_GUARDRAILED_POLICY


def test_text_only_camera_profile_is_capability_skipped(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("local_mlx.practical.RESULT_DIR", tmp_path)
    jsonl, _ = run_practical("gptoss", "camera")
    result = json.loads(jsonl.read_text())
    assert result["supported"] is False
    assert result["quality_score"] is None
    assert "text-only" in result["skip_reason"]


def test_gptoss_capabilities_do_not_treat_api_or_images_as_intelligence_failures(
    tmp_path, monkeypatch
) -> None:
    config = get_model("gptoss")
    assert not config.multimodal
    assert not config.responses_api
    monkeypatch.setattr("local_mlx.practical.RESULT_DIR", tmp_path)
    jsonl, _ = run_practical("gptoss", "vision")
    result = json.loads(jsonl.read_text())
    assert result["supported"] is False
    assert result["model_success"] is None
    assert result["quality_score"] is None


def test_text_only_hallucination_profile_skips_only_image_case(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("local_mlx.practical.RESULT_DIR", tmp_path)
    response = {
        "parsed": None,
        "output": "INSUFFICIENT_EVIDENCE: requested fact is missing.",
        "model_success": True,
        "model_latency": 0.1,
        "ttft_seconds": 0.01,
        "prompt_tokens": 10,
        "output_tokens": 4,
        "tokens_per_second": 20,
        "parse_success": None,
        "schema_valid": None,
        "error": None,
        "memory": {},
    }
    with patch("local_mlx.practical.model_call", return_value=response) as model_call:
        jsonl, _ = run_practical("gptoss", "hallucination-natural")
    rows = [json.loads(line) for line in jsonl.read_text().splitlines()]
    image_case = next(row for row in rows if row["test"] == "camera-absent-person")
    assert image_case["supported"] is False
    assert image_case["quality_score"] is None
    assert model_call.call_count == 3
    assert all(row["quality_score"] == 1 for row in rows if row is not image_case)
    assert {row["benchmark"] for row in rows} == {"hallucination_natural"}


def test_combined_hallucination_profile_keeps_tracks_distinct(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("local_mlx.practical.RESULT_DIR", tmp_path)
    response = {
        "parsed": None,
        "output": "INSUFFICIENT_EVIDENCE: requested fact is missing.",
        "model_success": True,
        "model_latency": 0.1,
        "ttft_seconds": 0.01,
        "prompt_tokens": 10,
        "output_tokens": 4,
        "tokens_per_second": 20,
        "parse_success": None,
        "schema_valid": None,
        "error": None,
        "memory": {},
    }
    with patch("local_mlx.practical.model_call", return_value=response):
        jsonl, _ = run_practical("gptoss", "hallucination")
    rows = [json.loads(line) for line in jsonl.read_text().splitlines()]
    assert {row["benchmark"] for row in rows} == {
        "hallucination_natural",
        "hallucination_guardrailed",
    }
    assert {row["prompt_version"] for row in rows} == {
        HALLUCINATION_NATURAL_PROMPT_VERSION,
        HALLUCINATION_GUARDRAILED_PROMPT_VERSION,
    }


def test_repository_adversarial_case_rewards_no_change() -> None:
    answers = [
        MagicMock(parsed=RepositoryAnswer(answer="x", files=["app/config.py", "app/rest_client.py"], evidence=[], confidence=1),
                  output="x", model_success=True, parse_success=True),
        MagicMock(parsed=RepositoryAnswer(answer="bool false", files=["app/config.py", "app/api.py", "tests/test_config_interaction.py"], evidence=[], confidence=1),
                  output="bool false", model_success=True, parse_success=True),
        MagicMock(parsed=ChangeDecision(change_required=False, files=[], explanation="contract", confidence=1),
                  output="no change", model_success=True, parse_success=True),
    ]
    normalized = []
    for answer in answers:
        value = {"parsed": answer.parsed, "output": answer.output, "model_success": True,
                 "model_latency": 1, "ttft_seconds": 0.1, "prompt_tokens": 10,
                 "output_tokens": 5, "tokens_per_second": 5, "parse_success": True,
                 "schema_valid": True, "error": None, "memory": {}}
        normalized.append(value)
    with patch("local_mlx.practical.model_call", side_effect=normalized):
        rows = repository_tier_cases("qwen")
    assert rows[-1]["metrics"]["appropriate_no_change_behavior"] == 1
    assert rows[-1]["quality_score"] == 1
