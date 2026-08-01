import numpy as np
from scipy.optimize import linprog, milp, minimize, LinearConstraint, Bounds


def solve_lp(c, A_ub, b_ub, bounds) -> dict:
    result = linprog(c=c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    return {"x": result.x, "objective": float(result.fun), "success": bool(result.success)}


def solve_milp(c, A_ub, b_ub, bounds, integrality) -> dict:
    """整数/0-1 规划（scipy.optimize.milp）。默认求最小化，最大化把 c 取负。

    integrality: 每个变量的整数约束，0=连续，1=整数；0-1 变量用 integrality=1 且 bounds=(0,1)。
    """
    c = np.asarray(c, dtype=float)
    constraints = LinearConstraint(np.asarray(A_ub, dtype=float), -np.inf, np.asarray(b_ub, dtype=float))
    lb = np.array([b[0] if b[0] is not None else -np.inf for b in bounds], dtype=float)
    ub = np.array([b[1] if b[1] is not None else np.inf for b in bounds], dtype=float)
    result = milp(c=c, constraints=constraints, integrality=np.asarray(integrality),
                  bounds=Bounds(lb, ub))
    return {"x": result.x, "objective": float(result.fun) if result.success else float("nan"),
            "success": bool(result.success)}


def solve_multi_objective(objectives, weights, A_ub, b_ub, bounds, normalize: bool = True) -> dict:
    """多目标线性规划——加权法：把多个目标线性加权成单目标求解。

    objectives: 目标系数列表，每个是一个 c 向量（均按**最小化**给出，要最大化的先取负）。
    weights: 各目标权重（和会自动归一化），可来自 AHP/熵权法。
    normalize: True 时先分别求各目标的单独最优值做无量纲化，避免量纲大的目标主导。
    返回折中解、各目标的单独最优值（理想点）与该解下各目标的实际取值。
    """
    objs = [np.asarray(c, dtype=float) for c in objectives]
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()

    # 各目标单独最优（理想点），用于无量纲化与后续差距分析
    ideals = []
    for c in objs:
        r = linprog(c=c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
        ideals.append(float(r.fun) if r.success else float("nan"))

    scales = []
    for c, ideal in zip(objs, ideals):
        s = abs(ideal) if (normalize and ideal not in (0.0,) and np.isfinite(ideal)) else 1.0
        scales.append(s if s > 0 else 1.0)

    combined = sum(wi * c / s for wi, c, s in zip(w, objs, scales))
    result = linprog(c=combined, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    values = [float(c @ result.x) for c in objs] if result.success else []
    return {"x": result.x, "objective_values": values, "ideals": ideals,
            "weights": w, "success": bool(result.success)}


def solve_nlp(func, x0, constraints=None, bounds=None) -> dict:
    """非线性规划（scipy.optimize.minimize，SLSQP）。求最小化，最大化把目标取负。

    func: 目标函数 f(x)->标量。
    constraints: scipy 约束字典列表，如 [{"type":"ineq","fun":lambda x: x[0]-1}]（fun>=0）。
    bounds: [(low, high), ...]。
    """
    result = minimize(func, np.asarray(x0, dtype=float), method="SLSQP",
                      bounds=bounds, constraints=constraints or ())
    return {"x": result.x, "objective": float(result.fun), "success": bool(result.success)}
