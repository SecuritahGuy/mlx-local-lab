from __future__ import annotations

import math
import re
from collections.abc import Iterable

from local_mlx.schemas import CameraScene, LedgerSummary, SportsPrediction

ABSTENTION_PATTERNS = (
    "insufficient evidence",
    "not enough information",
    "does not contain enough information",
    "lacks enough evidence",
    "insufficient information",
    "cannot determine",
    "not possible to determine",
    "not provided",
    "not specified",
    "not visible",
    "not in the provided",
    "unknown",
)


def abstained(text: str) -> bool:
    lowered = re.sub(r"[*`]", "", text.lower()).replace("_", " ")
    return any(pattern in lowered for pattern in ABSTENTION_PATTERNS) or bool(
        re.search(r"\bno\b.{0,80}\b(?:is|are) specified\b", lowered)
    )


def hallucination_score(text: str, should_abstain: bool) -> dict[str, float | bool]:
    did_abstain = abstained(text)
    return {
        "appropriate_abstention": did_abstain == should_abstain,
        "unsupported_claim_rate": float(should_abstain and not did_abstain),
        "score": 1.0 if did_abstain == should_abstain else 0.0,
    }


def camera_score(scene: CameraScene, truth: dict) -> dict[str, float]:
    fields = ["person_present", "package_present", "vehicle_present", "animal_present", "door_open"]
    correct = sum(getattr(scene, field) == truth[field] for field in fields)
    predicted = {field for field in fields if getattr(scene, field)}
    actual = {field for field in fields if truth[field]}
    hallucinated = len(predicted - actual)
    missing = len(actual - predicted)
    return {
        "object_presence_accuracy": correct / len(fields),
        "object_count_accuracy": float(scene.person_count == truth["person_count"]),
        "lighting_accuracy": float(scene.lighting == truth["lighting"]),
        "weather_accuracy": float(scene.weather_visible == truth["weather_visible"]),
        "hallucinated_object_rate": hallucinated / max(len(predicted), 1),
        "missing_object_rate": missing / max(len(actual), 1),
        "confidence_error": abs(scene.confidence - (correct / len(fields))),
    }


def evidence_grounding(evidence: Iterable[str], source: str) -> float:
    source_tokens = set(re.findall(r"[a-z0-9.%-]+", source.lower()))
    scores = []
    for item in evidence:
        tokens = set(re.findall(r"[a-z0-9.%-]+", item.lower()))
        meaningful = {token for token in tokens if len(token) > 2}
        scores.append(len(meaningful & source_tokens) / max(len(meaningful), 1))
    return sum(scores) / len(scores) if scores else 0.0


def sports_score(prediction: SportsPrediction, fixture: dict, prompt_source: str) -> dict[str, float | bool]:
    actual = fixture["actual_winner"]
    probability = prediction.win_probability
    p_actual = probability if prediction.predicted_winner == actual else 1 - probability
    return {
        "probability_valid": 0 <= probability <= 1,
        "winner_accuracy": float(prediction.predicted_winner == actual),
        "brier_score": round((1 - p_actual) ** 2, 6),
        "log_loss": round(-math.log(max(min(p_actual, 1 - 1e-12), 1e-12)), 6),
        "internal_consistency": float(prediction.confidence >= 0 and bool(prediction.key_factors)),
        "evidence_grounding": evidence_grounding(
            (factor.evidence for factor in prediction.key_factors), prompt_source
        ),
    }


def ledger_audit_score(summary: LedgerSummary, expected: dict) -> dict[str, float]:
    count_fields = ("wins", "losses", "pushes", "pending", "graded_bets")
    count_accuracy = sum(
        getattr(summary, field) == expected[field] for field in count_fields
    ) / len(count_fields)
    return {
        "settlement_count_accuracy": count_accuracy,
        "net_units_accuracy": float(abs(summary.net_units - expected["net_units"]) <= 0.005),
        "settled_stake_accuracy": float(
            abs(summary.settled_stake - expected["settled_stake"]) <= 0.005
        ),
        "roi_accuracy": float(abs(summary.roi - expected["roi"]) <= 0.005),
    }


def normalize_score(value: float) -> float:
    return round(max(0.0, min(10.0, value * 10)), 2)


def category_scores(rows: list[dict]) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        score = row.get("quality_score")
        if score is not None:
            grouped.setdefault(row["benchmark"], []).append(float(score))
    return {category: normalize_score(sum(values) / len(values)) for category, values in grouped.items()}


def recommendations(scores: dict[str, float]) -> list[str]:
    mapping = {
        "camera": "Recommended for home-camera scene analysis",
        "vision": "Recommended for multimodal use",
        "sports": "Recommended for sports-data interpretation",
        "agentic": "Recommended for REST-assisted multi-step workflows",
        "repository": "Recommended for repository navigation",
        "hallucination_natural": "Recommended for natural-prompt abstention and grounding",
        "hallucination_guardrailed": "Recommended with an explicit evidence contract",
    }
    result = [text for category, text in mapping.items() if scores.get(category, 0) >= 7.5]
    quality_values = [
        score for category, score in scores.items() if category not in {"speed", "memory_efficiency"}
    ]
    if quality_values and sum(quality_values) / len(quality_values) >= 8:
        result.insert(0, "Recommended as an everyday local development model")
    if "repository" in scores and scores["repository"] < 6:
        result.append("Not recommended for autonomous repository modification")
    return result
