# D 题复盘：需要固化到工具箱的经验

这份记录把 D 题求解过程中发现的错误模式转成通用规则。它描述工具链问题和修正方式，不把某道题的数值结论当成通用结论。

## 暴露的问题

1. 题目中的“优先保护”“尽量保持”和“允许重新安排”有多种合理解释。早期把加强假设当成题目硬约束，导致不同情景的结果不能直接比较。
2. 用加权目标或不透明的求解顺序表达字典序目标，不能证明高优先级目标没有被牺牲。
3. 限时整数规划找到可行方案后，容易把求解器当前解写成“最优”，忽略停止原因、上下界和 MIP gap。
4. 只检查优化器内存中的数组，无法发现 Excel/CSV 导出和再读入时丢负号、截断小数、错配设备编号等问题。
5. 只保留最终 PDF 和最好的一次运行，无法证明结果可复现，也无法区分代码问题、题意调整和排版修改。

## 工具箱中的对应改动

- `snippets.linear_programming` 增加 `solve_lexicographic_lp` 和 `solve_lexicographic_milp`。每层目标单独求解，并把已证明的最优值锁成下一层约束；返回每层状态、可行 incumbent 和 `optimality_proven`。
- `solve_lp`/`solve_milp` 保留 `status`、`message`、可行性和最优性信息；MILP 额外保留 `mip_gap` 与节点数。时间上限导致的可行解不能自动变成“最优”。
- `snippets.model_validation` 增加 `parse_number` 和 `compare_tabular_records`，用于从官方表、Excel 或 CSV 独立回读并逐字段比较，保留负号、小数和单位字段。
- `checklist.evidence_audit` 增加 `optimization` 证据类型，拒绝“未证明最优却声称最优”的记录，并检查停止原因、可行 incumbent、间隙和运行时间字段。
- `case.json` 新模板增加 `objective_policy` 和题意情景对照字段。`case_audit.py` 会检查字典序阶段、情景对照路径和最优性证据路径。
- 交付流程继续使用运行哈希、重复运行、PDF 检查和独立评审；这些记录用于确认重算时输入、代码和结果没有漂移。

## 使用顺序

先在 `case.json` 写明主情景、对照情景和目标优先级。优化代码用字典序接口或明确的单目标政策；每个阶段保存结果 JSON。把最终方案导出后重新读取，用 `compare_tabular_records` 检查编号、时间、频段、动作和目标值。若求解器到达时间上限，论文只写可行值和上下界。最后用 `record_run.py` 记录重复运行，再运行 `delivery_audit.py`。

这些规则解决的是证据链和表述边界，不能替代队伍对题意、公式和最终 PDF 的人工复核。
