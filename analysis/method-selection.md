# 建模方法选型索引

拿到题先判断属于哪一类问题，再进对应 `snippets/` 目录看 README。**不要跳过 README 直接抄代码**。下表按"题目特征 → 问题类型 → 推荐方法 → 脚手架路径"组织；一道题常常是多类的组合（如"先聚类分组、再对每组做预测"），按子问题拆开各自选方法。

## 一、四大类速判

| 题目在问什么 | 问题类型 | 先看哪一节 |
|---|---|---|
| 把样本/对象分成几组、判别属于哪一类 | **分类** | 下方「分类」 |
| 求最优方案/最大最小值、怎么安排最划算 | **优化** | 下方「优化」 |
| 预测未来值、补全/外推数据 | **预测** | 下方「预测」 |
| 给对象打分、排序、评优劣 | **评价** | 下方「评价」 |
| 描述某个随时间/空间连续变化的过程 | **机理建模** | `differential_equation` |

## 二、分类问题

| 题目特征 | 推荐方法 | 脚手架 |
|---|---|---|
| 无标签，自己把数据分堆 | K-Means / 层次聚类 | `snippets/clustering/` |
| 有标签、类别近似正态线性可分 | Fisher 判别 LDA | `snippets/classification/`（`lda_classify`） |
| 有标签、边界非线性、中小样本 | 支持向量机 SVM | `snippets/classification/`（`svm_classify`） |
| 有标签、要可解释规则 / 特征重要性 | 决策树 / 随机森林 | `snippets/classification/` |
| 有标签、关系复杂、样本充足 | BP 神经网络分类 | `snippets/neural_network/`（`bp_classify`） |
| 小样本、特征近似独立、要类别概率 | 朴素贝叶斯 | `snippets/classification/`（`naive_bayes_classify`） |
| 要解释「各因素如何影响发生概率」 | Logistic 回归 | `snippets/classification/`（`logistic_classify`） |
| 指标多、想先降维再分 | PCA 降维 + 聚类/分类 | `snippets/pca/` → `snippets/clustering/` |

> 拿不准先用随机森林拿 baseline；要写进正文的因素解释，优先 Logistic 或决策树。

## 三、优化问题

| 题目特征 | 推荐方法 | 脚手架 |
|---|---|---|
| 目标、约束都线性，变量连续 | 线性规划 | `snippets/linear_programming/`（`solve_lp`） |
| 变量必须取整数 / 0-1 选择 | 整数规划 | `snippets/linear_programming/`（`solve_milp`） |
| 目标或约束非线性 | 非线性规划 | `snippets/linear_programming/`（`solve_nlp`） |
| 两点间最短路 / 最省路径 | 图论最短路 | `snippets/graph_shortest_path/`（`shortest_path`） |
| 最小代价把所有点连通（铺管道/电缆） | 最小生成树 | `snippets/graph_shortest_path/`（`minimum_spanning_tree`） |
| 网络最大通过量 / 最小费用流 | 网络流 | `snippets/graph_shortest_path/`（`max_flow`·`min_cost_max_flow`） |
| 多个冲突目标要折中（成本↓+效益↑） | 多目标规划 | `snippets/linear_programming/`（`solve_multi_objective`） |
| 组合爆炸（TSP、排班、指派）、建不出标准型 | 遗传算法/模拟退火 | `snippets/metaheuristics/` |
| 分阶段决策、背包/凑数/序列（有最优子结构） | 动态规划 | `snippets/dynamic_programming/` |
| 含随机性、要靠仿真估计 | 蒙特卡洛 | `snippets/monte_carlo/` |

## 四、预测问题

| 题目特征 | 推荐方法 | 脚手架 |
|---|---|---|
| 有明显线性/曲线趋势 | 回归拟合 | `snippets/regression/` |
| 已知点之间补值（不外推） | 样条插值 | `snippets/regression/`（`spline_interpolate`） |
| 数据点少（4-10）、近似指数趋势 | 灰色预测 GM(1,1) | `snippets/grey_prediction/` |
| 数据点多、有周期/趋势的时间序列 | ARIMA | `snippets/time_series/` |
| 关系复杂非线性、样本充足 | BP 神经网络 | `snippets/neural_network/`（`bp_regress`） |
| 有限状态间转移、预测长期分布 | 马尔可夫链 | `snippets/markov/` |
| 非线性、样本不多、有离群点 | 支持向量机回归 SVR | `snippets/regression/`（`svr_fit`） |

> 组合预测法暂未做脚手架，见 `method-coverage.md`。

## 五、评价问题

| 题目特征 | 推荐方法 | 脚手架 |
|---|---|---|
| 指标权重靠专家主观两两比较 | 层次分析法 AHP | `snippets/ahp/` |
| 指标能量化、要客观赋权+排序 | 熵权法 + TOPSIS | `snippets/topsis_entropy/` |
| 评语是"优良中差"等模糊等级 | 模糊综合评价 | `snippets/fuzzy_evaluation/` |
| 小样本、与理想序列比接近度 | 灰色关联分析 | `snippets/grey_prediction/`（`grey_relation`） |
| 指标多且共线，想综合成几个主成分打分 | PCA 综合评价 | `snippets/pca/`（`pca_composite_score`） |
| 想提炼指标背后的「潜在因子」并命名 | 因子分析 | `snippets/pca/`（`factor_analysis`） |
| 研究**两组**变量整体之间的相关性 | 典型相关分析 | `snippets/pca/`（`canonical_correlation`） |

> 权重法（AHP/熵权）常与打分法（TOPSIS/模糊/灰色关联）组合：先定权重，再代入打分模型。

## 五·补、统计分析（数据分析型题，尤其 C 题）

要用数据**支撑一个结论**（有没有差异/相关/影响）时，别只比大小，做显著性检验：

| 题目特征 | 推荐方法 | 脚手架 |
|---|---|---|
| 两组/单组均值是否有显著差异 | t 检验 | `snippets/statistics/`（`t_test`） |
| 三组及以上均值是否有差异 | 方差分析 ANOVA | `snippets/statistics/`（`anova`） |
| 两个分类变量是否相关 | 卡方检验 | `snippets/statistics/`（`chi_square`） |
| 两个连续变量相关强度/方向 | 相关分析 | `snippets/statistics/`（`correlation`） |

## 六、别忘了的横向环节（几乎每题都要）

| 环节 | 脚手架 |
|---|---|
| 数据预处理（缺失值/异常值/标准化/归一化） | `snippets/preprocessing/` |
| 模型检验（精度指标/交叉验证/灵敏度分析） | `snippets/model_validation/` |
| 参数估计（反推模型系数） | `snippets/regression/`（`fit_nonlinear`）或 `snippets/metaheuristics/` |
| 结果可视化 | `snippets/plotting/` |

聚类/PCA/TOPSIS/神经网络前**必须先标准化**；预测/评价出结果后**必须做检验与灵敏度分析**，否则是评委高频扣分点（见 `judge-deductions.md`）。

## 更新记录

- 2026-08-01：初版，覆盖现有 11 个建模脚手架 + 2 个横向环节脚手架的选型映射
- 2026-08-01：并入第二批脚手架——分类补 LDA/SVM/决策树/随机森林，优化补动态规划，预测补马尔可夫，新增「统计分析」一节
- 2026-08-01：并入第三批——分类补朴素贝叶斯/Logistic，优化补多目标规划与图论细分（最小生成树/网络流），预测补 SVR，评价补因子分析/典型相关
