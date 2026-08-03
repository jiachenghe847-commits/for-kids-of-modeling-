"""外延层—衬底体系的红外反射率正演模型。

全部函数是纯函数：给定波数网格和物理参数，返回反射率或中间量，不读文件、不画图。
单位约定与论文一致：

- 波数 ``v``：cm^-1；
- 厚度 ``d_um``：µm（内部换算成 cm 参与相位计算）；
- 角度 ``theta_deg``：度，指空气中的入射角；
- 反射率：0~1 的小数（附件里是百分数，读取时已除以 100）。

介电函数用复数表示，虚部为正对应吸收（时间约定 exp(-i w t)）。
"""

from __future__ import annotations

import numpy as np

# µm -> cm，相位公式里厚度必须和波数 (cm^-1) 同制
UM_TO_CM = 1e-4


def lorentz_permittivity(v, eps_inf, v_to, v_lo, gamma):
    """极性晶体的单振子（剩余射线带）介电函数。

    碳化硅在 797~970 cm^-1 之间的高反射平台由 TO/LO 声子决定，这一段完整落在
    附件的测量范围内，因此 ``v_to``、``v_lo`` 可以直接从数据拟合出来，不需要外部常数。
    """
    v = np.asarray(v, dtype=float)
    return eps_inf * (1.0 + (v_lo**2 - v_to**2) / (v_to**2 - v**2 - 1j * gamma * v))


def drude_permittivity(v, eps_inf, v_p, gamma_p):
    """自由载流子（Drude）项对应的介电函数。

    重掺杂衬底在低波数呈金属性反射，等离子体波数 ``v_p`` 越大反射边越靠高波数。
    ``v_p`` 取 0 时退化为无色散的 ``eps_inf``。
    """
    v = np.asarray(v, dtype=float)
    if v_p <= 0.0:
        return np.full(v.shape, complex(eps_inf))
    return eps_inf * (1.0 - v_p**2 / (v**2 + 1j * gamma_p * v))


def sic_permittivity(v, eps_inf, v_to, v_lo, gamma, v_p=0.0, gamma_p=1.0):
    """碳化硅：声子振子 + 自由载流子。掺杂只进 Drude 项，声子参数层与衬底共用。"""
    eps = lorentz_permittivity(v, eps_inf, v_to, v_lo, gamma)
    if v_p > 0.0:
        eps = eps - eps_inf * v_p**2 / (np.asarray(v, dtype=float) ** 2 + 1j * gamma_p * np.asarray(v, dtype=float))
    return eps


def silicon_permittivity(v, eps_inf, v_p=0.0, gamma_p=1.0):
    """硅：非极性晶体，中红外无一阶声子带，只保留自由载流子色散。"""
    return drude_permittivity(v, eps_inf, v_p, gamma_p)


def transverse_index(eps, theta_deg):
    """返回 ``sqrt(eps - sin^2(theta))``，即折射角方向的等效纵向折射率 n·cosθ_t。

    这一个量同时承担斯涅尔定律和相位厚度两件事：界面菲涅耳系数和层内相位都只
    依赖它，因此模型里不需要显式出现折射角。
    """
    s2 = np.sin(np.radians(theta_deg)) ** 2
    return np.sqrt(np.asarray(eps, dtype=complex) - s2)


def fresnel_interface(eps_i, eps_j, theta_deg):
    """两介质界面的 s、p 振幅反射系数，入射角以空气中的角度给出。

    返回 ``(r_s, r_p)``。横向波矢守恒使得中间层的折射角不必单独求解。
    """
    k_i = transverse_index(eps_i, theta_deg)
    k_j = transverse_index(eps_j, theta_deg)
    eps_i = np.asarray(eps_i, dtype=complex)
    eps_j = np.asarray(eps_j, dtype=complex)
    r_s = (k_i - k_j) / (k_i + k_j)
    r_p = (eps_j * k_i - eps_i * k_j) / (eps_j * k_i + eps_i * k_j)
    return r_s, r_p


