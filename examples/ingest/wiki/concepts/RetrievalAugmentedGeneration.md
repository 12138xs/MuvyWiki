---
canonical_id: "RetrievalAugmentedGeneration"
type: concept
title: "Retrieval-Augmented Generation"
tags: [rag, example]
aliases:
  - "RAG"
source_ids:
  - "tiny-rag-note"
related_ids:
  - "TinyRagDemo"
raw_paths: []
created: 2026-05-13
last_updated: 2026-05-13
status: seed
confidence: medium
---

# Retrieval-Augmented Generation

## Definition

Retrieval-augmented generation is a pattern where a system retrieves relevant external context before asking a model to answer.

## Claims

- RAG is useful when the answer depends on changing or private documents.

## Why It Matters

It lets a model answer from a maintained knowledge source instead of relying only on model memory.

## Mechanism

Documents are chunked, embedded, indexed, retrieved for a query, and passed to the model as context.

## Boundaries and Failure Modes

- Poor chunking can hide missing evidence.
- Retrieval can look plausible without retrieving the evidence needed for a correct answer.

## Evidence

- [[tiny-rag-note|Tiny RAG Note]] describes a local-document RAG flow and its chunking risk.

## Contradictions or Tensions

- none

## Related Concepts

- none

## Supporting Sources

- [[tiny-rag-note|Tiny RAG Note]]

## Open Questions

- What chunking and evaluation practices best expose missing evidence?
