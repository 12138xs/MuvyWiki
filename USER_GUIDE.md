# MuvyWiki 使用手册

MuvyWiki 是一个由使用者和 agent 共同维护的个人知识库。使用者负责选择合法来源、判断事实与决定是否保存综合结论；agent 按 [AGENTS.md](AGENTS.md) 读取来源、维护知识页面、更新索引和日志，并使用确定性工具验证结果。

## 1. 获取、安装与首次验证

### 环境要求

- 已获得私有仓库 `12138xs/MuvyWiki` 的 GitHub 访问权限；
- Git；
- Python 3.10 或更高版本；
- 不需要安装第三方 Python 包，当前运行时只使用标准库。

macOS 或 Linux：

```bash
git clone https://github.com/12138xs/MuvyWiki.git
cd MuvyWiki
python3 -m venv .venv
source .venv/bin/activate
python --version
python tools/health.py
python tools/demo.py
```

Windows PowerShell：

```powershell
git clone https://github.com/12138xs/MuvyWiki.git
cd MuvyWiki
py -3.10 -m venv .venv
.venv\Scripts\activate
python --version
python tools/health.py
python tools/demo.py
```

`python --version` 应为 3.10 或更高版本。首次验证的稳定输出应包含：

```text
MuvyWiki health: ok
MuvyWiki demo: ok
Steps: health -> lint -> query -> graph
Workspace modified: no
```

demo 中的匹配数和图节点数必须大于 0，未来随 fixture 调整可能变化。demo 在临时目录运行，不会修改当前工作区。

## 2. 立即查询已有知识

根知识库已经包含一份可追溯的仓库契约来源，因此无需先导入材料即可查询：

```bash
python tools/query.py "repository root isolation provenance"
```

结果应包含 `muvywiki-repository-contract` 和 `RepositoryRootIsolation`。机器可读输出：

```bash
python tools/query.py "repository root isolation provenance" --json
```

需要匹配章节摘要时增加 `--include-sections`。query 是确定性关键词检索，只生成 context packet；它不会联网、调用 LLM、自动写入知识库或生成最终答案。

## 3. 仓库结构

```text
raw/
  originals/        原始资料，只追加、不覆盖
  converted/        从原始资料转换出的 Markdown/text
  source-manifest.jsonl

wiki/
  index.md          所有维护页面的全局索引
  overview.md       当前知识地图与重点主题
  log.md            规范化维护日志
  sources/          每个来源一页
  concepts/         可跨来源复用的概念
  entities/         人、组织、项目、论文、工具等实体
  syntheses/        经使用者确认后保存的综合判断

templates/          页面模板
tools/              确定性命令行工具
tests/              单元和集成测试
examples/ingest/    只包含内容的完整 ingest fixture
graph/              本地生成的图数据、HTML 和报告
```

三个核心边界：

- `raw/` 保存来源证据，已有文件不得原地改写；
- `wiki/` 保存能够继续演进的知识，不应只复制原文；
- `tools/` 检查结构和执行轻量操作，但不代替 agent 的阅读、抽取和判断。

## 4. 工具接口

### 健康、lint 与测试

```bash
python tools/health.py
python tools/health.py --json
python tools/lint.py
python tools/lint.py --json
python -m unittest discover -s tests
```

health 检查必要路径、frontmatter、canonical ID、index、log、wikilink、manifest 和 source provenance。lint 检查空章节、缺少 claims/evidence、孤立页面和过期 index 空状态。两者都通过才表示结构与基础内容形状合格；它们不证明所有知识结论都正确。

### 图构建

```bash
python tools/build_graph.py
```

该命令从 frontmatter、wikilink、source ID、related ID 和 raw path 生成：

- `graph/graph.json`；
- `graph/graph.html`；
- `graph/graph-report.md`。

生成文件用于本地查看，不应手工修改。

### 选择其他知识库根

health、lint、build_graph、convert、prepare_ingest、query 和 save_synthesis 接受 `--repo-root PATH`。fixture 示例：

```bash
python tools/health.py --repo-root examples/ingest
python tools/lint.py --repo-root examples/ingest
python tools/query.py --repo-root examples/ingest "retrieval augmented generation"
```