def layer_phase(v, d_um, eps_layer, theta_deg):
    """光在外延层中往返一次的相位 δ = 4π ν d sqrt(ε₁ - sin²θ₀)。

    实部是干涉相位，虚部对应吸收衰减。δ 的实部除以 2π 就是干涉级次，
    正文式(6) 的级次方程直接由它给出。
    """
    k1 = transverse_index(eps_layer, theta_deg)
    return 4.0 * np.pi * np.asarray(v, dtype=float) * (d_um * UM_TO_CM) * k1


def two_beam_reflectance(v, d_um, eps_layer, eps_sub, theta_deg, scale=1.0):
    """问题一的双光束模型：只保留表面反射和衬底界面的一次反射、透射。

    振幅叠加 r = r01 + t01·t10·r12·exp(iδ)，其中 t01·t10 = 1 - r01²。
    与 :func:`airy_reflectance` 的差别仅在于没有多次往返的等比级数分母。
    """
    r01_s, r01_p = fresnel_interface(1.0, eps_layer, theta_deg)
    r12_s, r12_p = fresnel_interface(eps_layer, eps_sub, theta_deg)
    ph = np.exp(1j * layer_phase(v, d_um, eps_layer, theta_deg))
    r_s = r01_s + (1.0 - r01_s**2) * r12_s * ph
    r_p = r01_p + (1.0 - r01_p**2) * r12_p * ph
    return 0.5 * (np.abs(r_s) ** 2 + np.abs(r_p) ** 2) * scale


def airy_reflectance(v, d_um, eps_layer, eps_sub, theta_deg, scale=1.0):
    """问题三的多光束模型：对无穷次往返求和得到的 Airy 公式。

    r = (r01 + r12·e^{iδ}) / (1 + r01·r12·e^{iδ})。分母就是多光束效应本身，
    |r01·r12| → 0 时分母 → 1，退化为双光束模型。
    """
    r01_s, r01_p = fresnel_interface(1.0, eps_layer, theta_deg)
    r12_s, r12_p = fresnel_interface(eps_layer, eps_sub, theta_deg)
    ph = np.exp(1j * layer_phase(v, d_um, eps_layer, theta_deg))
    r_s = (r01_s + r12_s * ph) / (1.0 + r01_s * r12_s * ph)
    r_p = (r01_p + r12_p * ph) / (1.0 + r01_p * r12_p * ph)
    return 0.5 * (np.abs(r_s) ** 2 + np.abs(r_p) ** 2) * scale


def finesse_coefficient(eps_layer, eps_sub, theta_deg):
    """多光束判据用的 |r01·r12|（s、p 取平均）。

    Airy 公式按 |r01·r12| 的幂次展开，二阶项相对一阶项的量级就是这个数，
    因此它同时是「多光束强不强」的物理判据和「二次谐波该有多大」的预测值。
    """
    r01_s, r01_p = fresnel_interface(1.0, eps_layer, theta_deg)
    r12_s, r12_p = fresnel_interface(eps_layer, eps_sub, theta_deg)
    return 0.5 * (np.abs(r01_s * r12_s) + np.abs(r01_p * r12_p))


def group_optical_path(v, d_um, eps_layer_fn, theta_deg, h=1.0):
    """条纹间隔实际测到的「群光程」dΦ/dν /(2π)，单位 cm。

    有色散时相邻条纹间隔给出的不是相位光程 2d·sqrt(ε₁-sin²θ)，而是它对波数的
    导数。两者之差正是傅里叶法在色散区出现系统偏差的原因，见正文 4.3 节。
    ``eps_layer_fn`` 是接受波数返回介电函数的可调用对象。
    """
    v = np.asarray(v, dtype=float)
    phi = lambda x: np.real(layer_phase(x, d_um, eps_layer_fn(x), theta_deg))
    return (phi(v + h) - phi(v - h)) / (2.0 * h) / (2.0 * np.pi)


def phase_optical_path(d_um, eps_layer, theta_deg):
    """相位光程 2·d·sqrt(ε₁ - sin²θ₀)，单位 cm。无色散时它等于群光程。"""
    return 2.0 * (d_um * UM_TO_CM) * np.real(transverse_index(eps_layer, theta_deg))
