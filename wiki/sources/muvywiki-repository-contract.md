---
canonical_id: "muvywiki-repository-contract"
type: source
title: "MuvyWiki Repository Contract"
tags: [architecture, provenance, maintenance]
aliases: ["MuvyWiki repository contract"]
source_ids: []
related_ids:
  - "RepositoryRootIsolation"
  - "MuvyWiki"
raw_paths:
  - "raw/originals/muvywiki-repository-contract.md"
created: 2026-09-08
last_updated: 2026-09-08
status: active
confidence: high
provenance:
  source_id: "muvywiki-repository-contract"
  raw_path: "raw/originals/muvywiki-repository-contract.md"
  content_hash: "sha256:0aa9384ad6340c57463914e0b02bdcdddab6ee776b1513bd3d7d849fe9a76172"
  source_url: null
  collected_at: "2026-09-08"
  published_at: null
  converted_from: null
  converted_path: null
  converter: null
  converter_version: null
---

# MuvyWiki Repository Contract

## Summary

这份维护者技术说明记录了 [[MuvyWiki]] 当前可由代码验证的仓库分层、来源追踪、校验边界，以及 [[RepositoryRootIsolation|Repository Root Isolation（仓库根隔离）]] 接口。

## Key Claims

- `raw/`、`wiki/` 与 `tools/` 分别承担不可变来源、维护后知识和确定性工具三个职责。
- 命令行工具通过 `--repo-root PATH` 对同一实现选择不同知识库根目录。
- `examples/ingest` 只保存示例内容，不复制生产工具。
- 完整来源追踪要求 source ID、内容 hash、manifest 和 source page provenance 保持一致。
- health、lint、query 与 graph 可以在临时 fixture 副本中组成非破坏性验证闭环。

## Evidence and Details

- `tools/wiki_utils.py` 解析并校验显式仓库根路径，8 个命令行工具复用该参数约定。
- `examples/ingest/README.md` 使用项目根工具和 `--repo-root examples/ingest` 运行示例。
- `tools/demo.py` 把 fixture 复制到临时目录，要求 health/lint 成功、query 非空且 graph 至少包含一个节点。
- `tools/health.py` 会核对 source provenance 与 `raw/source-manifest.jsonl` 的对应字段。

## Concepts

- [[RepositoryRootIsolation|Repository Root Isolation（仓库根隔离）]]

## Entities

- [[MuvyWiki]]

## Open Questions

- 未来是否需要让所有库函数显式接收 root，而不是只在 CLI 入口配置 root？
- fixture 内容契约是否应该形成独立 schema 版本？

## Contradictions or Tensions

- fixture 需要像独立知识库一样可验证，但若复制工具实现又会形成漂移；当前选择是共享工具、隔离内容。
- `raw/` 的 append-only 原则提高可追溯性，但错误摄取不能通过覆盖源文件修正，只能追加新来源并在维护层说明。

## Raw Source

- [raw/originals/muvywiki-repository-contract.md](../../raw/originals/muvywiki-repository-contract.md)
