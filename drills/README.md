# 历年真题模拟演练操作指南

Task 23 做的是"工具链跑不跑得通"的技术验证。这份指南是给团队三人的——真正检验工具箱好不好用，需要一次真实的、有时间压力的建模演练，这一步只能人做，agent 代替不了。

## 怎么选题

从 `corpus/manifest.md` 里选一道：
- 题型和难度接近最近两届（2024、2025）
- 三人都还没读过题解/没被剧透过思路的题（不然演练失真）

## 怎么跑

1. 定一个时间盒（建议 1-2 天，别用满 72 小时，重点是压力测试工具箱不是拿奖）
2. 按 `analysis/modeling-workflow.md` 走：用 `templates/init_contest_case.py` 建目录 → 只放官方题目/附件 → 填模型卡和歧义审计 → 候选方案拍板 → 基线+主模型 → 实验与独立验证 → JSON 生成论文 → 运行 `case_audit.py` 和合规检查
3. 全程记录卡手的地方——不管是模板排版问题、脚手架没覆盖到的方法、清单漏检了什么，还是 AI 出的方案不靠谱

演练冻结结果前禁止读取 `corpus/`、`建模/` 中的同题论文。需要和优秀论文比较时，先保存盲测结果、代码和审计报告，再把 `case.json` 的 `phase` 改为 `postmortem`。

## 已有的两次完整演练

### 2025 B 题：碳化硅外延层厚度（走完整质量契约）

[`2025-B-sic-epilayer/`](2025-B-sic-epilayer/) 是唯一一次把 `case.json` 证据链也跑完的演练——
`init_contest_case.py` → 模型卡 → 基线 + 主方法 → 分类验证 → `results.json` → 论文 →
`case_audit.py`（0 警告）+ `compliance_check.py`（未发现问题）：

```bash
.venv/bin/python drills/2025-B-sic-epilayer/src/compute.py       # 约 25 秒
.venv/bin/python drills/2025-B-sic-epilayer/src/make_figures.py
.venv/bin/python drills/2025-B-sic-epilayer/paper/gen_paper.py
```

想看「质量契约落到一道真题上是什么样」，从这个目录开始。它示范了三件事：把题目里最难的那个
未知量（折射率）正面解决而不是绕过去；把走不通的路线连同它的条件数一起报告；判据不设人为阈值。

### 2025 A 题：烟幕干扰弹投放策略（工具链演练）

[`2025-A-smoke-screen/`](2025-A-smoke-screen/) 是照上面流程走完的 2025 A 题，五问全解、可复现：

```bash
.venv/bin/python drills/2025-A-smoke-screen/solve.py     # 约一分钟，固定种子 2025
.venv/bin/python drills/2025-A-smoke-screen/make_artifacts.py
```

拿它当参照时注意三点：**一，** 它是盲测演练不是获奖范本，问题五用分层配对加边际追加，目录 README 里已声明只是可复现的启发式可行解、不声称全局最优；**二，** 它演示的是「官方输入 → 模型 → results.json → 论文和官方 xlsx」这条链怎么接，值得抄的是这个组织方式；**三，** 它没有建 `case.json`，所以 `case_audit.py` 的那套模型卡证据链在它身上没跑过——要看那一步，去上面的 2025 B 题。

两次演练都不是获奖范本，各自的局限写在自己的 README 和论文「模型的缺点」一节里。

## 演练之后

把发现的问题整理成一份 `drills/<日期>-real-drill.md`（格式参考 `2026-integration-drill.md`），然后回去修 `analysis/`、`templates/`、`snippets/`、`checklist/` 里对应的地方——这是"设计原则"里说的持续迭代，不是演练完就结束了。

已有两份复盘记录：

- [`2026-08-03-completeness.md`](2026-08-03-completeness.md) —— 2025 B 题演练与官方优秀论文 B060、B157 的对比复盘。核心发现是**工具箱早就把体量目标量化好了（`analysis/paper-structure.md`），但交稿前没有任何东西拿产出去比对它**，于是一篇 16 页、附录空白、图数只有中位值 29% 的论文以「0 个警告」通过了审计。由此新增了 `checklist/paper_completeness.py` 完备性对标、`templates/appendix_code.py` 附录代码内联，以及联合拟合、子区间漂移扫描、置信区间/CV/Bootstrap 等能力。
- [`2026-integration-drill.md`](2026-integration-drill.md) —— 骨架级工具链验证（不涉及真实建模）。
