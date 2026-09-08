# M5 — Ingest Preparation and Repository-root Isolation

## 目标与背景

仓库需要在正式 ingest 前确定输入类型、hash、source ID、manifest 冲突和安全路径；同时，原 fixture 通过复制工具保持自包含，造成重复 LOC 和实现漂移。本阶段先补齐 preflight/manifest，再用显式 root 消除复制架构。

## 实现内容

- 在 `839e8ff` 中加入 `manifest.py`、`prepare_ingest.py`、领域模板和相应测试/文档；
- 为 health、lint、graph、convert、manifest、prepare、query 和 save_synthesis 增加统一 `--repo-root`；
- 声明 Python `>=3.10` 和零第三方运行时依赖；
- 增加跨 root CLI 回归测试；
- 删除 `examples/ingest/tools` 下 7 个复制实现，改为由根工具操作 fixture；
- 更新 fixture 协议、命令和防重复测试。

## 对外行为变化

- 用户可以在同一实现上选择主知识库、fixture 或临时 root；
- 不传 `--repo-root` 时保留原调用行为；
- root 不存在或不是目录时返回参数错误；
- manifest 的全局 `--repo-root` 位于 `check/find/add` 子命令之前；
- fixture 不再能从自身目录直接运行私有工具副本，需从项目根选择 fixture root。

## 验证证据

- `tests/test_repo_root_cli.py` 覆盖所有支持 root 的 CLI 读写；
- `tests/test_ingest_examples.py` 明确断言 fixture 中没有 Python 工具副本；
- 阶段终点共有 124 个单元测试通过；
- 根工具对 fixture 的 health/lint 通过，查询 `retrieval augmented generation` 返回 4 个结果。

## Commit 区间说明

- Start：`839e8ff Updated func`；
- End：`4bf48b7 refactor: reuse root tools in the ingest fixture`；
- `839e8ff` 是一个需要明确披露的混合大提交：同时加入 manifest、preflight、模板、测试、文档和复制 fixture 工具；它不应被描述成单一小修复；
- `0d499e4` 建立替代复制代码所需的 root 接口，`4bf48b7` 再删除 2,544 行 fixture 工具副本；
- 该区间净变更较大，但被删除的复制工具不作为新增原创能力，阶段价值是统一实现和提高可维护性。
