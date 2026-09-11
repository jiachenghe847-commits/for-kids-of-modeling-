# 规划求解（线性 / 整数 / 非线性）

**什么时候用**：有明确目标函数（对应 `notation.md` 里的 `Z`）和约束，求最优解——资源分配、排班、生产计划、选址、投资组合等。按变量与约束类型选函数：
- 目标和约束都线性、变量连续 → `solve_lp`
- 变量必须取整数或 0-1（"派几辆车""选不选某方案"）→ `solve_milp`
- **多个相互冲突的目标**（成本最低 + 效益最高 + 风险最小）→ `solve_multi_objective`
- 有明确优先级（先最少撤销，再最少调整，最后最小幅度）→ `solve_lexicographic_lp` / `solve_lexicographic_milp`
- 目标或约束非线性 → `solve_nlp`
- 变量非线性且多峰/组合爆炸、建不出标准型 → 转 `snippets/metaheuristics/`

**参数怎么调**：
- 三个函数都默认求**最小化**，要最大化就把目标（`c` 或 `func`）取负号（见测试）。
- `solve_lp`/`solve_milp` 的 `A_ub, b_ub` 是 `<=` 不等式约束；等式约束 `linprog` 用 `A_eq, b_eq`。
- `solve_milp` 的 `integrality`：0=连续、1=整数；0-1 变量设 `integrality=1` 且 `bounds=(0,1)`。
- `solve_nlp` 的 `constraints` 用 scipy 字典格式，`{"type":"ineq","fun":g}` 表示 `g(x) >= 0`；非线性问题**对初值 `x0` 敏感**，给不好会收敛到局部最优。
- `solve_multi_objective` 的 `weights` 是关键，别拍脑袋——用 `snippets/ahp/`（主观）或 `snippets/topsis_entropy/` 熵权法（客观）定，并在正文说明依据；`normalize=True` 会先按各目标单独最优值无量纲化，避免量纲大的目标主导，一般保持开启。
- `solve_lexicographic_*` 按 `objectives` 列表从前到后逐层求解，每层把上一层的最优值锁成约束；`tolerances` 只用于说明数值容差。若某层达到时间上限，返回的可行解只能称为 incumbent，`optimality_proven` 会是 `False`。

**结果怎么解读**：`success=False` 说明无可行解或求解失败，不能报告 `x`——检查约束是否写错、是否真无解。`solve_lp`/`solve_milp` 会保留 `status`、`message`、`optimality_proven` 和 `feasible_incumbent`；MILP 另保存 `mip_gap`。论文中只能在 `optimality_proven=True` 时使用“最优/最多/最少”，否则报告可行值、上下界或间隙。`solve_nlp` 即使 `success=True` 也只是局部最优，重要问题要换多个初值验证或用 metaheuristics 对照。`solve_multi_objective` 返回 `ideals`（各目标单独最优的"理想点"）和 `objective_values`（折中解下各目标实际值），两者对比就是"为了兼顾其他目标各让了多少步"——这是多目标题目的核心结论，务必在正文给出这张对比表，并做权重灵敏度分析。

**常见坑**：
- 约束方向搞反（`A_ub, b_ub` 是 `<=`）
- 该整数的变量用连续松弛结果直接四舍五入报告——四舍五入后可能不可行或非最优，要用 `solve_milp`
- 非线性规划只跑一个初值就当全局最优
- 最大化忘了给目标取负，求成了最小化
- 用一个很大的加权系数假装实现了字典序；有明确优先级时必须逐层锁定目标，或在缩小规模上证明加权法等价
