---
canonical_id: "MuvyWiki"
type: entity
title: "MuvyWiki（个人知识库项目）"
tags: [project, knowledge-base]
aliases:
  - "Muvy Wiki"
  - "个人知识库项目"
source_ids:
  - "muvywiki-repository-contract"
related_ids:
  - "RepositoryRootIsolation"
raw_paths: []
created: 2026-09-08
last_updated: 2026-09-08
status: active
confidence: high
---

# MuvyWiki（个人知识库项目）

## Summary

MuvyWiki 是一个由 agent 协助维护、以来源可追溯和确定性本地工具为约束的个人知识库项目。

## Role in the Wiki

该实体代表当前仓库本身，用于连接项目架构、维护接口、来源协议和后续演进记录。

## Claims

- 项目将原始来源、维护后的知识和确定性工具分层保存。
- 项目不把结构检查通过等同于知识摄取完成。
- 项目使用 [[RepositoryRootIsolation|Repository Root Isolation（仓库根隔离）]] 让主库和 fixture 共享工具实现。

## Evidence

- [[muvywiki-repository-contract|MuvyWiki Repository Contract]] 描述了仓库当前实现和边界。
- `AGENTS.md` 规定 raw append-only、source provenance 和 ingest completion 的维护要求。

## Contradictions or Tensions

- 自动化可以保证结构、引用和部分内容形状，但不能替代对来源的深入阅读和事实判断。

## Related Concepts

- [[RepositoryRootIsolation|Repository Root Isolation（仓库根隔离）]]

## Related Sources

- [[muvywiki-repository-contract|MuvyWiki Repository Contract]]

## Timeline

- 2026-05-12：初始化仓库结构和维护协议。
- 2026-09-08：加入首个根知识源和跨 root 的统一工具接口。

## Open Questions

- 哪些项目专属查询任务最适合用于长期回归评测？
- 如何量化知识页面从 `needs-review` 到 `active` 的质量提升？
