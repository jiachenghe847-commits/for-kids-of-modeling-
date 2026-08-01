import numpy as np


def fill_missing(x: np.ndarray, strategy: str = "mean") -> dict:
    """一维序列缺失值（np.nan）填补。

    strategy: mean / median / interpolate（线性插值，适合时间序列）/ ffill（前向填充）。
    """
    x = np.asarray(x, dtype=float)
    mask = np.isnan(x)
    out = x.copy()
    if not mask.any():
        return {"filled": out, "n_filled": 0}
    if strategy == "mean":
        out[mask] = np.nanmean(x)
    elif strategy == "median":
        out[mask] = np.nanmedian(x)
    elif strategy == "interpolate":
        idx = np.arange(len(x))
        out[mask] = np.interp(idx[mask], idx[~mask], x[~mask])
    elif strategy == "ffill":
        last = np.nan
        for i in range(len(out)):
            if np.isnan(out[i]):
                out[i] = last
            else:
                last = out[i]
    else:
        raise ValueError(f"unknown strategy: {strategy}")
    return {"filled": out, "n_filled": int(mask.sum())}


def detect_outliers(x: np.ndarray, method: str = "iqr", k: float = 1.5) -> dict:
    """异常值检测。method: iqr（四分位距）或 zscore（3σ，k 默认取 3 更合适）。

    返回布尔掩码 outliers 与阈值区间 (low, high)。
    """
    x = np.asarray(x, dtype=float)
    if method == "iqr":
        q1, q3 = np.percentile(x, [25, 75])
        iqr = q3 - q1
        low, high = q1 - k * iqr, q3 + k * iqr
    elif method == "zscore":
        mu, sd = x.mean(), x.std()
        low, high = mu - k * sd, mu + k * sd
    else:
        raise ValueError(f"unknown method: {method}")
    outliers = (x < low) | (x > high)
    return {"outliers": outliers, "low": float(low), "high": float(high),
            "n_outliers": int(outliers.sum())}


def standardize(X: np.ndarray) -> dict:
    """Z-score 标准化（按列），使每列均值 0、标准差 1。返回结果及均值/标准差便于还原。"""
    X = np.asarray(X, dtype=float)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd_safe = np.where(sd == 0, 1.0, sd)
    return {"scaled": (X - mu) / sd_safe, "mean": mu, "std": sd}


def normalize(X: np.ndarray, feature_range=(0, 1)) -> dict:
    """min-max 归一化（按列）到 [a, b]。返回结果及每列 min/max。"""
    X = np.asarray(X, dtype=float)
    lo, hi = feature_range
    xmin = X.min(axis=0)
    xmax = X.max(axis=0)
    span = np.where(xmax - xmin == 0, 1.0, xmax - xmin)
    scaled = (X - xmin) / span * (hi - lo) + lo
    return {"scaled": scaled, "min": xmin, "max": xmax}
