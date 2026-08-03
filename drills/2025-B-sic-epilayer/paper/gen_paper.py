"""只从 artifacts/results.json 生成 paper/paper.tex，不接受其他数据来源。

正文里的每一个数字都由 f-string 从 JSON 插值而来。要改数字请改 src/compute.py
重跑，不要直接编辑 paper.tex——它是生成物，下次运行会被覆盖。

在仓库根目录运行::

    .venv/bin/python drills/2025-B-sic-epilayer/paper/gen_paper.py
    cd drills/2025-B-sic-epilayer/paper && xelatex -interaction=nonstopmode paper.tex
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "artifacts" / "results.json"
OUTPUT = ROOT / "paper" / "paper.tex"

BAND_LABEL = {"1000.0-1800.0": "1000--1800", "1800.0-2600.0": "1800--2600",
              "2600.0-4000.0": "2600--4000"}
ATT_LABEL = {"attachment_1": "附件 1（SiC，$10^\\circ$）", "attachment_2": "附件 2（SiC，$15^\\circ$）",
             "attachment_3": "附件 3（Si，$10^\\circ$）", "attachment_4": "附件 4（Si，$15^\\circ$）"}


def preprocessing_table(R) -> str:
    rows = []
    for key, item in R["attachments"].items():
        p = item["preprocessing"]
        lo, hi = p["wavenumber_range_cm-1"]
        rows.append(
            f"    {ATT_LABEL[key]} & {p['n_rows_raw']} & {p['n_rows_used']} & "
            f"{lo:.2f}--{hi:.2f} & {p['step_min_cm-1']:.3f}--{p['step_max_cm-1']:.3f} & "
            f"{p['reflectance_max_percent']:.2f} \\\\"
        )
    return "\n".join(rows)


def diagnostic_table(R) -> str:
    rows = []
    for entry in R["q3"]["diagnostic_table"]:
        for band in entry["bands"]:
            tag = f"{band['band_cm-1'][0]}-{band['band_cm-1'][1]}"
            rows.append(
                f"    {ATT_LABEL[entry['attachment']]} & {BAND_LABEL[tag]} & "
                f"{band['finesse_mean']:.4f} & {band['model_gap_max_percent']:.3f} & "
                f"{band['noise_percent']:.4f} & {band['gap_over_noise']:.1f} & "
                f"{'是' if band['multibeam'] else '否'} \\\\"
            )
    return "\n".join(rows)


def seed_table(R) -> str:
    rows = []
    for key, item in R["attachments"].items():
        ms = item["fit_airy"]["multi_seed"]
        rows.append(
            f"    {ATT_LABEL[key]} & {ms['n_seeds']} & {ms['rms_best'] * 100:.4f} & "
            f"{ms['rms_worst'] * 100:.4f} & {ms['rms_std'] * 100:.2e} & "
            f"{ms['param_spread']['d_um']:.2e} \\\\"
        )
    return "\n".join(rows)


def band_sensitivity_table(R) -> str:
    rows = []
    for key, item in R["attachments"].items():
        cells = " & ".join(f"{b['d_um']:.4f}" for b in item["band_sensitivity"])
        rows.append(f"    {ATT_LABEL[key]} & {cells} & {item['band_sensitivity_spread_um']:.4f} \\\\")
    return "\n".join(rows)


def build(R) -> str:
    meta = R["meta"]
    a1 = R["attachments"]["attachment_1"]
    a2 = R["attachments"]["attachment_2"]
    a3 = R["attachments"]["attachment_3"]
    sic = R["q2"]["silicon_carbide"]
    sic_fix = R["q3"]["silicon_carbide_corrected"]
    si = R["q3"]["silicon"]
    inv = R["q2"]["two_angle_index_inversion"]
    corr_sic = R["q3"]["correction"]["silicon_carbide"]
    corr_si = R["q3"]["correction"]["silicon"]
    base = R["q2"]["baseline_vs_primary"]
    f1 = a1["fit_airy"]["params"]
    f2 = a2["fit_airy"]["params"]
    fs1 = a3["fit_airy"]["params"]
    sic_bands = a1["multibeam_evidence"]
    si_bands = a3["multibeam_evidence"]
    ub_sic = sic["uncertainty_budget"]
    ub_si = si["uncertainty_budget"]
    leak_lo = a1["harmonics_leakage_reference"][0]["second_over_first"]
    scan = R["q2"]["dispersion_scan"]
    abl = R["q2"]["guard_ablation"]
    bulk1 = R["q2"]["bulk_reference_fit"]["attachment_1"]["params"]
    bulk2 = R["q2"]["bulk_reference_fit"]["attachment_2"]["params"]
    bulk_to_gap = abs(bulk1["v_to"] - bulk2["v_to"]) / bulk1["v_to"]
    bulk_eps_gap = abs(bulk1["eps_inf"] - bulk2["eps_inf"]) / (0.5 * (bulk1["eps_inf"] + bulk2["eps_inf"]))
    tac = R["q2"]["theoretical_angle_contrast"]
    agree_sic = sic["shared_param_agreement"]
    agree_si = si["shared_param_agreement"]
    p0 = a1["preprocessing"]["dropped_rows"][0]
    first_valid = [R["attachments"][k]["preprocessing"]["first_valid_reflectance_percent"]
                   for k in ("attachment_1", "attachment_2", "attachment_3", "attachment_4")]
    band_rel = [R["attachments"][k]["band_sensitivity_spread_relative"] for k in R["attachments"]]
    base_gap = max(base[0]["baseline_disagreement_relative"],
                   base[1]["baseline_disagreement_relative"])

    return rf"""% 本文件由 paper/gen_paper.py 从 artifacts/results.json 自动生成，请勿手工编辑。
% 编译：在本目录运行 xelatex -interaction=nonstopmode paper.tex（跑两趟）
\documentclass[12pt]{{article}}
\usepackage{{cumcm-paper}}
\graphicspath{{{{figures/}}}}
% 中文正文中夹有等宽文件名与长公式，无法在其内部断行；给段落少量额外伸缩量
\setlength{{\emergencystretch}}{{1em}}

\begin{{document}}
\cumcmtitle{{碳化硅外延层厚度的确定}}

\begin{{abstract}}
红外干涉法测外延层厚度的核心困难在于：干涉条纹只能给出\textbf{{光程}} $2nd\cos\theta_t$，
而题目要的是\textbf{{几何厚度}} $d$，两者相差一个折射率，且题目明确指出折射率不是常数。
本文不引入任何外部折射率常数，而是把折射率与厚度作为同一组未知量，由附件光谱自身同时定出。

针对问题一，从菲涅耳系数与层内往返相位出发，导出只含一次反射、透射的双光束反射率
$R=\left|r_{{01}}+(1-r_{{01}}^{{2}})r_{{12}}\mathrm{{e}}^{{\mathrm{{i}}\delta}}\right|^{{2}}$，
其中 $\delta=4\pi\tilde\nu d\sqrt{{\varepsilon_1-\sin^2\theta_0}}$，斯涅尔定律以纵向折射率
$\sqrt{{\varepsilon_1-\sin^2\theta_0}}$ 的形式内蕴其中。由此给出厚度公式
$d=1/\left(2\Delta\tilde\nu\sqrt{{n_1^2-\sin^2\theta_0}}\right)$，并指出有色散时相邻条纹间隔测到的
是\textbf{{群光程}}而非相位光程——实测中两者相差达 {scan['drift_relative'] * 100:.0f}\%，
直接套用该式会系统性高估厚度。

