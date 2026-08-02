"""示范论文的全部计算：区域农产品仓储选址与配送优化。

所有进入论文的数字都在这里算出来，写进 results.json，论文由 gen_paper.py 读
JSON 生成——数字不经人手转抄，物理上不可能与代码输出不一致。

运行（在哪个目录执行都可以，脚本自己定位仓库根）：
    .venv/bin/python examples/示范论文/compute.py
"""
import json
import pathlib
import sys

# 把仓库根加入 sys.path，使 snippets 可被 import
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

from snippets.preprocessing.model import fill_missing, detect_outliers
from snippets.grey_prediction.model import gm11_forecast
from snippets.model_validation.model import residual_stats, sensitivity_analysis
from snippets.topsis_entropy.model import entropy_weights, topsis_score
from snippets.graph_shortest_path.model import shortest_path, minimum_spanning_tree
from snippets.linear_programming.model import solve_lp
from snippets.plotting.style import apply_cumcm_style
from snippets.plotting.plots import fit_comparison, sensitivity_curve, workflow_diagram

OUT = pathlib.Path(__file__).parent          # 产物与脚本同目录
R = {}
apply_cumcm_style()

# ============ 研究流程图 ============
workflow_nodes = [
    "题目数据",
    "数据预处理",
    "GM(1,1)产量预测",
    "熵权-TOPSIS选址评价",
    "图论构建配送网络",
    "线性规划分配运量",
    "模型检验与综合决策",
]
workflow_edges = [
    ("题目数据", "数据预处理"),
    ("数据预处理", "GM(1,1)产量预测"),
    ("数据预处理", "熵权-TOPSIS选址评价"),
    ("数据预处理", "图论构建配送网络"),
    ("图论构建配送网络", "线性规划分配运量"),
    ("GM(1,1)产量预测", "模型检验与综合决策"),
    ("熵权-TOPSIS选址评价", "模型检验与综合决策"),
    ("线性规划分配运量", "模型检验与综合决策"),
]
fig = workflow_diagram(
    workflow_nodes,
    workflow_edges,
    groups={
        "数据层": workflow_nodes[:2],
        "模型层": workflow_nodes[2:6],
        "决策层": workflow_nodes[6:],
    },
    output_path=OUT / "fig0_workflow.png",
)
plt.close(fig)

# ============ 问题一：产量预测 ============
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
raw = np.array([120.0, 132.0, np.nan, 158.0, 171.0, 185.0])   # 2021 年缺测
R["raw"] = ["缺测" if np.isnan(v) else v for v in raw]
R["years"] = YEARS

f = fill_missing(raw, strategy="interpolate")
y = f["filled"]
od = detect_outliers(y, method="iqr")
R["filled"] = [round(v, 2) for v in y]
R["n_filled"] = f["n_filled"]
R["n_outliers"] = od["n_outliers"]
R["iqr_low"], R["iqr_high"] = round(od["low"], 2), round(od["high"], 2)

g = gm11_forecast(y, steps=2)
fitted, future = g["forecast"][:len(y)], g["forecast"][len(y):]
R["a"], R["b"] = round(g["a"], 4), round(g["b"], 4)
R["fitted"] = [round(v, 2) for v in fitted]
R["forecast"] = [round(v, 2) for v in future]
R["forecast_years"] = [2025, 2026]

# 级比检验（README 明确要求，不能跳过）
ratios = y[:-1] / y[1:]
n = len(y)
lo, hi = np.exp(-2 / (n + 1)), np.exp(2 / (n + 1))
R["ratios"] = [round(v, 4) for v in ratios]
R["ratio_bound"] = [round(lo, 4), round(hi, 4)]
R["ratio_ok"] = bool(np.all((ratios > lo) & (ratios < hi)))

rs = residual_stats(y, fitted)
R["r2"], R["rmse"] = round(float(rs["r2"]), 4), round(float(rs["rmse"]), 4)
R["mae"], R["mape"] = round(float(rs["mae"]), 4), round(float(rs["mape"]), 4)
R["resid"] = [round(v, 3) for v in (y - fitted)]

fig = fit_comparison(np.array(YEARS), y, fitted, xlabel="年份", ylabel="产量 / 万吨")
fig.savefig(f"{OUT}/fig1_fit.png", dpi=300); plt.close(fig)

# ============ 问题二：仓址评选 ============
SITES = ["甲", "乙", "丙"]
IND = ["年吞吐能力/万吨", "建设投资/百万元", "覆盖率", "路网密度"]
M = np.array([[185, 42, 0.91, 3.2],
              [172, 35, 0.88, 4.1],
              [199, 55, 0.95, 2.7]])
R["sites"], R["indicators"], R["matrix"] = SITES, IND, M.tolist()

