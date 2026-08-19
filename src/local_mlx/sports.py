from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from local_mlx.config import ROOT


class SportsProvider(Protocol):
    def get_team(self, sport: str, team: str) -> dict: ...
    def get_matchup(self, sport: str, team_a: str, team_b: str) -> dict: ...


class FixtureSportsProvider:
    def __init__(self, root: Path | None = None):
        self.root = root or ROOT / "benchmarks" / "fixtures" / "sports"

    def _load(self, name: str) -> dict:
        return json.loads((self.root / name).read_text())

    def get_team(self, sport: str, team: str) -> dict:
        return self._load(f"{sport}-{team}.json")

    def get_matchup(self, sport: str, team_a: str, team_b: str) -> dict:
        return self._load(f"{sport}-matchup-{team_a}-{team_b}.json")


def derived_features(team: dict) -> dict[str, float]:
    games = max(team["games_played"], 1)
    point_diff = team["points_for"] - team["points_against"]
    recent = team.get("recent_games", [])[-5:]
    recent_margin = sum(game["for"] - game["against"] for game in recent) / max(len(recent), 1)
    return {
        "points_per_game": round(team["points_for"] / games, 2),
        "points_allowed_per_game": round(team["points_against"] / games, 2),
        "point_differential": point_diff,
        "point_differential_per_game": round(point_diff / games, 2),
        "recent_average_margin": round(recent_margin, 2),
        "strength_adjusted_margin": round(point_diff / games * team["opponent_strength"]["index"], 2),
    }


def public_matchup(fixture: dict) -> dict:
    """Remove evaluator-only outcome fields to prevent temporal leakage."""
    clean = {key: value for key, value in fixture.items() if key not in {"actual_winner", "actual_score"}}
    assert "actual_winner" not in json.dumps(clean)
    return clean
