# M4 — Query and Synthesis Persistence

## 目标与背景

知识库完成 ingest 后，需要一种确定性方法找到候选上下文，并在用户确认后安全保存长期综合结论。该阶段建立 query 与 synthesis 的读写闭环。

## 实现内容

- 扩展 shared utility 的页面解析、章节提取和 excerpt 能力；
- 实现基于 ID、title、alias、tag、关系、章节与正文的保守关键词评分；
- 实现类型过滤、结果限制、JSON 输出和可选章节摘要；
- 实现 synthesis 页面、index 和 log 的事务式多文件写入；
- 加固匹配语义、YAML 标量解码、wikilink 校验、路径安全和失败回滚。

## 对外行为变化

- `query.py` 返回候选上下文，不调用 LLM、不生成最终回答；
- `save_synthesis.py` 只保存用户已确认的 answer/evidence 文件；
- synthesis ID 必须为 kebab-case，引用 ID 必须存在；
- 任一写入失败时，synthesis、index 和 log 不得留下部分成功状态。

## 验证证据

- query 测试覆盖大小写、camel case、类型过滤、保守匹配、排序和 JSON；
- save_synthesis 测试覆盖成功保存、未知 ID、重复目标、路径攻击和多文件回滚；
- 当前根查询 `repository root isolation provenance` 返回非空结果。

## Commit 区间说明

- Start：`4d3c40d docs: design query and synthesis interfaces`；
- End：`bc625f8 merge: query synthesis v1`；
- 区间包含设计、计划、共享能力、query、synthesis、加固、文档与最终 merge；
- merge commit 是该功能分支的集成终点，不把相同改动重复计算为独立功能；
- 多个小型 fix 对应测试发现的独立边界问题，均属于 query/synthesis 的可靠性交付。
