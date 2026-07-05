import numpy as np


def fit_linear(x: np.ndarray, y: np.ndarray) -> dict:
    coef, intercept = np.polyfit(x, y, 1)
    y_pred = coef * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return {"coef": float(coef), "intercept": float(intercept), "r2": float(r2)}
