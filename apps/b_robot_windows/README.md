# B题交付版 v9：问题三升级，问题四保留 v7

问题三采用 rollout，问题四继续 v7。问题三两类合并均值从 362.43 降至 291.57 秒/源，改善 19.55%；达到低于300秒/源目标。问题四 v7 合并均值为 658.06 秒/源，未达到低于400秒/源目标。

独立种子 30000–30029：问题三普通/边界各30例与v7逐例配对，问题四普通/边界各30例只运行v7。全部清除，计时残差小于1e-6秒，虚拟时间小于360000秒，整局墙钟小于1200秒。问题三配对平均节约95%区间 [62.15, 79.57] 秒/源；仅描述自建场景，不是官方成绩。

| 题目/场景 | v7均值 | 交付均值 | 交付90%分位 |
| --- | ---: | ---: | ---: |
| 问题3 普通 | 386.70 | 293.71 | 353.88 |
| 问题3 边界 | 338.16 | 289.44 | 355.35 |
| 问题4 普通 | 685.66 | 685.66 | 887.16 |
| 问题4 边界 | 630.47 | 630.47 | 833.54 |

本轮没有连接官方模拟器，没有开展官方演练或正式测试。旧v7/v8程序、旧论文、开发负面结果及源码快照均保留。

## 交付入口

- `交付材料/Solution Paper.pdf`：当前匿名论文，摘要、选型、消融、灵敏度和实际执行轨迹已同步。
- `交付材料/Supporting Materials.zip`：匿名源码、实验、配置、复现工具及AI说明。
- `B-Robot-Windows-x64-v9.zip`：新版Windows程序；必须完整解压，运行 `B-Robot.exe`。
- `B题-v9-同伴演练包.zip`：程序、论文、操作指南和可编辑工程的统一交接包。
- `artifacts/rollout-acceptance.json`：按题验收原始数值；`rollout-freeze.json`保存冻结配置和源码哈希。
- `artifacts/rollout-verification.md`：验证及保留结果说明。

## 默认行为与复现

桌面程序和 `src/run_robot.py` 根据 `src/rollout-defaults.json` 按题选择：问题三rollout/C++，问题四adaptive(v7)。源码或原生后端证书不匹配时默认退回v7，避免将未验收修改作为已验收版本运行。显式 `--scheduler adaptive` 可运行v7对照；显式 `--scheduler rollout --rollout-backend python|cpp|auto --rollout-config '{...}'` 用于开发。`Strategy` 的既有默认参数及benchmark对照默认仍是adaptive；测试不应误用发布默认。

安装兼容的Python、C++17编译器和XeLaTeX，在虚拟环境中执行：

    python -m pip install -r requirements.txt -r requirements-review.txt -r requirements-native.txt
    python tools/build_rollout_cpp.py
    python -m pytest tests -q
    python tools/rollout_study.py report
    python tools/compute_results.py
    python tools/render_rollout_evidence.py
    python tools/build_paper.py
    python tools/check_paper_numbers.py
    python tools/verify_support_rebuild.py

报告与论文重建读取冻结数据，不重新调参。若要复跑全套独立场景，应使用新的输出位置保留原始验收记录；任何算法修改需要重新开发、冻结并登记新种子段。问题二独立算法不变。

Windows本地构建需在x64 MSVC开发者命令行安装 `windows/requirements-build.txt`，执行 `python tools/build_windows_local.py --version 自定义版本号`。它编译原生内核、核对保存的Python参考费用、构建目录包并执行无网络窗口测试。开发者修改源码后不得沿用原验收结论。

## 队员仍需据实完成

人工复核模型与推导；核定历史AI使用记录、独立封面等真实信息。若后续另行开展官方演练或正式测试，应按真实界面和日志追加证据，不能将本轮自建结果填入正式成绩表。
