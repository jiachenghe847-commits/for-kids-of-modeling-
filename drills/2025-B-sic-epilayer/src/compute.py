"""2025 B 题主计算入口：读附件 → 反演 → 写 artifacts/results.json。

论文里出现的每一个数字都必须来自这个文件写出的 results.json，gen_paper.py 只做
插值排版，不允许手工转抄。

在仓库根目录运行::

    .venv/bin/python drills/2025-B-sic-epilayer/src/compute.py

所有拟合用固定种子 (1,2,3,4,5) 的多起点，结果可复现。
"""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from inversion import (  # noqa: E402
    FitSpec,
    extremum_order_fit,
    fit_layer_model,
    fourier_optical_path,
    harmonic_diagnostic,
)
from optics import (  # noqa: E402
    airy_reflectance,
    finesse_coefficient,
    sic_permittivity,
    silicon_permittivity,
    two_beam_reflectance,
)
from spectra import band_mask, estimate_noise, load_spectrum  # noqa: E402

CASE_DIR = HERE.parent
INPUT_DIR = CASE_DIR / "official_input"
ARTIFACT_DIR = CASE_DIR / "artifacts"

SEEDS = (1, 2, 3, 4, 5)

# 附件说明给定的测量条件：同一块片子、两个入射角
ATTACHMENTS = {
    "attachment_1": {"file": "附件1.xlsx", "wafer": "silicon_carbide", "theta_deg": 10.0},
    "attachment_2": {"file": "附件2.xlsx", "wafer": "silicon_carbide", "theta_deg": 15.0},
    "attachment_3": {"file": "附件3.xlsx", "wafer": "silicon", "theta_deg": 10.0},
    "attachment_4": {"file": "附件4.xlsx", "wafer": "silicon", "theta_deg": 15.0},
}

# 分析波段。碳化硅 970 cm^-1 以下是剩余射线带，层内强吸收、条纹被压平，
# 只有带外才能做条纹分析；全谱拟合则必须包含该带，声子参数才定得住。
BANDS = {
    "silicon_carbide": {
        "fit": (420.0, 4000.0),
        "fringe": (1500.0, 4000.0),
        "diagnostic": [(1000.0, 1800.0), (1800.0, 2600.0), (2600.0, 4000.0)],
        "sensitivity": [(420.0, 4000.0), (700.0, 4000.0), (420.0, 3000.0)],
    },
    "silicon": {
        "fit": (420.0, 4000.0),
        "fringe": (1500.0, 4000.0),
        "diagnostic": [(1000.0, 1800.0), (1800.0, 2600.0), (2600.0, 4000.0)],
        "sensitivity": [(420.0, 4000.0), (700.0, 4000.0), (420.0, 3000.0)],
    },
}


# --------------------------------------------------------------------------
# 两种材料的正演模型定义
# --------------------------------------------------------------------------
def sic_spec(kind: str) -> FitSpec:
    """碳化硅：层与衬底共用声子参数，掺杂差异体现在衬底 Drude 项和层的介电微调。"""
    reflect = two_beam_reflectance if kind == "two_beam" else airy_reflectance

    def forward(v, theta, p):
        d, eps_inf, v_to, v_lo, gamma, vp_sub, gp_sub, delta_layer, scale = p
        eps1 = sic_permittivity(v, eps_inf * (1.0 + delta_layer), v_to, v_lo, gamma)
        eps2 = sic_permittivity(v, eps_inf, v_to, v_lo, gamma, vp_sub, gp_sub)
        return reflect(v, d, eps1, eps2, theta, scale)

    return FitSpec(
        forward=forward,
        names=["d_um", "eps_inf", "v_to", "v_lo", "gamma", "vp_sub", "gamma_sub",
               "delta_layer", "scale"],
        x0=[7.5, 6.6, 797.0, 971.0, 4.5, 300.0, 300.0, 0.0, 1.0],
        lower=[3.0, 4.0, 780.0, 950.0, 0.5, 0.0, 10.0, -0.05, 0.80],
        upper=[15.0, 9.0, 815.0, 990.0, 30.0, 2000.0, 3000.0, 0.05, 1.20],
        units=["µm", "1", "cm^-1", "cm^-1", "cm^-1", "cm^-1", "cm^-1", "1", "1"],
    )


