# MuvyWiki 使用手册

MuvyWiki 是一个由你和 LLM 共同维护的个人知识库。你负责选择资料、提出问题、判断方向；LLM 负责整理来源、生成结构化页面、维护索引、记录日志、检查结构健康。

第一版适合技术文章、论文、开源项目、研究笔记和长期问题追踪，也保留了以后扩展图谱、语义 lint、批量导入和文档转换的接口。

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
python -m unittest discover -s tests
```

`health.py` 是第一版最重要的质量门。每次新增资料、修改索引、改页面结构后，都应该运行一次。

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
tools/              # 健康检查和预留工具接口
graph/              # 未来图谱输出目录
```

## 核心原则

`raw/` 是原始资料层。已有文件不要直接改写；如果要清洗或转换，原件放在 `raw/originals/`，转换结果放在 `raw/converted/`。

`wiki/` 是知识层。这里的页面可以被 LLM 更新，用来承载摘要、概念、实体、证据、矛盾和综合判断。

`AGENTS.md` 是操作协议。以后让 Codex 摄取资料或回答知识库问题时，它应该遵守这里的规则。

## 当前功能与接口状态

当前已经可以直接使用：

- `python tools/health.py`：结构健康检查。
- `python tools/health.py --json`：机器可读健康检查输出。
- `python -m unittest discover -s tests`：项目测试套件。
- `AGENTS.md` 里的 agent-first ingest/query 协议。
- `templates/source.md` 和 `templates/sources/` 里的来源模板。
- `examples/ingest/`：一个可运行的成功 ingest 示例。

当前是“接口已保留，功能未实现”：

- `python tools/lint.py`：语义 lint 入口，目前返回 exit code `3`。
- `python tools/build_graph.py`：图谱生成入口，目前返回 exit code `3`。
- `python tools/convert.py <input> --out raw/converted/<file>`：转换入口，目前只检查输出路径必须在 `raw/converted/` 下，然后返回 exit code `3`。

不要把预留工具当成已经完成的能力。比如现在不能直接让 `convert.py` 把 PDF、网页或 Office 文档转换成 Markdown；遇到这类资料时，先提供可读文本或已经转换好的 Markdown。

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

这些格式会在 Convert v2 里处理。现在遇到这类资料时，请先提供可读文本或转换后的 Markdown。

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
2. 计算内容 hash，检查 `raw/source-manifest.jsonl` 是否已有重复来源。
3. 创建或更新 `wiki/sources/<source-id>.md`。
4. 抽取稳定概念，更新 `wiki/concepts/`。
5. 抽取重要实体，更新 `wiki/entities/`。
6. 如果值得长期保存，更新 `wiki/overview.md` 或创建 `wiki/syntheses/` 页面。
7. 更新 `wiki/index.md` 和 `wiki/log.md`。
8. 运行 `python tools/health.py`。

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

## 预留工具

这些工具第一版是接口，不是完整实现：

```bash
python tools/lint.py
python tools/build_graph.py
python tools/convert.py raw/originals/example.pdf --out raw/converted/example.md
```

它们目前会返回 exit code `3`，表示“接口已保留，功能未来实现”。

`convert.py` 有一个已经生效的安全检查：`--out` 必须指向 `raw/converted/` 下面的相对路径。这个检查不代表转换功能已经完成。

未来用途：

- `lint.py`：语义 lint，例如矛盾、过时说法、孤立页面、缺少概念页。
- `build_graph.py`：生成 `graph/graph.json`、`graph/graph.html`、`graph/graph-report.md`。
- `convert.py`：PDF、arXiv、网页、Office 文档到 Markdown 的转换入口。

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
请检查当前功能和接口，更新 README、USER_GUIDE、AGENTS 以及相关目录 README，并运行测试和 health。
```

## 维护建议

- 每次 ingest 后都运行 `python tools/health.py`。
- 每次改工具接口、预留能力或 ingest 流程后，同步更新 `README.md`、`USER_GUIDE.md` 和 `AGENTS.md`。
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
