"""正演模型的解析特例检验。

每一条都对应正文里一个可以手算的极限，用来确认公式和代码表达的是同一个模型。
"""

import numpy as np
import pytest

from optics import (
    airy_reflectance,
    finesse_coefficient,
    fresnel_interface,
    group_optical_path,
    layer_phase,
    lorentz_permittivity,
    phase_optical_path,
    silicon_permittivity,
    transverse_index,
    two_beam_reflectance,
)


def test_normal_incidence_matches_hand_computed_fresnel():
    """θ→0 时 s、p 两支必须都退回 ((n-1)/(n+1))²。"""
    n = 2.55
    r_s, r_p = fresnel_interface(1.0, np.array([n**2]), 1e-6)
    expected = ((n - 1.0) / (n + 1.0)) ** 2
    assert np.abs(r_s[0]) ** 2 == pytest.approx(expected, rel=1e-6)
    assert np.abs(r_p[0]) ** 2 == pytest.approx(expected, rel=1e-6)


def test_brewster_angle_kills_p_polarisation():
    """p 分量在布儒斯特角处为零，这是菲涅耳系数符号约定正确的独立证据。"""
    n = 3.42
    brewster = np.degrees(np.arctan(n))
    _, r_p = fresnel_interface(1.0, np.array([n**2]), brewster)
    assert np.abs(r_p[0]) < 1e-12


def test_snell_law_is_embedded_in_transverse_index():
    """sqrt(ε - sin²θ₀) 应等于 n·cos(θ_t)，其中 θ_t 由斯涅尔定律给出。"""
    n, theta = 2.55, 15.0
    theta_t = np.arcsin(np.sin(np.radians(theta)) / n)
    assert np.real(transverse_index(n**2, theta)) == pytest.approx(n * np.cos(theta_t), rel=1e-12)


def test_reststrahlen_band_is_highly_reflective():
    """TO 与 LO 之间介电函数实部为负，体材料反射率应接近 1。"""
    v = np.linspace(820.0, 950.0, 200)
    eps = lorentz_permittivity(v, 6.56, 797.0, 970.0, 4.0)
    assert (np.real(eps) < 0).all()
    k = transverse_index(eps, 10.0)
    r_s = (np.cos(np.radians(10.0)) - k) / (np.cos(np.radians(10.0)) + k)
    reflectance = np.abs(r_s) ** 2
    # 带内处处高反，带心接近全反；阻尼 γ=4 使带边降到约 0.90，与附件实测的 95% 同量级
    assert (reflectance > 0.85).all()
    assert reflectance.max() > 0.95


def test_airy_reduces_to_two_beam_when_interface_contrast_vanishes():
    """|r01·r12| → 0 时 Airy 分母 → 1，两个模型必须重合。

    这是问题一与问题三模型自洽的关键：多光束模型不是另起炉灶，而是双光束的推广。
    """
    v = np.linspace(1500.0, 4000.0, 4000)
    eps1 = silicon_permittivity(v, 11.7)
    eps2 = silicon_permittivity(v, 11.7 * 1.00002)   # 界面对比度极小
    assert finesse_coefficient(eps1[0], eps2[0], 10.0) < 1e-4
    r_two = two_beam_reflectance(v, 3.4, eps1, eps2, 10.0)
    r_airy = airy_reflectance(v, 3.4, eps1, eps2, 10.0)
    assert np.max(np.abs(r_two - r_airy)) < 1e-6


def test_airy_and_two_beam_diverge_when_contrast_is_large():
    """界面对比度大时两个模型必须明显分开，否则问题三就没有讨论的必要。"""
    v = np.linspace(1000.0, 1800.0, 2000)
    eps1 = silicon_permittivity(v, 11.7)
    eps2 = silicon_permittivity(v, 11.7, v_p=1080.0, gamma_p=380.0)
    assert finesse_coefficient(eps1[0], eps2[0], 10.0) > 0.1
    r_two = two_beam_reflectance(v, 3.4, eps1, eps2, 10.0)
    r_airy = airy_reflectance(v, 3.4, eps1, eps2, 10.0)
    assert np.max(np.abs(r_two - r_airy)) > 0.02


def test_phase_and_group_optical_path_agree_without_dispersion():
    """无色散时群光程 = 相位光程；有色散时两者必须分开。"""
    d, theta = 7.45, 10.0
    flat = lambda x: np.full(np.shape(x), 6.5 + 0j)
    v = np.array([2000.0, 3000.0])
    expected = phase_optical_path(d, 6.5, theta)
    assert group_optical_path(v, d, flat, theta) == pytest.approx(expected, rel=1e-8)

    dispersive = lambda x: lorentz_permittivity(x, 6.56, 797.0, 970.0, 4.0)
    grp = group_optical_path(np.array([1200.0]), d, dispersive, theta)[0]
    pha = phase_optical_path(d, dispersive(1200.0), theta)
    assert abs(grp - pha) / pha > 0.05


def test_layer_phase_counts_one_order_per_fringe():
    """相位每增加 2π 对应一个干涉级次，间隔应为 1/(2nd·cosθ)。"""
    d, n, theta = 3.4, 3.42, 10.0
    v = np.array([2000.0, 2000.0 + 1e4 / (2 * 3.4 * np.sqrt(n**2 - np.sin(np.radians(theta)) ** 2))])
    phase = np.real(layer_phase(v, d, n**2, theta))
    assert (phase[1] - phase[0]) == pytest.approx(2 * np.pi, rel=1e-9)
