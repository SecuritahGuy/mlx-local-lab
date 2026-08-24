from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psutil

from local_mlx.config import ROOT, STATE_DIR, ModelConfig, get_model

STATE_FILE = STATE_DIR / "active.json"


def memory_snapshot() -> dict[str, float | str]:
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "available_gb": round(vm.available / 2**30, 2),
        "used_gb": round(vm.used / 2**30, 2),
        "percent": vm.percent,
        "swap_used_gb": round(swap.used / 2**30, 2),
        "pressure": macos_memory_pressure(),
    }


def macos_memory_pressure() -> str:
    try:
        text = subprocess.run(
            ["memory_pressure", "-Q"], capture_output=True, text=True, timeout=3, check=False
        ).stdout.lower()
        marker = "system-wide memory free percentage:"
        free = int(text.split(marker, 1)[1].split("%", 1)[0].strip())
        if free < 5:
            return "critical"
        if free < 10:
            return "warn"
        return "normal"
    except (FileNotFoundError, subprocess.TimeoutExpired, IndexError, ValueError):
        return "unknown"


def hf_cache_path(model_id: str) -> Path:
    cache_root = Path(os.getenv("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    return cache_root / ("models--" + model_id.replace("/", "--"))


def is_cached(model_id: str) -> bool:
    path = hf_cache_path(model_id)
    return path.exists() and any(path.glob("snapshots/*/*.safetensors"))


def missing_model_ids(model: ModelConfig) -> list[str]:
    return [
        model_id
        for model_id in [model.model_id, *model.additional_model_ids]
        if not is_cached(model_id)
    ]


def read_state() -> dict | None:
    if not STATE_FILE.exists():
        return None
    try:
        state = json.loads(STATE_FILE.read_text())
        process = psutil.Process(state["pid"])
        if process.create_time() != state["create_time"]:
            return None
        return state
    except (json.JSONDecodeError, KeyError, psutil.Error):
        return None


def server_command(model: ModelConfig) -> list[str]:
    if model.runtime == "mlx-optiq":
        command = [
            "uvx",
            "--from",
            "mlx-optiq>=0.4.20",
            "optiq",
            "serve",
            "--model",
            model.model_id,
            "--host",
            "127.0.0.1",
            "--port",
            str(model.port),
            "--max-tokens",
            "2048",
            *model.startup_args,
        ]
    else:
        command = [
            sys.executable,
            "-m",
            model.startup_command,
            "--model",
            model.model_id,
            "--host",
            "127.0.0.1",
            "--port",
            str(model.port),
            "--max-tokens",
            "2048",
            *model.startup_args,
        ]
    if model.chat_template:
        command.extend(["--chat-template", model.chat_template])
    return command


def start(alias: str, timeout: int = 600) -> dict:
    model = get_model(alias)
    missing = missing_model_ids(model)
    if missing:
        raise RuntimeError(
            f"Required model artifacts are not cached: {', '.join(missing)} "
            f"(~{model.estimated_download_gb} GB total). "
            f"Run `make download MODEL={alias}` first."
        )
    active = read_state()
    if active:
        if active["alias"] == alias:
            return active
        stop()
    STATE_DIR.mkdir(exist_ok=True)
    log_path = STATE_DIR / f"{alias}.log"
    log = log_path.open("a")
    before = memory_snapshot()
    process = subprocess.Popen(
        server_command(model), cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    )
    state = {
        "alias": alias,
        "model_id": model.model_id,
        "runtime": model.runtime,
        "pid": process.pid,
        "create_time": psutil.Process(process.pid).create_time(),
        "base_url": model.base_url,
        "log": str(log_path),
        "memory_before": before,
        "started_at": time.time(),
    }
    STATE_FILE.write_text(json.dumps(state, indent=2))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            STATE_FILE.unlink(missing_ok=True)
            raise RuntimeError(f"Server exited with {process.returncode}; inspect {log_path}")
        try:
            response = httpx.get(f"http://127.0.0.1:{model.port}/health", timeout=2)
            if response.is_success:
                state["memory_after_load"] = memory_snapshot()
                state["startup_seconds"] = round(time.time() - state["started_at"], 4)
                STATE_FILE.write_text(json.dumps(state, indent=2))
                return state
        except httpx.HTTPError:
            pass
        time.sleep(2)
    stop()
    raise TimeoutError(f"Model did not become healthy in {timeout}s; inspect {log_path}")


def stop(timeout: int = 20) -> dict | None:
    state = read_state()
    if not state:
        STATE_FILE.unlink(missing_ok=True)
        return None
    process = psutil.Process(state["pid"])
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout)
    except psutil.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(5)
    STATE_FILE.unlink(missing_ok=True)
    state["memory_after_shutdown"] = memory_snapshot()
    return state
