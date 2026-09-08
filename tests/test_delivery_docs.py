import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MILESTONE_DIR = ROOT / "docs/milestones"


class DeliveryDocumentationTests(unittest.TestCase):
    def test_all_milestone_records_have_required_sections(self):
        records = sorted(MILESTONE_DIR.glob("[0-9][0-9]-*.md"))
        self.assertEqual(len(records), 6)
        required_headings = (
            "## 目标与背景",
            "## 实现内容",
            "## 对外行为变化",
            "## 验证证据",
            "## Commit 区间说明",
        )
        for record in records:
            text = record.read_text(encoding="utf-8")
            for heading in required_headings:
                with self.subTest(record=record.name, heading=heading):
                    self.assertIn(heading, text)

    def test_roadmap_has_project_specific_module_targets(self):
        text = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        for module in (
            "tools/query.py",
            "tools/manifest.py",
            "tools/save_synthesis.py",
            "tools/prepare_ingest.py",
            "tools/convert.py",
            "tools/build_graph.py",
            "tools/health.py",
        ):
            with self.subTest(module=module):
                self.assertIn(module, text)
        self.assertGreaterEqual(text.count("### "), 8)

    def test_milestone_index_covers_full_history_and_upload_head(self):
        text = (MILESTONE_DIR / "README.md").read_text(encoding="utf-8")
        for boundary in ("`c0cacd3`", "`e6ae7b9`", "`0c8ca77`", "`94df9ee`", "`839e8ff`", "`4bf48b7`"):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, text)
        self.assertIn("upload candidate `HEAD`", text)
        self.assertIn("git rev-parse HEAD", text)


if __name__ == "__main__":
    unittest.main()