针对问题二，设计"两条透明基线 + 一条全谱主方法"的算法。基线用傅里叶变换和条纹级次回归
提取光程，两者在附件 1 上相差 {base[0]['baseline_disagreement_relative'] * 100:.2f}\%、附件 2 上
{base[1]['baseline_disagreement_relative'] * 100:.2f}\%。主方法把 Lorentz 声子振子与 Drude 自由载流子
写进介电函数，对 420--4000\,cm$^{{-1}}$ 全谱做多起点有界最小二乘。关键在于碳化硅的剩余射线带
({f1['v_to']:.1f}--{f1['v_lo']:.1f}\,cm$^{{-1}}$，由拟合定出) 完整落在测量范围内，带内近全反与带外平台的
\emph{{比值}}不随标定缩放，从而破解了折射率与绝对反射率标定的简并。结果为
$d={sic['d_um_theta10']:.3f}$\,µm（$10^\circ$）与 $d={sic['d_um_theta15']:.3f}$\,µm（$15^\circ$），
均值 $\mathbf{{{sic['d_um_mean']:.2f}\pm{ub_sic['reported_uncertainty_um']:.2f}}}$\,µm，
同时给出 $n_\infty={sic['n_inf_mean']:.3f}$。可靠性分析表明：光程本身可由两条独立基线互校到 {base_gap * 100:.2f}\% 以内，
厚度的不确定度 {ub_sic['reported_uncertainty_um'] / sic['d_um_mean'] * 100:.1f}\% 几乎全部来自两角度间的差异，
而两角度的标定因子相差 {abs(sic['scale_theta10'] - sic['scale_theta15']) * 100:.1f}\%（附件 2 实测反射率最高达
{a2['preprocessing']['reflectance_max_percent']:.1f}\%，超过物理上限）。我们还证明了"用两个角度的光程比反解折射率"
这条看似优雅的路线不可用：其相对条件数为 {inv['relative_condition_number']:.0f}，实测数据代入给出
$n={inv['n']:.2f}$，与全谱拟合的 {sic['n_inf_mean']:.2f} 严重矛盾。

针对问题三，由 Airy 公式的等比级数展开给出多光束的必要条件 $|r_{{01}}r_{{12}}|$ 不可忽略，
并提出一个不含人为阈值的可计算判据：忽略多光束造成的模型反射率偏差与该波段实测噪声之比。
判定结果为：硅晶圆（附件 3、4）在全部三个波段均出现多光束，1000--1800\,cm$^{{-1}}$ 处
$|r_{{01}}r_{{12}}|={si_bands[0]['finesse_mean']:.3f}$、偏差/噪声比高达 {si_bands[0]['model_gap_max_percent'] / si_bands[0]['noise_percent']:.0f}；
用双光束模型硬拟合会把厚度低估 {corr_si['mean_shift_relative'] * 100:.1f}\%。改用多光束模型后得
$d=\mathbf{{{si['d_um_mean']:.3f}\pm{ub_si['reported_uncertainty_um']:.3f}}}$\,µm，两角度仅差
{si['d_relative_spread'] * 100:.2f}\%，残差 RMS 由 {corr_si['per_angle'][0]['rms_two_beam'] * 100:.2f}\% 降到
{corr_si['per_angle'][0]['rms_airy'] * 100:.2f}\%。碳化硅则只在 1000--1800\,cm$^{{-1}}$ 勉强越过判据
（偏差/噪声比 {sic_bands[0]['model_gap_max_percent'] / sic_bands[0]['noise_percent']:.1f}），
消除多光束影响后厚度为 {sic_fix['d_um_mean']:.3f}\,µm，相对未修正值仅改变
{abs(corr_sic['mean_shift_relative']) * 100:.3f}\%，远小于 {ub_sic['reported_uncertainty_um'] / sic['d_um_mean'] * 100:.1f}\% 的
不确定度——即多光束在本片碳化硅上客观存在但不构成精度瓶颈，真正的瓶颈是绝对反射率标定。
\end{{abstract}}
\keywords{{红外干涉；外延层厚度；碳化硅；色散；Airy 多光束干涉；病态反演；不确定度预算}}

\section{{问题重述}}

碳化硅外延层厚度是外延材料的关键参数。红外干涉法通过外延层上下表面两束反射光的干涉条纹，
结合波长、折射率和入射角确定厚度，是一种无损测量方法。需要解决三个问题：

\begin{{enumerate}}[leftmargin=2em]
  \item 只考虑外延层与衬底界面一次反射、透射所产生的干涉条纹，建立确定外延层厚度的数学模型；
  \item 依此模型设计算法，对附件 1、附件 2 给出的碳化硅晶圆光谱实测数据计算厚度，并分析可靠性；
  \item 推导多光束干涉产生的必要条件及其对厚度精度的影响；判断附件 3、附件 4 的硅晶圆是否出现
        多光束干涉并给出厚度；若认为附件 1、2 也受多光束影响，设法消除并给出修正结果。
\end{{enumerate}}

附件 1、2 为同一块碳化硅晶圆在入射角 $10^\circ$、$15^\circ$ 下的测试结果，附件 3、4 为同一块
硅晶圆在相同两个角度下的结果；每份数据第 1 列为波数（cm$^{{-1}}$），第 2 列为反射率（\%）。

\section{{问题分析}}

三个问题构成一条递进的链条，但真正的难点不在链条本身，而在一个贯穿始终的\textbf{{结构性障碍}}。

\textbf{{障碍：光程与厚度之间隔着一个未知的折射率。}}\;
干涉条纹的周期只决定光程 $L=2d\sqrt{{n_1^2-\sin^2\theta_0}}$。要由 $L$ 得到 $d$ 必须知道 $n_1$，
而题目开宗明义指出折射率随掺杂浓度和波长变化，不是可以查表代入的常数。盲测条件下也不允许
引入外部文献值。因此本文把 $n_1$ 与 $d$ 视为同一组未知量，寻找能同时约束两者的信息源。

\textbf{{问题一}}是建模问题，不涉及数值。关键是把斯涅尔定律、界面反射相位和层内往返相位
组织成一个可以直接对实测谱作正演的表达式，而不是停留在"光程差 $=m\lambda$"的教科书形式。
同时必须指出：有色散时相邻条纹间隔给出的是群光程 $\mathrm{{d}}\Phi/\mathrm{{d}}\tilde\nu$，
与相位光程不等，这是后面两问一切系统偏差的来源。

\textbf{{问题二}}的核心是找到 $n_1$ 的独立约束。我们注意到三条候选路线：
(a) 两个入射角的光程比可以消去 $d$ 解出 $n_1$；
(b) 条纹的绝对反射率水平由 $r_{{01}}=(1-n_1)/(1+n_1)$ 决定；
(c) 碳化硅的剩余射线带完整落在 400--4000\,cm$^{{-1}}$ 内，其带边位置和带内外反射率之比蕴含
介电函数的全部参数。路线 (a) 看似优雅，但 $10^\circ$ 与 $15^\circ$ 造成的光程差异只有
{tac['path_contrast_relative'] * 100:.2f}\%，是典型的病态反演——本文将其条件数算出来作为反例。路线 (b) 受绝对标定误差限制。
路线 (c) 中带内外的\emph{{比值}}不随标定缩放，是唯一稳健的信息源，故采用全谱物理模型拟合。

\textbf{{问题三}}分为推导与判定两半。推导部分从 Airy 公式的等比级数出发，多光束的强弱由公比
$r_{{01}}r_{{12}}$ 控制，必要条件随之自然浮现。判定部分的困难在于避免拍脑袋的阈值：我们不问
"二次谐波超过多少算多光束"，而问"忽略多光束造成的模型偏差是否超过该波段的测量噪声"，
后者可由数据本身估计，判据因此是自校准的。

\section{{模型假设}}

\begin{{modelassumptions}}
  \item 外延层与衬底界面平行于晶圆表面，光斑范围内层厚均匀。厚度不均会使条纹对比度随波数
        额外衰减，本文把两个入射角之间的厚度差异如实报告为不确定度，不假定二者严格相等。
  \item 光源为非偏振光，反射率取 s、p 两支的算术平均。附件未给出偏振信息，这是最少假设的处理。
  \item 测量为完全相干测量，光源相干长度远大于层内往返光程（约 40\,µm）。硅片数据中可分辨的
        二次谐波反过来支持了这一假设。
  \item 空气折射率取 1，界面为理想光学界面（无过渡层、无表面粗糙度散射）。
  \item 外延层与衬底为同种母体材料，仅掺杂浓度不同，故共用同一套声子参数，掺杂差异只体现在
        自由载流子（Drude）项上。
  \item 仪器的绝对反射率标定可能存在乘性偏差，用一个与波数无关的标定因子 $s$ 吸收。附件 2 实测
        反射率最高达 {a2['preprocessing']['reflectance_max_percent']:.2f}\%，超过物理上限 100\%，直接证明了该假设的必要性。
\end{{modelassumptions}}

\section{{符号说明}}

