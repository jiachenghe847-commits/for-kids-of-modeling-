"""反演算法在已知真值上的回收检验。

这里的光谱是本文件用正演模型合成的，**不是附件数据**：合成谱的厚度是已知的，
因此可以直接检验算法误差；附件数据没有真值，只能靠多方法互校。
两者的用途不能混淆，正文报告的所有实测数字一律来自附件。
"""

import numpy as np
import pytest

from inversion import (
    FitSpec,
    extremum_order_fit,
    fit_layer_model,
    fourier_optical_path,
    harmonic_diagnostic,
)
from optics import airy_reflectance, silicon_permittivity, two_beam_reflectance

TRUE_D_UM = 3.4
TRUE_EPS = 11.7
THETA = 10.0


def _grid():
    """复刻附件的采样特征：399.67~4000.12 cm^-1，7468 点，步长轻微不等距。"""
    v = np.linspace(399.6747 + 0.4821, 4000.1220, 7468)
    rng = np.random.default_rng(0)
    return np.sort(v + rng.uniform(-0.001, 0.001, size=v.shape))


TRUE_VP_LAYER = 25.0


def _synthetic(kind, v_p_sub=0.0, noise=0.0, seed=0):
    v = _grid()
    # 层内给一个很小的等离子体项，使真值落在参数框内部而不是贴着下界，
    # 这样约束审计里「解贴边」才是真信号而不是构造出来的假警报
    eps1 = silicon_permittivity(v, TRUE_EPS, v_p=TRUE_VP_LAYER, gamma_p=100.0)
    # 0.98 的介电对比度对应 r12≈0.005、条纹幅度约 0.4%，与附件 1 高波数段实测同量级；
    # 取得再小就会让条纹淹没在下面加的噪声里，测的就不是算法而是构造缺陷了
    eps2 = silicon_permittivity(v, TRUE_EPS * 0.98 if v_p_sub == 0.0 else TRUE_EPS,
                                v_p=v_p_sub, gamma_p=380.0)
    model = two_beam_reflectance if kind == "two_beam" else airy_reflectance
    r = model(v, TRUE_D_UM, eps1, eps2, THETA)
    if noise:
        r = r + np.random.default_rng(seed).normal(0.0, noise, size=r.shape)
    return v, r


def _expected_optical_path_um():
    """真值光程 2·d·sqrt(ε₁ - sin²θ₀)，单位 µm。"""
    return 2.0 * TRUE_D_UM * np.sqrt(TRUE_EPS - np.sin(np.radians(THETA)) ** 2)


def test_fourier_baseline_recovers_known_optical_path():
    v, r = _synthetic("two_beam")
    got = fourier_optical_path(v, r, 1500.0, 4000.0)["optical_path_um"]
    assert got == pytest.approx(_expected_optical_path_um(), rel=2e-3)


def test_fourier_baseline_survives_realistic_noise():
    """加 0.05% 的高斯噪声——与附件高波数段实测噪声同量级——结果不应变坏。"""
    v, r = _synthetic("two_beam", noise=5e-4, seed=7)
    got = fourier_optical_path(v, r, 1500.0, 4000.0)["optical_path_um"]
    assert got == pytest.approx(_expected_optical_path_um(), rel=3e-3)


def test_extremum_order_fit_agrees_with_fourier_baseline():
    """两条只用条纹周期的路线互为独立实现，应给出一致的光程。"""
    v, r = _synthetic("two_beam")
    order = extremum_order_fit(v, r, 1500.0, 4000.0)
    assert order["optical_path_um"] == pytest.approx(_expected_optical_path_um(), rel=5e-3)
    assert order["order_residual_max"] < 0.05


def test_two_beam_spectrum_stays_near_the_leakage_floor():
    """双光束模型是 cosδ 的一次式，理论上没有二次谐波。

    实测到的约 3% 不是物理量，而是方法本身的泄漏本底：1000~1800 cm^-1 只装得下
    1.9 个条纹，三阶多项式去基线不可能与不到两个周期的振荡完全正交。这个数是
    判据的分辨下限，正文必须报出来，不能当成多光束证据。
    """
    v, r = _synthetic("two_beam")
    diag = harmonic_diagnostic(v, r, 1000.0, 1800.0)
    assert diag["second_over_first"] < 0.05


