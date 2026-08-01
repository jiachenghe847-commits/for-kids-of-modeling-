import numpy as np
from .model import bp_regress, bp_classify


def test_bp_regress_learns_nonlinear():
    rng = np.random.default_rng(0)
    X = rng.uniform(-3, 3, (200, 2))
    y = np.sin(X[:, 0]) + X[:, 1] ** 2
    result = bp_regress(X, y, hidden=(32, 16))
    assert result["r2"] > 0.9
    # predict 函数可用
    assert result["predict"](X[:5]).shape == (5,)


def test_bp_classify_separable():
    rng = np.random.default_rng(1)
    a = rng.normal([0, 0], 0.5, (50, 2))
    b = rng.normal([4, 4], 0.5, (50, 2))
    X = np.vstack([a, b])
    y = np.array([0] * 50 + [1] * 50)
    result = bp_classify(X, y)
    assert result["accuracy"] > 0.95
