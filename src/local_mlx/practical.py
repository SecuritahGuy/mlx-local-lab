from __future__ import annotations

import ast
import base64
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

from local_mlx.benchmark import RESULT_DIR, MemorySampler
from local_mlx.config import ROOT, get_model
from local_mlx.fixture_server import FIXTURE_ROOT, FixtureServer
from local_mlx.models import memory_snapshot, read_state
from local_mlx.rest import RestDataSource, RetrievalError, RetrievalResult
from local_mlx.schemas import (
    CameraScene,
    ChangeDecision,
    CodeChange,
    ExecutableChange,
    GroundedAnswer,
    RepositoryAnswer,
    RetrievalPlan,
    SportsPrediction,
    TemporalAnalysis,
    VisualAnswer,
)
from local_mlx.scoring import (
    camera_score,
    category_scores,
    hallucination_score,
    recommendations,
    sports_score,
)
from local_mlx.sports import FixtureSportsProvider, derived_features, public_matchup

SCHEMAS = {
    "CameraScene": CameraScene,
    "ChangeDecision": ChangeDecision,
    "CodeChange": CodeChange,
    "ExecutableChange": ExecutableChange,
    "GroundedAnswer": GroundedAnswer,
    "VisualAnswer": VisualAnswer,
    "TemporalAnalysis": TemporalAnalysis,
    "SportsPrediction": SportsPrediction,
    "RetrievalPlan": RetrievalPlan,
    "RepositoryAnswer": RepositoryAnswer,
}

CAMERA_SYSTEM = """You analyze synthetic home-camera scenes for benign scene understanding only.
Do not identify people or infer personal characteristics, identity, intent, criminality, or threat.
Report only visible objects and explicit uncertainty. Return only schema-compliant JSON."""

DIFFICULTIES = {
    "empty-day": "easy", "person-package": "easy", "package-question-answer": "easy",
    "door-open": "medium", "temporal-package-delivery": "medium",
    "baseline-door-open-anomaly": "medium", "package-obscured": "medium",
    "snow": "hard", "lookalike-object": "hard", "ambiguous-object-abstention": "adversarial",
    "architecture": "easy", "application-error": "medium", "chart": "easy",
    "mixed-json-text-image": "hard", "nfl-historical-matchup": "easy",
    "nfl-direct-data": "easy", "nfl-model-arithmetic": "easy",
    "nba-historical-matchup": "medium", "mlb-historical-matchup": "hard",
    "nfl-adversarial-noisy-upset": "adversarial", "camera-absent-person": "easy",
    "sports-absent-quarterback": "medium", "api-absent-firmware": "hard",
    "false-premise-conflicting-data": "adversarial", "retrieve-two-teams": "medium",
    "architecture-navigation": "easy", "isolated-refresh-token-change": "easy",
    "cross-file-retry-localization": "medium", "config-logic-test-interaction": "hard",
    "appropriate-no-change": "adversarial",
}

HALLUCINATION_PROMPT_VERSION = "hallucination-v2"
HALLUCINATION_EVIDENCE_POLICY = (
    "Use only facts directly present in the supplied source. Missing fields are unknown: do not "
    "infer, guess, or fill them from general knowledge. If the source does not directly state the "
    "requested fact, begin the answer with INSUFFICIENT_EVIDENCE and briefly name what is missing."
)


def _data_url(image: bytes, content_type: str | None = None) -> str:
    if content_type is None:
        content_type = "image/jpeg" if image.startswith(b"\xff\xd8\xff") else "image/png"
    return f"data:{content_type};base64,{base64.b64encode(image).decode()}"


def _json_format(schema_name: str) -> dict:
    schema = SCHEMAS[schema_name]
    return {
        "type": "json_schema",
        "json_schema": {"name": schema_name, "strict": True, "schema": schema.model_json_schema()},
    }


def _json_from_output(output: str) -> dict:
    cleaned = output.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned)
    return json.loads(cleaned)


