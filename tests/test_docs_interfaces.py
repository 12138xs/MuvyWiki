import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocsInterfaceTests(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_readme_marks_tools_implemented_or_partial(self):
        readme = self.read("README.md")
        self.assertIn("| Semantic lint | Implemented |", readme)
        self.assertIn("| Graph generation | Implemented |", readme)
        self.assertIn("| Source conversion | Partial |", readme)
        self.assertNotIn("returns exit code `3`", readme)

    def test_agents_do_not_call_interfaces_reserved(self):
        agents = self.read("AGENTS.md")
        self.assertIn("Implemented deterministic interfaces", agents)
        self.assertIn("python tools/lint.py", agents)
        self.assertIn("python tools/build_graph.py", agents)
        self.assertIn("python tools/convert.py", agents)
        self.assertNotIn("Reserved interfaces:", agents)

    def test_fixture_support_docs_match_current_interfaces(self):
        agents = self.read("examples/ingest/AGENTS.md")
        graph = self.read("examples/ingest/graph/README.md")
        readme_snapshot = self.read("examples/ingest/README-root.md")
        for text in (agents, graph, readme_snapshot):
            self.assertNotIn("reserved", text.lower())
            self.assertNotIn("exit code `3`", text)
        self.assertIn("lightweight local interfaces", agents)
        self.assertIn("python tools/build_graph.py", graph)
        self.assertIn("python tools/convert.py raw/originals/example.txt", readme_snapshot)

    def test_raw_and_graph_docs_describe_current_outputs(self):
        raw = self.read("raw/README.md")
        fixture_raw = self.read("examples/ingest/raw/README.md")
        graph = self.read("graph/README.md")
        self.assertIn("local Markdown/text conversion", raw)
        self.assertIn("does not update source-manifest.jsonl", raw)
        self.assertIn("local Markdown/text conversion", fixture_raw)
        self.assertIn("does not update source-manifest.jsonl", fixture_raw)
        self.assertNotIn("example.pdf", raw)
        self.assertNotIn("example.pdf", fixture_raw)
        self.assertIn("graph.json", graph)
        self.assertIn("graph.html", graph)
        self.assertIn("graph-report.md", graph)

    def test_maintenance_docs_include_current_verification(self):
        agents = self.read("AGENTS.md")
        guide = self.read("USER_GUIDE.md")
        self.assertIn("python -m unittest tests/test_docs_interfaces.py", agents)
        self.assertIn("python tools/lint.py", agents)
        self.assertIn("python tools/build_graph.py", agents)
        self.assertIn("cd examples/ingest && python tools/lint.py", agents)
        self.assertIn("docs/superpowers/specs", guide)
        self.assertIn("相关目录 README", guide)

    def test_referenced_design_docs_reflect_interface_v1(self):
        design = self.read("docs/superpowers/specs/2026-05-12-muvywiki-design.md")
        ingest = self.read("docs/superpowers/specs/2026-05-12-ingest-v2-design.md")
        self.assertIn("Interface v1 update", design)
        self.assertIn("Interface v1 update", ingest)
        self.assertNotIn("reserved interfaces with documented command behavior", design)
        self.assertNotIn("must use exit code `3`", design)
        self.assertNotIn("remain reserved interfaces", ingest)

    def test_query_and_synthesis_interfaces_are_documented(self):
        readme = self.read("README.md")
        guide = self.read("USER_GUIDE.md")
        agents = self.read("AGENTS.md")
        graph = self.read("graph/README.md")
        design = self.read("docs/superpowers/specs/2026-05-12-muvywiki-design.md")
        for text in (readme, guide, agents):
            self.assertIn("python tools/query.py", text)
            self.assertIn("python tools/save_synthesis.py", text)
        self.assertIn("saved syntheses appear in graph outputs", graph)
        self.assertIn("## Query & Synthesis v1 update", design)

    def test_historical_plans_are_labeled(self):
        initial = self.read("docs/superpowers/plans/2026-05-12-muvywiki-implementation.md")
        ingest = self.read("docs/superpowers/plans/2026-05-13-ingest-v2.md")
        interface = self.read("docs/superpowers/plans/2026-05-13-interface-v1.md")
        self.assertIn("Historical plan", initial)
        self.assertIn("Historical plan", ingest)
        self.assertIn("Historical plan", interface)


if __name__ == "__main__":
    unittest.main()
