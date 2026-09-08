# Ingest Example Fixture

This directory is a content fixture for a successful agent-first ingest.

It is not a second project and does not duplicate the implementation under `tools/`. Run the project-root tools with `--repo-root examples/ingest` so the same implementation validates both the real wiki and this fixture.

It demonstrates:

- one raw Markdown note
- one manifest entry
- one source page
- one concept page
- one entity page
- updated index, overview, and log

Key files to inspect:

- `raw/originals/tiny-rag-note.md` - original source artifact.
- `raw/source-manifest.jsonl` - source manifest entry with the source hash.
- `wiki/sources/tiny-rag-note.md` - source page with matching provenance.
- `wiki/concepts/RetrievalAugmentedGeneration.md` - concept page created from the source.
- `wiki/entities/TinyRagDemo.md` - entity page created from the source.
- `wiki/index.md` and `wiki/log.md` - required metadata updates.

Validate it with:

```bash
python tools/health.py --repo-root examples/ingest
```

The fixture also supports:

```bash
python tools/lint.py --repo-root examples/ingest
python tools/lint.py --repo-root examples/ingest --report graph/lint-report.md
python tools/build_graph.py --repo-root examples/ingest
python tools/manifest.py --repo-root examples/ingest check
python tools/manifest.py --repo-root examples/ingest find --source-id tiny-rag-note
python tools/query.py --repo-root examples/ingest "retrieval augmented generation"
```

To smoke-test conversion without changing the checked-in fixture, copy the fixture to a temporary directory and pass that copy as `--repo-root`. Conversion only writes a converted artifact; it does not update the manifest or wiki pages by itself.

The root ingest preparation helper can demonstrate duplicate detection against the fixture:

```bash
python tools/prepare_ingest.py --repo-root examples/ingest raw/originals/tiny-rag-note.md
```

That command is expected to exit `1` because `tiny-rag-note` is already present in `raw/source-manifest.jsonl`; this is a successful duplicate preflight demonstration, not a broken fixture. Run it as a separate verification step rather than chaining every command with `&&`.

`python tools/manifest.py --repo-root examples/ingest add ...` is available for finalized new sources, but this fixture already contains its manifest entry. The helper only changes `raw/source-manifest.jsonl`; it does not create wiki pages or update index/log.

From the repository root, the test suite also validates this fixture:

```bash
python -m unittest tests/test_ingest_examples.py
```
