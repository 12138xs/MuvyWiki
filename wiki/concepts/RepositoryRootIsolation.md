---
canonical_id: "RepositoryRootIsolation"
type: concept
title: "Repository Root Isolation（仓库根隔离）"
tags: [architecture, cli, isolation]
aliases:
  - "Repository Root Isolation"
  - "仓库根隔离"
source_ids:
  - "muvywiki-repository-contract"
related_ids:
  - "MuvyWiki"
raw_paths: []
created: 2026-09-08
last_updated: 2026-09-08
status: active
confidence: high
---

# Repository Root Isolation（仓库根隔离）

## Definition

Repository Root Isolation（仓库根隔离）是指工具把所有知识库相对路径解析到一个显式选择且经过校验的根目录，使同一套实现可以安全地操作主知识库、fixture 或临时副本。

## Claims

- 显式 root 能消除为了运行 fixture 而复制整套工具的需要。
- 输入、输出和元数据路径绑定到选定 root 后，端到端测试可以在临时目录中运行而不污染真实仓库。
- 保留无参数时的原有默认值，可以在增加隔离能力的同时减少兼容性破坏。

## Why It Matters

MuvyWiki 的工具既会读知识页面，也可能写 manifest、graph、converted artifact 或 synthesis。若 root 来源不一致，命令可能读取一个仓库却写入另一个目录。统一 root 协议使行为可预测，并让示例复用生产实现。

## Mechanism

`tools/wiki_utils.py` 将用户给出的 `--repo-root` 解析为存在的绝对目录。各 CLI 在处理业务参数前配置自己的 root 及派生目录；后续安全路径检查继续限制相对路径不能越出该 root。

## Boundaries and Failure Modes

- `--repo-root` 只选择本地知识库根，不提供远程抓取能力。
- 若指定路径不存在或不是目录，命令返回参数错误而不继续执行。
- 使用模块级 root 兼容现有函数，但同一进程反复调用不同 root 时仍需测试全局状态复位。
- root 隔离不能替代来源授权、内容审查或 manifest 完整性验证。

## Evidence

- [[muvywiki-repository-contract|MuvyWiki Repository Contract]] 记录了接口目的和当前边界。
- `tests/test_repo_root_cli.py` 对 health、lint、graph、convert、manifest、prepare、query 和 synthesis 写入执行跨根回归测试。

## Contradictions or Tensions

- fixture 越接近完整仓库，验证越真实；fixture 越独立，越容易重新产生复制代码。当前以内容完整、工具共享为原则。

## Related Concepts

- [[MuvyWiki]] 使用该机制维护主库与示例之间的一致性。

## Supporting Sources

- [[muvywiki-repository-contract|MuvyWiki Repository Contract]]

## Open Questions

- 是否应把模块级 root 逐步重构为显式函数参数或不可变 context 对象？
- 是否需要为只读工具和写入工具设置不同的 root 校验强度？
