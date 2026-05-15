# MuvyWiki 使用手册

MuvyWiki 是一个由你和 LLM 共同维护的个人知识库。你负责选择资料、提出问题、判断方向；LLM 负责整理来源、生成结构化页面、维护索引、记录日志、检查结构健康。

第一版适合技术文章、论文、开源项目、研究笔记和长期问题追踪；轻量图谱、语义 lint、本地 Markdown/text 转换接口已经可用，批量导入和复杂文档转换仍留作后续扩展。

## 快速开始

常用入口：

- `README.md`：项目简介和命令速查。
- `AGENTS.md`：给 Codex/LLM 看的维护规则。
- `wiki/index.md`：知识库总索引，找内容先看这里。
- `wiki/overview.md`：知识库当前状态和长期主题。
- `wiki/log.md`：操作日志。

常用检查命令：

```bash
python tools/health.py
python tools/health.py --json
python tools/lint.py
python -m unittest discover -s tests
```

`health.py` 是第一版最重要的结构质量门。每次新增资料、修改索引、改页面结构后，都应该运行一次；`lint.py` 用来补充检查空章节、缺少证据、孤立页面等维护风险。

## 目录说明

```text
raw/
  originals/        # 原始资料，追加写入，不覆盖
  converted/        # 转换后的 Markdown 或文本
  source-manifest.jsonl

wiki/
  index.md          # 全局索引
  overview.md       # 总览
  log.md            # 操作日志
  sources/          # 每个来源一页
  concepts/         # 可复用概念
  entities/         # 人、组织、项目、论文、工具等实体
  syntheses/        # 值得保存的综合回答

templates/          # 页面模板
tools/              # 健康检查、lint、图谱和本地转换工具
graph/              # 生成的图谱输出目录
```

## 核心原则

`raw/` 是原始资料层。已有文件不要直接改写；如果要清洗或转换，原件放在 `raw/originals/`，转换结果放在 `raw/converted/`。

`wiki/` 是知识层。这里的页面可以被 LLM 更新，用来承载摘要、概念、实体、证据、矛盾和综合判断。

`AGENTS.md` 是操作协议。以后让 Codex 摄取资料或回答知识库问题时，它应该遵守这里的规则。

## 当前功能与接口状态

当前已经可以直接使用：

- `python tools/health.py`：结构健康检查。
- `python tools/health.py --json`：机器可读健康检查输出。
- `python tools/lint.py`：语义轻量 lint，检查空章节、缺少 claims/evidence、孤立页面等维护风险。
- `python tools/lint.py --json`：机器可读 lint 输出。
- `python tools/lint.py --report graph/lint-report.md`：写入 Markdown lint 报告。
- `python tools/build_graph.py`：生成 `graph/graph.json`、`graph/graph.html`、`graph/graph-report.md`。
- `python tools/prepare_ingest.py <input> --json`：正式摄取前的本地预检；不调用 LLM，不创建 wiki 页面。
- `python tools/manifest.py check`：检查 `raw/source-manifest.jsonl` 结构、路径和重复项。
- `python tools/manifest.py find --source-id <source-id>`：按 source ID 查找 manifest 记录。
- `python tools/manifest.py find --hash <sha256:...>`：按内容 hash 查找 manifest 记录。
- `python tools/manifest.py find --path <raw-or-converted-path>`：按 raw、converted 或 converted-from 路径查找 manifest 记录。
- `python tools/manifest.py add ...`：在最终 raw path、source ID 和 hash 确认后追加 manifest 记录。
- `python tools/query.py "retrieval augmented generation"`：为 agent 查找本地 wiki 上下文，不生成回答。
- `python tools/query.py "retrieval augmented generation" --json`：机器可读 query context 输出。
- `python tools/save_synthesis.py --id example-synthesis --title "Example Synthesis" --question "What should be saved?" --answer-file /tmp/answer.md --evidence-file /tmp/evidence.md`：保存用户确认过的 synthesis 页面，并更新 index/log。
- `python tools/convert.py <input> --out raw/converted/<file>`：本地 Markdown/text 转换入口；不会自动更新 manifest 或 wiki 页面。
- `python -m unittest discover -s tests`：项目测试套件。
- `AGENTS.md` 里的 agent-first ingest/query 协议。
- `templates/source.md` 和 `templates/sources/` 里的来源模板。
- `examples/ingest/`：一个可运行的成功 ingest 示例。

