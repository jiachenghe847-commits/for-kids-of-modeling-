---
name: cumcm-toolkit
description: 国赛（CUMCM）备赛工具箱——论文结构规范、写作规范、评委扣分点清单、LaTeX/Word 模板、建模代码脚手架、赛前提交合规检查。写论文、选建模方法、赛前自查时使用。
---

# cumcm-toolkit

备赛期间用 Claude Code 迭代这个工具箱本身时使用这份 skill；内容和 `AGENTS.md`（Codex 用）保持同步，改动时两边都要改。

## 写论文前先看

- 拿到题先选方法：`analysis/method-selection.md`（题目特征→问题类型→推荐方法→脚手架路径）
- 成品参考：`examples/示范论文/`（11 页完整论文 + 生成它的脚本）。赛时照它的组织方式走：`compute.py` 算出全部数字写 `results.json`，`gen_paper.py` 读 JSON 插值出 `.tex`，杜绝手工转抄
- 章节结构和篇幅占比：`analysis/paper-structure.md`
- 写作规范：`analysis/writing-style-guide.md`
- 评委扣分点自查表：`analysis/judge-deductions.md`
- 配图指南（图类型/美观规范/工具选型）：`analysis/figure-guide.md`
- 三人共用符号表：`notation.md`

## 起草论文

- LaTeX 主模板：`templates/paper.tex`——**必须 xelatex**（ctex 不支持 pdflatex），`xelatex paper.tex` 跑两趟。工具链：`texlive-xetex texlive-lang-chinese texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended`
- Word 备选模板：`python templates/build_word_template.py <输出路径>`
- AI 建模方案提示词：`templates/model-proposal-prompt.md`

## 建模代码

**怎么跑**：依赖装虚拟环境（系统 Python 受 PEP 668 保护，`pip3 install` 会报 `externally-managed-environment`）——`python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt`，测试 `.venv/bin/python -m pytest checklist/tests/ templates/tests/ snippets/`（80 passed）。`snippets/` 是包，import 从仓库根算起：分析脚本放仓库根目录直接跑，或在根目录用 `PYTHONPATH=. .venv/bin/python <脚本>`；否则报 `ModuleNotFoundError: No module named 'snippets'`。

`snippets/<method>/{model.py, README.md, test_*.py}`，方法列表见 `AGENTS.md`，覆盖状态（已有/新增/未做）见 `analysis/method-coverage.md`。选方法先查 `analysis/method-selection.md`。数据预处理、模型检验分别有独立脚手架：`snippets/preprocessing/`、`snippets/model_validation/`。

注：`clustering`/`pca`/`neural_network` 依赖 scikit-learn，其余复用 numpy/scipy/statsmodels/networkx。

## 配图

`snippets/plotting/`：先调 `style.apply_cumcm_style()` 再用 `plots.py` 里的函数（灵敏度曲线/热力图/拟合对比/收敛曲线/多子图）。画什么图、怎么美化、AI 生图的合规边界见 `analysis/figure-guide.md`。

## 提交前必做

1. `python checklist/compliance_check.py <论文.tex>` 直到无问题
2. 逐条过 `checklist/manual_verification.md`
3. 图表编号约定：团队用全文连续编号（见 notation.md）；语料中约 21% 获奖论文用分章编号，均可获奖，但团队内必须统一（详见 analysis/writing-style-guide.md）

## 维护这个 skill

工具箱内容更新时（新语料、新分析结论、新脚手架），同步更新 `AGENTS.md` 和这份 `SKILL.md`，两者内容应该等价，只是格式适配不同工具。