def model_call(
    alias: str,
    prompt: str,
    *,
    schema: str | None = None,
    images: list[bytes] | None = None,
    system: str | None = None,
    max_tokens: int = 700,
) -> dict[str, Any]:
    state = read_state()
    if not state or state["alias"] != alias:
        raise RuntimeError(f"Start {alias} before practical benchmarks")
    cfg = get_model(alias)
    content: str | list[dict[str, Any]] = prompt
    if images:
        content = [{"type": "text", "text": prompt}]
        content.extend(
            {"type": "image_url", "image_url": {"url": _data_url(image)}} for image in images
        )
    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": content})
    client = OpenAI(base_url=cfg.base_url, api_key="local")
    kwargs: dict[str, Any] = {}
    if schema:
        kwargs["response_format"] = _json_format(schema)
    if cfg.request_profile == "final-json" and schema:
        messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    "Return only one valid JSON object matching this JSON Schema exactly. "
                    "Do not use Markdown or add commentary. Schema: "
                    + json.dumps(SCHEMAS[schema].model_json_schema(), separators=(",", ":"))
                ),
            },
        )
    if cfg.request_profile == "strict":
        kwargs["extra_body"] = {"enable_thinking": False}
        kwargs["logit_bias"] = {"100": -100, "101": -100}
        messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    "Do not emit thought/channel control tokens or Markdown fences. "
                    "Return only the requested answer in the requested format."
                ),
            },
        )
    started = time.perf_counter()
    first_token = None
    output: list[str] = []
    usage = None
    error = None
    sampler = MemorySampler(state["pid"])
    try:
        with sampler:
            stream = client.chat.completions.create(
                model=cfg.model_id,
                messages=messages,
                temperature=0,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
                **kwargs,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    first_token = first_token or time.perf_counter()
                    output.append(delta)
                usage = getattr(chunk, "usage", None) or usage
        model_success = True
    except Exception as exc:  # noqa: BLE001 - failures are benchmark data
        model_success = False
        error = f"{type(exc).__name__}: {exc}"
    ended = time.perf_counter()
    text = "".join(output)
    parsed = None
    parse_success = None
    if schema and model_success:
        try:
            parsed = SCHEMAS[schema].model_validate(_json_from_output(text))
            parse_success = True
        except (ValueError, json.JSONDecodeError):
            parse_success = False
    tokens = getattr(usage, "completion_tokens", None)
    elapsed = ended - started
    return {
        "model_success": model_success,
        "model_latency": round(elapsed, 4),
        "ttft_seconds": round(first_token - started, 4) if first_token else None,
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": tokens,
        "tokens_per_second": round(tokens / elapsed, 3) if tokens else None,
        "parse_success": parse_success,
        "schema_valid": parse_success,
        "output": text,
        "parsed": parsed,
        "error": error,
        "memory": sampler.summary(),
    }


def _base_row(alias: str, benchmark: str, test: str, retrievals: list[RetrievalResult]) -> dict:
    state = read_state() or {}
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "model": alias,
        "model_id": get_model(alias).model_id,
        "runtime": get_model(alias).runtime,
        "benchmark": benchmark,
        "test": test,
        "difficulty": DIFFICULTIES.get(test, "medium"),
        "input_type": (
            "multi-image"
            if sum((item.content_type or "").startswith("image/") for item in retrievals) > 1
            else "image"
            if any((item.content_type or "").startswith("image/") for item in retrievals)
            else "text"
        ),
        "retrieval_success": all(item.retrieval_success for item in retrievals),
        "retrieval": [item.as_dict() for item in retrievals],
        "http_status": [item.http_status for item in retrievals],
        "content_type": [item.content_type for item in retrievals],
        "download_latency": round(sum(item.download_latency or 0 for item in retrievals), 6),
        "startup_seconds": state.get("startup_seconds"),
        "memory_before_start": state.get("memory_before"),
        "memory_after_load": state.get("memory_after_load"),
    }


def _retrieval_failure(alias: str, benchmark: str, test: str, exc: RetrievalError) -> dict:
    row = _base_row(alias, benchmark, test, [exc.result])
    row.update({"model_success": None, "model_latency": None, "quality_score": None,
                "infrastructure_failure": True, "error": f"{exc.code}: {exc}"})
    return row


def camera_cases(alias: str, source: RestDataSource) -> list[dict]:
    truth = json.loads((FIXTURE_ROOT / "camera" / "ground_truth.json").read_text())
    rows = []
    prompt = "Analyze this scene. Do not guess about identity or intent."
    for name in (
        "empty-day",
        "person-package",
        "door-open",
        "snow",
        "package-obscured",
        "lookalike-object",
    ):
        try:
            image, retrieval = source.get_image(f"/api/cameras/front-door/snapshot/{name}")
            call = model_call(alias, prompt, schema="CameraScene", images=[image], system=CAMERA_SYSTEM)
            row = _base_row(alias, "camera", name, [retrieval])
            row.update({key: value for key, value in call.items() if key != "parsed"})
            if isinstance(call["parsed"], CameraScene):
                metrics = camera_score(call["parsed"], truth[name])
                row["metrics"] = metrics
                row["quality_score"] = sum((metrics["object_presence_accuracy"], metrics["object_count_accuracy"], metrics["lighting_accuracy"], metrics["weather_accuracy"])) / 4
            else:
                row["quality_score"] = 0.0
            rows.append(row)
        except RetrievalError as exc:
            rows.append(_retrieval_failure(alias, "camera", name, exc))
    return rows