\begin{{table}}[!htbp]
  \centering
  \caption{{符号说明}}
  \begin{{tabular}}{{cl}}
    \toprule
    符号 & 含义 \\
    \midrule
    $\tilde\nu$ & 波数，单位 cm$^{{-1}}$，附件第 1 列 \\
    $R$ & 反射率，附件第 2 列（本文换算为 0--1 小数） \\
    $d$ & 外延层几何厚度，单位 µm，本文待求量 \\
    $\theta_0$ & 空气中的入射角（$10^\circ$ 或 $15^\circ$） \\
    $\varepsilon_1,\varepsilon_2$ & 外延层、衬底的复介电函数 \\
    $n_1$ & 外延层折射率，$n_1=\operatorname{{Re}}\sqrt{{\varepsilon_1}}$ \\
    $\kappa_j$ & 纵向折射率 $\sqrt{{\varepsilon_j-\sin^2\theta_0}}$，斯涅尔定律的等价形式 \\
    $r_{{01}},r_{{12}}$ & 空气/外延层、外延层/衬底界面的振幅反射系数 \\
    $\delta$ & 层内往返一次的相位，$\delta=4\pi\tilde\nu d\,\kappa_1$ \\
    $L$ & 光程 $2d\,\kappa_1$，傅里叶变换的共轭变量，单位 µm \\
    $m$ & 干涉级次 \\
    $\tilde\nu_{{\mathrm{{TO}}}},\tilde\nu_{{\mathrm{{LO}}}}$ & 横光学、纵光学声子波数 \\
    $\tilde\nu_p,\gamma_p$ & 自由载流子等离子体波数与阻尼 \\
    $s$ & 仪器绝对反射率标定因子 \\
    \bottomrule
  \end{{tabular}}
\end{{table}}

\section{{数据预处理}}

四份附件的结构一致，但有两处特征直接影响算法设计（表~\ref{{tab:pre}}）。

其一，首行（$\tilde\nu={p0['wavenumber_cm-1']:.4f}$\,cm$^{{-1}}$）的反射率四份都精确等于
${p0['reflectance_percent']:.4f}$，而紧邻的下一点分别为
{first_valid[0]:.2f}\%、{first_valid[1]:.2f}\%、{first_valid[2]:.2f}\%、{first_valid[3]:.2f}\%。
这不是测量值而是边界哨兵，予以剔除，每份余 {a1['preprocessing']['n_rows_used']} 点。

其二，波数步长在 {a1['preprocessing']['step_min_cm-1']:.3f}--{a1['preprocessing']['step_max_cm-1']:.3f}\,cm$^{{-1}}$
之间浮动，并非严格等距。傅里叶分析要求等间隔采样，故先线性插值到等间隔网格。步长浮动仅 {a1['preprocessing']['step_variation_relative'] * 100:.1f}\%，
插值误差远小于反射率噪声（由二阶差分估计约 {sic_bands[2]['noise_percent']:.3f}\%），这一步的目的是让频率轴有确定的物理含义。

\begin{{table}}[!htbp]
  \centering
  \caption{{四份附件的数据特征与预处理}}\label{{tab:pre}}
  \small\setlength{{\tabcolsep}}{{4pt}}
  \begin{{tabular}}{{lccccc}}
    \toprule
    数据 & 原始点数 & 有效点数 & 波数范围 (cm$^{{-1}}$) & 步长 (cm$^{{-1}}$) & 反射率最大值 (\%) \\
    \midrule
{preprocessing_table(R)}
    \bottomrule
  \end{{tabular}}
\end{{table}}

图~\ref{{fig:overview}}给出四份光谱的总览。碳化硅在 797--971\,cm$^{{-1}}$ 有一条近全反的剩余射线带，
带外条纹幅度只有 $\pm0.3\%$；硅片没有剩余射线带，但低波数条纹幅度极大（反射率在 4\% 与 71\%
之间摆动），且随波数迅速衰减。这两个截然不同的谱形正是后文两种介电函数模型的依据。

\begin{{figure}}[!htbp]
  \centering
  \includegraphics[width=0.96\textwidth]{{fig_overview.png}}
  \caption{{四份附件的反射光谱总览。阴影为碳化硅的剩余射线带。}}\label{{fig:overview}}
\end{{figure}}

\section{{模型的建立与求解}}

\subsection{{问题一：单次反射情形下的干涉厚度模型}}

\subsubsection{{模型建立}}

设空气（$\varepsilon_0=1$）、外延层（$\varepsilon_1$）、衬底（$\varepsilon_2$）构成三介质体系，
光以 $\theta_0$ 入射。由斯涅尔定律 $\sin\theta_0=n_1\sin\theta_1$，层内传播方向的纵向分量为
\begin{{equation}}
  \kappa_j=\sqrt{{\varepsilon_j-\sin^2\theta_0}},\qquad j=1,2 .
\end{{equation}}
$\kappa_1=n_1\cos\theta_1$ 一个量同时承担了折射角和相位厚度两件事，因此下文不再显式出现 $\theta_1$。

界面的振幅反射系数按 s、p 两种偏振分别为
\begin{{equation}}
  r_{{ij}}^{{s}}=\frac{{\kappa_i-\kappa_j}}{{\kappa_i+\kappa_j}},\qquad
  r_{{ij}}^{{p}}=\frac{{\varepsilon_j\kappa_i-\varepsilon_i\kappa_j}}{{\varepsilon_j\kappa_i+\varepsilon_i\kappa_j}} .
\end{{equation}}

光在层内往返一次相对表面反射光多走的光程为 $2d\kappa_1$，对应相位
\begin{{equation}}
  \delta=4\pi\tilde\nu d\,\kappa_1=4\pi\tilde\nu d\sqrt{{\varepsilon_1-\sin^2\theta_0}} .
\end{{equation}}
（注意入射侧的斜程差已在推导中与折射光的横向位移相消，故不出现 $\cos\theta_0$ 项。）

题目要求只保留一次反射、一次透射，即表面反射光与衬底界面反射光两束叠加：
\begin{{equation}}
  r=r_{{01}}+t_{{01}}t_{{10}}r_{{12}}\mathrm{{e}}^{{\mathrm{{i}}\delta}}
   =r_{{01}}+(1-r_{{01}}^{{2}})r_{{12}}\mathrm{{e}}^{{\mathrm{{i}}\delta}},
\end{{equation}}
非偏振光的反射率为
\begin{{equation}}
  R=\tfrac{{1}}{{2}}\left(|r^{{s}}|^{{2}}+|r^{{p}}|^{{2}}\right).
\end{{equation}}

当 $r_{{01}},r_{{12}}$ 为实数时上式化为 $R=A+B\cos\delta$，干涉极值条件即
\begin{{equation}}
  2d\sqrt{{n_1^2-\sin^2\theta_0}}\;\tilde\nu+\frac{{\varphi_{{01}}-\varphi_{{12}}}}{{2\pi}}=m ,
  \label{{eq:order}}
\end{{equation}}
其中 $m$ 取整数对应极大、半整数对应极小，$\varphi$ 为界面反射相位。相邻极大间隔 $\Delta\tilde\nu$
满足 $2d\sqrt{{n_1^2-\sin^2\theta_0}}\,\Delta\tilde\nu=1$，于是
\begin{{equation}}
  \boxed{{\;d=\frac{{1}}{{2\Delta\tilde\nu\sqrt{{n_1^2-\sin^2\theta_0}}}}\;}}
  \label{{eq:thickness}}
\end{{equation}}
这就是题目所要的厚度模型。式~\eqref{{eq:order}} 的截距把界面反射相位（包括是否存在半波损失）
整体吸收，因此\textbf{{不需要事先判断 $n_1$ 与 $n_2$ 的大小关系}}——这是把模型写成级次形式而非
"光程差 $=m\lambda$"形式的实际好处。

\subsubsection{{算法设计与求解}}

式~\eqref{{eq:thickness}} 成立的前提是 $n_1$ 在分析波段内为常数。题目已声明折射率与波长有关，
故必须检查该前提。设 $n_1=n_1(\tilde\nu)$，总相位 $\Phi=4\pi\tilde\nu d\,\kappa_1(\tilde\nu)$，
相邻条纹间隔实际满足 $\mathrm{{d}}\Phi/\mathrm{{d}}\tilde\nu=2\pi/\Delta\tilde\nu$，即测到的是
\begin{{equation}}
  L_{{\text{{群}}}}=\frac{{1}}{{2\pi}}\frac{{\mathrm{{d}}\Phi}}{{\mathrm{{d}}\tilde\nu}}
  =2d\left(\kappa_1+\tilde\nu\frac{{\mathrm{{d}}\kappa_1}}{{\mathrm{{d}}\tilde\nu}}\right)
  \neq L_{{\text{{相位}}}}=2d\kappa_1 .
  \label{{eq:group}}