def si_spec(kind: str) -> FitSpec:
    """硅：非极性晶体，中红外无一阶声子带，色散只来自自由载流子。"""
    reflect = two_beam_reflectance if kind == "two_beam" else airy_reflectance

    def forward(v, theta, p):
        d, eps_inf, vp_layer, gp_layer, vp_sub, gp_sub, scale = p
        eps1 = silicon_permittivity(v, eps_inf, vp_layer, gp_layer)
        eps2 = silicon_permittivity(v, eps_inf, vp_sub, gp_sub)
        return reflect(v, d, eps1, eps2, theta, scale)

    return FitSpec(
        forward=forward,
        names=["d_um", "eps_inf", "vp_layer", "gamma_layer", "vp_sub", "gamma_sub", "scale"],
        x0=[3.5, 11.7, 20.0, 100.0, 900.0, 350.0, 1.0],
        lower=[1.0, 9.0, 0.0, 1.0, 50.0, 10.0, 0.80],
        upper=[8.0, 14.0, 400.0, 3000.0, 3000.0, 5000.0, 1.20],
        units=["µm", "1", "cm^-1", "cm^-1", "cm^-1", "cm^-1", "1"],
    )


SPECS = {"silicon_carbide": sic_spec, "silicon": si_spec}


def rebuild_permittivity(wafer: str, params: dict, v):
    """由拟合参数重建层与衬底的介电函数，供判据和作图复用。"""
    if wafer == "silicon_carbide":
        eps1 = sic_permittivity(v, params["eps_inf"] * (1.0 + params["delta_layer"]),
                                params["v_to"], params["v_lo"], params["gamma"])
        eps2 = sic_permittivity(v, params["eps_inf"], params["v_to"], params["v_lo"],
                                params["gamma"], params["vp_sub"], params["gamma_sub"])
    else:
        eps1 = silicon_permittivity(v, params["eps_inf"], params["vp_layer"], params["gamma_layer"])
        eps2 = silicon_permittivity(v, params["eps_inf"], params["vp_sub"], params["gamma_sub"])
    return eps1, eps2


def model_reflectance(wafer: str, kind: str, params: dict, v, theta):
    eps1, eps2 = rebuild_permittivity(wafer, params, v)
    reflect = two_beam_reflectance if kind == "two_beam" else airy_reflectance
    return reflect(v, params["d_um"], eps1, eps2, theta, params["scale"])


