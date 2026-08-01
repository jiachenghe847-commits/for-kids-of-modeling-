import numpy as np


def gm11_forecast(series: np.ndarray, steps: int) -> dict:
    x0 = np.asarray(series, dtype=float)
    n = len(x0)
    x1 = np.cumsum(x0)
    z1 = 0.5 * (x1[1:] + x1[:-1])

    B = np.column_stack([-z1, np.ones(n - 1)])
    Y = x0[1:]
    a, b = np.linalg.lstsq(B, Y, rcond=None)[0]

    def x1_hat(k):
        return (x0[0] - b / a) * np.exp(-a * k) + b / a

    total = n + steps
    x1_pred = np.array([x1_hat(k) for k in range(total)])
    x0_pred = np.empty(total)
    x0_pred[0] = x0[0]
    x0_pred[1:] = np.diff(x1_pred)

    return {"forecast": x0_pred, "a": float(a), "b": float(b)}


def grey_relation(reference: np.ndarray, comparisons: np.ndarray, rho: float = 0.5) -> dict:
    """灰色关联分析（评价用）：衡量各比较序列与参考序列的接近程度。

    reference: 参考（母）序列 (m,)，如各指标的理想值或某标杆样本。
    comparisons: 比较序列矩阵 (n, m)，n 个被评价对象，每行 m 个指标。
    rho: 分辨系数，通常取 0.5。
    返回每个对象的关联度与排名（关联度越大越接近参考序列，排名越靠前）。
    """
    ref = np.asarray(reference, dtype=float)
    comp = np.asarray(comparisons, dtype=float)
    # 无量纲化（均值化），消除量纲影响
    ref_n = ref / ref.mean()
    comp_n = comp / comp.mean(axis=1, keepdims=True)

    delta = np.abs(comp_n - ref_n)            # (n, m)
    dmin, dmax = delta.min(), delta.max()
    xi = (dmin + rho * dmax) / (delta + rho * dmax)   # 关联系数
    grade = xi.mean(axis=1)                    # 关联度
    rank = (-grade).argsort().argsort() + 1
    return {"grade": grade, "rank": rank, "xi": xi}
