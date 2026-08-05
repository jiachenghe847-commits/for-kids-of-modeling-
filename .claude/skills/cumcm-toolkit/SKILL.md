---
name: cumcm-toolkit
description: 国赛（CUMCM）完整建模与论文工具箱。用于新赛题盲测、目标口径审计、模型卡、代码与公式追踪、优化实验留痕、交叉验证、结果到 LaTeX/Word 生成、研究质量审计和提交合规检查；也用于选建模方法、写论文和赛后复盘。
---

# cumcm-toolkit

备赛期间用 Claude Code 迭代这个工具箱本身时使用这份 skill；内容和 `AGENTS.md`（Codex 用）保持同步，改动时两边都要改。

## 完整求解的质量契约

用户提供新题并要求完整求解、结果文件或论文时，必须执行 `analysis/modeling-workflow.md`：

1. 默认 `official-only` 盲测，只读取官方题目、附件和空白模板；不得读取 `corpus/`、`建模/` 中的同题论文、答案、代码或数值。用户明确要求赛后比较时才进入 `postmortem`。注意区分**演练与实战**：盲测演练连公开文献、国家标准也一并回避（否则演练失真），实战则必须检索行业标准与既有方法并写进参考文献——盲测该放弃，实战放弃就是白扔分。见 `analysis/modeling-workflow.md` 第 0 节。
2. 用 `python templates/init_contest_case.py <目录> --case-id <编号> --questions <数量>` 建立 `case.json`，逐问记录目标量、题意歧义、指标口径、变量、目标、约束、假设和方程到代码/测试映射。字段里的尖括号 `<...>` 是填写口径提示，审计器一律判为未填写，必须替换掉。
3. 先实现透明基线，再实现主方法。耦合变量默认联合求解；贪心、分层或分解方法必须在缩小规模上与联合搜索/精确解比较。
4. 随机算法至少保存 3 个固定种子的原始结果和汇总，迭代算法保存收敛轨迹，优化结果保存逐约束残差，每问至少做一种独立验证。另外主动找系统误差：用 `subrange_drift_scan` 看待求量在不同数据子区间上漂不漂（单调漂移几乎一定是漏建模），多组数据共享参数时用 `joint_fit` 联合拟合而不是各拟各的再平均（见第 5.5 节）。
5. 全部数字统一写入 `artifacts/results.json` 并由论文生成器插入。每问正文形成“分析 → 模型 → 算法 → 结果 → 验证 → 解释”闭环。这六项是内容要求不是节标题：模板把「问题分析」放在顶层 `\section{问题分析}`，其余五项落在「模型建立 / 算法设计与求解 / 结果分析 / 模型验证」四个小节里，求解结果与结果解释合并进「结果分析」。对应表见 `analysis/modeling-workflow.md` 第 6 节。每项该展开到什么程度（一个公式配哪几句、一张图怎么导入和解读、算法小节必须含「输入输出/步骤/停止条件/复杂度」四样）见 `analysis/exposition-guide.md`；`templates/paper_skeleton.py` 能把这些元素生成为论文里的 TODO 槽位，漏写时看得见而不是静默变短。**不要为凑字数注水**——展开的办法是补缺失的元素和没画的证据，不是加形容词。
6. 成稿前和提交前运行 `python checklist/case_audit.py <目录>`。默认只告警；有警告时只能称草稿，最终答复必须逐条披露。用户明确要求硬门槛时使用 `--strict`。**该审计只做结构检查**——字段填没填、登记的文件在不在，不判断证据是否成立，因此「0 个警告」不是质量背书；内容真伪一律走 `checklist/manual_verification.md`。某问 `task_type` 仍为 `unclassified` 时其后续检查全部跳过，报告会写明跳过几问，警告少不等于快做完。

7. 同一份审计报告末尾还有三个分节，都不计入警告数、不影响 `--strict`，只负责让差距看得见。**完备性对标**把论文体量与官方优秀论文的实测分布（`analysis/paper-structure.md`）逐项对照；两处最容易空掉：附录要用 `templates/appendix_code.py` 内嵌全量代码（官方实测附录占全文中位 49.9%，只写「程序见支撑材料」等于白丢一半篇幅），图要够且图多于表（官方图中位 20.5 张，每问的标准图组见 `analysis/figure-guide.md`）。**证据利用率**反过来查 `artifacts/` 里算出来的东西有几份真在论文里有图表——图不够时先来这里找，这些是已经算完、只差一张图的结果，比凭空想选题强。证据没露面本身不算错（诊断类图本就该放支撑材料），工具只让「算了但忘了用」看得见。**小节展开度**把各问同名小节的汉字数并排列出来，报最短、最长和倍数，并统计骨架里没填掉的 `% TODO(小节/元素)` 槽位；它不用外部基线，拿论文自己作参照。最短的那节往往不是漏写，而是内容放错了小节——2025-B 演练里「算法设计与求解」三问 59/346/117 字，翻开最短那节，写的其实是推导。展开模式见 `analysis/exposition-guide.md`。