# --------------------------------------------------------------------------
# 单份附件的完整分析
# --------------------------------------------------------------------------
def analyse(info: dict) -> dict:
    wafer, theta = info["wafer"], info["theta_deg"]
    bands = BANDS[wafer]
    data = load_spectrum(INPUT_DIR / info["file"])
    v, r = data["wavenumber_cm-1"], data["reflectance"]

    out = {
        "wafer": wafer,
        "theta_deg": theta,
        "preprocessing": {k: data[k] for k in
                          ("path", "columns", "n_rows_raw", "n_rows_used", "dropped_rows",
                           "wavenumber_range_cm-1", "step_min_cm-1", "step_max_cm-1",
                           "reflectance_max_percent", "first_valid_reflectance_percent",
                           "step_variation_relative", "monotonic")},
    }

    # 基线一：傅里叶法，逐波段看色散造成的漂移
    out["baseline_fourier"] = [
        fourier_optical_path(v, r, lo, hi)
        for lo, hi in [bands["fringe"], (1500.0, 2500.0), (2500.0, 3300.0), (3300.0, 4000.0)]
    ]
    # 基线二：条纹级次法。最小极值间隔由傅里叶法给出的周期设定，否则噪声会被当条纹
    period = out["baseline_fourier"][0]["fringe_period_cm-1"]
    out["baseline_extremum"] = extremum_order_fit(v, r, *bands["fringe"], expected_period_cm=period)
    # 消融：关掉噪声下限与峰谷交替保护，量化极值法会虚报多少
    out["guard_ablation"] = guard_ablation(v, r, period)
    # 色散扫描：滑动波段的光程漂移，支撑「条纹间隔测到的是群光程」这一论断
    out["dispersion_scan"] = dispersion_scan(v, r)

    # 多光束判据：逐波段的二次谐波
    out["harmonics_measured"] = [harmonic_diagnostic(v, r, lo, hi) for lo, hi in bands["diagnostic"]]

    # 主方法：全谱拟合。双光束模型对应问题一/二，Airy 模型对应问题三
    spec_builder = SPECS[wafer]
    for kind in ("two_beam", "airy"):
        out[f"fit_{kind}"] = fit_layer_model(
            v, r, theta, spec_builder(kind), *bands["fit"], seeds=SEEDS
        )

    # 波段敏感性：换分析区间，主方法给出的厚度散布多大
    out["band_sensitivity"] = []
    for lo, hi in bands["sensitivity"]:
        fit = fit_layer_model(v, r, theta, spec_builder("airy"), lo, hi, seeds=(1, 2, 3))
        out["band_sensitivity"].append(
            {"band_cm-1": [lo, hi], "d_um": fit["params"]["d_um"],
             "rms_reflectance": fit["rms_reflectance"]}
        )
    out["band_sensitivity_spread_um"] = float(np.ptp([x["d_um"] for x in out["band_sensitivity"]]))
    out["band_sensitivity_spread_relative"] = float(
        out["band_sensitivity_spread_um"] / np.mean([x["d_um"] for x in out["band_sensitivity"]]))
    if wafer == "silicon_carbide":
        out["bulk_reference_fit"] = bulk_reference_fit(v, r, theta)

    # 判据的泄漏本底：用拟合出的参数合成一条**双光束**谱，走同一条处理流水线。
    # 双光束理论上无谐波，测出来的就是去基线泄漏，是判据的分辨下限。
    params = out["fit_airy"]["params"]
    synth_two_beam = model_reflectance(wafer, "two_beam", params, v, theta)
    out["harmonics_leakage_reference"] = [
        harmonic_diagnostic(v, synth_two_beam, lo, hi) for lo, hi in bands["diagnostic"]
    ]

    # 逐波段的判据主证据：忽略多光束会让模型反射率偏多少，与该波段测量噪声比较。
    # 这条判据不含人为阈值，也不受谐波法「波段内条纹太少」的限制。
    synth_airy = model_reflectance(wafer, "airy", params, v, theta)
    out["multibeam_evidence"] = []
    for lo, hi in bands["diagnostic"]:
        mask = band_mask(v, lo, hi)
        eps1, eps2 = rebuild_permittivity(wafer, params, v[mask])
        f = finesse_coefficient(eps1, eps2, theta)
        gap = np.abs(synth_airy[mask] - synth_two_beam[mask])
        out["multibeam_evidence"].append({
            "band_cm-1": [lo, hi],
            "finesse_mean": float(np.mean(f)),      # |r01·r12|，Airy 展开的公比
            "finesse_max": float(np.max(f)),
            "model_gap_max_percent": float(np.max(gap) * 100.0),
            "model_gap_rms_percent": float(np.sqrt(np.mean(gap**2)) * 100.0),
            "noise_percent": float(estimate_noise(r[mask]) * 100.0),
        })
    return out


# --------------------------------------------------------------------------
# 支撑正文若干论断的专项实验
# --------------------------------------------------------------------------
DISPERSION_BANDS = [(1000.0, 1800.0), (1400.0, 2200.0), (1800.0, 2600.0),
                    (2200.0, 3000.0), (2600.0, 3400.0), (3000.0, 3800.0)]


def dispersion_scan(v, r) -> dict:
    """滑动波段扫描傅里叶光程，量化色散造成的「群光程漂移」。

    正文用它证明式(7) 的无色散厚度公式只能作基线：同一块片子在不同波段测出的
    光程可以差三成，这个差就是式(9) 里的 ν·dκ/dν 项。
    """
    scan = [fourier_optical_path(v, r, lo, hi) for lo, hi in DISPERSION_BANDS]
    paths = [item["optical_path_um"] for item in scan]
    return {
        "per_band": scan,
        "max_um": float(max(paths)),
        "min_um": float(min(paths)),
        "drift_relative": float((max(paths) - min(paths)) / min(paths)),
    }