当前仍不支持：

- PDF、Office 文档、远程网页、HTML 渲染和二进制文件转换。
- embeddings、向量检索、LLM 自动抽取和批量导入。
- 直接把远程 URL 抓取进知识库。

转换不等于 ingest。使用 `convert.py` 之后，仍需要让 agent 按 ingest 流程更新 `raw/source-manifest.jsonl`、source 页面、index 和 log。

`prepare_ingest.py` 和 `manifest.py` 也不等于 ingest。`prepare_ingest.py` 只做正式摄取前的预检、重复检查和建议；除非显式使用 `--report graph/ingest-prep-report.md`，它不会写文件。`manifest.py` 只维护 `raw/source-manifest.jsonl`，不会创建 source 页面，不会更新 `wiki/index.md` 或 `wiki/log.md`。

## 如何添加一份新资料

### Ingest v2 支持的输入

当前 agent-first ingest 支持：

- Markdown 文件。
- 纯文本文件。
- 直接粘贴到对话里的文本。
- 已经放在 `raw/converted/` 的 Markdown。

暂不直接支持：

- PDF。
- DOCX/PPTX/XLSX。
- 需要联网抓取或渲染的 HTML。
- 二进制文件。

这些格式仍是后续扩展。现在遇到这类资料时，请先提供可读文本或转换后的 Markdown。

### Ingest 请求示例

```text
请摄取 raw/originals/tiny-rag-note.md，类型是 technical article，更新 MuvyWiki，并运行 health。
```

```text
请把下面这段研究笔记整理进 MuvyWiki；如果值得长期保存，请创建 source 页面和必要的 concept/entity 页面。
```

```text
请检查这份资料是否已经在 raw/source-manifest.jsonl 里存在；如果不是重复来源，再 ingest。
```

推荐对 Codex 这样说：

```text
请 ingest 这份本地 Markdown/text 文件：<文件路径>
```

如果你手上只有网页链接，请先粘贴正文，或先提供转换后的本地 Markdown 文件。

或者：

```text
请把 raw/originals/<文件名> 摄取进 MuvyWiki。
```

一次 ingest 应该完成这些事：

1. 保存或读取原始资料。
2. 运行 `python tools/prepare_ingest.py <input> --json` 做预检。
3. 如需人工可读报告，运行 `python tools/prepare_ingest.py <input> --report graph/ingest-prep-report.md`。
4. 用 `python tools/manifest.py check` 检查 manifest 当前状态。
5. 用 `python tools/manifest.py find --source-id <source-id>`、`python tools/manifest.py find --hash <sha256:...>` 或 `python tools/manifest.py find --path <raw-or-converted-path>` 确认不是重复来源。
6. 最终 raw path、source ID 和 hash 确定后，用 `python tools/manifest.py add ...` 追加 manifest 记录。
7. 创建或更新 `wiki/sources/<source-id>.md`。
8. 抽取稳定概念，更新 `wiki/concepts/`。
9. 抽取重要实体，更新 `wiki/entities/`。
10. 如果值得长期保存，更新 `wiki/overview.md` 或创建 `wiki/syntheses/` 页面。
11. 更新 `wiki/index.md` 和 `wiki/log.md`。
12. 运行 `python tools/health.py`。

## 页面类型

### Source 页面

位置：`wiki/sources/`

用于记录单个来源，例如一篇论文、一篇博客、一份项目文档。每个 ingested document 都应该有且只有一个 source 页面。

Source 页面必须包含 provenance，用来追踪原始文件、URL、hash、转换结果和时间信息。

### Concept 页面

位置：`wiki/concepts/`

用于沉淀可复用概念，例如 `RetrievalAugmentedGeneration`、`TransformerArchitecture`、`AgentMemory`。

适合记录：

- 定义
- 核心机制
- 适用边界
- 支撑证据
- 相关概念
- 矛盾或争议

### Entity 页面

位置：`wiki/entities/`

用于记录人、组织、项目、论文、工具、产品、数据集等对象。

