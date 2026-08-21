import json

from local_mlx.practical import (
    _statspace_explanation_prompt,
    _statspace_ledger_prompt,
    _statspace_slate_prompt,
)
from local_mlx.schemas import (
    EvidenceFactor,
    LedgerSummary,
    MarketDecision,
    SportsPrediction,
    SportsSlateAssessment,
)
from local_mlx.scoring import ledger_audit_score, sports_score
from local_mlx.sports import FixtureSportsProvider, derived_features, public_matchup


def test_fixture_sports_provider_and_features() -> None:
    provider = FixtureSportsProvider()
    team = provider.get_team("nfl", "harbor-hawks")
    features = derived_features(team)
    assert team["games_played"] == 8
    assert features["points_per_game"] == 28.25
    assert features["point_differential"] == 58


def test_outcome_is_removed_to_prevent_temporal_leakage() -> None:
    fixture = FixtureSportsProvider().get_matchup("nba", "metro-comets", "coastal-tides")
    visible = public_matchup(fixture)
    assert "actual_winner" not in json.dumps(visible)
    assert visible["cutoff"] == "before-matchup"


def test_sports_metrics_include_prediction_and_grounding() -> None:
    fixture = FixtureSportsProvider().get_matchup("nfl", "harbor-hawks", "prairie-wolves")
    prediction = SportsPrediction(
        predicted_winner="Harbor Hawks",
        win_probability=0.7,
        key_factors=[EvidenceFactor(factor="Scoring", advantage="Harbor Hawks", evidence="226 points_for")],
        risks_to_prediction=[],
        missing_information=["Weather"],
        confidence=0.7,
    )
    metrics = sports_score(prediction, fixture, json.dumps(public_matchup(fixture)))
    assert metrics["winner_accuracy"] == 1
    assert metrics["brier_score"] == 0.09
    assert metrics["probability_valid"]


def test_statspace_style_fixtures_keep_expected_answers_separate() -> None:
    provider = FixtureSportsProvider()
    slate = provider._load("statspace-slate.json")
    ledger = provider._load("statspace-ledger.json")
    explanations = provider._load("statspace-explanations.json")

    public_slate = {key: value for key, value in slate.items() if key != "expected"}
    public_ledger = {key: value for key, value in ledger.items() if key != "expected"}
    public_explanations = {
        key: value for key, value in explanations.items() if key != "expected"
    }

    assert "expected" not in public_slate
    assert "expected" not in public_ledger
    assert "expected" not in public_explanations
    assert slate["expected"]["decisions"]["mlb-east-west-unpriced"] == "paper_only"
    assert len(slate["candidates"]) == 11
    assert slate["expected"]["decisions"]["mlb-border-plains-threshold"] == "recommended"
    assert slate["expected"]["decisions"]["mlb-pine-bay-bad-odds"] == "excluded"
    assert slate["expected"]["superseded_market_ids"] == [
        "mlb-north-south-old",
        "mlb-island-harbor-old",
    ]
    assert ledger["expected"]["roi"] == -0.02


def test_statspace_output_schemas_are_strict_and_bounded() -> None:
    assessment = SportsSlateAssessment(
        decisions=[
            MarketDecision(
                market_id="mlb-north-south-new",
                status="recommended",
                reason="clears the supplied gates",
            )
        ],
        superseded_market_ids=[],
        data_quality_issues=["overall odds source is degraded"],
    )
    ledger = LedgerSummary(
        wins=2,
        losses=1,
        pushes=1,
        pending=1,
        graded_bets=4,
        net_units=-0.1,
        settled_stake=5.0,
        roi=-0.02,
    )

    assert assessment.decisions[0].status == "recommended"
    assert ledger.graded_bets == 4


def test_ledger_audit_scoring_awards_per_field_count_credit() -> None:
    summary = LedgerSummary(
        wins=2,
        losses=1,
        pushes=1,
        pending=1,
        graded_bets=3,
        net_units=0.9,
        settled_stake=4.5,
        roi=0.3,
    )
    expected = {
        "wins": 2,
        "losses": 1,
        "pushes": 1,
        "pending": 1,
        "graded_bets": 4,
        "net_units": -0.1,
        "settled_stake": 5.0,
        "roi": -0.02,
    }

    metrics = ledger_audit_score(summary, expected)

    assert metrics == {
        "settlement_count_accuracy": 0.8,
        "net_units_accuracy": 0.0,
        "settled_stake_accuracy": 0.0,
        "roi_accuracy": 0.0,
    }


def test_statspace_v3_prompts_make_precedence_and_math_explicit() -> None:
    slate_prompt = _statspace_slate_prompt({"policy": {}, "candidates": []})
    ledger_prompt = _statspace_ledger_prompt({"bets": []})
    explanation_prompt = _statspace_explanation_prompt({"packets": []})

    assert "first-match procedure" in slate_prompt
    assert "never reinterpret >= as >" in slate_prompt
    assert "Optional missing or degraded sources" in slate_prompt
    assert "signed profit value verbatim" in ledger_prompt
    assert "settled_stake" in ledger_prompt
    assert "deterministic_status and primary_gate are authoritative" in explanation_prompt
    assert "never fill gaps" in explanation_prompt
    assert "at most two complete sentences and 45 words" in explanation_prompt