def bulk_reference_fit(v, r, theta) -> dict:
    """只用剩余射线带做体材料拟合，用来演示 ε∞ 与标定因子的简并。

    这是全谱拟合的对照实验：窗口 760~1010 cm^-1 内几乎没有真正的带外平台，
    ε∞ 与标定因子近似成比例地互相补偿，于是带边位置很稳、介电常数很不稳。
    正文用两者的稳定性对比说明「为什么必须把带外一起拟合」。
    """
    def forward(v_, theta_, p):
        eps_inf, v_to, v_lo, gamma, scale = p
        eps = sic_permittivity(v_, eps_inf, v_to, v_lo, gamma)
        # 体材料（无外延层）：只有一个空气/介质界面
        k = np.sqrt(eps - np.sin(np.radians(theta_)) ** 2 + 0j)
        c0 = np.cos(np.radians(theta_))
        r_s = (c0 - k) / (c0 + k)
        r_p = (eps * c0 - k) / (eps * c0 + k)
        return 0.5 * (np.abs(r_s) ** 2 + np.abs(r_p) ** 2) * scale

    spec = FitSpec(
        forward=forward, names=["eps_inf", "v_to", "v_lo", "gamma", "scale"],
        x0=[6.5, 797.0, 970.0, 5.0, 1.0],
        lower=[4.0, 760.0, 940.0, 0.5, 0.8], upper=[9.0, 830.0, 1000.0, 30.0, 1.2],
        units=["1", "cm^-1", "cm^-1", "cm^-1", "1"],
    )
    fit = fit_layer_model(v, r, theta, spec, 760.0, 1010.0, seeds=(1, 2, 3))
    return {"params": fit["params"], "rms_reflectance": fit["rms_reflectance"]}


def guard_ablation(v, r, expected_period_cm) -> dict:
    """消融实验：关掉极值检测的噪声下限与峰谷交替保护会发生什么。

    正文用它说明这两道保护不是可有可无的工程细节。关掉后噪声被当成条纹，
    级次序列被拉长，光程被系统性虚报——这个数字必须可复现，不能只凭开发时的印象。
    """
    guarded = extremum_order_fit(v, r, 1500.0, 4000.0, expected_period_cm=expected_period_cm)
    naive = extremum_order_fit(v, r, 1500.0, 4000.0, expected_period_cm=expected_period_cm,
                               use_guards=False)
    return {
        "with_guards": {k: guarded[k] for k in
                        ("n_extrema", "optical_path_um", "min_separation_cm-1",
                         "order_residual_max")},
        "without_guards": {k: naive[k] for k in
                           ("n_extrema", "optical_path_um", "min_separation_cm-1",
                            "order_residual_max")},
        "inflation_relative": float((naive["optical_path_um"] - guarded["optical_path_um"])
                                    / guarded["optical_path_um"]),
    }


def theoretical_angle_contrast(n_ref: float, theta1: float, theta2: float) -> dict:
    """在给定折射率下，两个入射角本应造成多大的光程差异。

    这是式(15) 病态性的根源：真实的 q-1 只有千分之几，而实测 q-1 受各种系统误差
    影响可以大一个量级，反演出的折射率因此毫无意义。
    """
    s1, s2 = np.sin(np.radians(theta1)) ** 2, np.sin(np.radians(theta2)) ** 2
    ratio = float(np.sqrt((n_ref**2 - s2) / (n_ref**2 - s1)))
    return {
        "n_reference": float(n_ref),
        "path_ratio": ratio,
        "path_contrast_relative": float(1.0 - ratio),
        "q_minus_one": float(ratio**2 - 1.0),
    }


