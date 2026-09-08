import json
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SaveSynthesisToolTests(unittest.TestCase):
    def make_repo(self):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        for rel in (
            "raw/originals",
            "raw/converted",
            "wiki/sources",
            "wiki/concepts",
            "wiki/entities",
            "wiki/syntheses",
            "templates",
            "tools",
            "graph",
        ):
            (root / rel).mkdir(parents=True, exist_ok=True)
        for rel in (
            ".gitignore",
            "README.md",
            "AGENTS.md",
            "raw/README.md",
            "templates/overview.md",
            "templates/index-entry.md",
            "templates/log-entry.md",
            "templates/source.md",
            "templates/concept.md",
            "templates/entity.md",
            "templates/synthesis.md",
            "tools/lint.py",
            "tools/build_graph.py",
            "tools/convert.py",
            "tools/demo.py",
            "tools/query.py",
            "graph/README.md",
        ):
            (root / rel).write_text("placeholder\n", encoding="utf-8")
        for tool in ("wiki_utils.py", "save_synthesis.py", "health.py"):
            shutil.copy(ROOT / "tools" / tool, root / "tools" / tool)

        (root / "raw/originals/source-one.txt").write_text("source body\n", encoding="utf-8")
        (root / "raw/source-manifest.jsonl").write_text(
            json.dumps(
                {
                    "source_id": "source-one",
                    "raw_path": "raw/originals/source-one.txt",
                    "content_hash": "sha256:abc123",
                    "source_url": None,
                    "collected_at": "2026-05-12",
                    "published_at": None,
                    "converted_from": None,
                    "converted_path": None,
                    "converter": None,
                    "converter_version": None,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.write_page(root / "wiki/overview.md", "overview", "overview", "Overview", "Knowledge map.")
        self.write_page(
            root / "wiki/concepts/RetrievalAugmentedGeneration.md",
            "RetrievalAugmentedGeneration",
            "concept",
            "Retrieval-Augmented Generation",
            "## Definition\n\nRAG retrieves source context before generation.\n",
        )
        self.write_source_page(root / "wiki/sources/source-one.md")
        (root / "wiki/index.md").write_text(
            """# MuvyWiki Index

## Overview

- [[overview|Overview]] (`wiki/overview.md`) - type: overview - updated: 2026-05-12 - Living map.

## Sources

- [[source-one|Source One]] (`wiki/sources/source-one.md`) - type: source - updated: 2026-05-12 - Test source.

## Concepts

- [[RetrievalAugmentedGeneration|Retrieval-Augmented Generation]] (`wiki/concepts/RetrievalAugmentedGeneration.md`) - type: concept - updated: 2026-05-12 - Test concept.

## Entities

No entity pages yet.

## Syntheses

No synthesis pages yet.
""",
            encoding="utf-8",
        )
        (root / "wiki/log.md").write_text(
            """# MuvyWiki Log

## [2026-05-12] init | fixture

- Changed pages:
  - `wiki/index.md`
  - `wiki/overview.md`
  - `wiki/sources/source-one.md`
  - `wiki/concepts/RetrievalAugmentedGeneration.md`
- Raw paths:
  - raw/originals/source-one.txt
- Source IDs:
  - source-one
- Unresolved issues:
  - none
""",
            encoding="utf-8",
        )
        return temp_dir, root

    def write_page(self, path, cid, page_type, title, body):
        path.write_text(
            f'''---
canonical_id: "{cid}"
type: {page_type}
title: "{title}"
tags: []
aliases: []
source_ids: []
related_ids: []
raw_paths: []
created: 2026-05-12
last_updated: 2026-05-12
status: seed
confidence: medium
---

# {title}

{body}
''',
            encoding="utf-8",
        )

    def write_source_page(self, path):
        path.write_text(
            """---
canonical_id: "source-one"
type: source
title: "Source One"
tags: []
aliases: []
source_ids: []
related_ids: []
raw_paths:
  - "raw/originals/source-one.txt"
created: 2026-05-12
last_updated: 2026-05-12
status: seed
confidence: medium
provenance:
  source_id: "source-one"
  raw_path: "raw/originals/source-one.txt"
  content_hash: "sha256:abc123"
  source_url: null
  collected_at: "2026-05-12"
  published_at: null
  converted_from: null
  converted_path: null
  converter: null
  converter_version: null
---

# Source One

## Key Claims

- Source-backed claim about [[RetrievalAugmentedGeneration]].
""",
            encoding="utf-8",
        )

    def write_input_files(self, root, answer="RAG systems now combine retrieval, ranking, and generation.", evidence=None):
        evidence = evidence or "- [[source-one]] says retrieval context matters."
        answer_path = root / "answer.md"
        evidence_path = root / "evidence.md"
        answer_path.write_text(answer, encoding="utf-8")
        evidence_path.write_text(evidence, encoding="utf-8")
        return answer_path, evidence_path

    def run_save(self, root, *extra_args):
        return subprocess.run(
            [sys.executable, "tools/save_synthesis.py", *extra_args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def import_save_module(self, root):
        tools_path = root / "tools"
        module_name = f"save_synthesis_under_test_{id(root)}"
        old_path = list(sys.path)
        old_wiki_utils = sys.modules.pop("wiki_utils", None)
        try:
            sys.path.insert(0, str(tools_path))
            spec = importlib.util.spec_from_file_location(module_name, tools_path / "save_synthesis.py")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        finally:
            sys.path[:] = old_path
            if old_wiki_utils is not None:
                sys.modules["wiki_utils"] = old_wiki_utils
            else:
                sys.modules.pop("wiki_utils", None)

    def default_namespace(self, answer_path, evidence_path, synthesis_id="rag-systems-architecture-survey"):
        args = self.default_args(answer_path, evidence_path, synthesis_id)
        values = {
            "synthesis_id": None,
            "title": None,
            "question": None,
            "answer_file": None,
            "evidence_file": None,
            "related": [],
            "sources": [],
            "tags": [],
            "confidence": "medium",
            "status": "seed",
            "json": False,
        }
        index = 0
        while index < len(args):
            key = args[index]
            value = args[index + 1]
            if key == "--id":
                values["synthesis_id"] = value
            elif key == "--title":
                values["title"] = value
            elif key == "--question":
                values["question"] = value
            elif key == "--answer-file":
                values["answer_file"] = value
            elif key == "--evidence-file":
                values["evidence_file"] = value
            elif key == "--related":
                values["related"].append(value)
            elif key == "--sources":
                values["sources"].append(value)
            elif key == "--tags":
                values["tags"].append(value)
            index += 2
        return Namespace(**values)

    def default_args(self, answer_path, evidence_path, synthesis_id="rag-systems-architecture-survey"):
        return [
            "--id",
            synthesis_id,
            "--title",
            "RAG Systems Architecture Survey",
            "--question",
            "How have RAG systems evolved?",
            "--answer-file",
            str(answer_path),
            "--evidence-file",
            str(evidence_path),
            "--related",
            "RetrievalAugmentedGeneration",
            "--sources",
            "source-one",
            "--tags",
            "rag,systems",
        ]

    def test_successful_save_with_json_creates_page_index_log_and_passes_health(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            answer_path, evidence_path = self.write_input_files(root)
            result = self.run_save(root, *self.default_args(answer_path, evidence_path), "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["id"], "rag-systems-architecture-survey")
            self.assertEqual(payload["path"], "wiki/syntheses/rag-systems-architecture-survey.md")
            self.assertEqual(payload["updated"], ["wiki/index.md", "wiki/log.md"])
            self.assertEqual(payload["source_ids"], ["source-one"])
            self.assertEqual(payload["related_ids"], ["RetrievalAugmentedGeneration"])
            self.assertIn("saved_at", payload)

            page = (root / "wiki/syntheses/rag-systems-architecture-survey.md").read_text(encoding="utf-8")
            self.assertIn('canonical_id: "rag-systems-architecture-survey"', page)
            self.assertIn("type: synthesis", page)
            self.assertIn('title: "RAG Systems Architecture Survey"', page)
            self.assertIn('  - "rag"', page)
            self.assertIn('  - "source-one"', page)
            self.assertIn('  - "RetrievalAugmentedGeneration"', page)
            self.assertIn("## Evidence\n\n- [[source-one]] says retrieval context matters.", page)
            self.assertIn("## Related Pages\n\n- [[RetrievalAugmentedGeneration]]\n- [[source-one]]", page)

            index = (root / "wiki/index.md").read_text(encoding="utf-8")
            self.assertIn(
                "- [[rag-systems-architecture-survey|RAG Systems Architecture Survey]] (`wiki/syntheses/rag-systems-architecture-survey.md`) - type: synthesis - updated:",
                index,
            )
            self.assertIn("Saved synthesis for: How have RAG systems evolved?", index)
            self.assertNotIn("No synthesis pages yet.", index)

            log = (root / "wiki/log.md").read_text(encoding="utf-8")
            self.assertIn("query | RAG Systems Architecture Survey", log)
            self.assertIn("  - `wiki/syntheses/rag-systems-architecture-survey.md`", log)
            self.assertIn("  - `wiki/index.md`", log)
            self.assertIn("  - `wiki/log.md`", log)
            self.assertIn("  - `source-one`", log)

            health = subprocess.run(
                [sys.executable, "tools/health.py"],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(health.returncode, 0, health.stdout + health.stderr)

    def test_text_output_is_concise(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            answer_path, evidence_path = self.write_input_files(root)
            result = self.run_save(root, *self.default_args(answer_path, evidence_path))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(
                result.stdout,
                "Saved synthesis wiki/syntheses/rag-systems-architecture-survey.md\n"
                "Updated wiki/index.md and wiki/log.md\n",
            )

    def test_unknown_related_id_does_not_mutate_files(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            answer_path, evidence_path = self.write_input_files(root)
            before_index = (root / "wiki/index.md").read_text(encoding="utf-8")
            before_log = (root / "wiki/log.md").read_text(encoding="utf-8")
            result = self.run_save(
                root,
                *self.default_args(answer_path, evidence_path),
                "--related",
                "MissingConcept",
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual((root / "wiki/index.md").read_text(encoding="utf-8"), before_index)
            self.assertEqual((root / "wiki/log.md").read_text(encoding="utf-8"), before_log)
            self.assertFalse((root / "wiki/syntheses/rag-systems-architecture-survey.md").exists())

    def test_rejects_duplicate_id_invalid_id_unknown_source_and_empty_evidence(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            answer_path, evidence_path = self.write_input_files(root)
            first = self.run_save(root, *self.default_args(answer_path, evidence_path))
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

            duplicate = self.run_save(root, *self.default_args(answer_path, evidence_path))
            self.assertEqual(duplicate.returncode, 1)

            invalid = self.run_save(root, *self.default_args(answer_path, evidence_path, synthesis_id="NotKebab"))
            self.assertEqual(invalid.returncode, 1)

            unknown_source = self.run_save(
                root,
                *self.default_args(answer_path, evidence_path, synthesis_id="unknown-source-case"),
                "--sources",
                "missing-source",
            )
            self.assertEqual(unknown_source.returncode, 1)

            _, empty_evidence_path = self.write_input_files(root, evidence="   \n")
            empty_evidence = self.run_save(
                root,
                *self.default_args(answer_path, empty_evidence_path, synthesis_id="empty-evidence-case"),
            )
            self.assertEqual(empty_evidence.returncode, 1)
            self.assertFalse((root / "wiki/syntheses/empty-evidence-case.md").exists())

    def test_rejects_symlinked_destination_without_altering_target(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            answer_path, evidence_path = self.write_input_files(root)
            target = root / "target.md"
            target.write_text("do not alter\n", encoding="utf-8")
            (root / "wiki/syntheses/symlinked-destination.md").symlink_to(target)

            result = self.run_save(
                root,
                *self.default_args(answer_path, evidence_path, synthesis_id="symlinked-destination"),
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(target.read_text(encoding="utf-8"), "do not alter\n")

    def test_rejects_symlinked_index_without_altering_target(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            answer_path, evidence_path = self.write_input_files(root)
            original_index = (root / "wiki/index.md").read_text(encoding="utf-8")
            original_log = (root / "wiki/log.md").read_text(encoding="utf-8")
            outside_target = root / "outside-index.md"
            outside_target.write_text("outside target\n", encoding="utf-8")
            (root / "wiki/index.md").unlink()
            (root / "wiki/index.md").symlink_to(outside_target)

            result = self.run_save(root, *self.default_args(answer_path, evidence_path))

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(outside_target.read_text(encoding="utf-8"), "outside target\n")
            self.assertEqual((root / "wiki/log.md").read_text(encoding="utf-8"), original_log)
            self.assertFalse((root / "wiki/syntheses/rag-systems-architecture-survey.md").exists())
            self.assertNotEqual((root / "wiki/index.md").read_text(encoding="utf-8"), original_index)

    def test_replace_failure_rolls_back_all_changes_and_cleans_temps(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            answer_path, evidence_path = self.write_input_files(root)
            before_index = (root / "wiki/index.md").read_text(encoding="utf-8")
            before_log = (root / "wiki/log.md").read_text(encoding="utf-8")
            save_synthesis = self.import_save_module(root)
            args = self.default_namespace(answer_path, evidence_path)
            replace_file = getattr(save_synthesis, "replace_file", None)
            self.assertIsNotNone(replace_file)

            def fail_on_log(temp_path, target_path):
                if target_path.name == "log.md":
                    raise OSError("simulated replace failure")
                return replace_file(temp_path, target_path)

            save_synthesis.replace_file = fail_on_log

            with self.assertRaises(OSError):
                save_synthesis.save(args)

            self.assertFalse((root / "wiki/syntheses/rag-systems-architecture-survey.md").exists())
            self.assertEqual((root / "wiki/index.md").read_text(encoding="utf-8"), before_index)
            self.assertEqual((root / "wiki/log.md").read_text(encoding="utf-8"), before_log)
            self.assertEqual(list((root / "wiki/syntheses").glob("*.tmp")), [])
            self.assertEqual(list((root / "wiki").glob("*.tmp")), [])

    def test_unknown_wikilink_in_evidence_does_not_mutate_files(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            answer_path, evidence_path = self.write_input_files(root, evidence="- [[MissingConcept]] is cited.")
            before_index = (root / "wiki/index.md").read_text(encoding="utf-8")
            before_log = (root / "wiki/log.md").read_text(encoding="utf-8")

            result = self.run_save(root, *self.default_args(answer_path, evidence_path))

            self.assertEqual(result.returncode, 1)
            self.assertIn("unknown wikilink target: MissingConcept", result.stderr)
            self.assertFalse((root / "wiki/syntheses/rag-systems-architecture-survey.md").exists())
            self.assertEqual((root / "wiki/index.md").read_text(encoding="utf-8"), before_index)
            self.assertEqual((root / "wiki/log.md").read_text(encoding="utf-8"), before_log)

    def test_rejects_unsafe_title_and_question_without_mutation(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            answer_path, evidence_path = self.write_input_files(root)
            before_index = (root / "wiki/index.md").read_text(encoding="utf-8")
            before_log = (root / "wiki/log.md").read_text(encoding="utf-8")

            bad_title = self.run_save(
                root,
                *self.default_args(answer_path, evidence_path),
                "--title",
                "Injected\nTitle",
            )
            bad_question = self.run_save(
                root,
                *self.default_args(answer_path, evidence_path, synthesis_id="bad-question-case"),
                "--question",
                "What breaks?\nA second entry",
            )

            self.assertEqual(bad_title.returncode, 1)
            self.assertIn("--title contains unsupported characters", bad_title.stderr)
            self.assertEqual(bad_question.returncode, 1)
            self.assertIn("--question contains unsupported characters", bad_question.stderr)
            self.assertFalse((root / "wiki/syntheses/rag-systems-architecture-survey.md").exists())
            self.assertFalse((root / "wiki/syntheses/bad-question-case.md").exists())
            self.assertEqual((root / "wiki/index.md").read_text(encoding="utf-8"), before_index)
            self.assertEqual((root / "wiki/log.md").read_text(encoding="utf-8"), before_log)


if __name__ == "__main__":
    unittest.main()
