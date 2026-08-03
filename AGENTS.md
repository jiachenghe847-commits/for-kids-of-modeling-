# cumcm-toolkit 使用指南（Codex 读取）

这是国赛备赛工具箱。赛时使用方式：由一名负责整合的人在这个仓库根目录打开单个 Codex/Claude 会话驱动全程，其他两人不需要各自开会话，直接打开对应文件（`analysis/`、`notation.md`、`templates/`、`snippets/`）手动参考即可。

## 完整求解的质量契约

当用户提供一道新题并要求完整求解、结果文件或论文时，必须执行 `analysis/modeling-workflow.md`，不能从“选一个算法”直接跳到成稿：

1. 默认按 `official-only` 盲测处理，只读取官方题目、附件和空白模板；不得读取 `corpus/`、`建模/` 中的同题论文、答案、代码或数值。只有用户明确要求赛后比较/复盘时才能进入 `postmortem` 阶段。
2. 运行 `python templates/init_contest_case.py <目录> --case-id <编号> --questions <数量>`，逐问填写 `case.json`：目标量、题意歧义、指标口径、变量、目标、约束、假设和方程到代码/测试映射。字段里的尖括号 `<...>` 是填写口径提示，审计器一律判为未填写，必须替换掉。
3. 先实现透明基线，再实现主方法。耦合决策默认联合求解；若用贪心、分层或分解，必须在缩小规模上与联合搜索/精确解比较，不能未经验证声称最优。
4. 随机算法保存至少 3 个固定种子的原始结果和汇总；迭代算法保存收敛轨迹；优化结果保存逐约束残差；每问至少提供一种独立验证。具体类型见 `analysis/modeling-workflow.md`。
5. 所有数字写入统一 `artifacts/results.json`，由论文生成器读取，禁止手工转抄。每问正文必须形成“分析 → 模型 → 算法 → 结果 → 验证 → 解释”闭环。这六项是内容要求不是节标题：模板把「问题分析」放在顶层 `\section{问题分析}`，其余五项落在「模型建立 / 算法设计与求解 / 结果分析 / 模型验证」四个小节里，求解结果与结果解释合并进「结果分析」。对应表见 `analysis/modeling-workflow.md` 第 6 节。
6. 生成论文前和提交前运行 `python checklist/case_audit.py <目录>`。审计默认只告警；有警告时可以输出草稿，但最终答复必须逐条披露，不能称为完成版。用户明确要求硬门槛时才使用 `--strict`。**该审计只做结构检查**——字段填没填、登记的文件在不在，不判断证据是否成立，因此「0 个警告」不是质量背书；内容真伪一律走 `checklist/manual_verification.md`。某问 `task_type` 仍为 `unclassified` 时其后续检查全部跳过，报告会写明跳过几问，警告少不等于快做完。

不以页数、公式数或图片数机械判定完整性。`examples/示范论文/` 只演示 `compute.py → results.json → gen_paper.py` 的数据链路，不是研究深度或目标篇幅范本。

## 写论文前先看

- 拿到题先选方法：`analysis/method-selection.md`（题目特征→问题类型→推荐方法→脚手架路径）
- 想看代码到论文的数据链路：`examples/示范论文/`（10 页工具链示范 + 两个生成脚本）。推荐复用其 `compute.py → results.json → gen_paper.py` 组织方式，但不要把它当作研究深度或篇幅范本；完整性按上方质量契约判断
- 新题完整工作流：`analysis/modeling-workflow.md`（资料隔离→模型卡→代码映射→实验记录→分类验证→论文闭环）
- 章节结构和篇幅占比：`analysis/paper-structure.md`
- 写作规范（时态/图表/公式/参考文献）：`analysis/writing-style-guide.md`
- 评委扣分点自查表：`analysis/judge-deductions.md`
- 配图指南（图类型/章节位置/美观规范/工具选型）：`analysis/figure-guide.md`
- 三人共用符号表：`notation.md`（新符号先加进这里再用）

## 起草论文

