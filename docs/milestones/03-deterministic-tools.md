# M3 — Deterministic Maintenance Tools

## 目标与背景

Agent 协议需要可重复执行的本地接口支持。该阶段实现共享解析工具、文本转换、图构建和 semantic-lite lint，使仓库维护不依赖人工目测。

## 实现内容

- 在 `tools/wiki_utils.py` 集中 frontmatter、wikilink、页面加载、hash 和安全路径能力；
- 在 `tools/convert.py` 实现本地 UTF-8 Markdown/text 转换；
- 在 `tools/build_graph.py` 生成 JSON、HTML 和 Markdown 图报告；
- 在 `tools/lint.py` 检查空章节、缺少 claims/evidence、孤立页面与过期 index；
- 加固 symlink、输出路径、报告错误处理和 fixture 接口一致性。

## 对外行为变化

- 新增 convert、build_graph 和 lint CLI；
- 输出只能写入约定目录，存在路径越界或 symlink 风险时拒绝执行；
- graph 以 wiki metadata 和链接为输入，不联网、不调用 LLM；
- lint 与 health 分工：health 检查结构，lint 检查维护质量风险。

## 验证证据

- `tests/test_wiki_utils.py`、`test_convert.py`、`test_build_graph.py` 和 `test_lint.py` 覆盖主要接口与错误路径；
- 当前 demo 在临时 fixture 上同时运行 lint 和 graph，证明两项能力仍可组合使用；
- 不支持的 PDF、Office、远程抓取和 LLM 抽取在文档中保持明确边界。

## Commit 区间说明

- Start：`779850c docs: add interface v1 design spec`；
- End：`57ffaa3 docs: refresh maintenance guidance`；
- 区间按 design → plan → shared utility → individual tool → hardening → fixture/test → docs 展开；
- fixture 同步提交属于这些接口的集成验证，不是另一套独立功能；
- 文档更新用于消除“reserved interface”旧状态，与实现交付属于同一阶段。
