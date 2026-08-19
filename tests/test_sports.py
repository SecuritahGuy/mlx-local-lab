import json

from local_mlx.schemas import EvidenceFactor, SportsPrediction
from local_mlx.scoring import sports_score
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
