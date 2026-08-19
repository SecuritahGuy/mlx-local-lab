import json

from local_mlx.comparison import compare_models, meaningful_winner, ttft_outliers


def row(model: str, test: str, quality: float, ttft: float = 1.0) -> dict:
    return {"model": model, "model_id": model, "runtime": "mlx-vlm", "benchmark": "camera",
            "test": test, "difficulty": "hard", "quality_score": quality,
            "supported": True, "model_success": True, "schema_valid": True,
            "ttft_seconds": ttft, "tokens_per_second": 10, "download_latency": 0.01,
            "retrieval": [], "memory": {"peak_system_used_gb": 10, "peak_process_rss_gb": 1,
            "peak_swap_used_gb": 0, "worst_pressure": "normal"}, "output": "answer",
            "timestamp": f"2026-01-01T00:00:0{int(ttft)}Z", "input_type": "image",
            "prompt_tokens": 100, "output_tokens": 20, "model_latency": 3}


def test_meaningful_margin_supports_ties() -> None:
    assert meaningful_winner(9.57, 9.58) == "Tie"
    assert meaningful_winner(9.0, 9.5) == "B"


def test_robust_ttft_outlier_rule() -> None:
    rows = [row("qwen", f"case-{index}", 1, value) for index, value in enumerate((0.8, 1, 1.1, 7.9))]
    threshold, outliers = ttft_outliers(rows)
    assert threshold == 3.15
    assert [item["test"] for item in outliers] == ["case-3"]
    assert "image" in outliers[0]["evidence_based_explanation"]


def test_comparison_reports_case_regressions_and_difficulty(tmp_path) -> None:
    for model, quality in (("qwen", 1.0), ("gemma", 0.5)):
        practical = tmp_path / f"20260101-{model}-camera.jsonl"
        practical.write_text(json.dumps(row(model, "hard-door", quality)) + "\n")
        context = tmp_path / f"20260101-{model}-ctx2048.jsonl"
        context.write_text(json.dumps({**row(model, "rag", 1), "benchmark": "rag",
                                      "difficulty": "easy", "input_type": "text"}) + "\n")
    report, data = compare_models("qwen", "gemma", tmp_path)
    text = report.read_text()
    assert "hard-door" in text
    assert "camera / hard" in text
    assert data["regressions"][0]["delta"] == -0.5
