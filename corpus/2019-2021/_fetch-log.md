# 语料抓取日志 —— 2019-2021 补充抽样

任务：Task 3 Step 3（cumcm-toolkit 实施计划）。目标：每年 2-3 篇，设计文档标注该区间"覆盖度待核实"。总体抓取策略、官方站点探查与共性失败记录见 `../2022-2025/_fetch-log.md`（本目录日志只记录本区间特有信息）。

抓取时间：2026-07-03

## 官方展示区探查（本区间特有）

- 2019 年官方展示区存在，URL 规律与 2022+ 不同：`qkt_sxjm_lw_2019qgdxssxjmjslwzs`（实例详情页 `https://dxs.moe.gov.cn/zx/a/qkt_sxjm_lw_2019qgdxssxjmjslwzs/191029/1529313.shtml`，由 2019-A 收录论文的作者仓库 README 提供，该论文即官方展示区收录的三篇 A 题范文之一）。按 2022+ 年份的实测结论（论文以图片形式嵌入，无法提取文本），未再对 2019-2021 官方详情页逐一重试。

## 成功收录（8 篇，均 completeness: full）

| 文件 | 年/题 | 论文标题 | 奖项（来源标注） | 来源仓库 | 提取方式 |
|---|---|---|---|---|---|
| `2019-A.md` | 2019-A | 高压油管的压强控制 | 国家一等奖（官方阅卷组范文） | fanxingcs/CUMCM2019Problems-A | pdftotext |
| `2019-B.md` | 2019-B | "同心协力"策略研究 | 未标注 | gtoxlili/CUMCM2019 | pdftotext |
| `2020-B-1.md` | 2020-B | 穿越沙漠游戏的最佳决策 | 全国一等奖（同济大学队） | seanys/CUMCM2020-Desert-Game | LaTeX 源码直接收录 |
| `2020-B-2.md` | 2020-B | 穿越沙漠路径规划的宽度优先搜索模型 | 未标注 | ShiZhuming/CUMCM2020 | pypdf |
| `2020-C.md` | 2020-C | 基于信贷风险评估模型的信贷决策 | 未标注 | UestcXiye/CUMCM2020-Probelms-C | pdftotext |
| `2021-A.md` | 2021-A | "FAST"主动反射面的形状调节 | 未标注 | yan-fanyu/CUMCM-Paper-And-SourceCode | pypdf |
| `2021-B.md` | 2021-B | 乙醇偶合制备 C4 烯烃 | 未标注 | yan-fanyu/CUMCM-Paper-And-SourceCode | pdftotext |
| `2021-C.md` | 2021-C | 不稳定供应下原材料订购方案制定与实施预测 | 未标注 | yan-fanyu/CUMCM-Paper-And-SourceCode | pypdf |

目标 vs 实际：2019 想拿 2-3 篇、实得 2 篇；2020 实得 3 篇；2021 实得 3 篇。达标。

备注：`gtoxlili/CUMCM2019` 仓库自称"C题论文"，经与官方赛题名单比对实为 B 题（"同心协力"/同心鼓），按实际内容归档为 `2019-B.md`。

## 失败记录（本区间特有）

- [失败] `QInzhengk/Math-Model-and-Machine-Learning` 仓库 `全国大学生数学建模竞赛（92-21）/2019|2020|2021/` 全部子目录 —— Task 2 曾用该仓库成功提取 2005-2018 论文，但 2019-2021 三个年份实测（抽样 2019 A023/A190/B047/C044/E003、2021 A028/B007/C006/D017 共 9 个文件）均为扫描图 PDF，文本层只有"MATHmodels"公众号水印（字体混淆），pdftotext/pypdf 提取均无一个可读汉字；2020 年份文件单个 12-25MB，判定同为扫描件未再下载。该仓库对 2019-2021 区间整体不可用。
- [失败] GitHub 仓库搜索 `2021 数学建模 国赛 论文`、`CUMCM2021 论文`、`2021 CUMCM paper thesis` 等查询均 0 结果；2021 年份最终依靠 yan-fanyu 论文合集仓库补齐（每篇均已核对标题与官方赛题一致）。
- 共性失败（CSDN 521 / 知乎 403 / 官方图片嵌入等）见 `../2022-2025/_fetch-log.md`。
