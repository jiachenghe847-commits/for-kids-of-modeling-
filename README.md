# 数模国赛备赛工具箱（CUMCM Toolkit）

三人队备战全国大学生数学建模竞赛的共享工具箱：往届获奖论文的实测分析、论文模板、常用建模方法代码脚手架、赛前合规检查，以及给 AI 工具（Codex / Claude Code）用的入口配置。

## 快速开始

**第一步（所有人）**：clone 本仓库即可，语料已直接入库（仓库为 private）：`corpus/` 下 37 篇往届获奖论文提取文本（来自 GitHub 公开仓库，清单见 `corpus/manifest.md`）+ `建模/` 下 64 篇官方优秀论文原文（2021-2025，教育部"中国大学生在线"展示区），不需要再单独要语料包。

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
| `analysis/writing-style-guide.md` | 写作规范：人称、图表编号、公式引用、参考文献的真实分布 |
| `analysis/judge-deductions.md` | 交稿前自查清单（29 条，每条标注证据来源） |
| `analysis/figure-guide.md` | 配图指南：图类型/章节位置/美观规范/工具选型（含 AI 生图的合规边界） |
| `corpus/` | 37 篇往届获奖论文提取文本（2002-2025，来自 GitHub 公开仓库）+ 官方 2023 年 14 篇提取件，来源清单见 `corpus/manifest.md` |
| `建模/` | 64 篇官方优秀论文原文（2021-2025），供人工/AI 深度分析，见 `corpus/manifest.md` 来源清单 |
| `notation.md` | 三人共用符号表——新符号先加进这里再用，避免合稿对不上 |
| `templates/paper.tex` | LaTeX 主模板，调用 `cumcm-paper.sty` 的 B226 竞赛型版式（紧凑首页、标题层级、三线表、浮动控制、AI 声明）。**项目统一使用 `xelatex`**：在 `templates/` 目录运行 `xelatex paper.tex` 两趟解析编号 |
| `templates/paper_template.docx` | 与 LaTeX 对齐页面、字体、标题、题注和页码的 Word 备选模板；由 `build_word_template.py` 生成 |
| `templates/model-proposal-prompt.md` | 赛时让 AI 出多个建模方案的提示词模板 |
| `templates/init_contest_case.py` | 初始化带 `case.json` 研究契约的比赛目录，默认只允许官方输入 |
| `snippets/<方法名>/` | 21 个建模脚手架，按四大类+横向环节分：分类（聚类/判别·SVM·决策树·随机森林·朴素贝叶斯·Logistic/BP 神经网络）、优化（线性·整数·非线性·多目标规划/图论最短路·最小生成树·网络流/遗传·模拟退火/动态规划/蒙特卡洛）、预测（回归·插值·SVR/ARIMA/灰色/马尔可夫/BP）、评价降维（AHP/TOPSIS·熵权/模糊综合/PCA·因子分析·典型相关/灰色关联）、统计分析（假设检验/方差分析/卡方/相关）、机理（微分方程）、横向（数据预处理/模型检验/绘图）。每个含代码+README+测试，选型见 `analysis/method-selection.md` |
| `checklist/compliance_check.py` | 自动合规初筛（摘要/图表 caption/明确身份字段/AI 声明），交稿前跑；PDF 属性和语义性问题仍需人工复核 |
| `checklist/case_audit.py` | 研究质量审计：逐问题检查口径、模型、代码映射、基线、收敛、约束、独立验证和论文证据；默认只告警 |
| `checklist/manual_verification.md` | **人工核对清单——AI 起草的所有数值/公式定稿前必须过这道关** |
| `examples/示范论文/` | **10 页工具链示范，不是深度/篇幅范本**——展示数据预处理→建模→验证→JSON→LaTeX 的单一数据源链路；完整比赛论文还必须满足 `analysis/modeling-workflow.md` |
| `drills/README.md` | 赛前模拟演练怎么做 |

## 测试

```bash
python3 -m venv .venv                                    # 首次
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest checklist/tests/ templates/tests/ snippets/
# 应全部通过
```

依赖：Python 3.11+（numpy/pandas/scipy/scikit-learn/networkx/statsmodels/matplotlib/python-docx/pytest），其中 scikit-learn 供聚类/PCA/分类/神经网络脚手架使用。

⚠️ **必须装在虚拟环境里**。Ubuntu 24.04+ 等系统的 Python 受 PEP 668 保护，直接 `pip3 install -r requirements.txt` 会报 `error: externally-managed-environment`。

自己写分析脚本调用脚手架时，`snippets/` 的 import 路径从仓库根目录算起——脚本放根目录直接跑，或在根目录用 `PYTHONPATH=. .venv/bin/python <脚本>`；否则报 `ModuleNotFoundError: No module named 'snippets'`。详见 [AGENTS.md](AGENTS.md#建模代码)。

## 维护约定

- 内容会持续迭代（新语料、演练发现的问题），改完更新对应文件的「更新记录」
- `AGENTS.md` 和 `.claude/skills/cumcm-toolkit/SKILL.md` 内容保持等价，改一处要同步另一处
- `corpus/`（37 篇 GitHub 语料提取文本）与 `建模/`（64 篇官方优秀论文原文）均已提交（仓库为 private）；若仓库权限变更（如加协作者、转 public），先评估版权风险再决定是否继续保留
