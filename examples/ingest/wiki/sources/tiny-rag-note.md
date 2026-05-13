---
canonical_id: "tiny-rag-note"
type: source
title: "Tiny RAG Note"
tags: [example, rag]
aliases: []
source_ids: []
related_ids:
  - "RetrievalAugmentedGeneration"
  - "TinyRagDemo"
raw_paths:
  - "raw/originals/tiny-rag-note.md"
created: 2026-05-13
last_updated: 2026-05-13
status: active
confidence: medium
provenance:
  source_id: "tiny-rag-note"
  raw_path: "raw/originals/tiny-rag-note.md"
  content_hash: "sha256:04a15f5bc8141cc577b226b0b78eb8bce70f79b2b65960fc5ec6f5ac149138b1"
  source_url: null
  collected_at: "2026-05-13"
  published_at: null
  converted_from: null
  converted_path: null
  converter: null
  converter_version: null
---

# Tiny RAG Note

## Summary

Tiny RAG Note describes [[TinyRagDemo|TinyRagDemo]], a teaching project that uses [[RetrievalAugmentedGeneration|Retrieval-Augmented Generation]] to answer questions over local documents.

## Practical Takeaways

- RAG is useful when answers depend on changing or private documents.
- Retrieval quality depends on chunking quality.

## Claims to Verify

- Poor chunking can hide missing evidence even when retrieval appears correct.

## Implementation Notes

- The note describes local documents, embeddings, a vector index, top chunk retrieval, and model-grounded answering.

## Related Work

- [[RetrievalAugmentedGeneration|Retrieval-Augmented Generation]]

## Key Claims

- RAG helps answer questions over changing or private documents.
- Poor chunking can make retrieval appear correct while hiding evidence gaps.

## Evidence and Details

- The raw note states that TinyRagDemo embeds local documents, retrieves top matching chunks, and passes those chunks to a language model.

## Concepts

- [[RetrievalAugmentedGeneration|Retrieval-Augmented Generation]]

## Entities

- [[TinyRagDemo|TinyRagDemo]]

## Open Questions

- Which embedding model and chunking strategy does TinyRagDemo use?

## Contradictions or Tensions

- none

## Raw Source

- [raw/originals/tiny-rag-note.md](../../raw/originals/tiny-rag-note.md)
