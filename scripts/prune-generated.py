#!/usr/bin/env python3
"""
Prune stale generated reports and their per-report artifacts.

Retention policy is intentionally conservative:
- Only operates inside this skill's own generated directories
- Only deletes report files older than the configured retention window
- Keeps shared reusable runtime artifacts such as caches
"""

import argparse
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from runtime_paths import archive_root, runtime_dir


DATE_FMT = "%Y-%m-%d"


def setup_logging(verbose: bool) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(__name__)


def iter_report_artifacts(prefix: str) -> Iterable[Path]:
    runtime = runtime_dir()
    yield from runtime.glob(f"{prefix}*")


def delete_path(path: Path, logger: logging.Logger, dry_run: bool) -> None:
    if dry_run:
        logger.info(f"DRY RUN delete: {path}")
        return
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()
    logger.info(f"Deleted: {path}")


def prune(mode: str, days: int, dry_run: bool, logger: logging.Logger) -> int:
    reports_dir = archive_root()
    cutoff = datetime.now().date() - timedelta(days=days)
    pattern = f"{mode}-*.md"

    deleted = 0
    kept = 0

    for report in sorted(reports_dir.glob(pattern)):
        stem = report.stem
        date_str = stem[len(mode) + 1:]
        try:
            report_date = datetime.strptime(date_str, DATE_FMT).date()
        except ValueError:
            logger.debug(f"Skip non-standard report name: {report.name}")
            continue

        if report_date >= cutoff:
            kept += 1
            continue

        delete_path(report, logger, dry_run)
        deleted += 1
        for artifact in iter_report_artifacts(stem):
            delete_path(artifact, logger, dry_run)

    logger.info(f"Prune done: deleted={deleted}, kept={kept}, mode={mode}, retention_days={days}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune stale generated tech-news-digest reports")
    parser.add_argument("--mode", choices=["daily", "weekly"], default="weekly")
    parser.add_argument("--days", type=int, default=30, help="Retention window in days")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logger = setup_logging(args.verbose)
    return prune(args.mode, args.days, args.dry_run, logger)


if __name__ == "__main__":
    raise SystemExit(main())
