#!/usr/bin/env python3
"""
Source health monitoring for tech-news-digest pipeline.

Tracks per-source success/failure history and reports unhealthy sources.

Usage:
    python3 source-health.py --rss rss.json --twitter twitter.json --github github.json [--output health.json]
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from runtime_paths import runtime_file

HEALTH_FILE = str(runtime_file("tech-news-digest-source-health.json"))
HISTORY_DAYS = 7
FAILURE_THRESHOLD = 0.5


def setup_logging(verbose: bool) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")
    return logging.getLogger(__name__)


def load_health_data() -> Dict[str, Any]:
    try:
        with open(HEALTH_FILE, "r") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_health_data(data: Dict[str, Any]) -> None:
    with open(HEALTH_FILE, "w") as handle:
        json.dump(data, handle, indent=2)


def load_source_file(path: Optional[Path]) -> list:
    if not path or not path.exists():
        return []
    try:
        with open(path, "r") as handle:
            data = json.load(handle)
        return data.get("sources", [])
    except (json.JSONDecodeError, OSError):
        return []


def load_source_file_flexible(path: Optional[Path]) -> list:
    if not path or not path.exists():
        return []
    try:
        with open(path, "r") as handle:
            data = json.load(handle)
        if "sources" in data:
            return data["sources"]
        if "subreddits" in data:
            return data["subreddits"]
        if "topics" in data:
            synthetic = []
            for topic in data["topics"]:
                synthetic.append(
                    {
                        "source_id": f"web-{topic.get('topic_id', 'unknown')}",
                        "name": f"Web: {topic.get('topic_id', 'unknown')}",
                        "status": topic.get("status", "ok"),
                        "articles": topic.get("articles", []),
                    }
                )
            return synthetic
        return []
    except (json.JSONDecodeError, OSError):
        return []


def update_health(health: Dict[str, Any], sources: list, now: float) -> None:
    cutoff = now - HISTORY_DAYS * 86400
    for source in sources:
        source_id = source.get("source_id", source.get("id", "unknown"))
        if source_id not in health:
            health[source_id] = {"name": source.get("name", source_id), "checks": []}
        health[source_id]["checks"] = [check for check in health[source_id]["checks"] if check["ts"] > cutoff]
        health[source_id]["checks"].append({"ts": now, "ok": source.get("status") == "ok"})


def report_unhealthy(health: Dict[str, Any], logger: logging.Logger) -> int:
    unhealthy = 0
    for source_id, info in health.items():
        checks = info.get("checks", [])
        if len(checks) < 2:
            continue
        failures = sum(1 for check in checks if not check["ok"])
        failure_rate = failures / len(checks)
        if failure_rate > FAILURE_THRESHOLD:
            logger.warning(
                f"⚠️  Unhealthy source: {info.get('name', source_id)} "
                f"({failures}/{len(checks)} failures, {failure_rate:.0%} failure rate)"
            )
            unhealthy += 1
    return unhealthy


def main() -> int:
    parser = argparse.ArgumentParser(description="Track source health for tech-news-digest pipeline.")
    parser.add_argument("--rss", type=Path, help="RSS output JSON")
    parser.add_argument("--twitter", type=Path, help="Twitter output JSON")
    parser.add_argument("--github", type=Path, help="GitHub output JSON")
    parser.add_argument("--reddit", type=Path, help="Reddit output JSON")
    parser.add_argument("--web", type=Path, help="Web search output JSON")
    parser.add_argument("--output", type=Path, help="Optional JSON summary output path")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logger = setup_logging(args.verbose)
    health = load_health_data()
    now = time.time()
    processed_inputs = []

    for label, path in [("rss", args.rss), ("twitter", args.twitter), ("github", args.github)]:
        sources = load_source_file(path)
        if sources:
            update_health(health, sources, now)
            processed_inputs.append({"name": label, "path": str(path), "count": len(sources)})

    for label, path in [("reddit", args.reddit), ("web", args.web)]:
        sources = load_source_file_flexible(path)
        if sources:
            update_health(health, sources, now)
            processed_inputs.append({"name": label, "path": str(path), "count": len(sources)})

    save_health_data(health)
    unhealthy = report_unhealthy(health, logger)

    total = len(health)
    summary = {
        "status": "ok",
        "tracked_sources": total,
        "unhealthy_sources": unhealthy,
        "inputs": processed_inputs,
        "health_file": HEALTH_FILE,
        "checked_at": datetime.utcfromtimestamp(now).isoformat() + "Z",
    }

    if args.output:
        with open(args.output, "w") as handle:
            json.dump(summary, handle, indent=2)

    logger.info(f"📊 Health check: {total} sources tracked, {unhealthy} unhealthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