def test_multi_beam_spectrum_shows_strong_second_harmonic():
    """强界面对比度的 Airy 谱必须远高于泄漏本底，判据才有区分力。"""
    v, r_two = _synthetic("two_beam")
    _, r_airy = _synthetic("airy", v_p_sub=1080.0)
    leak = harmonic_diagnostic(v, r_two, 1000.0, 1800.0)["second_over_first"]
    diag = harmonic_diagnostic(v, r_airy, 1000.0, 1800.0)
    assert diag["second_over_first"] > 0.1
    assert diag["second_over_first"] > 4.0 * leak
    assert diag["second_over_first"] > 10 * diag["noise_floor_over_first"]


def test_alternation_drops_a_spurious_extremum():
    """峰谷必须严格交替；同类相邻时保留更极端的那个。

    回归测试：附件 2 高波数段的噪声曾造出一个假谷，级次序列整体错半级，
    光程从 39.2 µm 虚报到 41.3 µm。
    """
    from inversion import _alternate

    values = np.array([0.0, 1.0, 0.0, -1.0, 0.0, 0.9, 0.0, -1.0, 0.0])
    #                        峰         谷        假峰(更矮)   谷
    kept = _alternate(peaks=[1, 5], troughs=[3, 7], values=values)
    assert list(kept) == [1, 3, 5, 7]

    # 两个峰相邻且中间没有谷时，只应留下更高的那个
    values2 = np.array([0.0, 0.6, 0.2, 1.0, 0.0, -1.0, 0.0])
    kept2 = _alternate(peaks=[1, 3], troughs=[5], values=values2)
    assert list(kept2) == [3, 5]


def test_extremum_fit_rejects_noise_induced_extrema():
    """给条纹叠加高频噪声后，最小极值间隔仍应接近半个条纹周期。"""
    v, r = _synthetic("two_beam", noise=8e-4, seed=3)
    period = 1e4 / _expected_optical_path_um()
    out = extremum_order_fit(v, r, 1500.0, 4000.0, expected_period_cm=period)
    assert out["min_separation_cm-1"] > 0.35 * period
    assert out["order_residual_max"] < 0.2
    assert out["optical_path_um"] == pytest.approx(_expected_optical_path_um(), rel=1e-2)


def _silicon_spec():
    def forward(v, theta, p):
        d, eps_inf, vp_l, gp_l, vp_s, gp_s, scale = p
        e1 = silicon_permittivity(v, eps_inf, vp_l, gp_l)
        e2 = silicon_permittivity(v, eps_inf, vp_s, gp_s)
        return airy_reflectance(v, d, e1, e2, theta, scale)

    return FitSpec(
        forward=forward,
        names=["d_um", "eps_inf", "vp_layer", "gamma_layer", "vp_sub", "gamma_sub", "scale"],
        x0=[3.6, 11.0, 20.0, 100.0, 900.0, 300.0, 1.0],
        lower=[1.0, 9.0, 0.0, 1.0, 50.0, 10.0, 0.8],
        upper=[8.0, 14.0, 400.0, 3000.0, 3000.0, 5000.0, 1.2],
        units=["µm", "1", "cm^-1", "cm^-1", "cm^-1", "cm^-1", "1"],
    )


def test_full_model_fit_recovers_thickness_and_index():
    """主方法在合成谱上应同时找回厚度和折射率，且五个种子给出同一个解。"""
    v, r = _synthetic("airy", v_p_sub=1080.0, noise=3e-4, seed=11)
    out = fit_layer_model(v, r, THETA, _silicon_spec(), 420.0, 4000.0)
    assert out["params"]["d_um"] == pytest.approx(TRUE_D_UM, rel=5e-3)
    assert out["params"]["eps_inf"] == pytest.approx(TRUE_EPS, rel=1e-2)
    assert out["multi_seed"]["param_spread"]["d_um"] < 5e-3
    assert out["multi_seed"]["n_seeds"] == 5


def test_fit_reports_convergence_trace_and_bound_slack():
    """收敛轨迹必须单调不增，且最优解不应贴在人为设定的参数边界上。"""
    v, r = _synthetic("airy", v_p_sub=1080.0)
    out = fit_layer_model(v, r, THETA, _silicon_spec(), 420.0, 4000.0, seeds=(1, 2, 3))
    trace = out["runs"][0]["convergence_trace"]
    assert len(trace) > 5
    assert all(b <= a + 1e-15 for a, b in zip(trace, trace[1:]))
    assert not any(item["active"] for item in out["constraint_audit"])