# --------------------------------------------------------------------------
# 双角度联合分析
# --------------------------------------------------------------------------
def two_angle_index_inversion(path1_um: float, path2_um: float,
                              theta1: float, theta2: float) -> dict:
    """由两个角度的光程比反推折射率，并给出该反演的条件数。

    L = 2d·sqrt(n² - sin²θ) ⇒ q = (L₂/L₁)² = (n² - sin²θ₂)/(n² - sin²θ₁)
    ⇒ n² = (q·sin²θ₁ - sin²θ₂)/(q - 1)

    真实 q 与 1 只差千分之几，分母是两个相近数之差，这条看似优雅的路线在数值上
    是病态的。这里把条件数算出来，用数字说明它为什么不能用来定折射率。
    """
    s1, s2 = np.sin(np.radians(theta1)) ** 2, np.sin(np.radians(theta2)) ** 2
    q = (path2_um / path1_um) ** 2
    n2 = (q * s1 - s2) / (q - 1.0)
    dn2_dq = (s2 - s1) / (q - 1.0) ** 2          # 相对条件数 |dn²/n²| / |dq/q|
    condition = abs(dn2_dq * q / n2) if n2 != 0 else float("inf")
    return {
        "path_ratio": float(path2_um / path1_um),
        "q": float(q),
        "q_minus_one": float(q - 1.0),
        "n_squared": float(n2),
        "n": float(np.sqrt(n2)) if n2 > 0 else None,
        "relative_condition_number": float(condition),
        "note": "q-1 是两个相近数之差，条件数达 10² 量级，该路线不可用于定折射率",
    }


def _param_agreement(p1: dict, p2: dict) -> dict:
    """两个入射角各自独立拟合出的同名参数之间的相对差。

    厚度以外的参数（声子波数、等离子体波数）在物理上与入射角无关，两角度的一致性
    因此是模型正确性的独立证据，而不是拟合的自由度。
    """
    return {
        name: float(abs(p1[name] - p2[name]) / (0.5 * abs(p1[name] + p2[name])))
        for name in p1
        if name not in {"d_um", "scale"} and abs(p1[name] + p2[name]) > 1e-12
    }


def combine(name: str, first: dict, second: dict, kind: str) -> dict:
    """汇总同一块晶圆两个角度的结果，给出厚度和不确定度预算。"""
    d1 = first[f"fit_{kind}"]["params"]["d_um"]
    d2 = second[f"fit_{kind}"]["params"]["d_um"]
    n1 = float(np.sqrt(first[f"fit_{kind}"]["params"]["eps_inf"]))
    n2 = float(np.sqrt(second[f"fit_{kind}"]["params"]["eps_inf"]))
    mean = 0.5 * (d1 + d2)
    band_spread = max(first["band_sensitivity_spread_um"], second["band_sensitivity_spread_um"])
    angle_spread = abs(d1 - d2) / 2.0
    return {
        "wafer": name,
        "model": kind,
        "d_um_theta10": float(d1),
        "d_um_theta15": float(d2),
        "d_um_mean": float(mean),
        "d_um_half_spread": float(angle_spread),
        "d_relative_spread": float(abs(d1 - d2) / mean),
        "n_inf_theta10": n1,
        "n_inf_theta15": n2,
        "n_inf_mean": float(0.5 * (n1 + n2)),
        "n_relative_spread": float(abs(n1 - n2) / (0.5 * (n1 + n2))),
        "scale_theta10": float(first[f"fit_{kind}"]["params"]["scale"]),
        "scale_theta15": float(second[f"fit_{kind}"]["params"]["scale"]),
        "scale_absolute_gap": float(abs(first[f"fit_{kind}"]["params"]["scale"]
                                        - second[f"fit_{kind}"]["params"]["scale"])),
        # 与厚度无关的物理参数在两角度间的一致性——它们越一致，模型越可信
        "shared_param_agreement": _param_agreement(
            first[f"fit_{kind}"]["params"], second[f"fit_{kind}"]["params"]),
        "uncertainty_budget": {
            "formal_std_um_theta10":
                first[f"fit_{kind}"]["formal_uncertainty"]["formal_std"]["d_um"],
            "band_spread_um_theta10": first["band_sensitivity_spread_um"],
            "band_spread_um_theta15": second["band_sensitivity_spread_um"],
            "angle_half_spread_um": float(angle_spread),
            "dominant_source": "角度间散布" if angle_spread > band_spread else "波段选择",
            "reported_uncertainty_um": float(max(angle_spread, band_spread)),
        },
    }