manifest 的全局参数放在子命令之前：

```bash
python tools/manifest.py --repo-root examples/ingest check
python tools/manifest.py --repo-root examples/ingest find --source-id tiny-rag-note
```

显式 root 不存在或不是目录时，工具退出 `2`，不会继续读写。

### 非破坏性 demo

```bash
python tools/demo.py
python tools/demo.py --json
```

demo 将 `examples/ingest` 复制到临时目录，依次运行 health、lint、query 和 graph，并要求 query 与 graph 非空。它是新用户首选验证入口。

## 5. 添加一份新资料

### 支持的输入

当前支持本地 UTF-8 Markdown、纯文本、对话中粘贴后保存的文本，以及已经转换为 Markdown/text 的材料。

当前不支持直接抓取远程 URL，也不支持 PDF、DOCX、PPTX、XLSX、渲染 HTML 或二进制文件转换。遇到这些格式时，先提供一份有合法权利的本地 Markdown/text 版本。

### 准备来源

1. 确认资料真实、对提交和保存具有权利，并检查隐私；
2. 为来源选择稳定的 kebab-case ID；
3. 将原始文件加入 `raw/originals/`，不得覆盖已有文件；
4. 对新文件运行预检。

假设使用者已新增 `raw/originals/my-note.md`：

```bash
python tools/prepare_ingest.py raw/originals/my-note.md --json
```

`my-note.md` 是用户输入占位符，不是仓库自带文件。无需准备文件即可运行的示例是 `python tools/demo.py`。

### 检查 manifest

```bash
python tools/manifest.py check
python tools/manifest.py find --source-id my-note
python tools/manifest.py find --path raw/originals/my-note.md
```

预检会给出内容 hash。再用 `find --hash sha256:<64位小写十六进制>` 检查重复来源。只有 source ID、raw path、hash 和来源权利全部确认后，才运行 `python tools/manifest.py add ...`。

manifest add 只追加一行 JSONL，不会创建 source 页面，也不会更新 index/log。

### Agent-led ingest

向 agent 提出：

```text
请摄取 raw/originals/my-note.md；深入阅读来源，维护 source、必要的 concept/entity、index 和 log，并运行 manifest、health 与 lint 检查。
```

一次完成的 ingest 必须：

1. 读取 `wiki/index.md`、`wiki/overview.md` 和相关现有页面；
2. 运行 prepare_ingest 并检查 ID、hash、路径和重复项；
3. 更新 `raw/source-manifest.jsonl`；
4. 创建或更新唯一的 `wiki/sources/<source-id>.md`；
5. 抽取有证据的 claims，不用目录或摘要冒充深入阅读；
6. 只在可复用时创建 concept，只在会反复讨论时创建 entity；
7. 明确记录不确定性、矛盾和 open questions；
8. 更新 `wiki/index.md` 和 `wiki/log.md`；
9. 仅在知识地图发生变化时更新 `wiki/overview.md`；
10. 通过 manifest、health 和 lint 后再报告完成。

`needs-review` 表示可见 backlog，不等于完成摄取。convert、prepare、manifest 或 health 单独成功也不等于完成摄取。

## 6. 页面类型和命名

### Source

每个 ingested source 对应一个 `wiki/sources/<source-id>.md`。页面必须含完整 provenance，并与 manifest 中同一 source ID 的字段一致。

### Concept

`wiki/concepts/` 保存跨来源复用的概念。文件名和 canonical ID 使用 PascalCase 或规范产品大小写，页面要包含定义、机制、边界、证据和 supporting sources。

### Entity

`wiki/entities/` 保存会反复讨论的人、组织、项目、论文、数据集或工具。私人或偶发名称留在 source 页面，不应无理由升级为实体。

### Synthesis

`wiki/syntheses/` 保存经使用者确认、以后可能再次使用的综合判断。普通查询不会自动保存 synthesis。

Source 和 synthesis ID 使用 kebab-case；concept 和 entity 使用 PascalCase 或官方大小写。内部链接始终指向 canonical ID：

```markdown
[[RepositoryRootIsolation|Repository Root Isolation（仓库根隔离）]]
```

## 7. 查询与保存综合回答

向 agent 查询时可使用：

