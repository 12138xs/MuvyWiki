# M2 — Agent-first Ingest Workflow

## 目标与背景

结构健康并不代表知识已经被摄取。该阶段把 ingest 定义为一条可审计流程：保留原始来源、检查重复、深入抽取、更新维护页面、同步 index/log，并通过 fixture 展示完成状态。

## 实现内容

- 增加中文用户指南和 ingest v2 设计/历史实施计划；
- 为技术论文、技术文章、项目 README、会议记录和日志增加领域模板；
- 扩展 AGENTS 的触发、preflight、页面更新、完成报告与 blocked 报告协议；
- 创建 `examples/ingest` fixture，包含 raw、manifest、source、concept、entity、index、overview 和 log；
- 增加 fixture 与模板合同测试。

## 对外行为变化

- 用户可以通过自然语言请求 agent 摄取本地 Markdown/text；
- remote URL 和不支持格式会明确阻断，而不是假装完成；
- `needs-review` 被定义为 backlog，不能报告为完整 ingest；
- 一个成功 ingest 必须同步 manifest、source 页面、index 和 log。

## 验证证据

- fixture 的 manifest hash、source provenance、canonical links 和 index/log 能被 health 验证；
- `tests/test_ingest_examples.py` 验证完整示例和领域模板基础字段；
- 当前 root tools 仍可用 `--repo-root examples/ingest` 验证该 fixture。

## Commit 区间说明

- Start：`0c8ca77 docs: add MuvyWiki user guide`；
- End：`94df9ee docs: sync current interfaces`；
- 用户指南先建立使用路径，随后设计、实现协议、模板、fixture 和测试，最后同步接口文档，形成完整业务闭环；
- 大量新增行来自设计/历史计划和 fixture 内容，不应全部视为生产代码 LOC；
- fixture 当时复制工具是为了原地验证，后续在 M5 中被识别为维护风险并移除。