注意：一篇论文被首次摄取时先是 source。只有当它成为反复讨论的对象时，才需要单独创建 entity 页面。

### Synthesis 页面

位置：`wiki/syntheses/`

用于保存高价值综合回答，例如：

- “RAG 系统从 2023 到 2026 的主要架构变化”
- “我目前对 AI agent memory 的判断”
- “某两个开源项目的技术路线比较”

普通查询不会自动写文件。若回答值得长期保存，Codex 应该先问你是否保存为 synthesis 页面。

## 命名规则

Source 和 synthesis 文件名使用 kebab-case：

```text
attention-is-all-you-need.md
rag-systems-architecture-survey.md
```

Concept 和 entity 文件名使用 PascalCase 或官方大小写：

```text
RetrievalAugmentedGeneration.md
OpenAI.md
AndrejKarpathy.md
GPT5.md
```

内部链接必须指向 canonical ID：

```markdown
[[RetrievalAugmentedGeneration|Retrieval-Augmented Generation]]
```

不要把 alias 当成链接目标。alias 只是搜索和消歧用。

## 如何提问

可以这样问：

```text
我对 RAG 知道什么？
```

```text
比较 wiki 里关于 agent memory 的几种方案。
```

```text
基于现有知识库，整理一个「下一步该读什么」清单。
```

查询时，Codex 应该先读 `wiki/index.md`，再读相关页面，然后基于知识库回答。若使用了模型自身知识而不是 wiki 内容，应该明确标注。

`python tools/query.py "retrieval augmented generation"` 可以作为确定性的第一轮上下文查找。它会从本地 wiki 找到可能相关的页面、链接和匹配分数，但不会调用 LLM，也不会替你生成最终答案。需要章节摘录时可以加 `--include-sections`。Agent 仍然需要阅读匹配到的 wiki 页面，优先基于 wiki 内容回答，并用 `[[WikiLinks]]` 标注来源。

需要机器可读结果时可以运行：

```bash
python tools/query.py "retrieval augmented generation" --json
```

## 如何保存综合回答

普通查询不会自动写入知识库。只有当你确认这次回答值得长期保存时，agent 才应该保存 synthesis 页面。

保存流程：

1. Agent 先向你确认是否保存。
2. Agent 准备 answer Markdown 和 evidence Markdown。
3. Agent 使用 `python tools/save_synthesis.py --id example-synthesis --title "Example Synthesis" --question "What should be saved?" --answer-file /tmp/answer.md --evidence-file /tmp/evidence.md` 写入 synthesis 页面，并更新 `wiki/index.md` 和 `wiki/log.md`。
4. Agent 运行 `python tools/health.py` 和 `python tools/lint.py`，修复结构问题后再报告完成。

## 日志和索引

`wiki/index.md` 必须包含每个 wiki 页面，格式类似：

```markdown
- [[CanonicalID|Human Title]] (`wiki/path/File.md`) - type: concept - updated: YYYY-MM-DD - One sentence summary.
```

`wiki/log.md` 每条记录必须包含：

```markdown
## [YYYY-MM-DD] operation | title

- Changed pages:
- Raw paths:
- Source IDs:
- Unresolved issues:
```

允许的 operation 包括：`init`、`ingest`、`query`、`health`、`lint`、`graph`、`convert`、`batch`。

## 健康检查

运行：

```bash
python tools/health.py
```

机器可读输出：

```bash
python tools/health.py --json
```

它会检查：

- 必要目录和文件是否存在。
- 页面 frontmatter 是否符合规范。
- `canonical_id` 是否和文件名一致。
- `wiki/index.md` 是否收录所有页面，且页面类型和所在 section 是否正确。
- `wiki/log.md` 是否有规范日志字段。
- `[[WikiLinks]]` 是否能解析到 canonical ID。
- source provenance 是否和 `raw/source-manifest.jsonl` 一致。
- `raw_path` 和非空 `converted_path` 是否存在。
- alias 和 canonical ID 是否有明显冲突。

如果 health 失败，先修 health 报告的问题，再继续 ingest 或 query 保存。

## 工具接口

常用工具命令：

