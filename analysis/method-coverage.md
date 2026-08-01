# 建模方法覆盖清单（缺口报告）

对照思维导图（分类/优化/预测/评价四大类）+ 常见「十大算法 / 五大模型」清单，逐项标注本工具箱的覆盖状态。这是**活文档**：补了新脚手架就把 ⬜ 改成 🆕/✅，让"现在有什么、还差什么"一目了然。

图例：✅ 原有 · 🆕 已补齐 · 🔸 部分覆盖 · ⬜ 未做（按需再补）

## 一、思维导图四大类

### 分类问题
| 方法 | 状态 | 脚手架 |
|---|---|---|
| 聚类分析（K-Means/层次） | 🆕 | `snippets/clustering/` |
| 神经网络分类（BP） | 🆕 | `snippets/neural_network/` |
| 判别分析（Fisher/LDA） | 🆕 | `snippets/classification/`（`lda_classify`） |
| 支持向量机 SVM 分类 | 🆕 | `snippets/classification/`（`svm_classify`） |
| 决策树 / 随机森林 | 🆕 | `snippets/classification/` |
| 朴素贝叶斯 | 🆕 | `snippets/classification/`（`naive_bayes_classify`） |
| Logistic 回归（分类） | 🆕 | `snippets/classification/`（`logistic_classify`，含优势比） |

### 优化问题
| 方法 | 状态 | 脚手架 |
|---|---|---|
| 线性规划 | ✅ | `snippets/linear_programming/` |
| 整数规划（0-1/整数） | 🆕 | 同上 `solve_milp` |
| 非线性规划 | 🆕 | 同上 `solve_nlp` |
| 图论（最短路） | ✅ | `snippets/graph_shortest_path/` |
| 概率模型/蒙特卡洛 | ✅ | `snippets/monte_carlo/` |
| 组合优化（TSP 等，启发式） | 🆕 | `snippets/metaheuristics/`（GA/SA + TSP 模板） |
| 动态规划 | 🆕 | `snippets/dynamic_programming/`（背包/LIS/凑数模板） |
| 多目标规划 | 🆕 | `snippets/linear_programming/`（`solve_multi_objective`，加权法+理想点） |
| 图论其他（最小生成树/最大流/最小费用流） | 🆕 | `snippets/graph_shortest_path/` |
| 组合优化专题（背包/指派/车间调度） | 🔸 | 背包见 `dynamic_programming/knapsack_01`；指派/调度可仿 `metaheuristics/tsp_anneal` 改造 |

### 预测问题
| 方法 | 状态 | 脚手架 |
|---|---|---|
| 回归拟合 | ✅→🆕 | `snippets/regression/`（补多项式/非线性） |
| 样条插值（一/二/三次） | 🆕 | 同上 `spline_interpolate` |
| 时间序列（ARIMA） | ✅ | `snippets/time_series/` |
| 灰色预测 GM(1,1) | ✅ | `snippets/grey_prediction/` |
| BP 神经网络预测 | 🆕 | `snippets/neural_network/` |
| 马尔可夫预测 | 🆕 | `snippets/markov/`（转移矩阵/平稳分布/n步预测） |
| 支持向量机 SVM | 🆕 | 分类 `snippets/classification/`；回归 `snippets/regression/`（`svr_fit`） |
| 组合预测法 | ⬜ | — |

### 评价问题
| 方法 | 状态 | 脚手架 |
|---|---|---|
| 层次分析法 AHP | ✅ | `snippets/ahp/` |
| 优劣解距离 TOPSIS + 熵权 | ✅ | `snippets/topsis_entropy/` |
| 模糊综合评价 | 🆕 | `snippets/fuzzy_evaluation/` |
| 灰色关联分析 | 🆕 | `snippets/grey_prediction/`（`grey_relation`） |
| 主成分分析 PCA（降维/评价） | 🆕 | `snippets/pca/` |
| BP 神经网络综合评价 | 🆕 | 复用 `snippets/neural_network/` |
| 因子分析（降维） | 🆕 | `snippets/pca/`（`factor_analysis`） |
| 典型相关分析 | 🆕 | `snippets/pca/`（`canonical_correlation`） |

## 二、十大算法 / 五大模型补充项

