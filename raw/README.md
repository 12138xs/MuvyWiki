# Raw Sources

`raw/` stores source artifacts. Treat existing artifacts as append-only.

- Put original files in `raw/originals/`.
- Put derived Markdown or text in `raw/converted/`.
- Record every raw or converted artifact in `raw/source-manifest.jsonl`.
- Do not overwrite a raw artifact unless the user explicitly asks for it.

## Current Interface Status

Ingest v2 supports local Markdown/text files, pasted text, and already converted Markdown. `tools/convert.py` supports local Markdown/text conversion into `raw/converted/`.

`tools/convert.py` does not update source-manifest.jsonl. The ingest workflow records artifacts and provenance after conversion.

`tools/prepare_ingest.py` performs ingest preflight against local Markdown/text inputs. It can emit JSON or write `graph/ingest-prep-report.md` when called with `--report`, but it does not create wiki pages, update `wiki/index.md`, or update `wiki/log.md`.

`tools/manifest.py` is the manifest helper:

- `python tools/manifest.py check` validates manifest shape, duplicate IDs/hashes/paths, and referenced raw/converted files.
- `python tools/manifest.py find --source-id <source-id>` reports whether a source ID already exists.
- `python tools/manifest.py find --hash <sha256:...>` reports whether a content hash already exists.
- `python tools/manifest.py find --path <raw-or-converted-path>` reports whether a raw, converted, or converted-from path already exists.
- `python tools/manifest.py add --source-id <source-id> --raw-path <raw-path> --content-hash <sha256:...> --collected-at <YYYY-MM-DD>` appends one validated entry to `raw/source-manifest.jsonl`.

`manifest.py` only maintains `raw/source-manifest.jsonl`. It does not create source pages, extract claims, or update index/log.

PDF, Office documents, remote webpages, HTML rendering, and binary files are not converted automatically yet.

## Manifest Format

Each manifest line is JSON:

```json
{"source_id":"example-source","raw_path":"raw/originals/example.md","content_hash":"sha256:...","source_url":null,"collected_at":"YYYY-MM-DD","published_at":null,"converted_from":null,"converted_path":null,"converter":null,"converter_version":null}
```

Fields:

- `source_id`: canonical source ID, usually kebab-case.
- `raw_path`: path to the original artifact under `raw/originals/`.
- `content_hash`: SHA-256 hash of the raw artifact, prefixed with `sha256:`.
- `source_url`: original URL when known; otherwise `null`.
- `collected_at`: date the artifact was added to MuvyWiki.
- `published_at`: source publication date when known; otherwise `null`.
- `converted_from`: source path used to create a converted artifact; otherwise `null`.
- `converted_path`: converted Markdown/text path under `raw/converted/` after ingest records it; otherwise `null`.
- `converter`: converter name used for conversion; otherwise `null`.
- `converter_version`: converter or interface version used for conversion; otherwise `null`.

For successful source ingests, the source page provenance block must match the corresponding manifest entry.