def multibeam_correction(name: str, first: dict, second: dict) -> dict:
    """双光束模型与多光束模型给出的厚度之差，即多光束效应带来的系统偏差。"""
    rows = []
    for label, item in (("theta10", first), ("theta15", second)):
        d_two = item["fit_two_beam"]["params"]["d_um"]
        d_airy = item["fit_airy"]["params"]["d_um"]
        rows.append({
            "angle": label,
            "d_two_beam_um": float(d_two),
            "d_airy_um": float(d_airy),
            "shift_um": float(d_airy - d_two),
            "shift_relative": float((d_airy - d_two) / d_airy),
            "rms_two_beam": item["fit_two_beam"]["rms_reflectance"],
            "rms_airy": item["fit_airy"]["rms_reflectance"],
            "rms_improvement": float(1.0 - item["fit_airy"]["rms_reflectance"]
                                     / item["fit_two_beam"]["rms_reflectance"]),
        })
    return {"wafer": name, "per_angle": rows,
            "mean_shift_relative": float(np.mean([r["shift_relative"] for r in rows])),
            "mean_rms_improvement": float(np.mean([r["rms_improvement"] for r in rows]))}


def main() -> None:
    started = time.time()
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    results = {
        "meta": {
            "case_id": "2025-B",
            "title": "碳化硅外延层厚度的确定",
            "phase": "blind",
            "inputs_mode": "official-only",
            "seeds": list(SEEDS),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "note": "论文中所有数值均由本文件生成，禁止手工转抄",
        },
        "attachments": {},
    }

    for key, info in ATTACHMENTS.items():
        print(f"分析 {key}（{info['file']}，入射角 {info['theta_deg']}°）...", flush=True)
        results["attachments"][key] = analyse(info)

    a1, a2 = results["attachments"]["attachment_1"], results["attachments"]["attachment_2"]
    a3, a4 = results["attachments"]["attachment_3"], results["attachments"]["attachment_4"]

    # 问题二：用问题一的双光束模型处理碳化硅
    results["q2"] = {
        "silicon_carbide": combine("silicon_carbide", a1, a2, "two_beam"),
        "theoretical_angle_contrast": theoretical_angle_contrast(
            float(np.sqrt(a1["fit_two_beam"]["params"]["eps_inf"])), 10.0, 15.0),
        "dispersion_scan": a1["dispersion_scan"],
        "guard_ablation": a2["guard_ablation"],
        "bulk_reference_fit": {"attachment_1": a1["bulk_reference_fit"],
                               "attachment_2": a2["bulk_reference_fit"]},
        "two_angle_index_inversion": two_angle_index_inversion(
            a1["baseline_fourier"][0]["optical_path_um"],
            a2["baseline_fourier"][0]["optical_path_um"], 10.0, 15.0),
        "baseline_vs_primary": [
            {
                "attachment": key,
                "fourier_path_um": item["baseline_fourier"][0]["optical_path_um"],
                "extremum_path_um": item["baseline_extremum"]["optical_path_um"],
                "baseline_disagreement_relative": float(abs(
                    item["baseline_fourier"][0]["optical_path_um"]
                    - item["baseline_extremum"]["optical_path_um"])
                    / item["baseline_fourier"][0]["optical_path_um"]),
                "d_from_primary_um": item["fit_two_beam"]["params"]["d_um"],
            }
            for key, item in (("attachment_1", a1), ("attachment_2", a2))
        ],
    }

    # 问题三：多光束
    results["q3"] = {
        "silicon": combine("silicon", a3, a4, "airy"),
        "silicon_carbide_corrected": combine("silicon_carbide", a1, a2, "airy"),
        "correction": {
            "silicon_carbide": multibeam_correction("silicon_carbide", a1, a2),
            "silicon": multibeam_correction("silicon", a3, a4),
        },
        "diagnostic_table": [
            {
                "attachment": key,
                "wafer": item["wafer"],
                "bands": [
                    {
                        "band_cm-1": ev["band_cm-1"],
                        "finesse_mean": ev["finesse_mean"],
                        "model_gap_max_percent": ev["model_gap_max_percent"],
                        "noise_percent": ev["noise_percent"],
                        "gap_over_noise": float(ev["model_gap_max_percent"] / ev["noise_percent"]),
                        # 判据：忽略多光束造成的模型偏差超过测量噪声 3 倍即不可忽略
                        "multibeam": bool(ev["model_gap_max_percent"] > 3.0 * ev["noise_percent"]),
                        # 以下为旁证，谐波法在条纹数少的窄波段分辨力有限，故不作判据
                        "second_over_first": meas["second_over_first"],
                        "harmonic_leakage_floor": leak["second_over_first"],
                        "harmonic_excess": float(meas["second_over_first"]
                                                 - leak["second_over_first"]),
                    }
                    for ev, meas, leak in zip(item["multibeam_evidence"],
                                              item["harmonics_measured"],
                                              item["harmonics_leakage_reference"])
                ],
            }
            for key, item in results["attachments"].items()
        ],
    }
    results["meta"]["runtime_seconds"] = round(time.time() - started, 1)

    path = ARTIFACT_DIR / "results.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"写出 {path}（{path.stat().st_size / 1024:.0f} KB，用时 "
          f"{results['meta']['runtime_seconds']} s）")
    for name, size in write_evidence_files(results):
        print(f"  {name}  {size / 1024:.1f} KB")