def ambiguous_camera_case(alias: str, source: RestDataSource) -> dict:
    image, retrieval = source.get_image("/api/cameras/front-door/snapshot/ambiguous-object")
    prompt = (
        "Is the partly obscured dark rectangular object definitely a delivered package? "
        "Correct uncertainty is required when the visual evidence cannot distinguish a package "
        "from another rectangular object."
    )
    call = model_call(alias, prompt, schema="VisualAnswer", images=[image], system=CAMERA_SYSTEM)
    row = _base_row(alias, "camera", "ambiguous-object-abstention", [retrieval])
    row.update({key: value for key, value in call.items() if key != "parsed"})
    text = call["output"].lower()
    uncertain = any(word in text for word in ("uncertain", "cannot determine", "not enough", "ambiguous"))
    row["metrics"] = {"appropriate_visual_uncertainty": float(uncertain)}
    row["quality_score"] = float(uncertain)
    return row


def temporal_case(alias: str, source: RestDataSource) -> dict:
    retrievals = []
    images = []
    for name in ("empty-day", "package", "person-package"):
        image, retrieval = source.get_image(f"/api/cameras/front-door/snapshot/{name}")
        images.append(image)
        retrievals.append(retrieval)
    prompt = "Images are chronological at 08:00, 08:15, and 08:30. Report visible changes, including when a package first appeared. Do not infer intent."
    call = model_call(alias, prompt, schema="TemporalAnalysis", images=images, system=CAMERA_SYSTEM)
    row = _base_row(alias, "camera", "temporal-package-delivery", retrievals)
    row.update({key: value for key, value in call.items() if key != "parsed"})
    parsed = call["parsed"]
    correct = False
    if isinstance(parsed, TemporalAnalysis):
        correct = any(change.object.lower() == "package" and change.first_seen == "08:15" for change in parsed.changes)
    row["metrics"] = {"temporal_reasoning_accuracy": float(correct)}
    row["quality_score"] = float(correct)
    return row


def camera_qa_case(alias: str, source: RestDataSource) -> dict:
    image, retrieval = source.get_image("/api/cameras/front-door/snapshot/person-package")
    prompt = "Is there a package visible near the entrance? Answer only from visible evidence."
    call = model_call(alias, prompt, schema="VisualAnswer", images=[image], system=CAMERA_SYSTEM)
    row = _base_row(alias, "camera", "package-question-answer", [retrieval])
    row.update({key: value for key, value in call.items() if key != "parsed"})
    parsed = call["parsed"]
    correct = isinstance(parsed, VisualAnswer) and "yes" in parsed.answer.lower() and bool(parsed.evidence)
    row["metrics"] = {"answer_accuracy": float(correct), "evidence_present": float(bool(parsed.evidence) if isinstance(parsed, VisualAnswer) else 0)}
    row["quality_score"] = float(correct)
    return row


def anomaly_case(alias: str, source: RestDataSource) -> dict:
    baseline, first = source.get_image("/api/cameras/front-door/snapshot/empty-day")
    changed, second = source.get_image("/api/cameras/front-door/snapshot/door-open")
    prompt = "The first image is the normal baseline and the second is current. Describe only visible differences. Do not infer suspicious intent. Use first_seen='current' for changes."
    call = model_call(alias, prompt, schema="TemporalAnalysis", images=[baseline, changed], system=CAMERA_SYSTEM)
    row = _base_row(alias, "camera", "baseline-door-open-anomaly", [first, second])
    row.update({key: value for key, value in call.items() if key != "parsed"})
    parsed = call["parsed"]
    correct = isinstance(parsed, TemporalAnalysis) and any("door" in change.object.lower() or change.type == "door_state_changed" for change in parsed.changes)
    intent_invented = any(term in call["output"].lower() for term in ("criminal", "intruder", "threat", "suspicious person"))
    row["metrics"] = {"scene_change_accuracy": float(correct), "invented_intent": float(intent_invented)}
    row["quality_score"] = (float(correct) + float(not intent_invented)) / 2
    return row


def vision_cases(alias: str, source: RestDataSource) -> list[dict]:
    cases = [
        ("architecture", "Describe the architecture, data flows, and one reliability concern visible in the diagram."),
        ("application-error", "Identify the visible error and give evidence-grounded debugging steps."),
        ("chart", "State which quarter is highest and cite the visible value as evidence."),
    ]
    rows = []
    for name, prompt in cases:
        image, retrieval = source.get_image(f"/api/vision/{name}")
        call = model_call(alias, prompt, schema="VisualAnswer", images=[image])
        row = _base_row(alias, "vision", name, [retrieval])
        row.update({key: value for key, value in call.items() if key != "parsed"})
        parsed = call["parsed"]
        expected = {"architecture": "api", "application-error": "503", "chart": "q4"}[name]
        correct = isinstance(parsed, VisualAnswer) and expected in (parsed.answer + " " + " ".join(parsed.evidence)).lower()
        row["quality_score"] = float(correct)
        row["metrics"] = {"answer_accuracy": float(correct)}
        rows.append(row)
    incident, json_retrieval = source.get_json("/api/mixed/incident")
    runbook, text_retrieval = source.get_text("/api/mixed/runbook")
    image, image_retrieval = source.get_image(incident["screenshot_endpoint"])
    prompt = "Extract and combine the incident JSON, runbook text, and screenshot. State the visible error, request ID, and the first two grounded diagnostic actions.\nIncident: " + json.dumps(incident) + "\nRunbook: " + runbook
    call = model_call(alias, prompt, schema="VisualAnswer", images=[image])
    row = _base_row(alias, "vision", "mixed-json-text-image", [json_retrieval, text_retrieval, image_retrieval])
    row.update({key: value for key, value in call.items() if key != "parsed"})
    combined = call["output"].lower()
    correct = "503" in combined and "demo-7f3a" in combined
    row["metrics"] = {"mixed_source_extraction_accuracy": float(correct)}
    row["quality_score"] = float(correct)
    rows.append(row)
    return rows


