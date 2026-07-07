# cumcm-toolkit 使用指南（Codex 读取）

这是国赛备赛工具箱。赛时使用方式：由一名负责整合的人在这个仓库根目录打开单个 Codex/Claude 会话驱动全程，其他两人不需要各自开会话，直接打开对应文件（`analysis/`、`notation.md`、`templates/`、`snippets/`）手动参考即可。

## 写论文前先看

- 章节结构和篇幅占比：`analysis/paper-structure.md`
- 写作规范（时态/图表/公式/参考文献）：`analysis/writing-style-guide.md`
- 评委扣分点自查表：`analysis/judge-deductions.md`
- 配图指南（图类型/章节位置/美观规范/工具选型）：`analysis/figure-guide.md`
- 三人共用符号表：`notation.md`（新符号先加进这里再用）

## 起草论文

- LaTeX 主模板：`templates/paper.tex`
- Word 备选模板：运行 `python templates/build_word_template.py <输出路径>` 生成
- 需要 AI 提建模方案时，用 `templates/model-proposal-prompt.md` 里的提示词模板，不要跳过"先出多方案再拍板"这一步

## 建模代码

`snippets/` 下按方法分目录，每个目录三件套：`model.py`（可直接调用的函数）、`README.md`（什么时候用/参数/怎么读结果/常见坑）、`test_*.py`（用法示例）。先看题目像哪一类，再进对应目录看 README，不要跳过 README 直接抄代码。

现有方法：`regression`（回归/拟合）、`ahp`（层次分析法）、`grey_prediction`（灰色预测）、`time_series`（ARIMA）、`graph_shortest_path`（图论最短路）、`linear_programming`（线性规划）、`monte_carlo`（蒙特卡洛仿真）、`topsis_entropy`（TOPSIS/熵权法）、`plotting`（配图脚手架：灵敏度曲线/热力图/拟合对比/收敛曲线/多子图，先调 `style.apply_cumcm_style()` 再画图）。

## 提交前必做

1. 跑 `python checklist/compliance_check.py <论文.tex>`，直到输出"未发现问题"
2. 逐条过 `checklist/manual_verification.md`，这是强制步骤，不是可选项——尤其是所有数值结果必须来自真实代码输出，不能是 AI 编的"合理数字"
3. 图表编号约定：团队用全文连续编号（见 notation.md）；语料中约 21% 获奖论文用分章编号，均可获奖，但团队内必须统一（详见 analysis/writing-style-guide.md）

## 工具箱本身在迭代

`analysis/`、`templates/`、`snippets/` 不是锁死的最终版。如果发现某处不趁手，或者又找到了新的金奖论文想补充分析，直接改，改完提交并在对应文件的"更新记录"里加一行。
