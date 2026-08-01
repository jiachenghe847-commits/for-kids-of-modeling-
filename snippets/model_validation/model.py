import numpy as np
from sklearn.model_selection import cross_val_score


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