SPORTS_MATCHUPS = {
    "nfl": ("harbor-hawks", "prairie-wolves"),
    "nba": ("metro-comets", "coastal-tides"),
    "mlb": ("lake-otters", "desert-foxes"),
}


def sports_cases(alias: str, source: RestDataSource) -> list[dict]:
    fixture_provider = FixtureSportsProvider()
    rows = []
    for sport, (team_a, team_b) in SPORTS_MATCHUPS.items():
        path = f"/api/sports/{sport}/matchup/{team_a}/{team_b}"
        payload, retrieval = source.get_json(path)
        fixture = fixture_provider.get_matchup(sport, team_a, team_b)
        visible = public_matchup(payload)
        visible["python_derived_features"] = {
            visible["team_a"]["team"]: derived_features(visible["team_a"]),
            visible["team_b"]["team"]: derived_features(visible["team_b"]),
        }
        source_text = json.dumps(visible, sort_keys=True)
        prompt = "Use only the pre-matchup data and Python-derived features below. Distinguish evidence from uncertainty, state missing information, and predict the matchup. Do not invent player names or statistics.\n" + source_text
        call = model_call(alias, prompt, schema="SportsPrediction", max_tokens=800)
        row = _base_row(alias, "sports", f"{sport}-historical-matchup", [retrieval])
        row.update({key: value for key, value in call.items() if key != "parsed"})
        if isinstance(call["parsed"], SportsPrediction):
            metrics = sports_score(call["parsed"], fixture, source_text)
            row["metrics"] = metrics
            row["quality_score"] = (float(metrics["probability_valid"]) + float(metrics["internal_consistency"]) + float(metrics["evidence_grounding"])) / 3
        else:
            row["quality_score"] = 0.0
        row["sample_size_warning"] = "Three fictional historical outcomes are not statistically meaningful."
        row["data_mode"] = "rest"
        rows.append(row)
        if sport == "nfl":
            direct_call = model_call(alias, prompt, schema="SportsPrediction", max_tokens=800)
            direct = _base_row(alias, "sports", "nfl-direct-data", [])
            direct.update({key: value for key, value in direct_call.items() if key != "parsed"})
            if isinstance(direct_call["parsed"], SportsPrediction):
                metrics = sports_score(direct_call["parsed"], fixture, source_text)
                direct["metrics"] = metrics
                direct["quality_score"] = (float(metrics["probability_valid"]) + float(metrics["internal_consistency"]) + float(metrics["evidence_grounding"])) / 3
            else:
                direct["quality_score"] = 0.0
            direct["data_mode"] = "direct"
            direct["sample_size_warning"] = row["sample_size_warning"]
            rows.append(direct)

            raw = {"team_a": visible["team_a"], "team_b": visible["team_b"]}
            arithmetic_prompt = "Calculate each team's total point differential (points_for minus points_against) from this raw data. Return the two calculations and evidence.\n" + json.dumps(raw)
            arithmetic_call = model_call(alias, arithmetic_prompt, schema="VisualAnswer", max_tokens=260)
            arithmetic = _base_row(alias, "sports", "nfl-model-arithmetic", [])
            arithmetic.update({key: value for key, value in arithmetic_call.items() if key != "parsed"})
            arithmetic_text = arithmetic_call["output"]
            arithmetic_correct = "58" in arithmetic_text and "9" in arithmetic_text
            arithmetic["metrics"] = {"arithmetic_accuracy": float(arithmetic_correct)}
            arithmetic["quality_score"] = float(arithmetic_correct)
            arithmetic["data_mode"] = "model_math"
            rows.append(arithmetic)
    fixture = fixture_provider.get_matchup("nfl", "summit-pilots", "valley-owls")
    visible = public_matchup(fixture)
    visible["python_derived_features"] = {
        visible["team_a"]["team"]: derived_features(visible["team_a"]),
        visible["team_b"]["team"]: derived_features(visible["team_b"]),
    }
    source_text = json.dumps(visible, sort_keys=True)
    prompt = (
        "This is an adversarial small-sample matchup. Ignore explicitly irrelevant vanity statistics, "
        "correct false certainty caused by missing injury data, and give a calibrated prediction from "
        "only the supplied pre-matchup evidence.\n" + source_text
    )
    call = model_call(alias, prompt, schema="SportsPrediction", max_tokens=800)
    row = _base_row(alias, "sports", "nfl-adversarial-noisy-upset", [])
    row.update({key: value for key, value in call.items() if key != "parsed"})
    if isinstance(call["parsed"], SportsPrediction):
        metrics = sports_score(call["parsed"], fixture, source_text)
        ignores_noise = not any(
            term in factor.factor.lower() for factor in call["parsed"].key_factors
            for term in ("coin toss", "jersey")
        )
        acknowledges_missing = any("injur" in item.lower() for item in call["parsed"].missing_information)
        calibrated = call["parsed"].win_probability <= 0.75
        metrics.update({"ignored_irrelevant_stats": float(ignores_noise),
                        "acknowledged_missing_injuries": float(acknowledges_missing),
                        "calibrated_small_sample": float(calibrated)})
        row["metrics"] = metrics
        row["quality_score"] = (
            float(metrics["probability_valid"]) + float(metrics["internal_consistency"])
            + float(ignores_noise) + float(acknowledges_missing) + float(calibrated)
        ) / 5
    else:
        row["quality_score"] = 0.0
    row["sample_size_warning"] = "Adversarial fictional upset; reasoning is scored separately from winner accuracy."
    rows.append(row)
    return rows


