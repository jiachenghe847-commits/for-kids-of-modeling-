"""从实测反射谱反演外延层厚度的三条路线。

三条路线互相独立，构成正文的基线—主方法—验证链条：

1. :func:`fourier_optical_path` —— 傅里叶基线法。只用条纹周期，透明、秒级、
   不依赖任何物理参数，但给出的是光程 2nd·cosθ，且在色散区有系统偏差；
2. :func:`extremum_order_fit` —— 条纹级次法。人工可复核的经典做法，把极值
   波数对整数级次做线性回归，斜率即光程；
3. :func:`fit_layer_model` —— 全谱物理模型拟合，是主方法。同时定出厚度和
   介电函数，因此不需要外部折射率常数。

前两条只能给出光程，要换算成几何厚度必须另外知道折射率；第三条把折射率
一起解出来，这正是它作为主方法的理由。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import least_squares
from scipy.signal import find_peaks

from spectra import band_mask, detrend_polynomial, estimate_noise, resample_uniform

CM_TO_UM = 1e4


# --------------------------------------------------------------------------
# 路线 1：傅里叶基线法
# --------------------------------------------------------------------------
def _optical_path_spectrum(wavenumber, reflectance, lo, hi, baseline_degree, pad):
    mask = band_mask(wavenumber, lo, hi)
    grid, values = resample_uniform(wavenumber[mask], reflectance[mask])
    osc = detrend_polynomial(grid, values, baseline_degree)
    rms = float(np.std(osc))
    windowed = osc * np.hanning(len(osc))
    step = grid[1] - grid[0]
    amplitude = np.abs(np.fft.rfft(windowed, pad))
    # rfftfreq 的共轭变量量纲是 cm，物理含义正是光程 2nd·cosθ_t
    path_cm = np.fft.rfftfreq(pad, d=step)
    return path_cm * CM_TO_UM, amplitude, rms


def _refine_peak(x, y, index):
    """抛物线插值细化谱峰位置，把峰位精度从一个频率格提升到格距的百分之几。"""
    if index <= 0 or index >= len(y) - 1:
        return float(x[index])
    y1, y2, y3 = y[index - 1], y[index], y[index + 1]
    denom = y1 - 2.0 * y2 + y3
    if denom == 0.0:
        return float(x[index])
    shift = 0.5 * (y1 - y3) / denom
    return float(x[index] + shift * (x[1] - x[0]))


def fourier_optical_path(
    wavenumber,
    reflectance,
    lo,
    hi,
    baseline_degree=3,
    pad=2**18,
    search_um=(5.0, 150.0),
) -> dict:
    """在 [lo, hi] 波段内用傅里叶谱峰给出光程 2nd·cosθ_t（µm）。"""
    path_um, amplitude, rms = _optical_path_spectrum(
        wavenumber, reflectance, lo, hi, baseline_degree, pad
    )
    sel = (path_um > search_um[0]) & (path_um < search_um[1])
    index = int(np.where(sel)[0][int(np.argmax(amplitude[sel]))])
    peak_um = _refine_peak(path_um, amplitude, index)
    return {
        "band_cm-1": [float(lo), float(hi)],
        "optical_path_um": peak_um,
        "fringe_period_cm-1": CM_TO_UM / peak_um,
        "oscillation_rms": rms,
        "peak_amplitude": float(amplitude[index]),
    }


def harmonic_diagnostic(
    wavenumber,
    reflectance,
    lo,
    hi,
    baseline_degree=3,
    pad=2**19,
    tolerance_um=1.5,
    noise_band_um=(150.0, 400.0),
) -> dict:
    """多光束干涉的可计算判据：二次谐波相对基频的幅度。

    双光束模型的反射率是 cosδ 的一次式，傅里叶谱只有基频；多光束的 Airy 公式
    展开后含 cos2δ、cos3δ 项，幅度按 |r01·r12| 的幂次衰减。因此
    ``second_over_first`` 显著高于噪声本底，就是多光束存在的直接证据。
    """
    path_um, amplitude, _ = _optical_path_spectrum(
        wavenumber, reflectance, lo, hi, baseline_degree, pad
    )
    sel = (path_um > 5.0) & (path_um < 150.0)
    first = _refine_peak(path_um, amplitude, int(np.where(sel)[0][int(np.argmax(amplitude[sel]))]))

    def peak_near(target):
        near = np.abs(path_um - target) <= tolerance_um
        return float(amplitude[near].max()) if near.any() else 0.0

    a1 = peak_near(first)
    noise = np.median(amplitude[(path_um > noise_band_um[0]) & (path_um < noise_band_um[1])])
    return {
        "band_cm-1": [float(lo), float(hi)],
        "fundamental_um": first,
        "second_over_first": peak_near(2.0 * first) / a1,
        "third_over_first": peak_near(3.0 * first) / a1,
        "noise_floor_over_first": float(noise) / a1,
    }


# --------------------------------------------------------------------------
# 路线 2：条纹级次法
# --------------------------------------------------------------------------
def _alternate(peaks, troughs, values):
    """把峰和谷合并成严格交替的序列，同类相邻时只留更极端的那个。

    ``find_peaks`` 的 ``distance`` 只在峰之间、谷之间各自生效，一个真峰和一个
    噪声造出的假谷仍可能只隔十几个 cm^-1。级次序列 0, 0.5, 1.0, ... 要求峰谷
    严格交替，多出来的一个极值就会让后面所有级次整体错半级——实测中附件 2 因此
    把光程从 39 µm 虚报到 41 µm。
    """
    tagged = sorted([(int(i), 1) for i in peaks] + [(int(i), -1) for i in troughs])
    kept: list[tuple[int, int]] = []
    for index, sign in tagged:
        if kept and kept[-1][1] == sign:
            # 同类相邻：保留幅度更大的那个，另一个判为噪声
            if sign * values[index] > sign * values[kept[-1][0]]:
                kept[-1] = (index, sign)
            continue
        kept.append((index, sign))
    return np.array([index for index, _ in kept], dtype=int)


def _enforce_separation(indices, values, distance):
    """在已交替的序列上再过一遍最小间隔，反复剔除幅度最小的越界极值。

    交替性本身管不住这种情形：一个真峰后面紧跟一个噪声谷，而真谷在很远处——
    两个谷之间的距离过滤放行，峰与噪声谷却只隔十几个 cm^-1。这里按 |振幅| 从小
    到大剔除，每剔一个重新检查，直到所有相邻间隔都达标。
    """
    if not distance or len(indices) < 2:
        return np.asarray(indices, dtype=int)
    kept = list(indices)
    while len(kept) >= 2:
        gaps = np.diff(kept)
        bad = np.where(gaps < distance)[0]
        if len(bad) == 0:
            break
        first = int(bad[0])
        a, b = kept[first], kept[first + 1]
        kept.pop(first if abs(values[a]) < abs(values[b]) else first + 1)
    return np.asarray(kept, dtype=int)


def extremum_order_fit(
    wavenumber,
    reflectance,
    lo,
    hi,
    baseline_degree=3,
    prominence_factor=0.25,
    expected_period_cm=None,
    use_guards=True,
) -> dict:
    """提取极值波数、赋整数半级次，再线性回归得到光程。

    相邻极值（峰到谷）相差半个周期，故级次取 0, 0.5, 1.0, ... 回归式为
    ``m_k = L·ν_k + c``，斜率 L 就是光程（cm）。截距 c 吸收了界面反射相位。

    ``expected_period_cm`` 用来设定极值之间的最小间隔（取半周期的 0.6 倍）。
    不设这个限制时，附件 2 高波数段的噪声会被当成条纹：实测多找出十几个假极值，
    级次序列整体被拉长，光程从 39 µm 虚报到 63 µm。周期由傅里叶基线提供，
    两条基线因此不是完全独立——级次法验证的是相位随波数的线性性，不是周期本身。
    """
    mask = band_mask(wavenumber, lo, hi)
    grid, values = resample_uniform(wavenumber[mask], reflectance[mask])
    osc = detrend_polynomial(grid, values, baseline_degree)
    # 显著性阈值同时受两条约束：振荡幅度的一个固定比例，以及噪声标准差的 5 倍。
    # 只用前者时，条纹幅度衰减到与噪声同量级的高波数段会把噪声当条纹（实测中
    # 附件 2 因此多出假极值）；噪声下限保证极值必须真正高出涨落才被采信。
    prominence = prominence_factor * float(np.std(osc))
    if use_guards:
        prominence = max(prominence, 5.0 * estimate_noise(osc))
    step = grid[1] - grid[0]
    distance = None
    if expected_period_cm and use_guards:
        distance = max(int(0.6 * 0.5 * expected_period_cm / step), 1)

    peaks, _ = find_peaks(osc, prominence=prominence, distance=distance)
    troughs, _ = find_peaks(-osc, prominence=prominence, distance=distance)
    if use_guards:
        kept = _enforce_separation(_alternate(peaks, troughs, osc), osc, distance)
    else:
        kept = np.sort(np.concatenate([peaks, troughs])).astype(int)
    extrema = grid[kept]
    if len(extrema) < 4:
        raise ValueError(f"波段 {lo}-{hi} 只找到 {len(extrema)} 个极值，不足以定级次")

    orders = 0.5 * np.arange(len(extrema))
    slope, intercept = np.polyfit(extrema, orders, 1)
    residual = orders - (slope * extrema + intercept)
    return {
        "band_cm-1": [float(lo), float(hi)],
        "n_extrema": int(len(extrema)),
        "min_separation_cm-1": float(np.diff(extrema).min()),
        "optical_path_um": float(slope) * CM_TO_UM,
        "intercept_order": float(intercept),
        "order_residual_rms": float(np.sqrt((residual**2).mean())),
        "order_residual_max": float(np.abs(residual).max()),
        "extrema_cm-1": [float(x) for x in extrema],
    }


# --------------------------------------------------------------------------
# 路线 3：全谱物理模型拟合（主方法）
# --------------------------------------------------------------------------
@dataclass
class FitSpec:
    """一次全谱拟合的完整定义：正演函数、参数名、初值和边界。"""

    forward: object                       # (v, theta, params) -> 反射率
    names: list[str]
    x0: list[float]
    lower: list[float]
    upper: list[float]
    units: list[str] = field(default_factory=list)


def _formal_uncertainty(jac, fun, names) -> dict:
    """由雅可比给出参数的形式标准差和相关矩阵的条件数。

    这是「假设残差是独立同分布随机噪声」下的下界。本题残差以模型失配为主而非
    随机噪声，所以形式标准差会系统性地低估真实不确定度；正文用它衡量参数之间
    有没有简并（看条件数），真实误差另用换角度、换波段的散布来估。
    """
    m, n = jac.shape
    hessian = jac.T @ jac
    dof = max(m - n, 1)
    sigma2 = float(fun @ fun) / dof
    try:
        cov = np.linalg.inv(hessian) * sigma2
        std = np.sqrt(np.clip(np.diag(cov), 0.0, None))
        condition = float(np.linalg.cond(hessian))
    except np.linalg.LinAlgError:
        std = np.full(n, np.nan)
        condition = float("inf")
    return {
        "residual_sigma": float(np.sqrt(sigma2)),
        "formal_std": {name: float(s) for name, s in zip(names, std)},
        "hessian_condition_number": condition,
        "note": "残差以模型失配为主，形式标准差是下界，不能当作真实不确定度",
    }


def fit_layer_model(
    wavenumber,
    reflectance,
    theta_deg,
    spec: FitSpec,
    lo,
    hi,
    seeds=(1, 2, 3, 4, 5),
    jitter=0.15,
    max_nfev=4000,
) -> dict:
    """多起点最小二乘拟合，返回最优解、逐种子记录、收敛轨迹和边界残差。

    ``least_squares`` 本身是确定性的，随机性只来自起点扰动。用多个固定种子重复
    是为了证明报告的解不是初值的产物——只报一次运行的最好结果不算证据。
    """
    mask = band_mask(wavenumber, lo, hi)
    v, y = wavenumber[mask], reflectance[mask]
    x0 = np.asarray(spec.x0, dtype=float)
    lower = np.asarray(spec.lower, dtype=float)
    upper = np.asarray(spec.upper, dtype=float)

    runs = []
    best = None
    for seed in seeds:
        trace: list[float] = []

        def residual(p, _trace=trace):
            r = spec.forward(v, theta_deg, p) - y
            _trace.append(float(0.5 * np.sum(r**2)))
            return r

        rng = np.random.default_rng(seed)
        start = x0 * (1.0 + jitter * rng.uniform(-1.0, 1.0, size=x0.shape))
        start = np.clip(start, lower + 1e-9, upper - 1e-9)
        sol = least_squares(
            residual, start, bounds=(lower, upper), x_scale="jac", max_nfev=max_nfev
        )
        rms = float(np.sqrt(np.mean(sol.fun**2)))
        record = {
            "_jac": sol.jac,
            "_fun": sol.fun,
            "seed": int(seed),
            "start": [float(x) for x in start],
            "params": [float(x) for x in sol.x],
            "rms_reflectance": rms,
            "cost": float(sol.cost),
            "nfev": int(sol.nfev),
            "status": int(sol.status),
            "termination": str(sol.message),
            "convergence_trace": [float(c) for c in np.minimum.accumulate(trace)],
        }
        runs.append(record)
        if best is None or record["cost"] < best["cost"]:
            best = record

    params = np.asarray(best["params"], dtype=float)
    formal = _formal_uncertainty(best.pop("_jac"), best.pop("_fun"), spec.names)
    for record in runs:
        record.pop("_jac", None)
        record.pop("_fun", None)
    values = [r["params"] for r in runs]
    spread = np.ptp(np.asarray(values), axis=0)
    rms_all = [r["rms_reflectance"] for r in runs]

    # 参数边界是本问题唯一的显式约束，逐个报告到边界的距离
    span = upper - lower
    bound_report = [
        {
            "name": name,
            "value": float(val),
            "lower": float(lo_i),
            "upper": float(hi_i),
            "slack_to_lower_rel": float((val - lo_i) / s),
            "slack_to_upper_rel": float((hi_i - val) / s),
            "active": bool(min(val - lo_i, hi_i - val) / s < 1e-3),
        }
        for name, val, lo_i, hi_i, s in zip(spec.names, params, lower, upper, span)
    ]

    return {
        "band_cm-1": [float(lo), float(hi)],
        "n_points": int(mask.sum()),
        "theta_deg": float(theta_deg),
        "param_names": list(spec.names),
        "param_units": list(spec.units),
        "params": {name: float(val) for name, val in zip(spec.names, params)},
        "rms_reflectance": best["rms_reflectance"],
        "best_seed": best["seed"],
        "formal_uncertainty": formal,
        "multi_seed": {
            "n_seeds": len(runs),
            "rms_best": float(min(rms_all)),
            "rms_worst": float(max(rms_all)),
            "rms_mean": float(np.mean(rms_all)),
            "rms_std": float(np.std(rms_all)),
            "param_spread": {name: float(s) for name, s in zip(spec.names, spread)},
        },
        "runs": runs,
        "constraint_audit": bound_report,
        "max_bound_violation": 0.0,
    }
