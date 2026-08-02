# 2026 集成验证演练记录

## 演练内容

用 2023 年 C 题《基于优化模型的蔬菜类商品自动定价与补货决策》（`corpus/2022-2025/2023-C.md`）的问题重述部分，跑了一次"模板 + 脚手架 + 合规检查"的骨架级全流程（不涉及真实建模）。

具体步骤：

1. 建 `drills/_scratch/`，复制 `templates/paper.tex` 进去。
2. 把 2023-C 语料文件里的"背景"+"问题重述"原文摘入 `\section{问题重述}`。
3. 假造 5 组"日均销量 $x$（kg）—日均定价 $y$（元/kg）"数据点：
   `x = [10, 15, 20, 25, 30]`，`y = [9.8, 9.0, 8.3, 7.9, 7.2]`，
   通过 `sys.path.insert(0, "../../snippets/regression")` 导入 `model.py` 调用 `fit_linear(x, y)`，
   得到真实返回值 `coef=-0.1260`、`intercept=10.9600`、`r2=0.9893`，原样填入"模型的建立与求解"新增小节的表格。
4. 编译：`"$HOME/AppData/Local/Programs/MiKTeX/miktex/bin/x64/pdflatex.exe" -interaction=nonstopmode paper.tex`。
   输出关键行：`Output written on paper.pdf (3 pages, 588374 bytes).`（仅有"未检查 MiKTeX 更新"的无害提示，无报错）。
5. 故意删掉新增表格的 `\caption{花菜类销量-定价回归结果（演练用假造数据）}`，跑
   `python ../../checklist/compliance_check.py paper.tex`，输出：
   ```
   发现问题：
     - 存在 table 环境缺少 \caption（表注）
   ```
   exit code = 1，正确检出。
6. 恢复 `\caption` 后重跑，输出：
   ```
   未发现问题
   ```
   exit code = 0，正确通过。重新执行一次 pdflatex 确认恢复后的版本仍能正常编译（`Output written on paper.pdf (3 pages, 592354 bytes).`）。

## 验证结果

- [x] LaTeX 模板编译通过
- [x] snippets/regression 能正常调用并把结果填进模板
- [x] compliance_check.py 能正确检出人为制造的违规（缺 caption），修复后能通过

## 发现的问题

本次演练**未发现卡手问题**——三个环节（模板编译、脚手架调用、合规检查）都按预期直接跑通，没有遇到宏包报错、接口不好用或 `AGENTS.md` 路径写错的情况。具体核实过的细节：

- 当时的特定 MiKTeX 环境中，`templates/paper.tex` 用 `pdflatex` 成功编译（`ctex` 自动加载系统 `simsun`/`simhei` 字体）。这是历史环境记录，不代表跨平台保证：2026-08-02 复核时，TeX Live 2025 的 pdfLaTeX 因 `ctex`/Fandol 字体模式直接失败，因此项目统一使用 XeLaTeX。
- `snippets/regression/model.py` 的 `fit_linear(x, y)` 接口签名与 `AGENTS.md`/README 描述一致，`sys.path.insert` 方式导入没有额外依赖问题（只需 `numpy`，已在环境中）。
- `checklist/compliance_check.py` 对 `\caption` 缺失的检测逻辑（基于 `\begin{table}...\end{table}` 内正则匹配）行为符合预期，删除/恢复后两次结果均与文档描述一致。
- 唯一算不上"问题"的观察：pdflatex 输出中有一行 `pdflatex: major issue: So far, you have not checked for MiKTeX updates.`，这是 MiKTeX 自身的更新提醒，不影响编译结果，brief 里也已提前说明可忽略。

## 后续行动

本次演练未发现需要修复的工具箱问题，无需改动 `templates/`、`snippets/`、`checklist/`、`AGENTS.md`。

提醒团队后续做真实建模演练（Task 24）时注意：这次只验证了"回归 + compliance_check"这一条最短路径，`snippets/` 下其他 7 个方法目录（ahp、grey_prediction、time_series、graph_shortest_path、linear_programming、monte_carlo、topsis_entropy）以及 `templates/build_word_template.py`、`checklist/manual_verification.md` 的人工过表流程都还没有被这次演练覆盖到，建议真实演练时按题目实际用到的方法交叉验证。