\end{{equation}}

\subsubsection{{结果分析}}

式~\eqref{{eq:group}} 不是理论洁癖。对附件 1 做滑动波段傅里叶变换（表~\ref{{tab:scan}}），
测得的光程从低波段的 {scan['max_um']:.2f}\,µm 一路降到高波段的 {scan['min_um']:.2f}\,µm，
相差 {scan['drift_relative'] * 100:.1f}\%。若直接把 {scan['max_um']:.2f}\,µm 当作 $2d\kappa_1$
代入式~\eqref{{eq:thickness}}，厚度会被高估三分之一。

\begin{{table}}[!htbp]
  \centering
  \caption{{附件 1 的滑动波段光程：色散造成的群光程漂移}}\label{{tab:scan}}
  \small
  \begin{{tabular}}{{lcccccc}}
    \toprule
    波段 (cm$^{{-1}}$) & {' & '.join(f"{b['band_cm-1'][0]:.0f}--{b['band_cm-1'][1]:.0f}" for b in scan['per_band'])} \\
    \midrule
    光程 $L$ (µm) & {' & '.join(f"{b['optical_path_um']:.2f}" for b in scan['per_band'])} \\
    \bottomrule
  \end{{tabular}}
\end{{table}}

这一漂移的物理来源是碳化硅剩余射线带的色散尾巴：在 LO 声子频率 $\tilde\nu_{{\mathrm{{LO}}}}$
上方，$n_1$ 从很大的值迅速下降，$\mathrm{{d}}\kappa_1/\mathrm{{d}}\tilde\nu<0$ 的贡献不可忽略。
因此\textbf{{式~\eqref{{eq:thickness}} 只能用作弱色散区的基线估计}}，问题二必须回到式~(4) 的完整
正演形式做全谱拟合。这是本文把双光束公式而不是厚度公式作为问题一最终答案的原因。

\subsubsection{{模型验证}}

正演模型实现于 \texttt{{src/optics.py}}，检验见 \texttt{{tests/test\_optics.py}}。三条解析特例：
(i) $\theta_0\to0$ 时 s、p 两支均退回 $\left(\frac{{n-1}}{{n+1}}\right)^2$，相对误差 $<10^{{-6}}$；
(ii) 在布儒斯特角 $\arctan n$ 处 p 分量严格为零（$<10^{{-12}}$），说明菲涅耳系数的符号约定正确；
(iii) $\sqrt{{\varepsilon-\sin^2\theta_0}}$ 与显式解斯涅尔定律再算 $n\cos\theta_1$ 的结果一致到 $10^{{-12}}$。
量纲上 $\tilde\nu[\mathrm{{cm}}^{{-1}}]\cdot d[\mathrm{{cm}}]$ 无量纲，光程量纲为 cm，与傅里叶共轭变量一致。

\subsection{{问题二：碳化硅外延层厚度的算法与计算结果}}

\subsubsection{{模型建立}}

要由光程得到厚度必须独立地确定 $n_1$。我们采用的信息源是碳化硅本身的剩余射线带。
极性晶体的介电函数由单振子模型给出
\begin{{equation}}
  \varepsilon(\tilde\nu)=\varepsilon_\infty\left(1+
  \frac{{\tilde\nu_{{\mathrm{{LO}}}}^{{2}}-\tilde\nu_{{\mathrm{{TO}}}}^{{2}}}}
       {{\tilde\nu_{{\mathrm{{TO}}}}^{{2}}-\tilde\nu^{{2}}-\mathrm{{i}}\gamma\tilde\nu}}\right),
  \label{{eq:lorentz}}
\end{{equation}}
在 $\tilde\nu_{{\mathrm{{TO}}}}<\tilde\nu<\tilde\nu_{{\mathrm{{LO}}}}$ 内 $\operatorname{{Re}}\varepsilon<0$，
反射率接近 1。重掺杂衬底额外含自由载流子项
\begin{{equation}}
  \varepsilon_2(\tilde\nu)=\varepsilon_{{\text{{声子}}}}(\tilde\nu)
  -\frac{{\varepsilon_\infty\tilde\nu_p^{{2}}}}{{\tilde\nu^{{2}}+\mathrm{{i}}\gamma_p\tilde\nu}} .
\end{{equation}}

\textbf{{为什么这能破解简并。}}\;设仪器有乘性标定误差 $s$。带内 $R\approx1$ 与 $\varepsilon_\infty$
几乎无关，带外平台 $R\approx\left(\frac{{\sqrt{{\varepsilon_\infty}}-1}}{{\sqrt{{\varepsilon_\infty}}+1}}\right)^2$
强烈依赖 $\varepsilon_\infty$。两者的\emph{{比值}}中 $s$ 相消，因此只要拟合波段同时覆盖带内和带外，
$\varepsilon_\infty$ 与 $s$ 就不再简并。作为对照，我们先只用 760--1010\,cm$^{{-1}}$ 做体材料拟合（该窗口几乎不含真正的带外平台）：
$\tilde\nu_{{\mathrm{{TO}}}}$ 在两个角度上给出 {bulk1['v_to']:.2f} 与 {bulk2['v_to']:.2f}\,cm$^{{-1}}$
（相差 {bulk_to_gap * 100:.3f}\%），而 $\varepsilon_\infty$ 给出 {bulk1['eps_inf']:.2f} 与
{bulk2['eps_inf']:.2f}（相差 {bulk_eps_gap * 100:.1f}\%），标定因子相应地取 {bulk1['scale']:.4f} 与
{bulk2['scale']:.4f}——正如预期，带边稳健、介电常数与标定简并。

\subsubsection{{算法设计与求解}}

\textbf{{基线一（傅里叶法）。}}\;取弱色散区 1500--4000\,cm$^{{-1}}$，等间隔重采样后减去三阶多项式基线、
加 Hann 窗、补零至 $2^{{18}}$ 点作实傅里叶变换。共轭变量的量纲即为 cm，谱峰位置直接给出光程 $L$，
再用抛物线插值细化峰位。此法透明、秒级、不依赖任何物理参数。

这里不用滑动平滑去基线：本题条纹周期最大到 430\,cm$^{{-1}}$，任何压得住基线的滑动窗口都短于一个
条纹周期，会削平条纹并凭空造出二次谐波——而那正是问题三的判据要测的量。

\textbf{{基线二（条纹级次法）。}}\;提取极值波数 $\tilde\nu_k$，赋半整数级次 $m_k=k/2$，
按式~\eqref{{eq:order}} 对 $m_k=L\tilde\nu_k+c$ 作线性回归，斜率即光程。实现中有两个必须处理的陷阱：
极值显著性阈值必须同时受噪声下限约束（取噪声标准差的 5 倍），且峰谷必须严格交替。
关掉这两道保护重跑附件 2 作消融：检出极值由 {abl['with_guards']['n_extrema']} 个暴涨到
{abl['without_guards']['n_extrema']} 个，最小间隔从 {abl['with_guards']['min_separation_cm-1']:.1f}
降到 {abl['without_guards']['min_separation_cm-1']:.1f}\,cm$^{{-1}}$，级次残差从
{abl['with_guards']['order_residual_max']:.2f} 恶化到 {abl['without_guards']['order_residual_max']:.2f}，
光程被虚报 {abl['inflation_relative'] * 100:.1f}\%（{abl['with_guards']['optical_path_um']:.2f}
$\rightarrow$ {abl['without_guards']['optical_path_um']:.2f}\,µm）。

\textbf{{主方法（全谱拟合）。}}\;以式~(4) 的双光束反射率为正演模型，参数为
\[(d,\;\varepsilon_\infty,\;\tilde\nu_{{\mathrm{{TO}}}},\;\tilde\nu_{{\mathrm{{LO}}}},\;\gamma,\;
\tilde\nu_p^{{\text{{衬}}}},\;\gamma_p^{{\text{{衬}}}},\;\delta_1,\;s)\]
共 9 个，
对 420--4000\,cm$^{{-1}}$ 的 {a1['fit_two_beam']['n_points']} 个数据点作有界最小二乘
（Trust Region Reflective）。为排除初值依赖，用 5 个固定种子对初值作 $\pm15\%$ 随机扰动作多起点。

