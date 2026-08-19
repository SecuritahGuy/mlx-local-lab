import json

from local_mlx.practical import write_practical_report


def test_report_preserves_raw_results_and_recommendation(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("local_mlx.practical.RESULT_DIR", tmp_path)
    rows = [{"benchmark": "camera", "test": "fixture", "retrieval_success": True,
             "model_success": True, "ttft_seconds": 0.2, "tokens_per_second": 20,
             "quality_score": 0.9, "memory": {"peak_system_used_gb": 10,
             "peak_swap_used_gb": 0}, "metrics": {"accuracy": 1}}]
    jsonl, report = write_practical_report("qwen", "camera", rows)
    assert json.loads(jsonl.read_text())["metrics"]["accuracy"] == 1
    text = report.read_text()
    assert "Camera analysis" in text
    assert "benchmark-derived" in text
