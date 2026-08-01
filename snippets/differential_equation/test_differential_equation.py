import numpy as np
from .model import solve_ode, sir_model


def test_exponential_decay_matches_analytic():
    # dy/dt = -k y, 解析解 y = y0 * exp(-k t)
    k = 0.5
    result = solve_ode(lambda t, y: -k * y, y0=[10.0], t_span=(0, 5),
                       t_eval=np.linspace(0, 5, 50))
    analytic = 10.0 * np.exp(-k * result["t"])
    assert result["success"]
    assert np.max(np.abs(result["y"][0] - analytic)) < 1e-2  # RK45 默认容差量级


def test_sir_conserves_population():
    result = sir_model(beta=0.3, gamma=0.1, S0=990, I0=10, R0=0, t_end=100)
    totals = result["y"].sum(axis=0)
    assert np.allclose(totals, 1000.0, atol=1e-4)  # S+I+R 守恒
    # 该参数下会爆发疫情，I 峰值应显著高于初始
    assert result["y"][1].max() > 100
