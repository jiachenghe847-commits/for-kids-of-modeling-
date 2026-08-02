# cumcm-toolkit 使用指南（Codex 读取）

这是国赛备赛工具箱。赛时使用方式：由一名负责整合的人在这个仓库根目录打开单个 Codex/Claude 会话驱动全程，其他两人不需要各自开会话，直接打开对应文件（`analysis/`、`notation.md`、`templates/`、`snippets/`）手动参考即可。

## 写论文前先看

- 拿到题先选方法：`analysis/method-selection.md`（题目特征→问题类型→推荐方法→脚手架路径）
- 想知道成品长什么样：`examples/示范论文/`（11 页完整论文 + 生成它的两个脚本）。这也是推荐的赛时组织方式——`compute.py` 算出所有数字写进 `results.json`，`gen_paper.py` 读 JSON 插值生成 `.tex`，论文里没有一处手工转抄的数字，改数据重跑即可，不存在"代码改了论文忘改"
- 章节结构和篇幅占比：`analysis/paper-structure.md`
- 写作规范（时态/图表/公式/参考文献）：`analysis/writing-style-guide.md`
- 评委扣分点自查表：`analysis/judge-deductions.md`
- 配图指南（图类型/章节位置/美观规范/工具选型）：`analysis/figure-guide.md`
- 三人共用符号表：`notation.md`（新符号先加进这里再用）

## 起草论文

- LaTeX 主模板：`templates/paper.tex`。**必须用 xelatex 编译**（`ctex` 宏包不支持 pdflatex）：`xelatex paper.tex` 跑两趟（第二趟解析图表编号与目录）。缺工具链就装 `sudo apt install texlive-xetex texlive-lang-chinese texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended`
- Word 备选模板：运行 `python templates/build_word_template.py <输出路径>` 生成
- 需要 AI 提建模方案时，用 `templates/model-proposal-prompt.md` 里的提示词模板，不要跳过"先出多方案再拍板"这一步

## 建模代码

**怎么跑**（第一次用必看）。依赖装在虚拟环境里——Ubuntu 24.04+ 的系统 Python 受 PEP 668 保护，直接 `pip3 install` 会报 `externally-managed-environment`：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest checklist/tests/ templates/tests/ snippets/   # 应为 80 passed
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

1. 跑 `python checklist/compliance_check.py <论文.tex>`，直到输出"未发现问题"
2. 逐条过 `checklist/manual_verification.md`，这是强制步骤，不是可选项——尤其是所有数值结果必须来自真实代码输出，不能是 AI 编的"合理数字"
3. 图表编号约定：团队用全文连续编号（见 notation.md）；语料中约 21% 获奖论文用分章编号，均可获奖，但团队内必须统一（详见 analysis/writing-style-guide.md）

## 工具箱本身在迭代

`analysis/`、`templates/`、`snippets/` 不是锁死的最终版。如果发现某处不趁手，或者又找到了新的金奖论文想补充分析，直接改，改完提交并在对应文件的"更新记录"里加一行。