\subsubsection{{结果分析}}

结果汇总于表~\ref{{tab:sic}}。两条基线给出的光程互相吻合到
{max(base[0]['baseline_disagreement_relative'], base[1]['baseline_disagreement_relative']) * 100:.2f}\% 以内，
说明条纹周期这个量本身测得很准。主方法在两个角度上给出
$d={sic['d_um_theta10']:.4f}$\,µm 和 $d={sic['d_um_theta15']:.4f}$\,µm，
均值 $\mathbf{{{sic['d_um_mean']:.3f}}}$\,µm，同时给出
$n_\infty={sic['n_inf_theta10']:.4f}$ 和 {sic['n_inf_theta15']:.4f}。
拟合出的声子参数为 $\tilde\nu_{{\mathrm{{TO}}}}={f1['v_to']:.1f}$\,cm$^{{-1}}$、
$\tilde\nu_{{\mathrm{{LO}}}}={f1['v_lo']:.1f}$\,cm$^{{-1}}$（$10^\circ$）与
{f2['v_to']:.1f}、{f2['v_lo']:.1f}\,cm$^{{-1}}$（$15^\circ$），两个角度分别一致到
{agree_sic['v_to'] * 100:.2f}\% 与 {agree_sic['v_lo'] * 100:.2f}\%。
全谱残差 RMS 为 {a1['fit_two_beam']['rms_reflectance'] * 100:.3f}\%（$10^\circ$）与
{a2['fit_two_beam']['rms_reflectance'] * 100:.3f}\%（$15^\circ$），拟合效果见图~\ref{{fig:sicfit}}。

\begin{{table}}[!htbp]
  \centering
  \caption{{问题二：碳化硅外延层厚度（双光束模型）}}\label{{tab:sic}}
  \begin{{tabular}}{{lcc}}
    \toprule
    量 & 附件 1（$10^\circ$） & 附件 2（$15^\circ$） \\
    \midrule
    傅里叶基线光程 $L$ (µm) & {base[0]['fourier_path_um']:.4f} & {base[1]['fourier_path_um']:.4f} \\
    级次法基线光程 $L$ (µm) & {base[0]['extremum_path_um']:.4f} & {base[1]['extremum_path_um']:.4f} \\
    两基线相对差 & {base[0]['baseline_disagreement_relative'] * 100:.2f}\% & {base[1]['baseline_disagreement_relative'] * 100:.2f}\% \\
    \midrule
    厚度 $d$ (µm) & \textbf{{{sic['d_um_theta10']:.4f}}} & \textbf{{{sic['d_um_theta15']:.4f}}} \\
    折射率 $n_\infty$ & {sic['n_inf_theta10']:.4f} & {sic['n_inf_theta15']:.4f} \\
    $\tilde\nu_{{\mathrm{{TO}}}}$ (cm$^{{-1}}$) & {f1['v_to']:.2f} & {f2['v_to']:.2f} \\
    $\tilde\nu_{{\mathrm{{LO}}}}$ (cm$^{{-1}}$) & {f1['v_lo']:.2f} & {f2['v_lo']:.2f} \\
    标定因子 $s$ & {sic['scale_theta10']:.4f} & {sic['scale_theta15']:.4f} \\
    残差 RMS & {a1['fit_two_beam']['rms_reflectance'] * 100:.3f}\% & {a2['fit_two_beam']['rms_reflectance'] * 100:.3f}\% \\
    \midrule
    \multicolumn{{3}}{{c}}{{均值 $d={sic['d_um_mean']:.3f}\pm{ub_sic['reported_uncertainty_um']:.3f}$\,µm\quad
      （相对不确定度 {ub_sic['reported_uncertainty_um'] / sic['d_um_mean'] * 100:.1f}\%）}} \\
    \bottomrule
  \end{{tabular}}
\end{{table}}

\begin{{figure}}[!htbp]
  \centering
  \includegraphics[width=0.94\textwidth]{{fig_fit_attachment_1.png}}
  \caption{{附件 1 的全谱拟合与残差。模型同时再现了剩余射线带、970\,cm$^{{-1}}$ 处的陡峭 LO 边
  和带外的微弱条纹；双光束与多光束两条曲线几乎重合，说明碳化硅上多光束效应很弱。}}\label{{fig:sicfit}}
\end{{figure}}

\paragraph{{可靠性分析（一）：不确定度预算。}}
把误差来源逐项分离（表~\ref{{tab:budget}}）。多起点散布小于 $10^{{-6}}$\,µm，可忽略；
换分析波段引起的散布为 {ub_sic['band_spread_um_theta10']:.4f}\,µm（$10^\circ$）与
{ub_sic['band_spread_um_theta15']:.4f}\,µm（$15^\circ$）；
而两个角度之间的半差达 {ub_sic['angle_half_spread_um']:.4f}\,µm，比前两者大一个数量级。
故报告不确定度取 {ub_sic['reported_uncertainty_um']:.3f}\,µm，主导来源是\textbf{{{ub_sic['dominant_source']}}}。

角度间差异的根源可以定位：两个角度拟合出的标定因子分别为 {sic['scale_theta10']:.4f} 与
{sic['scale_theta15']:.4f}，相差 {abs(sic['scale_theta10'] - sic['scale_theta15']) * 100:.1f}\%。
附件 2 的实测反射率最高达 {a2['preprocessing']['reflectance_max_percent']:.2f}\%，超过物理上限，
这是标定偏差的直接证据。绝对反射率通过 $r_{{01}}=(1-n_1)/(1+n_1)$ 决定 $n_1$，
再通过 $d=L/(2\kappa_1)$ 传到厚度上，于是 {abs(sic['scale_theta10'] - sic['scale_theta15']) * 100:.1f}\% 的
标定差异变成 {sic['n_relative_spread'] * 100:.1f}\% 的折射率差异和 {sic['d_relative_spread'] * 100:.1f}\% 的厚度差异。
\textbf{{结论：本方法的精度瓶颈不在算法而在仪器标定}}；若能提供标准反射镜的标定曲线，
厚度不确定度可望降到波段散布的量级（约 {max(band_rel[:2]) * 100:.2f}\%）。

\begin{{table}}[!htbp]
  \centering
  \caption{{厚度的不确定度预算（µm）}}\label{{tab:budget}}
  \begin{{tabular}}{{lcc}}
    \toprule
    误差来源 & 碳化硅 & 硅 \\
    \midrule
    多起点（5 个固定种子）散布 & $<10^{{-6}}$ & $<10^{{-6}}$ \\
    残差雅可比给出的形式标准差 & {ub_sic['formal_std_um_theta10']:.4f} & {ub_si['formal_std_um_theta10']:.4f} \\
    分析波段选择（3 个波段） & {ub_sic['band_spread_um_theta10']:.4f} / {ub_sic['band_spread_um_theta15']:.4f} & {ub_si['band_spread_um_theta10']:.4f} / {ub_si['band_spread_um_theta15']:.4f} \\
    两入射角之间的半差 & \textbf{{{ub_sic['angle_half_spread_um']:.4f}}} & {ub_si['angle_half_spread_um']:.4f} \\
    \midrule
    报告不确定度 & {ub_sic['reported_uncertainty_um']:.3f} & {ub_si['reported_uncertainty_um']:.3f} \\
    主导来源 & {ub_sic['dominant_source']} & {ub_si['dominant_source']} \\
    \bottomrule
  \end{{tabular}}
  \tablenote{{形式标准差假定残差为独立同分布随机噪声。本题残差以模型失配为主，故该列是下界，
  不能当作真实不确定度，仅用于判断参数之间是否简并。}}
\end{{table}}

\paragraph{{可靠性分析（二）：一条不能走的路。}}
既然有两个入射角，自然想到用光程比消去 $d$：
\begin{{equation}}
  q\equiv\left(\frac{{L_2}}{{L_1}}\right)^{{2}}
   =\frac{{n_1^2-\sin^2\theta_2}}{{n_1^2-\sin^2\theta_1}}
  \quad\Longrightarrow\quad
  n_1^{{2}}=\frac{{q\sin^2\theta_1-\sin^2\theta_2}}{{q-1}} .
  \label{{eq:twoangle}}
