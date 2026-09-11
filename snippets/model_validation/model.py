import numpy as np
from sklearn.model_selection import cross_val_score
import math
from itertools import zip_longest


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


def parse_number(value, name="value") -> float:
    """Parse a finite number without losing a sign or decimal precision.

    This is intentionally strict for result-table and spreadsheet re-reads:
    booleans, empty cells, NaN/Inf and strings with trailing units are rejected
    instead of being silently truncated or coerced to zero.
    """
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{name} must be a finite number")
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            raise ValueError(f"{name} is empty")
        try:
            value = float(text)
        except ValueError as exc:
            raise ValueError(f"{name} is not numeric: {value!r}") from exc
    elif not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{name} is not numeric: {value!r}")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def compare_tabular_records(expected, observed, fields, key_field=None, tolerances=None) -> dict:
    """Compare a rebuilt result table with an independently read source table.

    ``expected`` and ``observed`` are lists of row dictionaries. Numeric fields
    are parsed through :func:`parse_number`, so negative signs and decimals are
    preserved. The returned row-level mismatches are suitable for a JSON audit
    artifact and for binding a validation claim to the exported table.
    """
    expected, observed = list(expected), list(observed)
    fields = list(fields)
    if not fields:
        raise ValueError("fields must not be empty")
    if key_field is not None:
        def keyed(rows, label):
            result = {}
            for row in rows:
                if not isinstance(row, dict) or key_field not in row:
                    raise ValueError(f"{label} row is missing key field {key_field!r}")
                key = str(row[key_field])
                if key in result:
                    raise ValueError(f"duplicate key {key!r} in {label}")
                result[key] = row
            return result
        left, right = keyed(expected, "expected"), keyed(observed, "observed")
        keys = sorted(set(left) | set(right))
        pairs = [(key, left.get(key), right.get(key)) for key in keys]
    else:
        if len(expected) != len(observed):
            pairs = [(index, left if index < len(expected) else None,
                      right if index < len(observed) else None)
                     for index, (left, right) in enumerate(zip_longest(expected, observed))]
        else:
            pairs = [(index, left, right) for index, (left, right) in enumerate(zip(expected, observed))]
    tolerance_map = ({field: float(tolerances) for field in fields}
                     if isinstance(tolerances, (int, float)) else
                     {field: float((tolerances or {}).get(field, 0.0)) for field in fields})
    if any(tolerance < 0 or not math.isfinite(tolerance) for tolerance in tolerance_map.values()):
        raise ValueError("tolerances must be finite and non-negative")
    rows, mismatches, max_error = [], [], 0.0
    for key, left, right in pairs:
        row_result = {"key": key, "fields": {}}
        if left is None or right is None:
            mismatches.append({"key": key, "reason": "missing_row"})
            continue
        for field in fields:
            a = parse_number(left.get(field), f"expected[{key}].{field}")
            b = parse_number(right.get(field), f"observed[{key}].{field}")
            error = abs(a - b)
            max_error = max(max_error, error)
            row_result["fields"][field] = {"expected": a, "observed": b, "abs_error": error,
                                            "matched": error <= tolerance_map[field]}
            if error > tolerance_map[field]:
                mismatches.append({"key": key, "field": field, "expected": a,
                                   "observed": b, "abs_error": error,
                                   "tolerance": tolerance_map[field]})
        rows.append(row_result)
    return {"matched": not mismatches, "max_abs_error": max_error,
            "tolerances": tolerance_map, "rows": rows, "mismatches": mismatches}


