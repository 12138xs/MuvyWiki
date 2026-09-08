# MuvyWiki Repository Contract

Date: 2026-09-08
Author: MuvyWiki repository maintainer

## Purpose

MuvyWiki is a personal, agent-maintained knowledge base. It separates immutable source artifacts from maintained knowledge pages and deterministic maintenance tools so that claims remain traceable and repository checks remain reproducible.

## Repository layers

- `raw/` stores original and converted source artifacts. Existing raw artifacts are append-only.
- `wiki/` stores maintained source, concept, entity, synthesis, index, overview, and log pages.
- `tools/` provides deterministic local interfaces for validation, ingest preparation, querying, graph generation, conversion, and synthesis persistence.

## Root selection

The command-line tools accept `--repo-root PATH`. Paths read from or written to the knowledge base are resolved against that selected root. Without the option, existing default behavior is preserved.

The fixture at `examples/ingest` contains example content but does not carry a second copy of the tool implementation. Project-root tools validate the fixture by selecting it with `--repo-root examples/ingest`.

## Provenance and validation

Every ingestable source has a stable source ID, a content hash, a manifest entry, and a source page whose provenance agrees with the manifest. Structural health and semantic lint are separate checks: health validates repository shape and references, while lint identifies incomplete maintained knowledge.

The bundled demo copies the fixture to a temporary directory, runs health, lint, query, and graph generation there, requires a non-empty query result and graph, and leaves the checked-in fixture unchanged.

## Current boundaries

The deterministic tools do not fetch remote URLs, call a language model, or claim that conversion alone completes ingest. PDF, Office, rendered HTML, and binary conversion remain outside the implemented interface.
