import numpy as np
from .model import fit_linear, fit_polynomial, fit_nonlinear, spline_interpolate, svr_fit


def test_fit_linear_recovers_known_line():
    x = np.array([0, 1, 2, 3, 4], dtype=float)
    y = 2 * x + 1
    result = fit_linear(x, y)
    assert abs(result["coef"] - 2.0) < 1e-9
    assert abs(result["intercept"] - 1.0) < 1e-9
    assert result["r2"] > 0.999


def test_fit_polynomial_recovers_quadratic():
    x = np.linspace(-3, 3, 20)
    y = 2 * x ** 2 - x + 5
    result = fit_polynomial(x, y, degree=2)
    assert result["r2"] > 0.999
    assert abs(result["predict"](0) - 5.0) < 1e-6


def test_fit_nonlinear_exponential():
    x = np.linspace(0, 2, 30)
    y = 3.0 * np.exp(0.8 * x)
    result = fit_nonlinear(x, y, lambda t, a, b: a * np.exp(b * t), p0=[1, 1])
    assert abs(result["params"][0] - 3.0) < 1e-3
    assert abs(result["params"][1] - 0.8) < 1e-3


def test_spline_passes_through_points():
    x = np.array([0.0, 1.0, 2.0, 3.0])
    y = np.array([0.0, 1.0, 4.0, 9.0])  # y = x^2 的采样
    result = spline_interpolate(x, y, x_new=[1.0, 2.0])
    assert np.allclose(result["y_new"], [1.0, 4.0], atol=1e-9)  # 严格过已知点


def test_svr_fits_nonlinear_curve():
    rng = np.random.default_rng(0)
    x = np.linspace(-3, 3, 120)
    y = np.sin(x) + 0.05 * rng.normal(0, 1, 120)
    result = svr_fit(x.reshape(-1, 1), y, C=10.0)
    assert result["r2"] > 0.95
    assert result["predict"](x[:5].reshape(-1, 1)).shape == (5,)
