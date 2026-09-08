---
canonical_id: "overview"
type: overview
title: "MuvyWiki Overview"
tags: []
aliases: []
source_ids:
  - "muvywiki-repository-contract"
related_ids:
  - "RepositoryRootIsolation"
  - "MuvyWiki"
raw_paths: []
created: 2026-05-12
last_updated: 2026-09-08
status: active
confidence: high
---

# MuvyWiki Overview

## Current Shape

[[MuvyWiki]] 是一个以来源可追溯、知识维护和确定性验证为核心的个人知识库。当前已经从空骨架进入可查询状态。

## Active Themes

- [[RepositoryRootIsolation|Repository Root Isolation（仓库根隔离）]] 与多知识库根的安全操作
- 原始来源、manifest 与维护页面之间的 provenance 一致性
- 技术和研究资料的 agent-first ingest

## Strongest Syntheses

- 尚无已保存 synthesis；当前最完整的知识链是 [[muvywiki-repository-contract|MuvyWiki Repository Contract]] → [[RepositoryRootIsolation|Repository Root Isolation（仓库根隔离）]] → [[MuvyWiki]]。

## Open Questions

- 哪些真实查询任务应该形成固定回归评测集？
- 如何把 source、concept、entity 和 synthesis 的质量变化量化？

## Maintenance Notes

- Keep raw artifacts append-only.
- Use canonical IDs for internal links.
- Run `python tools/health.py` after structural edits.
- Run `python tools/demo.py` to verify the bundled fixture without modifying the repository.
