from __future__ import annotations

import base64
import json
import mimetypes
import subprocess
from pathlib import Path

import httpx
import typer
from rich import print

from local_mlx.advanced import (
    run_executable,
    run_photographic,
    run_realistic_rag,
    write_reliability_report,
)
from local_mlx.benchmark import comparison_report, run_suite
from local_mlx.comparison import compare_models
from local_mlx.config import ROOT, get_model, load_models
from local_mlx.health import health_report
from local_mlx.models import is_cached, missing_model_ids, server_command, start, stop
from local_mlx.practical import run_practical

app = typer.Typer(no_args_is_help=True)
CATEGORY_OPTION = typer.Option(None)
IMAGE_OPTION = typer.Option(..., exists=True, dir_okay=False)


@app.command()
def models() -> None:
    for alias, model in load_models().items():
        print(f"[bold]{alias}[/]: {model.model_id} ({model.runtime}, ~{model.estimated_download_gb} GB, cached={is_cached(model.model_id)})")


@app.command("start")
def start_command(alias: str) -> None:
    model = get_model(alias)
    print(f"Starting {model.model_id} with {model.runtime} on localhost only...")
    try:
        print(json.dumps(start(alias), indent=2))
    except (RuntimeError, TimeoutError) as exc:
        print(f"[red]Start failed:[/] {exc}")
        raise typer.Exit(1) from exc


@app.command("stop")
def stop_command() -> None:
    result = stop()
    print(json.dumps(result, indent=2) if result else "No managed model is running.")


@app.command()
def health() -> None:
    report = health_report()
    print(json.dumps(report, indent=2))
    if not report["running"]:
        raise typer.Exit(1)


@app.command()
def preflight(alias: str) -> None:
    model = get_model(alias)
    print(" ".join(server_command(model)))
    print(f"cached={is_cached(model.model_id)} localhost=127.0.0.1 context_cap={model.context_limit}")


@app.command()
def download(alias: str) -> None:
    model = get_model(alias)
    model_ids = [model.model_id, *model.additional_model_ids]
    print(f"About to download {', '.join(model_ids)} (~{model.estimated_download_gb} GB total).")
    print(f"Purpose: {model.notes}")
    if not typer.confirm("Continue?"):
        raise typer.Abort()
    for model_id in missing_model_ids(model):
        subprocess.run(["uv", "run", "hf", "download", model_id], cwd=ROOT, check=True)


@app.command()
def benchmark(
    model: str = typer.Option(...),
    context_size: int = typer.Option(2048),
    category: list[str] | None = CATEGORY_OPTION,
) -> None:
    jsonl, summary = run_suite(model, context_size, category)
    print(f"Results: {jsonl}\nSummary: {summary}")


@app.command("benchmark-all")
def benchmark_all(context_size: int = 2048) -> None:
    paths: list[Path] = []
    for alias in load_models():
        start(alias)
        try:
            jsonl, _ = run_suite(alias, context_size)
            paths.append(jsonl)
        finally:
            stop()
    print(f"Comparison: {comparison_report(paths)}")


@app.command("practical")
def practical_command(
    model: str = typer.Option("qwen"),
    profile: str = typer.Option("fast"),
) -> None:
    jsonl, summary = run_practical(model, profile)
    print(f"Results: {jsonl}\nSummary: {summary}")


@app.command("compare")
def compare_command(model_a: str, model_b: str) -> None:
    report, _ = compare_models(model_a, model_b)
    print(f"Comparison: {report}")


@app.command("bench-executable")
def bench_executable(model: str = typer.Option(...)) -> None:
    jsonl, report = run_executable(model)
    print(f"Results: {jsonl}\nSummary: {report}")


@app.command("bench-realistic-rag")
def bench_realistic_rag(model: str = typer.Option(...)) -> None:
    jsonl, report = run_realistic_rag(model)
    print(f"Results: {jsonl}\nSummary: {report}")


@app.command("bench-photographic")
def bench_photographic(model: str = typer.Option(...)) -> None:
    jsonl, report = run_photographic(model)
    print(f"Results: {jsonl}\nSummary: {report}")


@app.command("reliability-report")
def reliability_report() -> None:
    data, report = write_reliability_report()
    print(f"Data: {data}\nReport: {report}")


@app.command()
def chat(prompt: str) -> None:
    from local_mlx.client import LocalLLM

    print(LocalLLM().chat(prompt))


@app.command()
def multimodal(
    model: str = typer.Option(...),
    image: Path = IMAGE_OPTION,
    prompt: str = typer.Option("Describe this image precisely."),
) -> None:
    cfg = get_model(model)
    if not cfg.multimodal:
        raise typer.BadParameter(f"{model} is text-only")
    mime_type = mimetypes.guess_type(image.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(image.read_bytes()).decode("ascii")
    payload = {
        "model": cfg.model_id,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                    },
                ],
            }
        ],
        "max_tokens": 300,
    }
    response = httpx.post(f"{cfg.base_url}/chat/completions", json=payload, timeout=300)
    response.raise_for_status()
    print(response.json()["choices"][0]["message"]["content"])


@app.command("system-info")
def system_info() -> None:
    subprocess.run([str(ROOT / "scripts" / "system-info.sh")], check=True)


if __name__ == "__main__":
    app()