# 成本型指标（投资）两种正向化对比 —— 见 topsis_entropy/README 常见坑第 3 条
inv = M[:, 1].copy()
A = M.copy(); A[:, 1] = inv.max() - inv          # max(x)-x
B = M.copy(); B[:, 1] = 1.0 / inv                # 倒数法
cmp = {}
for tag, mat in (("maxmin", A), ("recip", B)):
    w = entropy_weights(mat); s = topsis_score(mat, w)
    cmp[tag] = {"w": [round(v, 4) for v in w], "s": [round(v, 4) for v in s],
                "best": SITES[int(np.argmax(s))], "wmax": round(float(w.max()), 4)}
R["topsis_cmp"] = cmp
R["weights"] = cmp["recip"]["w"]
R["scores"] = cmp["recip"]["s"]
R["best_site"] = cmp["recip"]["best"]
R["rank"] = [SITES[i] for i in np.argsort(-np.array(cmp["recip"]["s"]))]

# ============ 问题三：配送网络 ============
EDGES = [("W", "A", 12), ("W", "B", 18), ("W", "C", 25), ("A", "B", 9),
         ("A", "D", 21), ("B", "C", 11), ("B", "D", 14), ("C", "E", 16),
         ("D", "E", 8), ("C", "D", 19)]
R["edges"] = [[u, v, w] for u, v, w in EDGES]

mst = minimum_spanning_tree(EDGES)
R["mst_edges"] = [[u, v, w] for u, v, w in mst["edges"]]
R["mst_total"] = round(mst["total_weight"], 2)
R["mst_saving"] = round(sum(w for *_, w in EDGES) - mst["total_weight"], 2)

sp = shortest_path(EDGES, "W", "E")
R["sp_path"], R["sp_len"], R["sp_method"] = sp["path"], round(sp["length"], 2), sp["method"]

# 运输量分配：最小化总运费，满足各点需求、不超仓库产能
# 变量 x1..x4 = 经 A/B/C/D 中转的运量（万吨）
c = [12, 18, 25, 21]
A_ub = [[1, 1, 1, 1], [-1, -1, 0, 0], [0, 0, -1, -1]]
b_ub = [185, -80, -60]          # 总量≤产能；A+B≥80；C+D≥60
lp = solve_lp(c=c, A_ub=A_ub, b_ub=b_ub, bounds=[(0, 70)] * 4)
R["lp_x"] = [round(v, 2) for v in lp["x"]]
R["lp_cost"] = round(lp["objective"], 2)
R["lp_ok"] = bool(lp["success"])

# ============ 灵敏度分析 ============
def total_cost(p):
    return p["unit"] * p["volume"] + p["fixed"]

base = {"unit": 12.0, "volume": 140.0, "fixed": 380.0}
deltas = (-0.10, -0.05, 0.05, 0.10)
sens = sensitivity_analysis(total_cost, base, deltas=deltas)
R["sens_base"] = round(sens["base"], 2)
R["sens"] = {k: {"elasticity": round(v["elasticity"], 4),
                 "outputs": [round(v["outputs"][d], 2) for d in deltas]}
             for k, v in sens["per_param"].items()}
R["deltas"] = [int(d * 100) for d in deltas]

NAME = {"unit": "单位运费", "volume": "配送量", "fixed": "固定成本"}
fig = sensitivity_curve(
    np.array(R["deltas"]),
    {NAME[k]: v["outputs"] for k, v in R["sens"].items()},
    xlabel="参数相对变化 / %", ylabel="总成本 / 万元", baseline=R["sens_base"])
fig.savefig(f"{OUT}/fig2_sens.png", dpi=300); plt.close(fig)

# ============ 网络图 ============
G = nx.Graph(); G.add_weighted_edges_from(EDGES)
pos = nx.spring_layout(G, seed=7)
fig, ax = plt.subplots(figsize=(7.2, 4.8))
mst_set = {frozenset((u, v)) for u, v, _ in mst["edges"]}
nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#B7BEC7", width=1.2)
nx.draw_networkx_edges(G, pos, ax=ax, width=2.8, edge_color="#A61B1B",
                       edgelist=[(u, v) for u, v, _ in mst["edges"]])
nx.draw_networkx_nodes(G, pos, ax=ax, node_color="#1F4E79", node_size=820,
                       edgecolors="white", linewidths=1.2)
nx.draw_networkx_labels(G, pos, ax=ax, font_color="white", font_size=13)
nx.draw_networkx_edge_labels(G, pos, ax=ax, font_size=9,
                             bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82},
                             edge_labels={(u, v): w for u, v, w in EDGES})
ax.grid(False)
ax.axis("off")
fig.savefig(f"{OUT}/fig3_net.png", dpi=300, bbox_inches="tight"); plt.close(fig)

json.dump(R, open(f"{OUT}/results.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(R, ensure_ascii=False, indent=1))
