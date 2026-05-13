# Raw Sources

`raw/` stores source artifacts. Treat existing artifacts as append-only.

- Put original files in `raw/originals/`.
- Put derived Markdown or text in `raw/converted/`.
- Record every raw or converted artifact in `raw/source-manifest.jsonl`.
- Do not overwrite a raw artifact unless the user explicitly asks for it.

## Current Interface Status

Ingest v2 supports local Markdown/text files, pasted text, and already converted Markdown. `tools/convert.py` supports local Markdown/text conversion into `raw/converted/`.

`tools/convert.py` does not update source-manifest.jsonl. The ingest workflow records artifacts and provenance after conversion.

PDF, Office documents, remote webpages, HTML rendering, and binary files are not converted automatically yet.

## Manifest Format

Each manifest line is JSON:

```json
{"source_id":"example-source","raw_path":"raw/originals/example.pdf","content_hash":"sha256:...","source_url":null,"collected_at":"YYYY-MM-DD","published_at":null,"converted_from":null,"converted_path":null,"converter":null,"converter_version":null}
```

Fields:

- `source_id`: canonical source ID, usually kebab-case.
- `raw_path`: path to the original artifact under `raw/originals/`.
- `content_hash`: SHA-256 hash of the raw artifact, prefixed with `sha256:`.
- `source_url`: original URL when known; otherwise `null`.
- `collected_at`: date the artifact was added to MuvyWiki.
- `published_at`: source publication date when known; otherwise `null`.
- `converted_from`: source path used to create a converted artifact; otherwise `null`.
- `converted_path`: converted Markdown/text path under `raw/converted/`; otherwise `null`.
- `converter`: converter name when conversion is implemented; otherwise `null`.
- `converter_version`: converter version when conversion is implemented; otherwise `null`.

For successful source ingests, the source page provenance block must match the corresponding manifest entry.
