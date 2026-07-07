---
name: cumcm-toolkit
description: 国赛（CUMCM）备赛工具箱——论文结构规范、写作规范、评委扣分点清单、LaTeX/Word 模板、建模代码脚手架、赛前提交合规检查。写论文、选建模方法、赛前自查时使用。
---

# cumcm-toolkit

备赛期间用 Claude Code 迭代这个工具箱本身时使用这份 skill；内容和 `AGENTS.md`（Codex 用）保持同步，改动时两边都要改。

## 写论文前先看

- 章节结构和篇幅占比：`analysis/paper-structure.md`
- 写作规范：`analysis/writing-style-guide.md`
- 评委扣分点自查表：`analysis/judge-deductions.md`
- 配图指南（图类型/美观规范/工具选型）：`analysis/figure-guide.md`
- 三人共用符号表：`notation.md`

## 起草论文

- LaTeX 主模板：`templates/paper.tex`
- Word 备选模板：`python templates/build_word_template.py <输出路径>`
- AI 建模方案提示词：`templates/model-proposal-prompt.md`

## 建模代码

`snippets/<method>/{model.py, README.md, test_*.py}`，方法列表见 `AGENTS.md`。

## 配图

`snippets/plotting/`：先调 `style.apply_cumcm_style()` 再用 `plots.py` 里的函数（灵敏度曲线/热力图/拟合对比/收敛曲线/多子图）。画什么图、怎么美化、AI 生图的合规边界见 `analysis/figure-guide.md`。

## 提交前必做

1. `python checklist/compliance_check.py <论文.tex>` 直到无问题
2. 逐条过 `checklist/manual_verification.md`
3. 图表编号约定：团队用全文连续编号（见 notation.md）；语料中约 21% 获奖论文用分章编号，均可获奖，但团队内必须统一（详见 analysis/writing-style-guide.md）

## 维护这个 skill

工具箱内容更新时（新语料、新分析结论、新脚手架），同步更新 `AGENTS.md` 和这份 `SKILL.md`，两者内容应该等价，只是格式适配不同工具。
