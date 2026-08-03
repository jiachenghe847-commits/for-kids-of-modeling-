"""附件光谱的读取与预处理。

附件的两个已核实特征决定了这里的处理方式：

1. 首行波数 399.6747 cm^-1 对应的反射率是 0.0000，四份附件都一样。相邻点是
   31.29 / 36.34 / 79.80 / 91.49，说明这不是真实测值而是边界哨兵，必须剔除；
2. 波数步长在 0.481~0.483 cm^-1 之间浮动，不是严格等距。傅里叶分析要求等间隔
   采样，因此重采样是必需步骤而不是可选优化。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# 首行哨兵的判定阈值：真实测值最低也在个位数百分比以上，0 只可能是占位
SENTINEL_REFLECTANCE = 1e-9


def load_spectrum(path: str | Path) -> dict:
    """读入一份附件，返回波数（cm^-1）、反射率（0~1 小数）和预处理记录。

    返回的 ``dropped_rows`` 会写进 results.json，用来说明剔除了哪些点、为什么。
    """
    path = Path(path)
    frame = pd.read_excel(path)
    wavenumber = frame.iloc[:, 0].to_numpy(dtype=float)
    reflectance = frame.iloc[:, 1].to_numpy(dtype=float)

    keep = reflectance > SENTINEL_REFLECTANCE
    dropped = [
        {"index": int(i), "wavenumber_cm-1": float(wavenumber[i]), "reflectance_percent": float(reflectance[i])}
        for i in np.where(~keep)[0]
    ]
    wavenumber, reflectance = wavenumber[keep], reflectance[keep]

    steps = np.diff(wavenumber)
    return {
        "path": str(path),
        "columns": [str(c) for c in frame.columns],
        "n_rows_raw": int(len(frame)),
        "n_rows_used": int(len(wavenumber)),
        "dropped_rows": dropped,
        "wavenumber_cm-1": wavenumber,
        "reflectance": reflectance / 100.0,
        "wavenumber_range_cm-1": [float(wavenumber.min()), float(wavenumber.max())],
        "step_min_cm-1": float(steps.min()),
        "step_max_cm-1": float(steps.max()),
        "reflectance_max_percent": float(reflectance.max()),
        # 哨兵行的紧邻测值：它与 0 相差几十个百分点，正是判定哨兵而非真实测量的依据
        "first_valid_reflectance_percent": float(reflectance[0]),
        "step_variation_relative": float((steps.max() - steps.min()) / steps.mean()),
        "monotonic": bool((steps > 0).all()),
    }


def band_mask(wavenumber: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """闭区间 [lo, hi] 的布尔掩码。"""
    return (wavenumber >= lo) & (wavenumber <= hi)


def resample_uniform(wavenumber: np.ndarray, values: np.ndarray, n_points: int | None = None):
    """线性插值到等间隔波数网格，点数默认与原始点数相同。

    步长浮动只有 0.4%，线性插值引入的误差远小于反射率噪声；这一步的目的是让
    FFT 的频率轴有确定含义，而不是提高精度。
    """
    n_points = len(wavenumber) if n_points is None else n_points
    grid = np.linspace(wavenumber[0], wavenumber[-1], n_points)
    return grid, np.interp(grid, wavenumber, values)


def estimate_noise(values: np.ndarray) -> float:
    """用二阶差分估计逐点白噪声的标准差：σ = std(Δ²y)/√6。

    二阶差分把任何局部近似为二次的慢变成分（基线、条纹的峰谷附近）消去，剩下的
    就是随机涨落，因此这个估计不依赖对基线形状或条纹周期的任何假设。
    """
    return float(np.std(np.diff(np.asarray(values, dtype=float), n=2)) / np.sqrt(6.0))


def detrend_polynomial(wavenumber: np.ndarray, values: np.ndarray, degree: int = 3) -> np.ndarray:
    """减去低阶多项式基线，只留干涉振荡。

    这里不用滑动平滑（Savitzky-Golay）去基线：本题条纹周期最大到 430 cm^-1，
    分析波段本身才 800~2500 cm^-1 宽，任何能压住基线的滑动窗口都短于一个条纹
    周期，会把条纹削平并凭空造出二次谐波——那正是多光束判据要测的量，必须避开。
    低阶多项式对波段内 2~6 个完整条纹几乎正交，不会吃掉振荡。
    """
    center = (wavenumber - wavenumber.mean()) / max(np.ptp(wavenumber), 1e-12)
    coeffs = np.polyfit(center, values, degree)
    return values - np.polyval(coeffs, center)
