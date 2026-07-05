import numpy as np
from .model import fit_linear


def test_fit_linear_recovers_known_line():
    x = np.array([0, 1, 2, 3, 4], dtype=float)
    y = 2 * x + 1
    result = fit_linear(x, y)
    assert abs(result["coef"] - 2.0) < 1e-9
    assert abs(result["intercept"] - 1.0) < 1e-9
    assert result["r2"] > 0.999
