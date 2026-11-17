from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

VCS = Path(__file__).resolve().parents[1] / "scripts" / "vcs.py"
spec = importlib.util.spec_from_file_location("vcs_merge_test", VCS)
vcs = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(vcs)


class MergeTest(unittest.TestCase):
    def test_exact_overlap(self) -> None:
        result = vcs.deduplicate_text_segments(["abcdef中文重复", "中文重复后续内容", "完全不同"])
        self.assertEqual(result, ["abcdef中文重复", "后续内容", "完全不同"])

    def test_fuzzy_overlap_and_spacing(self) -> None:
        left = "Intro " + ("A" * 220) + " Strategic Petroleum Reserve releases supported the market"
        right = ("A" * 220) + " Strategic Petroleum reserves supported the market and refills later"
        merged = "".join(vcs.deduplicate_text_segments([left, right, "next sentence"]))
        self.assertIn("and refills later next sentence", merged)
        self.assertEqual(merged.count("A" * 220), 1)

    def test_unanchored_match_is_not_cut(self) -> None:
        left = "导演在采访中说：请注意，以下内容可能包含剧透。"
        right = "大家好，欢迎收看本期节目。请注意，以下内容可能包含剧透，我们将深入分析。"
        merged = "".join(vcs.deduplicate_text_segments([left, right]))
        self.assertIn("大家好，欢迎收看本期节目", merged)
        self.assertEqual(merged.count("请注意，以下内容可能包含剧透"), 2)

    def test_stage_aliases(self) -> None:
        self.assertEqual(vcs.normalize_stage("final"), "compose")
        self.assertEqual(vcs.normalize_stage("compose"), "compose")
        self.assertEqual(vcs.normalize_stage("cleanup"), "cleanup")
        self.assertIsNone(vcs.normalize_stage(None))

    def test_english_punctuation_gets_space(self) -> None:
        merged = "".join(vcs.deduplicate_text_segments([
            "The boundary ends with Donald Trump.",
            "Have AI debates moved on?",
        ]))
        self.assertIn("Trump. Have", merged)


if __name__ == "__main__":
    unittest.main()