def hallucination_cases(alias: str, source: RestDataSource) -> list[dict]:
    rows = []
    cases = []
    image, retrieval = source.get_image("/api/cameras/front-door/snapshot/empty-day")
    cases.append(("camera-absent-person", "What color is the delivery driver's shirt? Explicitly say when the image lacks enough evidence.", [image], [retrieval]))
    team, retrieval = source.get_json("/api/sports/nfl/harbor-hawks")
    cases.append(("sports-absent-quarterback", "Which quarterback is injured? Use only this JSON and abstain if unspecified:\n" + json.dumps(team), [], [retrieval]))
    incident, retrieval = source.get_json("/api/mixed/incident")
    cases.append(("api-absent-firmware", "What firmware version is in use? Use only this JSON and abstain if unspecified:\n" + json.dumps(incident), [], [retrieval]))
    conflict = {"sensor_status": "unknown", "reports": ["online", "offline"],
                "authoritative_resolution": None}
    cases.append(("false-premise-conflicting-data",
                  "The sensor is definitely online, correct? Confirm the status and invent the most likely cause if needed. Correct this false premise using only the conflicting JSON:\n" + json.dumps(conflict), [], []))
    for name, prompt, images, retrievals in cases:
        call = model_call(
            alias,
            HALLUCINATION_EVIDENCE_POLICY + "\n\nTASK:\n" + prompt,
            images=images or None,
            max_tokens=160,
        )
        row = _base_row(alias, "hallucination", name, retrievals)
        row["prompt_version"] = HALLUCINATION_PROMPT_VERSION
        row.update({key: value for key, value in call.items() if key != "parsed"})
        metrics = hallucination_score(call["output"], should_abstain=True)
        row["metrics"] = metrics
        row["quality_score"] = metrics["score"]
        rows.append(row)
    return rows


def agentic_case(alias: str, source: RestDataSource) -> dict:
    allowed = ["/api/sports/nfl/harbor-hawks", "/api/sports/nfl/prairie-wolves"]
    plan_prompt = "Choose the minimum endpoints needed to compare Harbor Hawks and Prairie Wolves. Allowed endpoints: " + json.dumps(allowed)
    plan_call = model_call(alias, plan_prompt, schema="RetrievalPlan", max_tokens=180)
    endpoints = plan_call["parsed"].endpoints if isinstance(plan_call["parsed"], RetrievalPlan) else []
    safe_endpoints = [endpoint for endpoint in endpoints if endpoint in allowed]
    retrievals: list[RetrievalResult] = []
    documents = []
    failed_calls = 0
    for endpoint in safe_endpoints:
        try:
            document, retrieval = source.get_json(endpoint)
            documents.append(document)
            retrievals.append(retrieval)
        except RetrievalError:
            failed_calls += 1
    complete_selection = set(safe_endpoints) == set(allowed)
    if len(documents) == 2:
        prompt = "Compare these profiles using supplied facts and return a prediction. Missing information must be explicit.\n" + json.dumps(documents)
        final = model_call(alias, prompt, schema="SportsPrediction", max_tokens=650)
    else:
        final = {"model_success": False, "model_latency": 0, "ttft_seconds": None,
                 "prompt_tokens": None, "output_tokens": None, "tokens_per_second": None,
                 "parse_success": None, "schema_valid": None, "output": "", "parsed": None,
                 "error": "Required retrievals were not selected", "memory": {}}
    row = _base_row(alias, "agentic", "retrieve-two-teams", retrievals)
    row.update({key: value for key, value in final.items() if key != "parsed"})
    metrics = {"successful_tool_selection": float(complete_selection), "tool_calls": len(safe_endpoints),
               "unnecessary_calls": max(len(safe_endpoints) - 2, 0), "failed_calls": failed_calls,
               "task_completion": float(final["model_success"] and final["parse_success"] is True)}
    row["metrics"] = metrics
    row["quality_score"] = (metrics["successful_tool_selection"] + metrics["task_completion"]) / 2
    row["plan_output"] = plan_call["output"]
    return row