```bash
python tools/lint.py
python tools/lint.py --json
python tools/lint.py --report graph/lint-report.md
python tools/build_graph.py
python tools/prepare_ingest.py raw/originals/example.md --json
python tools/prepare_ingest.py raw/originals/example.md --report graph/ingest-prep-report.md
python tools/manifest.py check
python tools/manifest.py find --source-id example-source
python tools/manifest.py find --hash sha256:<64-hex-digits>
python tools/manifest.py find --path raw/originals/example.md
python tools/manifest.py add --source-id example-source --raw-path raw/originals/example.md --content-hash sha256:<64-hex-digits> --collected-at YYYY-MM-DD
python tools/query.py "retrieval augmented generation"
python tools/query.py "retrieval augmented generation" --json
python tools/save_synthesis.py --id example-synthesis --title "Example Synthesis" --question "What should be saved?" --answer-file /tmp/answer.md --evidence-file /tmp/evidence.md
python tools/convert.py raw/originals/example.txt --out raw/converted/example.md
```

`lint.py` 会检查空的必填章节、source 缺少 claims/evidence、concept 缺少 supporting sources、entity 缺少 evidence、孤立页面，以及 index 里仍保留的 `No ... yet.` 过期摘要。

`build_graph.py` 会从 wiki frontmatter、wikilinks、`source_ids`、`related_ids`、raw paths 和 provenance 生成 `graph/graph.json`、`graph/graph.html`、`graph/graph-report.md`。

`prepare_ingest.py` 会读取本地 Markdown/text 输入，计算 hash，检查 manifest 重复项，并给出 source ID、模板和下一步建议；它不会调用 LLM，也不会创建 wiki 页面。`manifest.py` 提供 `check`、`find` 和 `add` 子命令，只负责 `raw/source-manifest.jsonl`。

`query.py` 会查找本地 wiki 上下文包，但不生成回答、不联网、不摄取新 raw source。`save_synthesis.py` 会保存已经由用户确认的 synthesis 页面并维护 index/log，但不会调用 LLM，也不会把回答当作新来源写入 raw manifest。

`convert.py` 支持本地 Markdown/text 输入，输出必须是 `raw/converted/` 下的新文件。它不会自动更新 `raw/source-manifest.jsonl`，也不会自动创建 source 页面。

PDF、Office、远程网页、HTML 渲染和二进制文件仍不支持。需要先手动提供可读文本或转换后的 Markdown。

## 推荐日常工作流

### 摄取资料

```text
请摄取 raw/originals/<文件名>，更新 MuvyWiki，并运行 health。
```

### 查询已有知识

```text
请基于 MuvyWiki 回答：<问题>
```

### 保存综合判断

```text
这次回答值得保存，请保存为 synthesis 页面，并更新 index/log。
```

### 例行维护

```text
请运行 health，解释所有问题，并修复结构性问题。
```

### 同步文档

```text
请检查当前功能和接口，更新 README、USER_GUIDE、AGENTS、docs/superpowers/specs 以及相关目录 README，并运行测试、lint、graph 和 health。
```

## 维护建议

- 每次 ingest 后都运行 `python tools/health.py`。
- 每次改工具接口、能力边界或 ingest 流程后，同步更新 `README.md`、`USER_GUIDE.md`、`AGENTS.md`、`docs/superpowers/specs` 和相关目录 README。
- 不要手动绕过 `wiki/index.md` 和 `wiki/log.md`。
- 不要直接覆盖 `raw/originals/` 里的既有文件。
- 概念页不要太早泛滥；只有能复用的概念才单独成页。
- Synthesis 页面应该保存“以后会再问”的判断，而不是每个普通回答。
- 遇到矛盾时记录矛盾，不要静默选择一个说法覆盖另一个。

## 第一次使用建议

可以从 3 到 5 份高价值技术资料开始，例如：

- 一篇你最近读过的技术文章。
- 一篇论文。
- 一个你长期关注的开源项目 README。
- 一份你自己的研究笔记。

摄取完后，问：

```text
请基于当前 MuvyWiki，总结我现在的技术/科研知识图谱雏形，并建议接下来该补哪些概念页。
```

这样 MuvyWiki 会从“文件夹”开始变成真正的个人知识系统。