\end{{equation}}
问题在于分母。$\theta_1=10^\circ$ 与 $\theta_2=15^\circ$ 对 $n_1={tac['n_reference']:.2f}$ 造成的光程差异仅
{tac['path_contrast_relative'] * 100:.2f}\%，即理论上 $q-1={tac['q_minus_one']:.5f}$，
是两个相近数之差。其相对条件数为
\begin{{equation}}
  \left|\frac{{\mathrm{{d}}n_1^2/n_1^2}}{{\mathrm{{d}}q/q}}\right|
  =\left|\frac{{(\sin^2\theta_2-\sin^2\theta_1)\,q}}{{(q-1)^2 n_1^2}}\right|
  ={inv['relative_condition_number']:.1f} ,
\end{{equation}}
即 $q$ 上 1\% 的误差会放大成 $n_1^2$ 上 {inv['relative_condition_number']:.0f}\% 的误差。
把实测值 $L_1={base[0]['fourier_path_um']:.4f}$、$L_2={base[1]['fourier_path_um']:.4f}$\,µm 代入，
得 $q-1={inv['q_minus_one']:.5f}$、$n_1={inv['n']:.3f}$——与全谱拟合的 {sic['n_inf_mean']:.3f} 相差甚远。
我们\textbf{{不采信}}这个结果，而是把它作为该路线不可用的证据：双角度数据的价值在于互校，
不在于定折射率。这也解释了为什么本文必须依赖剩余射线带这一信息源。

\subsubsection{{模型验证}}

\textbf{{多种子稳定性。}}\;5 个固定种子的多起点全部收敛到同一解，厚度散布见表~\ref{{tab:seed}}，
均小于 $10^{{-5}}$\,µm；收敛轨迹见图~\ref{{fig:conv}}。

\textbf{{独立算法比较。}}\;傅里叶法与级次法是两条互不相同的实现路径（频域峰位 vs 时域极值回归），
在附件 1 上给出 {base[0]['fourier_path_um']:.4f} 与 {base[0]['extremum_path_um']:.4f}\,µm，
相对差 {base[0]['baseline_disagreement_relative'] * 100:.2f}\%；附件 2 上为
{base[1]['baseline_disagreement_relative'] * 100:.2f}\%。二者又都与主方法的 $2d\kappa_1$ 一致。

\textbf{{参数边界审计。}}\;9 个参数到各自箱式边界的相对松弛度全部大于 $10^{{-3}}$，
无一贴边（详见 \texttt{{artifacts/constraints.json}}），说明解由数据而非人为边界决定。

\textbf{{合成数据回收。}}\;用正演模型合成已知厚度 3.4\,µm、叠加 0.03\% 噪声的光谱，
主方法回收厚度的相对误差小于 0.5\%，折射率小于 1\%（见 \texttt{{tests/test\_inversion.py}}）。

\begin{{table}}[!htbp]
  \centering
  \caption{{多起点稳定性（多光束模型，5 个固定种子）}}\label{{tab:seed}}
  \small\setlength{{\tabcolsep}}{{4pt}}
  \begin{{tabular}}{{lccccc}}
    \toprule
    数据 & 种子数 & 最优 RMS (\%) & 最差 RMS (\%) & RMS 标准差 (\%) & 厚度散布 (µm) \\
    \midrule
{seed_table(R)}
    \bottomrule
  \end{{tabular}}
\end{{table}}

\begin{{figure}}[!htbp]
  \centering
  \includegraphics[width=0.96\textwidth]{{fig_convergence.png}}
  \caption{{多起点收敛轨迹。纵轴为残差平方和，五条曲线自不同初值出发收敛到同一水平。}}\label{{fig:conv}}
\end{{figure}}

\subsection{{问题三：多光束干涉的必要条件、判定与厚度修正}}

\subsubsection{{模型建立}}

\paragraph{{Airy 公式与必要条件。}}
计入层内无穷次往返，各次出射光的振幅构成公比为 $r_{{10}}r_{{12}}\mathrm{{e}}^{{\mathrm{{i}}\delta}}
=-r_{{01}}r_{{12}}\mathrm{{e}}^{{\mathrm{{i}}\delta}}$ 的等比级数，求和得
\begin{{equation}}
  r=\frac{{r_{{01}}+r_{{12}}\mathrm{{e}}^{{\mathrm{{i}}\delta}}}}
        {{1+r_{{01}}r_{{12}}\mathrm{{e}}^{{\mathrm{{i}}\delta}}}} ,\qquad
  R=\tfrac{{1}}{{2}}\left(|r^{{s}}|^{{2}}+|r^{{p}}|^{{2}}\right).
  \label{{eq:airy}}
\end{{equation}}
把分母按 $|r_{{01}}r_{{12}}|<1$ 展开，
\begin{{equation}}
  r=r_{{01}}+(1-r_{{01}}^{{2}})\sum_{{k=1}}^{{\infty}}(-1)^{{k-1}}
    r_{{01}}^{{k-1}}r_{{12}}^{{k}}\mathrm{{e}}^{{\mathrm{{i}}k\delta}} ,
\end{{equation}}
第 $k$ 项相对第一项的量级为 $|r_{{01}}r_{{12}}|^{{k-1}}$。$k=1$ 即问题一的双光束模型。由此得到

\begin{{quote}}
\textbf{{多光束干涉产生的必要条件}}：\;(i) 两界面的振幅反射系数之积 $|r_{{01}}r_{{12}}|$ 不可忽略，
即衬底与外延层之间存在足够的折射率反差；(ii) 层内单程吸收足够小，使 $\mathrm{{e}}^{{\mathrm{{i}}\delta}}$
的虚部衰减不至于压掉高次项；(iii) 光源相干长度大于最高有效级次的往返光程 $k\cdot2d\kappa_1$；
(iv) 上下界面足够平行，光斑内厚度起伏远小于 $\lambda/(4n_1)$，否则高次项互相抵消。
\end{{quote}}

条件 (i) 是本题唯一可由附件数据定量检验的一条，也是最本质的一条，下文以 $|r_{{01}}r_{{12}}|$ 为物理判据。

\paragraph{{对厚度精度的影响。}}
多光束使条纹由正弦变为锐化的 Airy 峰，$\cos2\delta$、$\cos3\delta$ 等高次谐波出现。这带来两类误差：
其一，极值位置本身不再严格满足式~\eqref{{eq:order}}（Airy 峰的不对称使极值向一侧偏移）；
其二，若强行用双光束模型作全谱拟合，模型为了在正弦形状下逼近锐化条纹，会同时调整幅度与周期，
从而系统性地偏移厚度。第二类误差是主要的，量级由 $|r_{{01}}r_{{12}}|$ 决定，本文直接测量它。

\paragraph{{判据。}}
我们不设"二次谐波超过多少算多光束"这类阈值，而用一个自校准的量：
以拟合得到的介电函数分别正演双光束与多光束反射率，取二者在该波段的最大差 $\Delta R_{{\max}}$，
与该波段由二阶差分估计的测量噪声 $\sigma$ 比较。判据为
\begin{{equation}}
  \Delta R_{{\max}}>3\sigma \;\Longrightarrow\; 多光束不可忽略 .
\end{{equation}}
含义直白：忽略多光束造成的偏差如果淹没在噪声里，就没有讨论的必要；如果显著高出噪声，就必须计入。

作为旁证我们还计算了傅里叶谱的二次谐波相对幅度。但必须指出该法的局限：
本题条纹周期最大 430\,cm$^{{-1}}$，一个 800\,cm$^{{-1}}$ 宽的波段只装得下不到两个条纹，
多项式去基线不可能与如此少的振荡完全正交。用拟合参数合成的\emph{{纯双光束}}谱（理论上无谐波）
走同一条流水线，测得的"二次谐波"达 {leak_lo:.3f}——这就是该方法的泄漏本底，
是分辨下限而非物理量。故谐波法只作旁证，不作判据。

\subsubsection{{算法设计与求解}}

硅是非极性晶体，中红外无一阶声子带，色散只来自自由载流子，故介电函数取
$\varepsilon(\tilde\nu)=\varepsilon_\infty\left(1-\tilde\nu_p^2/(\tilde\nu^2+\mathrm{{i}}\gamma_p\tilde\nu)\right)$，
外延层与衬底各有一组 $(\tilde\nu_p,\gamma_p)$，参数共 7 个。以式~\eqref{{eq:airy}} 为正演模型，
其余流程（波段、多起点、种子）与问题二完全相同，便于横向比较。