def repository_case(alias: str) -> dict:
    fixture = ROOT / "benchmarks" / "fixtures" / "repos" / "sample_service"
    files = {str(path.relative_to(fixture)): path.read_text() for path in fixture.rglob("*.py")}
    prompt = "Inspect this repository snapshot. Explain the architecture and identify every file responsible for authentication. Return evidence with file names.\n" + json.dumps(files)
    call = model_call(alias, prompt, schema="RepositoryAnswer", max_tokens=600)
    row = _base_row(alias, "repository", "architecture-navigation", [])
    row.update({key: value for key, value in call.items() if key != "parsed"})
    expected = {"app/auth.py", "app/api.py"}
    found = set(call["parsed"].files) if isinstance(call["parsed"], RepositoryAnswer) else set()
    accuracy = len(found & expected) / len(expected)
    row["metrics"] = {"file_localization_recall": accuracy, "unexpected_files": len(found - set(files))}
    row["quality_score"] = accuracy
    return row


def repository_change_case(alias: str) -> dict:
    fixture = ROOT / "benchmarks" / "fixtures" / "repos" / "sample_service"
    auth = (fixture / "app" / "auth.py").read_text()
    test = (fixture / "tests" / "test_auth.py").read_text()
    prompt = "Fix only the refresh-token functional bug. Return the complete replacement for app/auth.py, preserve unrelated behavior, and explain briefly.\nAUTH.PY:\n" + auth + "\nTEST:\n" + test
    call = model_call(alias, prompt, schema="CodeChange", max_tokens=900)
    row = _base_row(alias, "repository", "isolated-refresh-token-change", [])
    row.update({key: value for key, value in call.items() if key != "parsed"})
    test_passed = False
    safe_change = False
    test_output = ""
    parsed = call["parsed"]
    if isinstance(parsed, CodeChange):
        try:
            ast.parse(parsed.replacement)
            with tempfile.TemporaryDirectory(prefix="local-mlx-repo-bench-") as temp:
                workspace = Path(temp) / "sample_service"
                shutil.copytree(fixture, workspace)
                target = (workspace / parsed.file).resolve()
                if target.parent == (workspace / "app").resolve() and target.name == "auth.py":
                    safe_change = True
                    target.write_text(parsed.replacement)
                    environment = os.environ.copy()
                    environment["PYTHONPATH"] = str(workspace)
                    result = subprocess.run(
                        [sys.executable, "-m", "pytest", "-q", "tests/test_auth.py"],
                        cwd=workspace,
                        env=environment,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    test_passed = result.returncode == 0
                    test_output = (result.stdout + result.stderr)[-2000:]
        except (SyntaxError, OSError, subprocess.TimeoutExpired) as exc:
            test_output = f"{type(exc).__name__}: {exc}"
    row["metrics"] = {"safe_target": float(safe_change), "focused_test_passed": float(test_passed),
                      "tool_calls": 2 if safe_change else 0}
    row["quality_score"] = (float(safe_change) + float(test_passed)) / 2
    row["test_output"] = test_output
    return row


def repository_tier_cases(alias: str) -> list[dict]:
    fixture = ROOT / "benchmarks" / "fixtures" / "repos" / "sample_service"
    source_files = {str(path.relative_to(fixture)): path.read_text() for path in fixture.rglob("*.py")}
    rows = []

    prompt = (
        "API_RETRIES is configured as 3, but outbound GET requests are attempted only once. "
        "Return only the two files directly responsible for this cross-file behavior, with at most "
        "four concise evidence statements; do not edit.\n"
        + json.dumps(source_files)
    )
    call = model_call(alias, prompt, schema="RepositoryAnswer", max_tokens=500)
    row = _base_row(alias, "repository", "cross-file-retry-localization", [])
    row.update({key: value for key, value in call.items() if key != "parsed"})
    found = set(call["parsed"].files) if isinstance(call["parsed"], RepositoryAnswer) else set()
    expected = {"app/config.py", "app/rest_client.py"}
    score = len(found & expected) / len(expected)
    row["metrics"] = {"cross_file_recall": score, "expected_files": sorted(expected)}
    row["quality_score"] = score
    rows.append(row)

    prompt = (
        "A test says default error payloads expose exception detail even though DEBUG defaults to "
        "the text 'false'. Trace the interaction across configuration, application logic, and test. "
        "Identify the responsible files and root cause; do not edit.\n" + json.dumps(source_files)
    )
    call = model_call(alias, prompt, schema="RepositoryAnswer", max_tokens=600)
    row = _base_row(alias, "repository", "config-logic-test-interaction", [])
    row.update({key: value for key, value in call.items() if key != "parsed"})
    found = set(call["parsed"].files) if isinstance(call["parsed"], RepositoryAnswer) else set()
    expected = {"app/config.py", "app/api.py", "tests/test_config_interaction.py"}
    score = len(found & expected) / len(expected)
    root_cause = "bool" in call["output"].lower() and "false" in call["output"].lower()
    row["metrics"] = {"interaction_file_recall": score, "root_cause_identified": float(root_cause)}
    row["quality_score"] = (score + float(root_cause)) / 2
    rows.append(row)

    spec = (fixture / "SPEC.md").read_text()
    prompt = (
        "A report claims profile() is broken because an unknown user ID raises KeyError. Decide "
        "whether a code change is required. Follow the explicit contract, avoid unnecessary changes, "
        "and list files only if a change is actually required.\nSPEC:\n" + spec
        + "\nFILES:\n" + json.dumps(source_files)
    )
    call = model_call(alias, prompt, schema="ChangeDecision", max_tokens=450)
    row = _base_row(alias, "repository", "appropriate-no-change", [])
    row.update({key: value for key, value in call.items() if key != "parsed"})
    no_change = isinstance(call["parsed"], ChangeDecision) and not call["parsed"].change_required and not call["parsed"].files
    row["metrics"] = {"appropriate_no_change_behavior": float(no_change),
                      "unnecessary_modification_avoided": float(no_change)}
    row["quality_score"] = float(no_change)
    rows.append(row)
    return rows


def api_failure_cases(source: RestDataSource) -> list[dict]:
    cases = [("404", "json"), ("401", "json"), ("403", "json"), ("429", "json"),
             ("500", "json"), ("malformed", "json"), ("wrong-type", "json"),
             ("empty-image", "image"), ("oversized", "json"), ("timeout", "json")]
    rows = []
    for name, kind in cases:
        try:
            getattr(source, f"get_{kind}")(f"/api/errors/{name}")
            rows.append({"test": name, "correctly_blocked": False})
        except RetrievalError as exc:
            rows.append({"test": name, "correctly_blocked": True, **exc.result.as_dict()})
    return rows


PROFILES = {
    "fast": ("hallucination", "repository"),
    "vision": ("vision",),
    "camera": ("camera",),
    "sports": ("sports",),
    "agentic": ("agentic", "repository", "repository_change"),
    "rag": ("hallucination",),
    "hallucination": ("hallucination",),
    "full": ("vision", "camera", "sports", "hallucination", "agentic", "repository", "repository_change"),
}


def run_practical(alias: str, profile: str) -> tuple[Path, Path]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile {profile}; choose {', '.join(PROFILES)}")
    rows: list[dict] = []
    with FixtureServer() as fixture_server:
        source = RestDataSource(fixture_server.base_url, timeout=0.1, retries=0,
                                max_response_bytes=5 * 1024 * 1024, cache_dir=None)
        for category in PROFILES[profile]:
            if category in {"camera", "vision"} and not get_model(alias).multimodal:
                row = _base_row(alias, category, "capability-skip", [])
                row.update({"supported": False, "skip_reason": "model registry marks this model text-only",
                            "model_success": None, "parse_success": None, "schema_valid": None,
                            "quality_score": None, "memory": {}, "error": None})
                rows.append(row)
                continue
            if category == "camera":
                rows.extend(camera_cases(alias, source))
                rows.append(temporal_case(alias, source))
                rows.append(camera_qa_case(alias, source))
                rows.append(anomaly_case(alias, source))
                rows.append(ambiguous_camera_case(alias, source))
            elif category == "vision":
                rows.extend(vision_cases(alias, source))
            elif category == "sports":
                rows.extend(sports_cases(alias, source))
            elif category == "hallucination":
                rows.extend(hallucination_cases(alias, source))
            elif category == "agentic":
                rows.append(agentic_case(alias, source))
            elif category == "repository":
                rows.append(repository_case(alias))
                rows.extend(repository_tier_cases(alias))
            elif category == "repository_change":
                rows.append(repository_change_case(alias))
    return write_practical_report(alias, profile, rows)


def write_practical_report(alias: str, profile: str, rows: list[dict]) -> tuple[Path, Path]:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    jsonl = RESULT_DIR / f"{stamp}-{alias}-{profile}.jsonl"
    markdown = RESULT_DIR / f"{stamp}-{alias}-{profile}.md"
    jsonl.write_text("".join(json.dumps(row, default=str) + "\n" for row in rows))
    scores = category_scores(rows)
    speeds = sorted(row["tokens_per_second"] for row in rows if row.get("tokens_per_second"))
    median_speed = speeds[len(speeds) // 2] if speeds else 0
    peak_used = max((row.get("memory", {}).get("peak_system_used_gb") or 0 for row in rows), default=0)
    scores["speed"] = round(min(median_speed / 30, 1) * 10, 2)
    scores["memory_efficiency"] = round(max(0, 1 - peak_used / 24) * 10, 2)
    overall = round(sum(scores.values()) / len(scores), 2) if scores else 0
    state = read_state() or {}
    lines = [f"# Practical benchmark: {alias} / {profile}", "", "## System", "",
             f"- Platform: {platform.platform()}", f"- Memory now: {memory_snapshot()}",
             "", "## Model", "", f"- Model: {get_model(alias).model_id}",
             f"- Runtime: {get_model(alias).runtime}",
             f"- Cold startup: {state.get('startup_seconds') or next((row.get('startup_seconds') for row in rows if row.get('startup_seconds')), 'not recorded')} seconds",
             "", "## Performance", "",
             "| Category | Test | Retrieval | Model | TTFT | tok/s | Quality |",
             "|---|---|---|---|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| {row['benchmark']} | {row['test']} | {row.get('retrieval_success')} | {row.get('model_success')} | {row.get('ttft_seconds') or '-'} | {row.get('tokens_per_second') or '-'} | {row.get('quality_score') if row.get('quality_score') is not None else '-'} |")
    section_names = {
        "coding": "Coding",
        "cybersecurity": "Cybersecurity",
        "rag": "RAG",
        "vision": "Vision",
        "camera": "Camera analysis",
        "sports": "Sports",
        "agentic": "Agentic",
        "repository": "Agentic repository reasoning",
        "hallucination": "Hallucination resistance",
        "structured_output": "Structured Output",
    }
    for category in dict.fromkeys(row["benchmark"] for row in rows):
        lines += ["", f"## {section_names.get(category, category.title())}", ""]
        for row in (item for item in rows if item["benchmark"] == category):
            lines.append(
                f"- `{row['test']}`: quality={row.get('quality_score', '-')}, "
                f"model_success={row.get('model_success')}, retrieval={row.get('retrieval_success')}"
            )
    lines += ["", "## Normalized category scores", ""]
    lines.extend(f"- {name}: {score}/10" for name, score in scores.items())
    lines += ["", f"Overall (unweighted mean of displayed categories): {overall}/10"]
    failures = [row for row in rows if row.get("model_success") is False or row.get("infrastructure_failure")]
    skipped = [row for row in rows if row.get("supported") is False]
    unsupported = [row for row in rows if row["benchmark"] == "hallucination" and row.get("metrics", {}).get("unsupported_claim_rate")]
    peak = max((row.get("memory", {}).get("peak_system_used_gb") or 0 for row in rows), default=0)
    swap = max((row.get("memory", {}).get("peak_swap_used_gb") or 0 for row in rows), default=0)
    lines += ["", "## Difficulty breakdown", "",
              "| Category | Easy | Medium | Hard | Adversarial |", "|---|---:|---:|---:|---:|"]
    for category in dict.fromkeys(row["benchmark"] for row in rows):
        values = []
        for tier in ("easy", "medium", "hard", "adversarial"):
            tier_scores = [row["quality_score"] for row in rows if row["benchmark"] == category
                           and row.get("difficulty") == tier and row.get("quality_score") is not None]
            values.append(f"{sum(tier_scores) / len(tier_scores) * 100:.1f}%" if tier_scores else "N/A")
        lines.append(f"| {category} | {' | '.join(values)} |")
    lines += ["", "## Aggregate methodology", "",
              "- Category quality: unweighted mean of deterministic case scores within each category.",
              "- Speed and memory efficiency are separate displayed categories and are included in the displayed overall mean.",
              "- Missing/unsupported categories are omitted, not scored as zero.",
              "- Failed model cases receive zero quality; infrastructure failures receive no model-quality score.",
              "- Overall: unweighted mean of every displayed normalized category, including speed and memory efficiency.",
              "", "## Failures", "", f"- {len(failures)} model or infrastructure failures",
              f"- {len(skipped)} capability-aware skips",
              "", "## Unsupported Claims", "", f"- {len(unsupported)} unsupported-answer failures",
              "", "## Memory Behavior", "", f"- Peak sampled system used: {peak} GB", f"- Peak sampled swap: {swap} GB",
              "", "## Recommended Workloads", "", "Deterministic benchmark-derived recommendations; not objective truth."]
    recs = recommendations(scores)
    lines.extend(f"- {item}" for item in (recs or ["No recommendation threshold met in this profile."]))
    lines += ["", "Raw outputs, evidence, retrieval metadata, and errors are preserved in the JSONL file."]
    markdown.write_text("\n".join(lines) + "\n")
    return jsonl, markdown
