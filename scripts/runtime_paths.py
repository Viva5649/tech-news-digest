#!/usr/bin/env python3
from datetime import datetime
from pathlib import Path
import os


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def generated_root() -> Path:
    override = os.environ.get("TECH_NEWS_DIGEST_OUTPUT_ROOT")
    path = Path(override).expanduser().resolve() if override else skill_root() / "generated"
    path.mkdir(parents=True, exist_ok=True)
    return path


def workspace_root() -> Path:
    return generated_root()


def archive_root() -> Path:
    path = generated_root() / "archive"
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_dir() -> Path:
    path = generated_root() / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_file(name: str) -> Path:
    return runtime_dir() / name


def make_run_dir(prefix: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = runtime_dir() / f"{prefix}-{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path