```text
请基于当前 MuvyWiki 回答：仓库根隔离解决了什么问题？只引用已有 wiki 页面；模型自身知识请单独标注。
```

Agent 应先运行 query 获取候选，再阅读实际页面后回答。若回答值得长期维护，使用者需要明确确认保存。

保存 synthesis 的接口说明可安全查看：

```bash
python tools/save_synthesis.py --help
```

实际保存时，agent 会准备真实存在的 answer/evidence Markdown，选择新的 synthesis ID，调用 save_synthesis，并在写入后运行 health 与 lint。不要复制依赖不存在临时文件的示例命令。

## 8. 开发与 CI

本地合并前运行：

```bash
python -m unittest discover -s tests
python tools/manifest.py check
python tools/health.py
python tools/lint.py
python tools/demo.py
python tools/health.py --repo-root examples/ingest
python tools/lint.py --repo-root examples/ingest
```

GitHub Actions 在 Python 3.10、3.11、3.12 上执行同一组门槛。修改 CLI 参数、默认值、输出、错误处理或目录结构时，必须同步更新 README、USER_GUIDE、AGENTS、当前 specs、相关目录 README、测试和 CI。

## 9. 日志、索引与维护

`wiki/index.md` 必须收录每个维护页面，并写明路径、类型、更新时间和一句话摘要。`wiki/log.md` 的每条操作至少包含 Changed pages、Raw paths、Source IDs 和 Unresolved issues。

日常维护原则：

- 每次 ingest 或结构变更后运行 health；
- 活跃页面内容变化后运行 lint；
- 不绕过 index 和 log；
- 不覆盖已有 raw artifact；
- 不为扩大页面数量而创建无证据 concept/entity；
- 发现矛盾时记录矛盾，不静默覆盖旧判断；
- fixture 只保存内容，不复制生产工具；
- 生成图后确认没有意外未跟踪文件；
- 提交前检查 diff、测试和敏感信息。

## 10. 常见问题

### `python: command not found`

确认虚拟环境已激活，或使用实际的 Python 3.10+ 命令。不要用 Python 2。

### 私有仓库 clone 显示 `Repository not found`

先在 GitHub 登录有权限的账号，并确认 Git 凭据能够访问 `12138xs/MuvyWiki`。

### `Invalid repository root`

检查 `--repo-root` 指向的路径是否存在且为目录。fixture 命令应从项目根运行，路径为 `examples/ingest`。

### health 失败

按输出逐项修复缺失路径、frontmatter、index、log、wikilink、manifest 或 provenance。health 未通过时不要继续报告 ingest 完成。

### lint 失败

补充来源支持的 claims/evidence，连接孤立页面，清理 index 的过期空状态；尚未完成的内容保持 `needs-review`。

### fixture preflight 返回 1

`tiny-rag-note` 已存在于 fixture manifest，重复预检返回 1 是预期行为，不代表 fixture 损坏。

### 运行命令后工作区出现变化

普通 health、lint、query 和 demo 不应修改仓库。build_graph、带 `--report` 的 lint/prepare、convert、manifest add 和 save_synthesis 会写文件；运行前确认目标，运行后检查 `git status --short`。

## 11. 安全边界

不得把 API key、token、cookie、密码、数据库连接串、私钥、助记词、客户数据、个人身份信息或内部地址写入 raw、wiki、日志、测试 fixture 或 Git 历史。

若真实凭据曾进入历史，删除 HEAD 文件并不足够：立即轮换凭据，再评估历史清理和协作者同步影响。

来源必须真实且具有合法保存、加工和提交权利。第三方、生成、vendor 或复制内容必须说明来源与用途，不能冒充原创实现。

## 12. 文档入口

- [README.md](README.md)：首次安装、验证与接口总览；
- [AGENTS.md](AGENTS.md)：agent 的完整维护协议；
- [raw/README.md](raw/README.md)：来源与 manifest 规则；
- [graph/README.md](graph/README.md)：图产物说明；
- [examples/ingest/README.md](examples/ingest/README.md)：fixture 运行说明；
- `docs/superpowers/specs/`：当前设计依据；
- `docs/superpowers/plans/`：历史实施计划，不是当前操作指令。
