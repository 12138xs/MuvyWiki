# M1 — Repository Foundation and Structural Health

## 目标与背景

项目需要从设计设想变成具有明确目录职责、页面契约和可自动检查结构的知识库。该阶段建立“raw 保存来源、wiki 保存维护知识、templates 定义页面形状、tools 提供确定性检查”的基础。

## 实现内容

- 编写总体设计、实现计划和操作协议；
- 创建 `raw/`、`wiki/`、`templates/`、`tools/` 与 `graph/` 骨架；
- 定义 source、concept、entity、synthesis、overview、index 和 log 模板；
- 实现 health 对必需路径、frontmatter、canonical ID、index、log、wikilink 和 provenance 的检查；
- 增加路径越界、重复 ID、索引错位和来源字段不一致等回归测试。

## 对外行为变化

- 从无可运行仓库变为可以执行 `python tools/health.py` 的结构化项目；
- raw artifact 和 wiki page 的职责被明确分离；
- source 页面必须通过 canonical ID、raw path、hash 和 manifest 建立追踪关系；
- health 使用退出码区分健康与结构问题，并支持 JSON 输出。

## 验证证据

- 起点只有设计意图，没有稳定的仓库检查接口；
- 终点 health 可以发现缺失路径、无效 frontmatter、重复 ID、错误 index 和 provenance 不一致；
- 相关行为由 `tests/test_health.py` 覆盖；
- 后续当前 HEAD 上运行 `python tools/health.py` 仍为 `ok`，证明基础契约保持兼容。

## Commit 区间说明

- Start：`c0cacd3 docs: add MuvyWiki design spec`；
- End：`e6ae7b9 fix: close final health blind spots`；
- 区间包含初始设计、实现计划、scaffold、模板、agent 协议和 health 加固，组成从零到结构可验证仓库的完整阶段；
- `bd2e085 chore: ignore local worktrees` 是开发环境卫生配置，服务于同一仓库建立阶段；
- README 文案修订和 health 修复均围绕同一结构契约，没有隐藏独立业务功能。