不以页数、公式数或图片数机械判断完整性——完备性对标给的是分布对照不是及格线，偏低本身不算错。但偏低几乎总在提示某个已经算出来的证据没画出来、某段推导没写完整，要逐项看过再决定。`examples/示范论文/` 只演示数据链路，不是研究深度或目标篇幅范本。

## 写论文前先看

- 拿到题先选方法：`analysis/method-selection.md`（题目特征→问题类型→推荐方法→脚手架路径）
- 数据链路参考：`examples/示范论文/`（10 页工具链示范 + 生成脚本）。复用 `compute.py → results.json → gen_paper.py` 组织方式，但不要把它当作深度或篇幅范本
- 新题完整流程：`analysis/modeling-workflow.md`
- 章节结构和篇幅占比：`analysis/paper-structure.md`
- 写作规范：`analysis/writing-style-guide.md`
- 评委扣分点自查表：`analysis/judge-deductions.md`
- 配图指南（图类型/美观规范/工具选型）：`analysis/figure-guide.md`
- 三人共用符号表：`notation.md`

## 起草论文

- LaTeX 主模板：`templates/paper.tex`——**项目统一使用 XeLaTeX**，`xelatex paper.tex` 跑两趟。旧演练在特定 MiKTeX 字体环境中用 pdfLaTeX 成功过，但当前 TeX Live 2025 会因 `ctex`/Fandol 字体模式失败，不将 pdfLaTeX 作为受支持的跨平台路径。工具链：`texlive-xetex texlive-lang-chinese texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended`
- Word 备选模板：`python templates/build_word_template.py <输出路径>`
- AI 建模方案提示词：`templates/model-proposal-prompt.md`

## 建模代码

**怎么跑**：依赖装虚拟环境（系统 Python 受 PEP 668 保护，`pip3 install` 会报 `externally-managed-environment`）——`python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt`，测试 `.venv/bin/python -m pytest checklist/tests/ templates/tests/ snippets/` 应全部通过。`snippets/` 是包，import 从仓库根算起：分析脚本放仓库根目录直接跑，或在根目录用 `PYTHONPATH=. .venv/bin/python <脚本>`；否则报 `ModuleNotFoundError: No module named 'snippets'`。

`snippets/<method>/{model.py, README.md, test_*.py}`，方法列表见 `AGENTS.md`，覆盖状态（已有/新增/未做）见 `analysis/method-coverage.md`。选方法先查 `analysis/method-selection.md`。数据预处理、模型检验分别有独立脚手架：`snippets/preprocessing/`、`snippets/model_validation/`。

注：`clustering`/`pca`/`neural_network` 依赖 scikit-learn，其余复用 numpy/scipy/statsmodels/networkx。

## 配图

`snippets/plotting/`：先调 `style.apply_cumcm_style()` 再用 `plots.py` 里的函数（灵敏度曲线/热力图/拟合对比/收敛曲线/多子图）。画什么图、怎么美化、AI 生图的合规边界见 `analysis/figure-guide.md`。

## 提交前必做

1. `python checklist/case_audit.py <比赛目录>` 检查模型、代码、实验、验证和论文证据链；警告必须解决或披露
2. `python checklist/compliance_check.py <论文.tex>` 检查摘要、图表 caption、明确身份字段和 AI 声明，直到无问题
3. 逐条过 `checklist/manual_verification.md`
4. 图表编号约定：团队用全文连续编号（见 notation.md）；语料中约 21% 获奖论文用分章编号，均可获奖，但团队内必须统一（详见 analysis/writing-style-guide.md）

## 维护这个 skill

工具箱内容更新时（新语料、新分析结论、新脚手架），同步更新 `AGENTS.md` 和这份 `SKILL.md`，两者内容应该等价，只是格式适配不同工具。