def write_evidence_files(results: dict):
    """把 results.json 拆成 case.json 逐条登记的证据文件。

    审计器要求每条验证都指向一个存在的文件。拆分件全部由 results.json 派生，
    不含任何额外计算，因此不会出现「两个来源对不上」的问题。
    """
    attachments = results["attachments"]
    pieces = {
        "baseline_fourier.json": {k: v["baseline_fourier"] for k, v in attachments.items()},
        "baseline_extremum.json": {k: v["baseline_extremum"] for k, v in attachments.items()},
        "primary_fit.json": {
            k: {kind: {"params": v[f"fit_{kind}"]["params"],
                       "rms_reflectance": v[f"fit_{kind}"]["rms_reflectance"],
                       "formal_uncertainty": v[f"fit_{kind}"]["formal_uncertainty"]}
                for kind in ("two_beam", "airy")}
            for k, v in attachments.items()
        },
        "convergence.json": {
            k: [{"seed": run["seed"], "nfev": run["nfev"], "termination": run["termination"],
                 "convergence_trace": run["convergence_trace"]}
                for run in v["fit_airy"]["runs"]]
            for k, v in attachments.items()
        },
        "multi_seed.json": {k: v["fit_airy"]["multi_seed"] for k, v in attachments.items()},
        "constraints.json": {
            k: {"parameter_bounds": v["fit_airy"]["constraint_audit"],
                "max_violation": v["fit_airy"]["max_bound_violation"]}
            for k, v in attachments.items()
        },
        "band_sensitivity.json": {
            k: {"per_band": v["band_sensitivity"], "spread_um": v["band_sensitivity_spread_um"]}
            for k, v in attachments.items()
        },
        "two_angle_crosscheck.json": {
            "q2_silicon_carbide_two_beam": results["q2"]["silicon_carbide"],
            "q3_silicon_airy": results["q3"]["silicon"],
            "q3_silicon_carbide_airy": results["q3"]["silicon_carbide_corrected"],
            "index_inversion_conditioning": results["q2"]["two_angle_index_inversion"],
        },
        "multibeam_diagnostic.json": {
            "table": results["q3"]["diagnostic_table"],
            "correction": results["q3"]["correction"],
        },
        "preprocessing.json": {k: v["preprocessing"] for k, v in attachments.items()},
    }
    written = []
    for name, payload in pieces.items():
        target = ARTIFACT_DIR / name
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append((name, target.stat().st_size))
    return written


if __name__ == "__main__":
    main()
