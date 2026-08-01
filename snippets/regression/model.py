import numpy as np
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d, CubicSpline


def fit_linear(x: np.ndarray, y: np.ndarray) -> dict:
    coef, intercept = np.polyfit(x, y, 1)
    y_pred = coef * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return {"coef": float(coef), "intercept": float(intercept), "r2": float(r2)}


def _r2(y, y_pred):
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    return 1 - ss_res / ss_tot if ss_tot > 0 else 1.0


def fit_polynomial(x: np.ndarray, y: np.ndarray, degree: int) -> dict:
    """多项式回归。degree 从低到高试，配合残差图，别一上来就高阶（过拟合）。"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    coeffs = np.polyfit(x, y, degree)          # 高次到低次
    y_pred = np.polyval(coeffs, x)
    return {"coeffs": coeffs, "predict": lambda xn: np.polyval(coeffs, np.asarray(xn, dtype=float)),
            "r2": float(_r2(y, y_pred))}


def fit_nonlinear(x: np.ndarray, y: np.ndarray, func, p0=None) -> dict:
    """非线性最小二乘拟合（指数/幂/对数/自定义）。func(x, *params)，p0 是参数初值。"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    params, cov = curve_fit(func, x, y, p0=p0, maxfev=10000)
    y_pred = func(x, *params)
    return {"params": params, "cov": cov,
            "predict": lambda xn: func(np.asarray(xn, dtype=float), *params),
            "r2": float(_r2(y, y_pred))}


def svr_fit(X, y, kernel: str = "rbf", C: float = 1.0, epsilon: float = 0.1) -> dict:
    """支持向量机回归（SVR）：非线性、样本不多时的稳健预测，对离群点比最小二乘鲁棒。

    X: (n, 特征数)；y: (n,)。已内置标准化。返回 predict 函数与训练集 R²/RMSE。
    """
    from sklearn.svm import SVR
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline

    X = np.atleast_2d(np.asarray(X, dtype=float))
    if X.shape[0] == 1 and len(np.asarray(y)) > 1:
        X = X.T
    y = np.asarray(y, dtype=float)
    model = make_pipeline(StandardScaler(), SVR(kernel=kernel, C=C, epsilon=epsilon))
    model.fit(X, y)
    pred = model.predict(X)
    rmse = float(np.sqrt(np.mean((y - pred) ** 2)))
    return {"predict": model.predict, "r2": float(_r2(y, pred)), "rmse": rmse, "model": model}


def spline_interpolate(x: np.ndarray, y: np.ndarray, x_new, kind: str = "cubic") -> dict:
    """样条插值。kind: linear / quadratic / cubic。用于填补/加密已知点之间的值，不做外推。"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    order = np.argsort(x)
    x, y = x[order], y[order]
    if kind == "cubic":
        f = CubicSpline(x, y)
    else:
        f = interp1d(x, y, kind=kind)
    return {"y_new": np.asarray(f(np.asarray(x_new, dtype=float))), "interp": f}
