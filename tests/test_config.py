#!/usr/bin/env python3
"""Tests for config_loader.py."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from config_loader import load_merged_sources, load_merged_topics

DEFAULTS_DIR = Path(__file__).parent.parent / "config" / "defaults"
README_EN = Path(__file__).parent.parent / "README.md"
README_ZH = Path(__file__).parent.parent / "README_CN.md"


def get_source_counts():
    sources = load_merged_sources(DEFAULTS_DIR)
    return {
        "total": len(sources),
        "rss": len([s for s in sources if s["type"] == "rss"]),
        "twitter": len([s for s in sources if s["type"] == "twitter"]),
        "github": len([s for s in sources if s["type"] == "github"]),
        "reddit": len([s for s in sources if s["type"] == "reddit"]),
    }


class TestLoadSources(unittest.TestCase):
    def test_loads_defaults(self):
        sources = load_merged_sources(DEFAULTS_DIR)
        self.assertGreater(len(sources), 100)

    def test_all_sources_have_required_fields(self):
        sources = load_merged_sources(DEFAULTS_DIR)
        for source in sources:
            self.assertIn("id", source, f"Source missing id: {source}")
            self.assertIn("type", source, f"Source missing type: {source}")
            self.assertIn("enabled", source, f"Source missing enabled: {source}")

    def test_source_types(self):
        sources = load_merged_sources(DEFAULTS_DIR)
        types = set(source["type"] for source in sources)
        self.assertIn("rss", types)
        self.assertIn("twitter", types)
        self.assertIn("github", types)
        self.assertIn("reddit", types)

    def test_user_overlay_merges(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            overlay = {
                "sources": [
                    {"id": "test-new-source", "type": "rss", "enabled": True, "url": "https://test.com/feed"},
                ]
            }
            overlay_path = Path(tmpdir) / "tech-news-digest-sources.json"
            with open(overlay_path, "w") as handle:
                json.dump(overlay, handle)

            sources = load_merged_sources(DEFAULTS_DIR, Path(tmpdir))
            ids = [source["id"] for source in sources]
            self.assertIn("test-new-source", ids)

    def test_user_overlay_disables(self):
        defaults = load_merged_sources(DEFAULTS_DIR)
        first_id = defaults[0]["id"]

        with tempfile.TemporaryDirectory() as tmpdir:
            overlay = {
                "sources": [
                    {"id": first_id, "type": defaults[0]["type"], "enabled": False},
                ]
            }
            overlay_path = Path(tmpdir) / "tech-news-digest-sources.json"
            with open(overlay_path, "w") as handle:
                json.dump(overlay, handle)

            sources = load_merged_sources(DEFAULTS_DIR, Path(tmpdir))
            matched = [source for source in sources if source["id"] == first_id]
            self.assertEqual(len(matched), 1)
            self.assertFalse(matched[0]["enabled"])

    def test_no_overlay_dir(self):
        sources = load_merged_sources(DEFAULTS_DIR, None)
        self.assertGreater(len(sources), 100)


class TestLoadTopics(unittest.TestCase):
    def test_loads_defaults(self):
        topics = load_merged_topics(DEFAULTS_DIR)
        self.assertGreater(len(topics), 0)

    def test_topics_have_required_fields(self):
        topics = load_merged_topics(DEFAULTS_DIR)
        for topic in topics:
            self.assertIn("id", topic, f"Topic missing id: {topic}")
            self.assertIn("label", topic, f"Topic missing label: {topic}")

    def test_topic_ids(self):
        topics = load_merged_topics(DEFAULTS_DIR)
        ids = [topic["id"] for topic in topics]
        self.assertIn("llm", ids)
        self.assertIn("crypto", ids)


class TestSourceCounts(unittest.TestCase):
    def test_total_sources(self):
        sources = load_merged_sources(DEFAULTS_DIR)
        enabled = [source for source in sources if source.get("enabled", True)]
        self.assertGreaterEqual(len(enabled), 130)

    def test_twitter_count(self):
        counts = get_source_counts()
        self.assertEqual(counts["twitter"], 48)

    def test_rss_count(self):
        counts = get_source_counts()
        self.assertEqual(counts["rss"], 78)

    def test_github_count(self):
        counts = get_source_counts()
        self.assertEqual(counts["github"], 29)

    def test_reddit_count(self):
        counts = get_source_counts()
        self.assertEqual(counts["reddit"], 13)


class TestValidateConfigCli(unittest.TestCase):
    def test_validate_config_works_from_arbitrary_cwd(self):
        script = SCRIPTS_DIR / "validate-config.py"
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [sys.executable, str(script)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("All validations passed", result.stdout + result.stderr)


class TestReadmeCounts(unittest.TestCase):
    def test_english_readme_counts_are_current(self):
        counts = get_source_counts()
        content = README_EN.read_text(encoding="utf-8")
        self.assertIn(
            f"Automated tech news digest — {counts['total']} built-in sources, 6-source pipeline, one chat message to install.",
            content,
        )
        self.assertIn(
            f"A quality-scored, deduplicated tech digest built from **{counts['total']} built-in sources** plus **4 web search topics**:",
            content,
        )
        self.assertIn(f"| 📡 RSS | {counts['rss']} feeds |", content)
        self.assertIn(f"| 🐙 GitHub | {counts['github']} repos |", content)
        self.assertIn(
            f"`config/defaults/sources.json` — {counts['total']} built-in sources ({counts['rss']} RSS, {counts['twitter']} Twitter, {counts['github']} GitHub, {counts['reddit']} Reddit)",
            content,
        )

    def test_chinese_readme_counts_are_current(self):
        counts = get_source_counts()
        content = README_ZH.read_text(encoding="utf-8")
        self.assertIn(
            f"自动化科技资讯汇总 — {counts['total']} 个内置数据源，6 层管道，一句话安装。",
            content,
        )
        self.assertIn(
            f"基于 **{counts['total']} 个内置数据源** + **4 个 Web 搜索主题** 的质量评分、去重科技日报：",
            content,
        )
        self.assertIn(f"| 📡 RSS | {counts['rss']} 个订阅源 |", content)
        self.assertIn(f"| 🐙 GitHub | {counts['github']} 个仓库 |", content)
        self.assertIn(
            f"`config/defaults/sources.json` — {counts['total']} 个内置数据源（{counts['rss']} RSS、{counts['twitter']} Twitter、{counts['github']} GitHub、{counts['reddit']} Reddit）",
            content,
        )


if __name__ == "__main__":
    unittest.main()