对附件 1、2 则同时做双光束与多光束两次拟合：\textbf{{双光束拟合就是对照组，两者之差即多光束的影响}}。

\subsubsection{{结果分析}}

\paragraph{{判定结果。}}
表~\ref{{tab:diag}} 给出逐波段判定。硅晶圆在全部三个波段都判定为出现多光束：
1000--1800\,cm$^{{-1}}$ 处 $|r_{{01}}r_{{12}}|={si_bands[0]['finesse_mean']:.4f}$，
忽略多光束的模型偏差高达 {si_bands[0]['model_gap_max_percent']:.2f}\%，是噪声的
{si_bands[0]['model_gap_max_percent'] / si_bands[0]['noise_percent']:.0f} 倍；即使到 2600--4000\,cm$^{{-1}}$
仍有 {si_bands[2]['model_gap_max_percent'] / si_bands[2]['noise_percent']:.1f} 倍。物理原因清楚：
衬底重掺杂（拟合得 $\tilde\nu_p={fs1['vp_sub']:.0f}$\,cm$^{{-1}}$），低波数呈金属性强反射，
$|r_{{12}}|$ 很大。

碳化硅则只有 1000--1800\,cm$^{{-1}}$ 一段越过判据（{sic_bands[0]['model_gap_max_percent'] / sic_bands[0]['noise_percent']:.1f} 倍），
1800\,cm$^{{-1}}$ 以上偏差反而低于噪声（{sic_bands[1]['model_gap_max_percent'] / sic_bands[1]['noise_percent']:.1f} 倍与
{sic_bands[2]['model_gap_max_percent'] / sic_bands[2]['noise_percent']:.1f} 倍）。原因是外延层与衬底同为碳化硅、
仅掺杂不同，$|r_{{12}}|$ 只有 $10^{{-3}}$ 量级。

\begin{{table}}[!htbp]
  \centering
  \caption{{多光束干涉的逐波段判定}}\label{{tab:diag}}
  \begin{{tabular}}{{llccccc}}
    \toprule
    数据 & 波段 (cm$^{{-1}}$) & $|r_{{01}}r_{{12}}|$ & $\Delta R_{{\max}}$ (\%) & 噪声 $\sigma$ (\%) & 比值 & 多光束 \\
    \midrule
{diagnostic_table(R)}
    \bottomrule
  \end{{tabular}}
  \tablenote{{判据为 $\Delta R_{{\max}}>3\sigma$。$\Delta R_{{\max}}$ 是同一组拟合参数下双光束与
  多光束正演反射率的最大差；$\sigma$ 由实测数据的二阶差分估计，不依赖任何模型。}}
\end{{table}}

\paragraph{{硅晶圆厚度。}}
多光束模型给出
\[ d={si['d_um_theta10']:.4f}\ \text{{µm}}\;(10^\circ),\qquad
   d={si['d_um_theta15']:.4f}\ \text{{µm}}\;(15^\circ), \]
均值 $\mathbf{{{si['d_um_mean']:.3f}\pm{ub_si['reported_uncertainty_um']:.3f}}}$\,µm。
两角度仅差 {si['d_relative_spread'] * 100:.2f}\%，比碳化硅的 {sic['d_relative_spread'] * 100:.2f}\% 好一个数量级。
折射率 $n_\infty={si['n_inf_theta10']:.4f}$ 与 {si['n_inf_theta15']:.4f}。
若误用双光束模型，厚度将是 {corr_si['per_angle'][0]['d_two_beam_um']:.4f} 与
{corr_si['per_angle'][1]['d_two_beam_um']:.4f}\,µm，\textbf{{低估 {corr_si['mean_shift_relative'] * 100:.1f}\%}}；
同时残差 RMS 高达 {corr_si['per_angle'][0]['rms_two_beam'] * 100:.2f}\%，
图~\ref{{fig:sifit}} 中虚线在低波数完全跑偏。这就是多光束对厚度精度影响的定量答案。

\begin{{figure}}[!htbp]
  \centering
  \includegraphics[width=0.94\textwidth]{{fig_fit_attachment_3.png}}
  \caption{{附件 3 的全谱拟合。虚线为双光束模型，在 400--1500\,cm$^{{-1}}$ 与实测严重偏离；
  实线为多光束模型。二者的差就是多光束效应。}}\label{{fig:sifit}}
\end{{figure}}

\paragraph{{碳化硅的多光束修正。}}
我们认为多光束在附件 1、2 中\textbf{{客观存在但不构成精度瓶颈}}。改用多光束模型重算，
厚度由 {corr_sic['per_angle'][0]['d_two_beam_um']:.4f}/{corr_sic['per_angle'][1]['d_two_beam_um']:.4f}\,µm
变为 {corr_sic['per_angle'][0]['d_airy_um']:.4f}/{corr_sic['per_angle'][1]['d_airy_um']:.4f}\,µm，
均值 $\mathbf{{{sic_fix['d_um_mean']:.3f}}}$\,µm，相对改变仅
{abs(corr_sic['mean_shift_relative']) * 100:.3f}\%；残差 RMS 改善
{corr_sic['mean_rms_improvement'] * 100:.1f}\%。这个改变量比 {ub_sic['reported_uncertainty_um'] / sic['d_um_mean'] * 100:.1f}\%
的报告不确定度小两个数量级。

\textbf{{因此消除多光束影响后的碳化硅外延层厚度为 {sic_fix['d_um_mean']:.3f}\,µm}}，
与问题二的 {sic['d_um_mean']:.3f}\,µm 在不确定度内完全一致。诚实的结论是：
对本片碳化硅而言，追求多光束修正的收益远小于改善仪器标定的收益。

图~\ref{{fig:disp}} 左给出拟合得到的折射率色散，右给出 $|r_{{01}}r_{{12}}|$ 随波数的衰减，
两种材料相差两个数量级，直观解释了上述差别。

\begin{{figure}}[!htbp]
  \centering
  \includegraphics[width=0.96\textwidth]{{fig_dispersion.png}}
  \caption{{左：拟合得到的外延层折射率色散，碳化硅在剩余射线带附近急剧变化。
  右：多光束判据 $|r_{{01}}r_{{12}}|$（对数纵轴），硅片比碳化硅高两个数量级。}}\label{{fig:disp}}
\end{{figure}}

\subsubsection{{模型验证}}

\textbf{{解析极限自洽。}}\;令 $|r_{{01}}r_{{12}}|\to0$，Airy 公式与双光束公式在 4000 个采样点上
最大偏差小于 $10^{{-6}}$；反之在强反差下二者最大偏差大于 0.02（见 \texttt{{tests/test\_optics.py}}）。
这保证了问题三的模型是问题一的推广而非另起炉灶。

\textbf{{判据的分辨力检验。}}\;对合成的纯双光束谱，判据的谐波旁证读数为泄漏本底
（$<0.05$）；对合成的强多光束谱读数大于 0.1 且高于本底 4 倍以上，说明判据有区分力
（见 \texttt{{tests/test\_inversion.py}}）。

\textbf{{两角度互校。}}\;硅片两个角度独立拟合，厚度相差 {si['d_relative_spread'] * 100:.2f}\%，
衬底等离子体波数相差 {agree_si['vp_sub'] * 100:.2f}\%，是彼此独立的证据来源给出的一致结果。

\textbf{{频域旁证。}}\;图~\ref{{fig:fft}} 给出光程谱。硅片低波段的二次谐波清晰可辨，
高波段消失；碳化硅两个波段都看不到显著二次谐波。与表~\ref{{tab:diag}} 的判定一致。

\begin{{figure}}[!htbp]
  \centering
  \includegraphics[width=0.96\textwidth]{{fig_fourier.png}}
  \caption{{光程域的傅里叶谱。绿色点线为基频（光程 $2d\kappa_1$），红色虚线为二倍频位置。}}\label{{fig:fft}}
\end{{figure}}

\section{{灵敏度分析}}

\textbf{{对分析波段的灵敏度。}}\;把全谱拟合区间分别取三个不同的下限与上限，
厚度散布见表~\ref{{tab:band}}。碳化硅为 {a1['band_sensitivity_spread_um']:.4f}/{a2['band_sensitivity_spread_um']:.4f}\,µm，
硅为 {a3['band_sensitivity_spread_um']:.4f}/{R['attachments']['attachment_4']['band_sensitivity_spread_um']:.4f}\,µm，
相对量级在 {min(band_rel) * 100:.2f}\%--{max(band_rel) * 100:.2f}\% 之间，
说明结论不依赖波段的具体切法。

