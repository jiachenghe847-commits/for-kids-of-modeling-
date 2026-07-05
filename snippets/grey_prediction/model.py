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