| 方法 | 状态 | 说明 |
|---|---|---|
| 蒙特卡洛 | ✅ | `snippets/monte_carlo/` |
| 数据拟合/插值/参数估计 | 🆕 | `regression`（拟合+插值+非线性参数估计） |
| 规划类（线性/整数/非线性） | ✅+🆕 | `linear_programming` 三合一 |
| 图论算法 | ✅+🆕 | 最短路/最小生成树/最大流/最小费用最大流 |
| 微分方程模型 | 🆕 | `snippets/differential_equation/`（含 SIR 示例） |
| 现代优化（遗传/模拟退火） | 🆕 | `snippets/metaheuristics/` |
| 现代优化（粒子群/蚁群/禁忌） | ⬜ | GA/SA 已能覆盖多数场景，暂缓 |
| 神经网络 | 🆕 | `snippets/neural_network/`（回归+分类） |
| 决策树/随机森林/朴素贝叶斯 | 🆕 | `snippets/classification/` |
| 马尔可夫模型 | 🆕 | `snippets/markov/` |
| 动态规划 | 🆕 | `snippets/dynamic_programming/` |
| 排队论模型 | ⬜ | 可用 `monte_carlo` 仿真近似 |
| 统计分析（假设检验/方差分析/卡方/相关） | 🆕 | `snippets/statistics/` |
| Logistic 回归 | 🆕 | `snippets/classification/`（`logistic_classify`） |
| 图像处理算法 | ⬜ | 题型少见，暂缓 |

## 三、框架横向步骤（不是单一方法，但每题都要）

| 环节 | 状态 | 脚手架 |
|---|---|---|
| 方法选型索引 | 🆕 | `analysis/method-selection.md` |
| 数据预处理 | 🆕 | `snippets/preprocessing/` |
| 模型检验/灵敏度分析 | 🆕 | `snippets/model_validation/` |
| 结果可视化 | ✅ | `snippets/plotting/` |

## 四、本轮做了什么 · 还差什么

**第一批（🆕）**：6 个新方法目录（clustering / pca / fuzzy_evaluation / differential_equation / metaheuristics / neural_network）+ 2 个框架横向目录（preprocessing / model_validation）+ 扩展 3 个现有目录（regression 补插值/非线性、grey_prediction 补灰色关联、linear_programming 补整数/非线性规划）+ 2 份文档。脚手架数 9 → 17。

**第二批（🆕）**：4 个新目录 `statistics`（假设检验/方差分析/卡方/相关/正态性）、`markov`（转移矩阵/平稳分布/n步预测）、`classification`（LDA/SVM/决策树/随机森林）、`dynamic_programming`（0-1 背包/LIS/凑数模板）。脚手架数 17 → 21。分类问题四大类里唯一"整类全缺"的判别系补齐。

**第三批（🆕）**：不新增目录，全部扩展现有目录——`graph_shortest_path` 补最小生成树/最大流/最小费用最大流（并让最短路支持有向图与负权自动切 Bellman-Ford）、`pca` 补因子分析/典型相关分析、`classification` 补朴素贝叶斯/Logistic 回归、`regression` 补 SVR、`linear_programming` 补多目标规划（加权法+理想点）。目录仍为 21 个，方法函数覆盖面显著扩大。

**仍未做（⬜），按题型需要再补**：
1. **组合预测法**——多个预测模型加权融合，实现简单但需先有多个基模型，赛时按需临时组合即可。
2. **排队论**——M/M/1 等解析公式；也可用 `monte_carlo` 仿真近似，优先级低。
3. **粒子群 / 蚁群 / 禁忌搜索**——`metaheuristics` 的遗传/模拟退火已能覆盖绝大多数场景。
4. **图像处理算法**——国赛题型少见，需要时再引入 opencv/skimage。
5. **指派 / 车间调度专题**（🔸 部分覆盖）——可仿 `metaheuristics/tsp_anneal` 或用 `solve_milp` 建模。

至此思维导图四大类与十大算法/五大模型清单中的**高频项已全部覆盖**，剩余 4 项均属低频或可用现有脚手架替代。

## 更新记录

- 2026-08-01：初版。脚手架 9→17；分类问题从"整类全缺"补上聚类+神经网络分类；优化补整数/非线性/启发式；预测补插值/BP；评价补模糊/灰色关联/PCA；新增数据预处理与模型检验两个横向环节
- 2026-08-01：第二批。脚手架 17→21，新增 statistics / markov / classification / dynamic_programming；判别分析/SVM/决策树/随机森林/马尔可夫/动态规划/统计检验由 ⬜ 转 🆕
- 2026-08-01：第三批（扩展现有目录，不新增）。图论补最小生成树/最大流/最小费用最大流+有向图+负权、pca 补因子分析/典型相关、classification 补朴素贝叶斯/Logistic、regression 补 SVR、linear_programming 补多目标规划；同时修正「组合优化专题」标记（背包实际已由 dynamic_programming 覆盖，改标 🔸）。测试 69→80
