# M6 — Reproducible Delivery and Quality Governance

## 目标与背景

此前 README 罗列了内部命令，却引用不存在的输入和临时文件，根知识库也为空。新用户无法只依赖仓库完成从 clone 到非空结果的验证。本阶段建立可复现交付路径，并把验收固化为 CI、路线图和 Milestone 证据。

## 实现内容

- 新增 `tools/demo.py`，在临时 fixture 副本中运行 health、lint、query 和 graph；
- 导入维护者拥有的 `muvywiki-repository-contract`，建立 raw → manifest → source → concept/entity → index/overview/log 知识链；
- 新增 Python 3.10、3.11、3.12 GitHub Actions 矩阵；
- 重写 README 与 USER_GUIDE 的 clone、环境、首次验证、真实查询和故障排查；
- 删除当前操作文档中不存在的 `example.*` 与 `/tmp` 输入引用；
- 建立 `ROADMAP.md` 和本目录的开发证据记录。

## 对外行为变化

- `python tools/demo.py` 提供零准备、非破坏性的首个成功路径；
- 根查询不再为空，可直接检索 repository root isolation 和 provenance；
- README 明确 Python 版本、零第三方依赖、private clone 权限和预期输出；
- 每次 push/PR 自动执行测试、manifest、health、lint、demo 和 fixture 验证；
- 路线图 TODO 绑定具体模块和可验收结果。

## 验证证据

- demo 稳定报告 health → lint → query → graph，fixture 当前为 4 个查询匹配、4 个节点、18 条边，并声明工作区未修改；
- manifest 包含 1 个根来源且 hash 与 raw artifact 一致；
- README 查询同时命中 `muvywiki-repository-contract` 和 `RepositoryRootIsolation`；
- 最终测试数量和 CI 结果应在上传候选 HEAD 上重新记录，不能复用中间提交数字。

## Commit 区间说明

- Start：`97bce0a feat: add a non-mutating end-to-end demo`；
- End：外部平台实际上传的 `quality-hardening` 合并后 HEAD；
- 已知阶段提交依次为 demo、根知识源、CI、README/USER_GUIDE、ROADMAP/Milestone evidence；
- 根知识源不是外部抓取或虚构材料，而是维护者对当前已实现仓库契约的原始技术说明；
- 文档和测试变更是修复可复现性硬门槛所需的产品交付，不应描述为新增检索算法；
- 最终填写平台前运行 `git rev-parse HEAD` 回填准确 end commit，并再次执行全部验证。
