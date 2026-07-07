# 数模国赛备赛工具箱（CUMCM Toolkit）

三人队备战全国大学生数学建模竞赛的共享工具箱：往届获奖论文的实测分析、论文模板、常用建模方法代码脚手架、赛前合规检查，以及给 AI 工具（Codex / Claude Code）用的入口配置。

## 快速开始

**第一步（所有人）**：clone 本仓库后，向队内要语料包 `cumcm-corpus.zip`，解压到仓库的 `corpus/` 目录下（37 篇往届获奖论文原文，版权原因不入 git，`corpus/manifest.md` 里有完整清单可核对）。`建模/` 目录下的 64 篇官方优秀论文（2021-2025，教育部"中国大学生在线"展示区）已直接提交进本仓库（仓库为 private，`corpus/manifest.md` 有来源清单）。

**用 Codex**：在仓库根目录打开 Codex 会话，它会自动读取 [AGENTS.md](AGENTS.md)——写论文前看什么、建模方法脚手架怎么用、提交前必须过哪些检查，都在里面。

**用 Claude Code**：在仓库根目录打开，`.claude/skills/cumcm-toolkit/` 会被自动发现，内容与 AGENTS.md 等价。

**不用 AI 工具**：直接读下面这些文件即可，全部是普通 markdown。

## 内容导览

| 位置 | 内容 |
|---|---|
| `analysis/paper-structure.md` | 论文章节结构与篇幅占比（基于 25 篇实测，非经验口传） |
| `analysis/writing-style-guide.md` | 写作规范：人称、图表编号、公式引用、参考文献的真实分布 |
| `analysis/judge-deductions.md` | 交稿前自查清单（29 条，每条标注证据来源） |
| `analysis/figure-guide.md` | 配图指南：图类型/章节位置/美观规范/工具选型（含 AI 生图的合规边界） |
| `建模/` | 64 篇官方优秀论文原文（2021-2025），供人工/AI 深度分析，见 `corpus/manifest.md` 来源清单 |
| `notation.md` | 三人共用符号表——新符号先加进这里再用，避免合稿对不上 |
| `templates/paper.tex` | LaTeX 主模板（已验证可编译，含关键词/支撑材料清单节） |
| `templates/paper_template.docx` | Word 备选模板 |
| `templates/model-proposal-prompt.md` | 赛时让 AI 出多个建模方案的提示词模板 |
| `snippets/<方法名>/` | 9 个建模方法脚手架（回归/AHP/灰色预测/ARIMA/图论/线性规划/蒙特卡洛/TOPSIS/绘图），每个含代码+README+测试 |
| `checklist/compliance_check.py` | 自动合规检查（摘要/图表 caption），交稿前跑 |
| `checklist/manual_verification.md` | **人工核对清单——AI 起草的所有数值/公式定稿前必须过这道关** |
| `drills/README.md` | 赛前模拟演练怎么做 |

## 测试

```bash
python -m pytest checklist/tests/ templates/tests/ snippets/
# 20 passed
```

依赖：Python 3 + numpy/pandas/scipy/networkx/statsmodels/python-docx/pytest（pip 直接装）。

## 维护约定

- 内容会持续迭代（新语料、演练发现的问题），改完更新对应文件的「更新记录」
- `AGENTS.md` 和 `.claude/skills/cumcm-toolkit/SKILL.md` 内容保持等价，改一处要同步另一处
- `corpus/` 下的 GitHub 语料原文不提交（.gitignore 已配置），新增语料走队内文件传输，只有 `corpus/manifest.md`（来源清单）入库
- `建模/` 下的官方优秀论文原文已提交（仓库为 private）；若仓库权限变更（如加协作者、转 public），先评估版权风险再决定是否继续保留
