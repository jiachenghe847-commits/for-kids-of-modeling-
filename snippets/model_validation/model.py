import numpy as np
from sklearn.model_selection import cross_val_score


def _jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def multi_seed_summary(run, seeds, objective_key: str = "objective", sense: str = "min") -> dict:
    """Repeat a stochastic solver and summarize objective stability.

    ``run(seed)`` must return a mapping containing ``objective_key``.  The raw
    run records are retained so they can be serialized into the experiment
    artifact instead of reporting only the best run.
    """
    if sense not in {"min", "max"}:
        raise ValueError("sense must be 'min' or 'max'")
    seeds = [int(seed) for seed in seeds]
    if not seeds:
        raise ValueError("seeds must not be empty")

    records = []
    objectives = []
    for seed in seeds:
        result = run(seed)
        if objective_key not in result:
            raise KeyError(f"run result is missing {objective_key!r}")
        objective = float(result[objective_key])
        records.append({**_jsonable(result), "seed": seed})
        objectives.append(objective)

    values = np.asarray(objectives, dtype=float)
    best_index = int(np.argmin(values) if sense == "min" else np.argmax(values))
    worst_index = int(np.argmax(values) if sense == "min" else np.argmin(values))
    return {
        "sense": sense,
        "objective_key": objective_key,
        "runs": records,
        "best_seed": seeds[best_index],
        "best_objective": float(values[best_index]),
        "worst_objective": float(values[worst_index]),
        "mean": float(values.mean()),
        "std": float(values.std()),
    }


def compare_objectives(candidate: float, reference: float, sense: str = "min") -> dict:
    """Compare a candidate with an independent reference objective.

    ``degradation`` is positive when the candidate is worse, negative when it
    is better.  This convention works for both minimization and maximization.
    """
    if sense not in {"min", "max"}:
        raise ValueError("sense must be 'min' or 'max'")
    candidate = float(candidate)
    reference = float(reference)
    degradation = candidate - reference if sense == "min" else reference - candidate
    scale = max(abs(reference), np.finfo(float).eps)
    return {
        "sense": sense,
        "candidate": candidate,
        "reference": reference,
        "degradation": float(degradation),
        "relative_degradation_pct": float(100.0 * degradation / scale),
        "candidate_is_better": bool(degradation < 0.0),
    }


def constraint_residual_report(constraints: list[dict], default_tolerance: float = 1e-8) -> dict:
    """Audit scalar equality and inequality constraints.

    Each constraint is a mapping with ``name``, ``lhs``, ``relation`` (``<=``,
    ``>=`` or ``==``), ``rhs``, and an optional per-row ``tolerance``.
    """
    rows = []
    for index, item in enumerate(constraints, start=1):
        relation = item.get("relation")
        if relation not in {"<=", ">=", "=="}:
            raise ValueError(f"constraint {index} has invalid relation: {relation!r}")
        lhs = float(item["lhs"])
        rhs = float(item["rhs"])
        tolerance = float(item.get("tolerance", default_tolerance))
        if tolerance < 0:
            raise ValueError("constraint tolerance must be non-negative")

        residual = lhs - rhs
        if relation == "<=":
            violation = max(residual - tolerance, 0.0)
        elif relation == ">=":
            violation = max(-residual - tolerance, 0.0)
        else:
            violation = max(abs(residual) - tolerance, 0.0)
        rows.append(
            {
                "name": str(item.get("name") or f"constraint_{index}"),
                "lhs": lhs,
                "relation": relation,
                "rhs": rhs,
                "tolerance": tolerance,
                "residual": float(residual),
                "violation": float(violation),
                "satisfied": bool(violation == 0.0),
            }
        )

    violations = [row["violation"] for row in rows]
    return {
        "feasible": all(row["satisfied"] for row in rows),
        "max_violation": float(max(violations, default=0.0)),
        "violated": [row["name"] for row in rows if not row["satisfied"]],
        "constraints": rows,
    }


def residual_stats(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """拟合/预测精度指标：R²、RMSE、MAE、MAPE，以及残差数组供画残差图。"""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    resid = y_true - y_pred
    ss_res = np.sum(resid ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    rmse = np.sqrt(np.mean(resid ** 2))
    mae = np.mean(np.abs(resid))
    nonzero = y_true != 0
    mape = np.mean(np.abs(resid[nonzero] / y_true[nonzero])) * 100 if nonzero.any() else float("nan")
    return {"r2": float(r2), "rmse": float(rmse), "mae": float(mae),
            "mape": float(mape), "residuals": resid}


def cross_validate_score(model, X, y, k: int = 5, scoring=None) -> dict:
    """K 折交叉验证。model 是任意 sklearn 估计器（或兼容接口）。

    返回每折得分、均值、标准差；标准差大说明模型不稳定。
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y)
    scores = cross_val_score(model, X, y, cv=k, scoring=scoring)
    return {"scores": scores, "mean": float(scores.mean()), "std": float(scores.std())}


def sensitivity_analysis(func, base_params: dict, deltas=(-0.1, -0.05, 0.05, 0.1)) -> dict:
    """单因素灵敏度分析：逐个参数按相对比例扰动，观察输出变化。

    func: 接受 params 字典、返回标量指标的函数。
    base_params: 基准参数字典。
    deltas: 相对扰动比例（如 ±5%、±10%）。
    返回每个参数在各扰动下的输出，以及相对基准的敏感度（输出相对变化 / 参数相对变化）。
    """
    base_val = func(base_params)
    result = {}
    for name, val in base_params.items():
        row = {}
        sens = []
        for d in deltas:
            p = dict(base_params)
            p[name] = val * (1 + d)
            out = func(p)
            row[d] = out
            if d != 0 and base_val != 0:
                sens.append(((out - base_val) / base_val) / d)
        result[name] = {"outputs": row, "elasticity": float(np.mean(sens)) if sens else float("nan")}
    return {"base": base_val, "per_param": result}
