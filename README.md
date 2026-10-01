# 数模国赛备赛工具箱（CUMCM Toolkit）

三人队备战全国大学生数学建模竞赛的共享工具箱：往届获奖论文的实测分析、论文模板、常用建模方法代码脚手架、赛前合规检查，以及给 AI 工具（Codex / Claude Code）用的入口配置。

## 快速开始

**第一步（所有人）**：clone 本仓库即可，语料已直接入库（仓库目前公开；第三方论文的再分发许可尚未核实，请先核对来源和许可）：`corpus/` 下 37 篇往届获奖论文提取文本（来自 GitHub 公开仓库，清单见 `corpus/manifest.md`）+ `建模/` 下 64 篇官方优秀论文原文（2021-2025，教育部"中国大学生在线"展示区），不需要再单独要语料包。

**用 Codex**：在仓库根目录打开 Codex 会话，它会自动读取 [AGENTS.md](AGENTS.md)——写论文前看什么、建模方法脚手架怎么用、提交前必须过哪些检查，都在里面。

**用 Claude Code**：在仓库根目录打开，`.claude/skills/cumcm-toolkit/` 会被自动发现，内容与 AGENTS.md 等价。

**不用 AI 工具**：直接读下面这些文件即可，全部是普通 markdown。

## 内容导览

| 位置 | 内容 |
|---|---|
| `analysis/method-selection.md` | 建模方法选型索引（题目特征→问题类型→推荐方法→脚手架路径） |
| `analysis/modeling-workflow.md` | 新题完整工作流：官方资料隔离、模型卡、方程到代码映射、实验留痕、分类验证和论文证据链 |
| `analysis/method-coverage.md` | 建模方法覆盖清单/缺口报告（哪些已做、哪些待补，活文档） |
| `analysis/paper-structure.md` | 论文章节结构与篇幅占比（基于 25 篇实测，非经验口传） |
| `analysis/writing-style-guide.md` | 写作规范：人称、图表编号、公式引用、参考文献的真实分布——管**格式怎么写对** |
| `analysis/exposition-guide.md` | 论证展开指南：一个公式该配哪几句、一张图该怎么导入和解读、算法小节必须含哪四样——管**内容展开到什么程度**。每条配官方优秀论文原文对照。刻意不给字数指标（小节级语料基线做不出来，理由写在文档里） |
| `analysis/judge-deductions.md` | 交稿前自查清单（29 条，每条标注证据来源） |
| `analysis/figure-guide.md` | 配图指南：图类型/章节位置/美观规范/工具选型（含 AI 生图的合规边界） |
| `corpus/` | 37 篇往届获奖论文提取文本（2002-2025，来自 GitHub 公开仓库；三个年份目录共 40 个文件，其余 3 个是 `_fetch-log.md` 抓取日志）+ `official-2023/` 下官方 2023 年 14 篇提取件，来源清单见 `corpus/manifest.md`（`python checklist/check_corpus.py corpus` 报告共 51 篇） |
| `建模/` | 64 篇官方优秀论文原文（2021-2025），供人工/AI 深度分析，见 `corpus/manifest.md` 来源清单 |
| `notation.md` | 三人共用符号表——新符号先加进这里再用，避免合稿对不上 |
| `templates/paper.tex` | LaTeX 主模板，调用 `cumcm-paper.sty` 的 B226 竞赛型版式（紧凑首页、标题层级、三线表、浮动控制、AI 声明）。**项目统一使用 `xelatex`**：在 `templates/` 目录运行 `xelatex paper.tex` 两趟解析编号 |
| `templates/paper_template.docx` | 与 LaTeX 对齐页面、字体、标题、题注和页码的 Word 备选模板；由 `build_word_template.py` 生成 |
| `templates/model-proposal-prompt.md` | 赛时让 AI 出多个建模方案的提示词模板 |
| `templates/init_contest_case.py` | 初始化带 `case.json` 研究契约的比赛目录，默认只允许官方输入；字段用尖括号 `<...>` 给出填写口径，审计器一律判为未填写 |
| `templates/paper_skeleton.py` | 生成每问四小节的论文骨架，把契约要求的每个元素写成显式 `% TODO(小节/元素)` 槽位——漏写时看得见，而不是静默地少一截；`case_audit.py` 会报未填槽位数 |
| `templates/appendix_code.py` | 把源码目录渲染成论文附录的「程序代码」一节（配 `cumcm-paper.sty` 的 `\codefile` 宏）。官方优秀论文附录占全文中位 49.9%，正文只写「程序见支撑材料」等于白丢一半篇幅 |
| `snippets/<方法名>/` | 21 个建模脚手架，按四大类+横向环节分：分类（聚类/判别·SVM·决策树·随机森林·朴素贝叶斯·Logistic/BP 神经网络）、优化（线性·整数·非线性·多目标规划/图论最短路·最小生成树·网络流/遗传·模拟退火/动态规划/蒙特卡洛）、预测（回归·插值·SVR/ARIMA/灰色/马尔可夫/BP）、评价降维（AHP/TOPSIS·熵权/模糊综合/PCA·因子分析·典型相关/灰色关联）、统计分析（假设检验/方差分析/卡方/相关）、机理（微分方程）、横向（数据预处理/模型检验/绘图）。每个含代码+README+测试，选型见 `analysis/method-selection.md` |
| `checklist/compliance_check.py` | 自动合规初筛（摘要/图表 caption/明确身份字段/AI 声明），交稿前跑；PDF 属性和语义性问题仍需人工复核 |
| `checklist/case_audit.py` | 研究质量审计：逐问题检查口径、模型、代码映射、基线、收敛、约束、独立验证和论文证据；默认只告警。**只查结构**（字段填没填、登记的文件在不在），不判断证据是否成立，「0 个警告」不是质量背书。报告末尾附三个不计入警告数的分节：完备性对标、证据利用率（`artifacts/` 里算出来的东西有几份真在论文里有图表——图不够时先来这里找）、小节展开度（各问同名小节的字数与倍数，最短的那节往往是内容放错了位置） |
| `checklist/paper_completeness.py` | 完备性对标：把论文的摘要字数、正文字数、图表数、附录占比、各章占比与官方优秀论文（2023，n=14）的实测四分位逐项对照。**不计入警告数、不影响 `--strict`**——篇幅达标和研究质量是两件事。基准直接由 `analysis/paper-structure.md` 附表二的原始数据算出，可单独运行 |
| `checklist/manual_verification.md` | **人工核对清单——AI 起草的所有数值/公式定稿前必须过这道关**；`case_audit.py` 查不到的内容真伪由这份清单兜底 |
| `examples/示范论文/` | **10 页工具链示范，不是深度/篇幅范本**——展示数据预处理→建模→验证→JSON→LaTeX 的单一数据源链路；完整比赛论文还必须满足 `analysis/modeling-workflow.md` |
| `drills/2025-B-sic-epilayer/` | 2025 B 题（碳化硅外延层厚度）**走完整质量契约的盲测演练**：唯一一次把 `case.json` 证据链也跑完的演练，`case_audit.py` 0 警告、`compliance_check.py` 未发现问题、主计算数值经独立重跑一致（跨环境重跑时版本号、绝对路径和 PNG 字节会变，见该目录 README）。折射率与厚度从附件光谱联合拟合，不引用任何外部材料常数。想看质量契约落到真题上是什么样，从这里开始 |
| `drills/2025-A-smoke-screen/` | 2025 A 题（烟幕干扰弹）**五问全解的盲测演练**：只用官方题目 PDF 和空白结果模板，不看同题论文。`solve.py` 约一分钟跑完，产出 `results.json`、三份官方 xlsx 和完整论文 PDF。这是「一道真题从头做到尾长什么样」的参照，不是获奖范本——问题五用的是分层配对启发式，本身就声明了不是全局最优 |
| `drills/README.md` | 赛前模拟演练怎么做 |

