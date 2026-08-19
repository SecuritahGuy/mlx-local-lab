import json
from unittest.mock import MagicMock, patch

from local_mlx.practical import DIFFICULTIES, repository_tier_cases, run_practical
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


def test_text_only_camera_profile_is_capability_skipped(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("local_mlx.practical.RESULT_DIR", tmp_path)
    jsonl, _ = run_practical("gptoss", "camera")
    result = json.loads(jsonl.read_text())
    assert result["supported"] is False
    assert result["quality_score"] is None
    assert "text-only" in result["skip_reason"]


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