def multi_seed_summary(run, seeds, objective_key: str = "objective", sense: str = "min") -> dict:
    """多种子重复运行随机算法，汇总目标值的稳定性。

    `run(seed)` 必须返回含 `objective_key` 的字典。每次运行的原始记录都保留在
    `runs` 里，供直接序列化进实验 JSON——正文不能只报告最好的那一次。
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
    """把主算法结果与独立参考算法的目标值作比较。

    `degradation` 为正表示候选方案更差、为负表示更好；最大化和最小化共用这一套
    符号约定，正文引用时不用再判方向。
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
    """逐条审计标量等式/不等式约束，给出残差和违反量。

    每条约束是一个字典：`name`、`lhs`、`relation`（`<=`、`>=` 或 `==`）、`rhs`，
    可选 `tolerance` 覆盖该行的容差。
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


def joint_fit(datasets, forward, shared_names, local_names, x0_shared, x0_local,
              bounds_shared=None, bounds_local=None, **least_squares_kwargs) -> dict:
    """多工况联合拟合：几组数据共享一部分参数，各自保留一部分参数。

    **什么时候用**：同一个对象在不同条件下测了好几组数据（不同角度、不同温度、
    不同批次），而其中一些物理量在各组之间**本来就该相同**。这时把各组分开拟合再
    取平均，等于扔掉了「它们必须相同」这条硬约束——各组会各自漂到不同的值，
    组间散布反而成了主要误差来源。联合拟合把共享参数强制绑成一个，散布自然消失。

    2025 B 题演练就吃了这个亏：两个入射角各拟各的，厚度分别是 7.4517 和 7.5925 µm，
    角度间半散布 0.0704 µm 成了主导不确定度；而同题的官方优秀论文 B157 用双角联合
    拟合共享厚度与色散参数，从源头上避免了这个问题。

    参数
    ----
    datasets     : [{"x": ..., "y": ...}, ...]，每组一个字典，可另带任意元信息
    forward      : forward(shared, local, dataset) -> 预测值，形状与 dataset["y"] 相同
                   shared/local 都是 {参数名: 值} 字典
    shared_names : 各组共享的参数名
    local_names  : 每组各自独立的参数名
    x0_shared    : 共享参数初值，长度与 shared_names 一致
    x0_local     : 每组的局部参数初值，形状 (组数, len(local_names))
    bounds_shared / bounds_local : (下界, 上界) 元组，与对应初值同长；None 表示不设界

    返回
    ----
    ``shared`` 共享参数估计；``local`` 逐组的局部参数；``separate`` 各组单独拟合的
    结果；``comparison`` 两种做法的对比——**这一项才是报告里要写的东西**：
    它给出单独拟合时共享参数的组间散布，以及联合拟合把它压到了多少。
    """
    from scipy.optimize import least_squares

    datasets = list(datasets)
    n_sets, n_shared, n_local = len(datasets), len(shared_names), len(local_names)
    x0_local = np.atleast_2d(np.asarray(x0_local, dtype=float))
    if x0_local.shape != (n_sets, n_local):
        raise ValueError(f"x0_local 形状应为 ({n_sets}, {n_local})，实际 {x0_local.shape}")

    def _pack(shared, local):
        return np.concatenate([np.asarray(shared, dtype=float), np.asarray(local, dtype=float).ravel()])

    def _unpack(vector):
        shared = dict(zip(shared_names, vector[:n_shared]))
        block = vector[n_shared:].reshape(n_sets, n_local)
        return shared, [dict(zip(local_names, row)) for row in block]

    def _residuals(vector):
        shared, locals_ = _unpack(vector)
        return np.concatenate([
            (np.asarray(forward(shared, locals_[i], data), dtype=float)
             - np.asarray(data["y"], dtype=float)).ravel()
            for i, data in enumerate(datasets)
        ])

    def _stack_bounds():
        if bounds_shared is None and bounds_local is None:
            return (-np.inf, np.inf)
        lo_s, hi_s = bounds_shared if bounds_shared else ([-np.inf] * n_shared, [np.inf] * n_shared)
        lo_l, hi_l = bounds_local if bounds_local else ([-np.inf] * n_local, [np.inf] * n_local)
        return (_pack(lo_s, np.tile(lo_l, (n_sets, 1))), _pack(hi_s, np.tile(hi_l, (n_sets, 1))))

    fit = least_squares(_residuals, _pack(x0_shared, x0_local),
                        bounds=_stack_bounds(), **least_squares_kwargs)
    shared, locals_ = _unpack(fit.x)

    # 对照组：每组单独拟合，共享参数也各拟各的——这正是「不联合」时会发生的事
    separate = []
    for i, data in enumerate(datasets):
        def _one(vector, data=data):
            s, l = dict(zip(shared_names, vector[:n_shared])), dict(zip(local_names, vector[n_shared:]))
            return (np.asarray(forward(s, l, data), dtype=float)
                    - np.asarray(data["y"], dtype=float)).ravel()

        lo_s, hi_s = bounds_shared if bounds_shared else ([-np.inf] * n_shared, [np.inf] * n_shared)
        lo_l, hi_l = bounds_local if bounds_local else ([-np.inf] * n_local, [np.inf] * n_local)
        one_bounds = ((-np.inf, np.inf) if bounds_shared is None and bounds_local is None
                      else (np.concatenate([lo_s, lo_l]), np.concatenate([hi_s, hi_l])))
        solo = least_squares(_one, np.concatenate([x0_shared, x0_local[i]]),
                             bounds=one_bounds, **least_squares_kwargs)
        separate.append({
            "shared": dict(zip(shared_names, solo.x[:n_shared])),
            "local": dict(zip(local_names, solo.x[n_shared:])),
            "rms": float(np.sqrt(np.mean(solo.fun ** 2))),
        })

    comparison = {}
    for j, name in enumerate(shared_names):
        values = [s["shared"][name] for s in separate]
        spread = (max(values) - min(values)) / 2.0
        mean = float(np.mean(values))
        comparison[name] = {
            "joint": float(fit.x[j]),
            "separate": [float(v) for v in values],
            "separate_mean": mean,
            # 单独拟合时这个「本该相同」的参数散布了多少——联合拟合消掉的就是它
            "separate_half_spread": float(spread),
            "separate_relative_spread": float(spread / abs(mean)) if mean else float("nan"),
            "joint_minus_separate_mean": float(fit.x[j] - mean),
        }

    return _jsonable({
        "shared": shared,
        "local": locals_,
        "rms": float(np.sqrt(np.mean(fit.fun ** 2))),
        "cost": float(fit.cost),
        "success": bool(fit.success),
        "n_datasets": n_sets,
        "separate": separate,
        "comparison": comparison,
    })


def subrange_drift_scan(x, y, estimator, windows) -> dict:
    """把待求量在数据的不同子区间上各算一遍，看它漂不漂——系统误差探测器。

    **为什么这该是标准动作**：模型里没建进去的系统效应（色散、老化、季节性、
    量程非线性）通常不会让残差变得难看，而是让**估计值随所用数据区间平移**。
    只在全量数据上算一次，这种漂移完全看不见；分区间各算一次，它立刻暴露。

    2025 B 题演练里这个扫描测出光程随波段漂移 12%（硅）和 34%（碳化硅），
    直接解释了三篇论文结果分歧的来源——而当时它只是被当作波段选择的论证，
    没意识到它是个通用工具。

    参数
    ----
    x, y      : 完整数据
    estimator : estimator(x_sub, y_sub) -> 标量，在一个子区间上给出待求量
    windows   : [(lo, hi), ...]，按 x 的取值划定的子区间（闭区间）

    返回的 ``drift_relative`` 是最大最小值之差除以中位数；``monotonic`` 说明漂移
    是不是单调的——单调漂移几乎一定是没建模的系统效应，来回跳则更像噪声。
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    rows = []
    for lo, hi in windows:
        mask = (x >= lo) & (x <= hi)
        if mask.sum() < 2:
            raise ValueError(f"子区间 [{lo}, {hi}] 内不足 2 个数据点")
        rows.append({"window": [float(lo), float(hi)], "n_points": int(mask.sum()),
                     "value": float(estimator(x[mask], y[mask]))})

    values = np.array([r["value"] for r in rows], dtype=float)
    median = float(np.median(values))
    spread = float(values.max() - values.min())
    diffs = np.diff(values)
    return _jsonable({
        "windows": rows,
        "values": values,
        "median": median,
        "min": float(values.min()),
        "max": float(values.max()),
        "drift_absolute": spread,
        "drift_relative": float(spread / abs(median)) if median else float("nan"),
        "monotonic": bool(np.all(diffs > 0) or np.all(diffs < 0)) if diffs.size else True,
        "full_range_value": float(estimator(x, y)),
    })
