from __future__ import annotations

import json
import subprocess
from pathlib import Path

import httpx
import typer
from rich import print

from local_mlx.benchmark import comparison_report, run_suite
from local_mlx.comparison import compare_models
from local_mlx.config import ROOT, get_model, load_models
from local_mlx.health import health_report
from local_mlx.models import is_cached, server_command, start, stop
from local_mlx.practical import run_practical

app = typer.Typer(no_args_is_help=True)
CATEGORY_OPTION = typer.Option(None)


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
    print(f"About to download {model.model_id} (~{model.estimated_download_gb} GB).")
    print(f"Purpose: {model.notes}")
    if not typer.confirm("Continue?"):
        raise typer.Abort()
    subprocess.run(["uv", "run", "hf", "download", model.model_id], cwd=ROOT, check=True)


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


@app.command()
def chat(prompt: str) -> None:
    from local_mlx.client import LocalLLM

    print(LocalLLM().chat(prompt))


@app.command()
def multimodal(model: str, image: Path, prompt: str = "Describe this image precisely.") -> None:
    cfg = get_model(model)
    if not cfg.multimodal:
        raise typer.BadParameter(f"{model} is text-only")
    payload = {
        "model": cfg.model_id,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image.resolve().as_uri()}},
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