- LaTeX 主模板：`templates/paper.tex`。**项目统一使用 XeLaTeX**：`xelatex paper.tex` 跑两趟（第二趟解析图表编号与目录）。旧演练曾在特定 MiKTeX 字体环境用 pdfLaTeX 编译成功，但当前 TeX Live 2025 会因 `ctex`/Fandol 字体模式失败，因此 pdfLaTeX 不是受支持的跨平台路径。缺工具链就装 `sudo apt install texlive-xetex texlive-lang-chinese texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended`
- Word 备选模板：运行 `python templates/build_word_template.py <输出路径>` 生成
- 需要 AI 提建模方案时，用 `templates/model-proposal-prompt.md` 里的提示词模板，不要跳过"先出多方案再拍板"这一步

## 建模代码

**怎么跑**（第一次用必看）。依赖装在虚拟环境里——Ubuntu 24.04+ 的系统 Python 受 PEP 668 保护，直接 `pip3 install` 会报 `externally-managed-environment`：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest checklist/tests/ templates/tests/ snippets/   # 应全部通过
```

`snippets/` 是一个 Python 包，import 路径从**仓库根目录**算起，三种方式任选：

```bash
# A. 分析脚本直接放仓库根目录（最省事）
.venv/bin/python 我的分析.py                   # 脚本里写 from snippets.grey_prediction.model import gm11_forecast

# B. 脚本放别处，在仓库根目录执行
PYTHONPATH=. .venv/bin/python ~/somewhere/我的分析.py

# C. 临时试算，在仓库根目录开交互式
.venv/bin/python -c "from snippets.ahp.model import ahp_weights; ..."
```

在别的目录直接 `python 我的分析.py` 会报 `ModuleNotFoundError: No module named 'snippets'`。

`snippets/` 下按方法分目录，每个目录三件套：`model.py`（可直接调用的函数）、`README.md`（什么时候用/参数/怎么读结果/常见坑）、`test_*.py`（用法示例）。先看题目像哪一类——用 `analysis/method-selection.md` 定位——再进对应目录看 README，不要跳过 README 直接抄代码。全部方法的覆盖状态（已有/新增/还没做）见 `analysis/method-coverage.md`。

现有方法（按四大类+横向环节，共 21 个目录）：
- **分类**：`clustering`（K-Means/层次聚类）、`classification`（LDA 判别/SVM/决策树/随机森林/朴素贝叶斯/Logistic）、`neural_network`（BP 分类/回归）
- **优化**：`linear_programming`（线性/整数/非线性/多目标规划）、`graph_shortest_path`（最短路/最小生成树/最大流/最小费用最大流）、`metaheuristics`（遗传/模拟退火/TSP）、`dynamic_programming`（0-1 背包/LIS/凑数模板）、`monte_carlo`（蒙特卡洛仿真）
- **预测**：`regression`（回归/拟合/样条插值/SVR）、`time_series`（ARIMA）、`grey_prediction`（GM(1,1) 预测 + 灰色关联评价）、`markov`（马尔可夫链）、`neural_network`（BP 预测）
- **评价/降维**：`ahp`（层次分析法）、`topsis_entropy`（TOPSIS/熵权法）、`fuzzy_evaluation`（模糊综合评价）、`pca`（主成分/因子分析/典型相关）、`grey_prediction`（灰色关联）
- **统计分析**：`statistics`（t 检验/方差分析/卡方/相关/正态性）
- **机理**：`differential_equation`（ODE 数值解，含 SIR 示例）
- **横向环节**：`preprocessing`（缺失值/异常值/标准化/归一化）、`model_validation`（精度指标/交叉验证/灵敏度分析）、`plotting`（配图脚手架，先调 `style.apply_cumcm_style()` 再画图）

## 提交前必做

1. 跑 `python checklist/case_audit.py <比赛目录>`，核对模型卡、代码映射、实验、验证和论文证据链；若有警告必须解决或在交付中披露
2. 跑 `python checklist/compliance_check.py <论文.tex>`，检查摘要、图表 caption、明确身份字段和 AI 工具声明，直到输出"未发现问题"
3. 逐条过 `checklist/manual_verification.md`，这是强制步骤，不是可选项——尤其是所有数值结果必须来自真实代码输出，不能是 AI 编的"合理数字"
4. 图表编号约定：团队用全文连续编号（见 notation.md）；语料中约 21% 获奖论文用分章编号，均可获奖，但团队内必须统一（详见 analysis/writing-style-guide.md）

## 工具箱本身在迭代

`analysis/`、`templates/`、`snippets/` 不是锁死的最终版。如果发现某处不趁手，或者又找到了新的金奖论文想补充分析，直接改，改完提交并在对应文件的"更新记录"里加一行。