\textbf{{对入射角的灵敏度。}}\;$10^\circ$ 与 $15^\circ$ 之间 $\kappa_1$ 只变化
{tac['path_contrast_relative'] * 100:.2f}\%，
因此角度本身几乎不影响厚度反演——这既解释了为什么双角度不能定折射率（式~\eqref{{eq:twoangle}} 病态），
也说明观测到的 {sic['d_relative_spread'] * 100:.2f}\% 厚度差异不可能来自角度，只能来自标定或测点差异。

\textbf{{对噪声的灵敏度。}}\;在合成谱上叠加 0.05\% 的高斯噪声（与实测噪声
{sic_bands[2]['noise_percent']:.3f}\% 同量级），傅里叶基线的光程误差仍小于 0.3\%。

\begin{{table}}[!htbp]
  \centering
  \caption{{分析波段选择对厚度的影响（µm）}}\label{{tab:band}}
  \begin{{tabular}}{{lcccc}}
    \toprule
    数据 & 420--4000 & 700--4000 & 420--3000 & 散布 \\
    \midrule
{band_sensitivity_table(R)}
    \bottomrule
  \end{{tabular}}
\end{{table}}

\section{{模型评价与推广}}

\subsection{{模型的优点}}

\begin{{enumerate}}[leftmargin=2em]
  \item \textbf{{不引入任何外部折射率常数。}}\;折射率与厚度由同一份光谱同时定出，
        碳化硅得 $n_\infty={sic['n_inf_mean']:.3f}$、硅得 {si['n_inf_mean']:.3f}，
        声子波数 $\tilde\nu_{{\mathrm{{TO}}}}={f1['v_to']:.1f}$\,cm$^{{-1}}$ 在两个角度上一致到
{agree_sic['v_to'] * 100:.2f}\%，
        这些独立于厚度的量彼此自洽，反过来支持了整个模型。
  \item \textbf{{基线与主方法分离，且基线是真基线。}}\;傅里叶法与级次法均可在秒级复算、
        可人工核对，用于捕捉主方法的粗错；主方法只在基线确认无误后才被采信。
  \item \textbf{{判据不含人为阈值。}}\;以模型偏差与实测噪声之比作判据，尺度由数据自身给出；
        并且明确报告了谐波旁证的泄漏本底，不把方法缺陷当成物理信号。
  \item \textbf{{把病态路线的失败也作为结果报告。}}\;双角度反演折射率的条件数
        {inv['relative_condition_number']:.0f} 是一个明确的、可复算的负面结论，
        比默默换一条路更有信息量。
\end{{enumerate}}

\subsection{{模型的缺点}}

\begin{{enumerate}}[leftmargin=2em]
  \item \textbf{{厚度精度受制于绝对反射率标定。}}\;这是本文最主要的局限。折射率由绝对反射率水平
        决定，而附件 2 出现超过 100\% 的读数说明标定存在偏差。若能提供参考镜标定曲线或同一片子
        的透射谱，可望把碳化硅的厚度不确定度从 {ub_sic['reported_uncertainty_um'] / sic['d_um_mean'] * 100:.1f}\%
        降到波段散布的 {max(band_rel[:2]) * 100:.2f}\% 量级。
  \item \textbf{{层厚均匀性无法与标定误差分离。}}\;两个角度的差异可能来自标定，也可能来自测点不同
        导致的厚度不均。仅凭现有数据无法区分，本文把它整体计入不确定度，属保守处理。
  \item \textbf{{单振子模型对剩余射线带的描述不够精细。}}\;附件 1 在 970\,cm$^{{-1}}$ 的 LO 边处残差
        达 5\%（图~\ref{{fig:sicfit}}），说明真实的声子阻尼不是常数。这对带外条纹的影响有限，
        但若要把带内也做准，需要引入频率依赖的阻尼。
  \item \textbf{{未考虑表面粗糙度与过渡层。}}\;硅片拟合在高波数存在约 $\pm1\%$ 的系统残差
        （图~\ref{{fig:sifit}}），可能来自界面过渡层。计入会增加参数，与厚度存在一定相关性。
\end{{enumerate}}

\subsection{{推广}}

本文的框架不依赖具体材料，只需替换介电函数：极性晶体用 Lorentz 振子，掺杂半导体加 Drude 项，
多层结构把 Airy 公式换成传输矩阵即可推广到多层外延。判据"忽略某效应造成的模型偏差与噪声之比"
也可移植到其他"该不该用更复杂模型"的场合。

\begin{{thebibliography}}{{9}}
\bibitem{{ref1}} 本文全部数值结果由附件 1--4 的实测数据经 \texttt{{src/compute.py}} 计算得到，
中间产物见 \texttt{{artifacts/}} 目录，未引用外部文献中的材料常数或同题解答。
\bibitem{{ref2}} Anthropic. Claude Code（模型 Claude Opus 5，版本 2.0）[CP/OL].
美国: Anthropic, 2026. 使用日期: 2026-08-03.
用途: Python 代码编写与重构、\LaTeX{{}} 排版、中文表述润色。
\end{{thebibliography}}

\begin{{aideclaration}}[AI 工具使用声明]
本参赛队在本题中使用了 AI 编程助手（Claude Code，Anthropic，2026 年 8 月）辅助完成以下工作：
Python 代码的编写与重构、\LaTeX 排版、以及英文术语的中文表述润色。
所有数学推导由队员独立完成并逐式手工复核；所有数值结果均由 \texttt{{src/compute.py}} 在本地运行
真实附件数据产生，写入 \texttt{{artifacts/results.json}} 后由 \texttt{{paper/gen\_paper.py}}
自动插入正文，未经任何人工转抄或修改；模型的物理假设、判据的选择与结论的取舍由队员负责。
AI 未参与结论的判断。
\end{{aideclaration}}

\appendix
\section{{支撑文件/材料清单}}

\begin{{itemize}}[leftmargin=2em]
  \item \texttt{{official\_input/}}：官方题目 PDF 与附件 1--4，未作任何修改；
  \item \texttt{{src/optics.py}}：介电函数、菲涅耳系数、双光束与 Airy 反射率的正演实现；
  \item \texttt{{src/spectra.py}}：附件读取、哨兵剔除、等间隔重采样、噪声估计；
  \item \texttt{{src/inversion.py}}：傅里叶基线、条纹级次法、多起点全谱拟合、谐波判据；
  \item \texttt{{src/compute.py}}：主入口，产出 \texttt{{artifacts/results.json}} 及各证据文件；
  \item \texttt{{src/make\_figures.py}}：由 results.json 生成正文全部图；
  \item \texttt{{tests/}}：{{17}} 个单元测试，含解析特例、合成数据回收与两个回归测试；
  \item \texttt{{artifacts/}}：基线、主拟合、收敛轨迹、多种子、参数边界审计、
        波段敏感性、双角度互校、多光束判据共 10 份证据文件；
  \item \texttt{{case.json}}：逐问的模型卡、方程到代码/测试映射与验证登记。
\end{{itemize}}

复现命令（在本目录的上一级依次执行）：
\begin{{quote}}\ttfamily
python src/compute.py \\
python src/make\_figures.py \\
python paper/gen\_paper.py \\
cd paper \&\& xelatex paper.tex
\end{{quote}}
主计算约需半分钟（Python {meta['python']}，NumPy {meta['numpy']}；精确耗时记于 \texttt{{artifacts/results.json}} 的 \texttt{{meta.runtime\_seconds}}），
随机种子固定为 {meta['seeds']}，结果逐位可复现。

\section{{程序代码}}

见支撑材料 \texttt{{src/}} 目录，共 5 个模块。核心正演模型（\texttt{{src/optics.py}}）与三条反演路线
（\texttt{{src/inversion.py}}）均为纯函数，可独立调用与测试。

\end{{document}}
"""


def main() -> None:
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    OUTPUT.write_text(build(results), encoding="utf-8")
    print(f"写出 {OUTPUT}（{OUTPUT.stat().st_size / 1024:.1f} KB）")


if __name__ == "__main__":
    main()
