# Raw Sources

`raw/` stores source artifacts. Treat existing artifacts as append-only.

- Put original files in `raw/originals/`.
- Put derived Markdown or text in `raw/converted/`.
- Record every raw or converted artifact in `raw/source-manifest.jsonl`.
- Do not overwrite a raw artifact unless the user explicitly asks for it.

## Current Interface Status

This fixture supports local Markdown/text conversion into `raw/converted/` through `tools/convert.py`.

`tools/convert.py` does not update source-manifest.jsonl. The ingest workflow records artifacts and provenance after conversion.

`tools/prepare_ingest.py` performs local Markdown/text preflight before formal ingest. It may report that `raw/originals/tiny-rag-note.md` is a duplicate because this fixture already contains that source.

`tools/manifest.py` supports:

- `python tools/manifest.py check`
- `python tools/manifest.py find --source-id tiny-rag-note`
- `python tools/manifest.py find --hash <sha256:...>`
- `python tools/manifest.py add --source-id <source-id> --raw-path <raw-path> --content-hash <sha256:...> --collected-at <YYYY-MM-DD>`

`manifest.py` only maintains `raw/source-manifest.jsonl`. It does not create wiki pages or update index/log.

PDF, Office documents, remote webpages, HTML rendering, and binary files are not converted automatically.

Each manifest line is JSON:

```json
{"source_id":"example-source","raw_path":"raw/originals/example.md","content_hash":"sha256:...","source_url":null,"collected_at":"YYYY-MM-DD","published_at":null,"converted_from":null,"converted_path":null,"converter":null,"converter_version":null}
```
