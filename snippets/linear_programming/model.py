import numpy as np
from scipy.optimize import linprog, milp, minimize, LinearConstraint, Bounds


def _as_objective(c):
    values = np.asarray(c, dtype=float)
    if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("objective coefficients must be a finite one-dimensional array")
    return values


def _as_ub(A_ub, b_ub, n):
    if A_ub is None and b_ub is None:
        return np.empty((0, n), dtype=float), np.empty(0, dtype=float)
    if A_ub is None or b_ub is None:
        raise ValueError("A_ub and b_ub must be supplied together")
    matrix = np.asarray(A_ub, dtype=float)
    rhs = np.asarray(b_ub, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != n or rhs.shape != (matrix.shape[0],):
        raise ValueError("A_ub and b_ub have incompatible shapes")
    if not np.all(np.isfinite(matrix)) or not np.all(np.isfinite(rhs)):
        raise ValueError("constraints must contain finite numbers")
    return matrix, rhs


def _with_objective_lock(A_ub, b_ub, c, value, tolerance):
    """Keep a lexicographic stage within a declared objective tolerance."""
    if tolerance < 0 or not np.isfinite(tolerance):
        raise ValueError("objective tolerance must be a finite non-negative number")
    return (
        np.vstack([A_ub, c, -c]),
        np.concatenate([b_ub, [value + tolerance, -value + tolerance]]),
    )


def _linprog_status(result, x, objective):
    return {
        "x": x,
        "objective": objective,
        "success": bool(result.status == 0),
        "status": int(result.status),
        "message": str(result.message),
        "optimality_proven": bool(result.status == 0),
        "feasible_incumbent": x is not None,
    }


def solve_lp(c, A_ub, b_ub, bounds, A_eq=None, b_eq=None, options=None) -> dict:
    """Solve a continuous LP and retain solver status needed for an honest report."""
    c = _as_objective(c)
    result = linprog(c=c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                     bounds=bounds, method="highs", options=options)
    x = result.x if result.x is not None else None
    objective = float(result.fun) if result.fun is not None else None
    return _linprog_status(result, x, objective)


def solve_milp(c, A_ub, b_ub, bounds, integrality, A_eq=None, b_eq=None, options=None) -> dict:
    """整数/0-1 规划（scipy.optimize.milp）。默认求最小化，最大化把 c 取负。

    integrality: 每个变量的整数约束，0=连续，1=整数；0-1 变量用 integrality=1 且 bounds=(0,1)。
    """
    c = _as_objective(c)
    A_ub, b_ub = _as_ub(A_ub, b_ub, c.size)
    if A_eq is not None or b_eq is not None:
        if A_eq is None or b_eq is None:
            raise ValueError("A_eq and b_eq must be supplied together")
        A_eq = np.asarray(A_eq, dtype=float)
        b_eq = np.asarray(b_eq, dtype=float)
        if A_eq.ndim != 2 or A_eq.shape[1] != c.size or b_eq.shape != (A_eq.shape[0],):
            raise ValueError("A_eq and b_eq have incompatible shapes")
        matrix = np.vstack([A_ub, A_eq])
        lower = np.concatenate([np.full(A_ub.shape[0], -np.inf), b_eq])
        upper = np.concatenate([b_ub, b_eq])
    else:
        matrix, lower, upper = A_ub, np.full(A_ub.shape[0], -np.inf), b_ub
    constraints = LinearConstraint(matrix, lower, upper)
    lb = np.array([b[0] if b[0] is not None else -np.inf for b in bounds], dtype=float)
    ub = np.array([b[1] if b[1] is not None else np.inf for b in bounds], dtype=float)
    result = milp(c=c, constraints=constraints, integrality=np.asarray(integrality),
                  bounds=Bounds(lb, ub), options=options)
    x = result.x if result.x is not None else None
    objective = float(result.fun) if result.fun is not None else None
    return {
        "x": x,
        "objective": objective,
        "success": bool(result.status == 0),
        "status": int(result.status),
        "message": str(result.message),
        "optimality_proven": bool(result.status == 0),
        "feasible_incumbent": x is not None,
        "mip_gap": float(result.mip_gap) if getattr(result, "mip_gap", None) is not None else None,
        "mip_node_count": int(result.mip_node_count) if getattr(result, "mip_node_count", None) is not None else None,
    }


def solve_lexicographic_lp(objectives, A_ub, b_ub, bounds, tolerances=None,
                           A_eq=None, b_eq=None, options=None) -> dict:
    """Solve minimization objectives in strict priority order.

    After each stage, the attained objective is added as a two-sided constraint
    before solving the next stage. This preserves the earlier optimum within the
    declared tolerance; arbitrary weighted sums cannot provide that guarantee.
    """
    objectives = [_as_objective(c) for c in objectives]
    if not objectives:
        raise ValueError("at least one objective is required")
    n = objectives[0].size
    if any(c.size != n for c in objectives):
        raise ValueError("all objectives must have the same length")
    A_work, b_work = _as_ub(A_ub, b_ub, n)
    tolerances = [0.0] * len(objectives) if tolerances is None else list(tolerances)
    if len(tolerances) != len(objectives):
        raise ValueError("tolerances must match objectives")
    stages, values, x = [], [], None
    for index, c in enumerate(objectives):
        result = solve_lp(c, A_work, b_work, bounds, A_eq=A_eq, b_eq=b_eq, options=options)
        stages.append({k: v for k, v in result.items() if k != "x"})
        if result["x"] is None:
            return {"x": None, "objective_values": values, "stages": stages,
                    "success": False, "optimality_proven": False}
        x = result["x"]
        value = float(c @ x)
        values.append(value)
        if not result["optimality_proven"]:
            return {"x": x, "objective_values": values, "stages": stages,
                    "success": False, "optimality_proven": False,
                    "feasible_incumbent": True, "failed_stage": index}
        if index < len(objectives) - 1:
            A_work, b_work = _with_objective_lock(A_work, b_work, c, value, float(tolerances[index]))
    return {"x": x, "objective_values": values, "stages": stages,
            "success": True, "optimality_proven": True, "feasible_incumbent": True}


def solve_lexicographic_milp(objectives, A_ub, b_ub, bounds, integrality,
                             tolerances=None, A_eq=None, b_eq=None, options=None) -> dict:
    """MILP counterpart of :func:`solve_lexicographic_lp`.

    A time limit or a nonzero MIP gap stops the hierarchy. The returned incumbent
    remains useful as a feasible solution, but ``optimality_proven`` is false and
    must not be reported as an optimum.
    """
    objectives = [_as_objective(c) for c in objectives]
    if not objectives:
        raise ValueError("at least one objective is required")
    n = objectives[0].size
    if any(c.size != n for c in objectives):
        raise ValueError("all objectives must have the same length")
    A_work, b_work = _as_ub(A_ub, b_ub, n)
    tolerances = [0.0] * len(objectives) if tolerances is None else list(tolerances)
    if len(tolerances) != len(objectives):
        raise ValueError("tolerances must match objectives")
    stages, values, x = [], [], None
    for index, c in enumerate(objectives):
        result = solve_milp(c, A_work, b_work, bounds, integrality,
                            A_eq=A_eq, b_eq=b_eq, options=options)
        stages.append({k: v for k, v in result.items() if k != "x"})
        if result["x"] is None:
            return {"x": None, "objective_values": values, "stages": stages,
                    "success": False, "optimality_proven": False}
        x = result["x"]
        value = float(c @ x)
        values.append(value)
        if not result["optimality_proven"]:
            return {"x": x, "objective_values": values, "stages": stages,
                    "success": False, "optimality_proven": False,
                    "feasible_incumbent": True, "failed_stage": index}
        if index < len(objectives) - 1:
            A_work, b_work = _with_objective_lock(A_work, b_work, c, value, float(tolerances[index]))
    return {"x": x, "objective_values": values, "stages": stages,
            "success": True, "optimality_proven": True, "feasible_incumbent": True}


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
