import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocsInterfaceTests(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text(encoding="utf-8")

    def assert_no_current_support_claims(self, rel, phrases):
        text = self.read(rel)
        normalized = text.replace("\n", " ")
        sentences = [
            sentence.strip()
            for sentence in normalized.replace(";", ".").split(".")
            if sentence.strip()
        ]
        safe_markers = (
            "does not",
            "do not",
            "doesn't",
            "no pdf",
            "no office",
            "no llm",
            "unsupported",
            "not supported",
            "not implemented",
            "not converted",
            "future work",
            "remain future work",
            "future versions",
            "ask the user",
            "rather than",
            "不支持",
            "暂不直接支持",
            "仍不支持",
            "不调用",
            "不会调用",
        )
        for phrase in phrases:
            matches = [
                sentence
                for sentence in sentences
                if phrase in sentence.lower()
                and not any(marker in sentence.lower() for marker in safe_markers)
            ]
            self.assertEqual(
                [],
                matches,
                f"{rel} appears to claim current support for {phrase!r}: {matches}",
            )

    def test_readme_marks_tools_implemented_or_partial(self):
        readme = self.read("README.md")
        self.assertIn("| Semantic lint | Implemented |", readme)
        self.assertIn("| Graph generation | Implemented |", readme)
        self.assertIn("| Source conversion | Partial |", readme)
        self.assertNotIn("returns exit code `3`", readme)

    def test_readme_has_a_complete_clone_to_demo_path(self):
        readme = self.read("README.md")
        required_steps = (
            "git clone https://github.com/12138xs/MuvyWiki.git",
            "cd MuvyWiki",
            "python3 -m venv .venv",
            "source .venv/bin/activate",
            "python --version",
            "python tools/health.py",
            "python tools/demo.py",
            "MuvyWiki demo: ok",
            "Workspace modified: no",
        )
        for step in required_steps:
            with self.subTest(step=step):
                self.assertIn(step, readme)
        self.assertIn("Python 3.10 or newer", readme)
        self.assertIn("No third-party runtime dependencies", readme)

    def test_current_onboarding_docs_do_not_reference_missing_example_inputs(self):
        invalid_paths = (
            "raw/originals/example.md",
            "raw/originals/example.txt",
            "raw/converted/example.md",
            "/tmp/answer.md",
            "/tmp/evidence.md",
        )
        for doc in ("README.md", "USER_GUIDE.md", "AGENTS.md"):
            text = self.read(doc)
            for invalid_path in invalid_paths:
                with self.subTest(doc=doc, invalid_path=invalid_path):
                    self.assertNotIn(invalid_path, text)

    def test_readme_documentation_links_exist(self):
        paths = (
            "USER_GUIDE.md",
            "AGENTS.md",
            "raw/README.md",
            "graph/README.md",
            "examples/ingest/README.md",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())

    def test_agents_do_not_call_interfaces_reserved(self):
        agents = self.read("AGENTS.md")
        self.assertIn("Implemented deterministic interfaces", agents)
        self.assertIn("python tools/lint.py", agents)
        self.assertIn("python tools/build_graph.py", agents)
        self.assertIn("python tools/convert.py", agents)
        self.assertIn("python tools/prepare_ingest.py", agents)
        self.assertIn("python tools/manifest.py", agents)
        self.assertNotIn("Reserved interfaces:", agents)

    def test_ingest_prep_interfaces_are_documented(self):
        readme = self.read("README.md")
        guide = self.read("USER_GUIDE.md")
        agents = self.read("AGENTS.md")
        raw = self.read("raw/README.md")
        graph = self.read("graph/README.md")
        for text in (readme, guide, agents):
            self.assertIn("python tools/prepare_ingest.py", text)
            self.assertIn("python tools/manifest.py", text)
        self.assertIn("manifest.py", raw)
        self.assertIn("ingest-prep-report.md", graph)

    def test_fixture_support_docs_match_current_interfaces(self):
        agents = self.read("examples/ingest/AGENTS.md")
        graph = self.read("examples/ingest/graph/README.md")
        readme_snapshot = self.read("examples/ingest/README-root.md")
        for text in (agents, graph, readme_snapshot):
            self.assertNotIn("reserved", text.lower())
            self.assertNotIn("exit code `3`", text)
        self.assertIn("lightweight local interfaces", agents)
        self.assertIn("python tools/build_graph.py --repo-root examples/ingest", graph)
        self.assertIn("python tools/query.py --repo-root examples/ingest", readme_snapshot)

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
        self.assertIn("python tools/lint.py --repo-root examples/ingest", agents)
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
        self.assertNotIn("ingesting a URL", design)
        self.assertNotIn("<input_path_or_url>", design)

    def test_docs_do_not_claim_unsupported_current_automation(self):
        docs = [
            "README.md",
            "USER_GUIDE.md",
            "AGENTS.md",
            "raw/README.md",
            "graph/README.md",
            "examples/ingest/README.md",
            "docs/superpowers/specs/2026-05-12-muvywiki-design.md",
        ]
        phrases = [
            "fetch remote",
            "crawl",
            "render remote",
            "automatic ingest",
            "automatic wiki page creation",
            "pdf conversion is implemented",
            "office documents are supported",
            "llm extraction is implemented",
            "automatically extracts",
            "automatic pdf",
            "automatic office",
            "pdf 转换已实现",
            "office 文档已支持",
            "llm 自动抽取已实现",
        ]
        for doc in docs:
            with self.subTest(doc=doc):
                self.assert_no_current_support_claims(doc, phrases)

    def test_ingest_example_documents_duplicate_preflight_exit_code(self):
        readme = self.read("examples/ingest/README.md")
        self.assertIn("python tools/prepare_ingest.py --repo-root examples/ingest raw/originals/tiny-rag-note.md", readme)
        self.assertIn("expected to exit `1`", readme)

    def test_query_and_synthesis_interfaces_are_documented(self):
        readme = self.read("README.md")
        guide = self.read("USER_GUIDE.md")
        agents = self.read("AGENTS.md")
        graph = self.read("graph/README.md")
        design = self.read("docs/superpowers/specs/2026-05-12-muvywiki-design.md")
        for text in (readme, guide, agents):
            self.assertIn("python tools/query.py", text)
            self.assertIn("python tools/save_synthesis.py", text)
        self.assertIn("wiki/syntheses/", graph)
        self.assertIn("synthesis` nodes", graph)
        self.assertIn("graph outputs", graph)
        self.assertIn("## Query & Synthesis v1 update", design)

    def test_manifest_find_docs_use_option_form(self):
        docs = [
            "README.md",
            "USER_GUIDE.md",
            "AGENTS.md",
            "raw/README.md",
            "examples/ingest/README.md",
            "examples/ingest/README-root.md",
            "examples/ingest/AGENTS.md",
            "examples/ingest/raw/README.md",
            "docs/superpowers/specs/2026-05-12-muvywiki-design.md",
            "docs/superpowers/specs/2026-05-12-ingest-v2-design.md",
        ]
        option_examples = (
            "python tools/manifest.py find --source-id",
            "python tools/manifest.py find --hash",
            "python tools/manifest.py find --path",
            "python tools/manifest.py --repo-root examples/ingest find --source-id",
            "python tools/manifest.py --repo-root examples/ingest find --hash",
            "python tools/manifest.py --repo-root examples/ingest find --path",
        )
        for doc in docs:
            with self.subTest(doc=doc):
                text = self.read(doc)
                self.assertNotIn("manifest.py find <source-id-or-hash>", text)
                self.assertNotRegex(text, r"manifest\.py find (?!--)[^\s`]+")
                self.assertTrue(
                    any(example in text for example in option_examples),
                    f"{doc} must document manifest.py find with an option form",
                )

    def test_historical_plans_are_labeled(self):
        initial = self.read("docs/superpowers/plans/2026-05-12-muvywiki-implementation.md")
        ingest = self.read("docs/superpowers/plans/2026-05-13-ingest-v2.md")
        interface = self.read("docs/superpowers/plans/2026-05-13-interface-v1.md")
        self.assertIn("Historical plan", initial)
        self.assertIn("Historical plan", ingest)
        self.assertIn("Historical plan", interface)


if __name__ == "__main__":
    unittest.main()
