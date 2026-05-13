import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ConvertToolTests(unittest.TestCase):
    def make_repo(self):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        (root / "tools").mkdir()
        (root / "raw" / "originals").mkdir(parents=True)
        (root / "raw" / "converted").mkdir(parents=True)
        shutil.copy(ROOT / "tools" / "convert.py", root / "tools" / "convert.py")
        shutil.copy(ROOT / "tools" / "wiki_utils.py", root / "tools" / "wiki_utils.py")
        return temp_dir, root

    def run_convert(self, root, *args):
        return subprocess.run(
            [sys.executable, "tools/convert.py", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_converts_markdown_without_wrapping(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/note.md").write_text("# Existing\n\nBody\r\n", encoding="utf-8")
            result = self.run_convert(root, "raw/originals/note.md", "--out", "raw/converted/note.md")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Converted raw/originals/note.md -> raw/converted/note.md", result.stdout)
            self.assertEqual((root / "raw/converted/note.md").read_text(encoding="utf-8"), "# Existing\n\nBody\n")

    def test_converts_plain_text_with_heading(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/plain.txt").write_text("line one\nline two\n", encoding="utf-8")
            result = self.run_convert(root, "raw/originals/plain.txt", "--out", "raw/converted/plain.md")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            text = (root / "raw/converted/plain.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# plain\n\n"))
            self.assertIn("line one\nline two\n", text)

    def test_json_output_contains_hashes_and_counts(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/plain.txt").write_text("hello\n", encoding="utf-8")
            result = self.run_convert(root, "raw/originals/plain.txt", "--out", "raw/converted/plain.md", "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["input_path"], "raw/originals/plain.txt")
            self.assertEqual(payload["output_path"], "raw/converted/plain.md")
            self.assertTrue(payload["input_hash"].startswith("sha256:"))
            self.assertTrue(payload["output_hash"].startswith("sha256:"))
            self.assertGreater(payload["output_bytes"], payload["input_bytes"])

    def test_rejects_remote_url(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_convert(root, "https://example.com/page", "--out", "raw/converted/page.md")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Remote URLs are not supported", result.stderr)

    def test_rejects_unsupported_extension(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/file.pdf").write_bytes(b"%PDF-")
            result = self.run_convert(root, "raw/originals/file.pdf", "--out", "raw/converted/file.md")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Unsupported input type", result.stderr)

    def test_rejects_binary_like_utf8_text(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/binary.txt").write_bytes(b"\x00\x01hello\n")
            result = self.run_convert(root, "raw/originals/binary.txt", "--out", "raw/converted/binary.md")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Unsupported input type", result.stderr)
            self.assertFalse((root / "raw/converted/binary.md").exists())

    def test_rejects_del_and_c1_control_text(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/del.txt").write_bytes(b"hello\x7f\n")
            del_result = self.run_convert(root, "raw/originals/del.txt", "--out", "raw/converted/del.md")
            self.assertEqual(del_result.returncode, 2)
            (root / "raw/originals/c1.txt").write_text("hello\u0085\n", encoding="utf-8")
            c1_result = self.run_convert(root, "raw/originals/c1.txt", "--out", "raw/converted/c1.md")
            self.assertEqual(c1_result.returncode, 2)

    def test_rejects_absolute_and_traversal_output(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/plain.txt").write_text("hello\n", encoding="utf-8")
            absolute = self.run_convert(root, "raw/originals/plain.txt", "--out", "/tmp/plain.md")
            self.assertEqual(absolute.returncode, 2)
            traversal = self.run_convert(root, "raw/originals/plain.txt", "--out", "raw/converted/../originals/plain.md")
            self.assertEqual(traversal.returncode, 2)

    def test_rejects_existing_output(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/plain.txt").write_text("hello\n", encoding="utf-8")
            (root / "raw/converted/plain.md").write_text("existing\n", encoding="utf-8")
            result = self.run_convert(root, "raw/originals/plain.txt", "--out", "raw/converted/plain.md")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Output path already exists", result.stderr)
            self.assertEqual((root / "raw/converted/plain.md").read_text(encoding="utf-8"), "existing\n")

    def test_rejects_symlink_loop_input_without_traceback(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "loop").symlink_to("loop")
            result = self.run_convert(root, "loop", "--out", "raw/converted/loop.md")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Input path must stay inside the repository", result.stderr)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