## 测试

```bash
python3 -m venv .venv                                    # 首次
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest checklist/tests/ templates/tests/ snippets/
# 应全部通过
```

依赖：Python 3.11+（numpy/pandas/scipy/scikit-learn/networkx/statsmodels/matplotlib/python-docx/pytest），其中 scikit-learn 供聚类/PCA/分类/神经网络脚手架使用。

## 交付验收

完成案例后运行统一质量门：

```bash
.venv/bin/python -m checklist.delivery_audit CASE_DIR --profile reference-quality --strict
```

它会汇总结构、证据、正文绑定、图件、PDF、重复运行记录和独立评审。严格模式返回 `0=pass`、`1=fail`、`2=needs_review`；视觉质量仍必须由独立人员逐页检查并提交 `reviews/review.json`。用 `tools/record_run.py CASE_DIR --repeat 3 -- COMMAND ...` 记录真实重复运行，用 `tools/export_blind_toolkit.py` 导出不含语料、演练和测试的盲测发行包。

复盘补上的通用求解规则：有“先……再……”优先级时使用 `snippets.linear_programming.solve_lexicographic_lp` / `solve_lexicographic_milp`，不要用大权重冒充字典序；限时 MILP 必须保存 `optimality_proven`、可行 incumbent、上下界和 `mip_gap`，未闭合时不能写“最优”；从 Excel/CSV 反读结果时使用 `snippets.model_validation.parse_number` 和 `compare_tabular_records`，避免负号丢失、小数截断和只检查内存结果。完整复盘见 [docs/postmortems/2026-09-10-d-question.md](docs/postmortems/2026-09-10-d-question.md)。

⚠️ **必须装在虚拟环境里**。Ubuntu 24.04+ 等系统的 Python 受 PEP 668 保护，直接 `pip3 install -r requirements.txt` 会报 `error: externally-managed-environment`。

自己写分析脚本调用脚手架时，`snippets/` 的 import 路径从仓库根目录算起——脚本放根目录直接跑，或在根目录用 `PYTHONPATH=. .venv/bin/python <脚本>`；否则报 `ModuleNotFoundError: No module named 'snippets'`。详见 [AGENTS.md](AGENTS.md#建模代码)。

## 维护约定

- 内容会持续迭代（新语料、演练发现的问题），改完更新对应文件的「更新记录」
- `AGENTS.md` 和 `.claude/skills/cumcm-toolkit/SKILL.md` 内容保持等价，改一处要同步另一处
- `corpus/`（37 篇 GitHub 语料提取文本）与 `建模/`（64 篇官方优秀论文原文）均已提交，随本仓库**公开**分发；其中包含第三方论文，**再分发许可尚未核实**。分享或复用这些资料前请先确认授权，必要时将语料移至私有存储
