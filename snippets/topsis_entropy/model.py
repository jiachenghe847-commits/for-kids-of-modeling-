import numpy as np


def _normalize(matrix: np.ndarray) -> np.ndarray:
    col_sum = matrix.sum(axis=0)
    col_sum[col_sum == 0] = 1e-12
    return matrix / col_sum


def entropy_weights(matrix: np.ndarray) -> np.ndarray:
    p = _normalize(matrix)
    p_safe = np.where(p == 0, 1e-12, p)
    n = matrix.shape[0]
    k = 1.0 / np.log(n)
    entropy = -k * np.sum(p_safe * np.log(p_safe), axis=0)
    diversity = 1 - entropy
    return diversity / diversity.sum()


def topsis_score(matrix: np.ndarray, weights: np.ndarray) -> np.ndarray:
    norm = matrix / np.sqrt((matrix ** 2).sum(axis=0))
    weighted = norm * weights
    best = weighted.max(axis=0)
    worst = weighted.min(axis=0)
    dist_best = np.sqrt(((weighted - best) ** 2).sum(axis=1))
    dist_worst = np.sqrt(((weighted - worst) ** 2).sum(axis=1))
    denom = dist_best + dist_worst
    denom[denom == 0] = 1e-12
    return dist_worst / denom
