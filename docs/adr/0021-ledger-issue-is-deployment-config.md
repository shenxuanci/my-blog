# 台账 issue 号改为部署配置，`shadow-status` 显式不参与

2026-08-20 原 GitHub 账号被停用，仓库必须在新账号下重建。迁移过程中发现台账 issue 号 `15` 硬编码在 10 处：`issue_ledger.py` 五个子命令的 `default=15`，加上三个 workflow 的五处 `--issue 15` 实参。

也就是说，「把仓库换到另一个账号」这件本该是改设置的事，被写成了一次代码改动。这不是迁移引入的问题，是迁移把它暴露出来了。

## 决定

号码来自 GitHub repo variable `LEDGER_ISSUE`，经 workflow 的**步骤级** `env:` 传入，`main()` 从 `environ` 读取。`--issue` 保留为显式覆盖，供人工排障使用。

`_resolve_issue_number` **不提供任何回退默认值**。缺失、非整数、非正数一律抛 `ValueError`，非零退出。

理由是这个 sink 的性质：台账是 append-only 的，workflow 每天无人值守地跑。一个「看起来合理但是错的」号码不会报错，它会把当日台账静默追加进新仓库里恰好占着那个号的 issue —— 那可能是一条真实的讨论。等发现时已经写了若干天，而且没法干净地撤回。相比之下，缺配置时当场失败是便宜得多的失败。

## 刻意不对称的部分：`shadow-status` 不接 `--issue`

五个子命令里，只有 `shadow-status` 既不接受 `--issue`，也不读 `LEDGER_ISSUE`。这看起来像是漏改，它不是。

`shadow-status` 自 ADR 0016 起判定已是常量，它不做任何网络 I/O、不要 token。`readme.md` 记着这条约束的代价：workflow 把它的**非零退出当作「状态未知」并 fail-open 去跑一遍完整的付费 shadow 管线**。所以对这一步而言，任何新增的失败可能性都等价于「多花一次十分钟的付费运行」。

如果让它也去解析 `LEDGER_ISSUE`，就等于给一个不需要这个号的命令新开了一条失败路径 —— 一次忘配 repo variable 就会买单一次 shadow 运行。号码解析因此被放在 `shadow-status` 提前返回**之后**：这条命令在结构上就到不了解析器，而不是靠调用顺序碰巧绕开。

**看到这个不一致不要「修」它。** 把 `--issue` 加回 `shadow-status`、或者把解析上移到 `main()` 开头，都会重新打开 ADR 0016 关掉的那条 fail-open 路径。`test_shadow_status_cli_survives_a_missing_token_without_forcing_a_run` 用一个完全空的 environ（无 token、无 repository、无 `LEDGER_ISSUE`）钉住了这一点。

## 代价与被接受的风险

**旧台账历史随旧仓库一起丢失。** 账号停用后旧仓库对外 404、API 403，Issue #15 的逐日评论无法导出。新仓库的台账从空开始：`compute_streaks` 从零重算，`fingerprints.runtime` 在下一次成功 publish 之前没有当前值。

这个损失是账号停用造成的，不是本决策造成的 —— 换成「只改号码不抽配置」也一样丢。按 ADR 0016，台账已降为质量仪表盘、不通往任何开关，所以损失的是趋势可读性，没有任何流程被阻塞。

**多了一个部署前置项。** 新仓库必须设置 `LEDGER_ISSUE`，否则台账相关的三个 workflow 会失败。这是刻意的：见上面关于「不提供回退默认值」的理由。已记入 `readme.md`。

## 与既有决策的关系

不改变 ADR 0016 与 ADR 0019 的任何判断。ADR 0016 关于 `shadow_status` 零网络 I/O、fail-open 代价的分析是本决策不对称设计的**直接依据**；ADR 0019 关于「台账是读趋势的仪表盘」的定位，是本决策接受历史丢失这一代价的依据。
