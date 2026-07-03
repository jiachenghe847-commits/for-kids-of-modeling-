# 语料抓取日志 —— 2022-2025 官网展示区抽样（含 2019-2021 补充）

任务：Task 3（cumcm-toolkit 实施计划）。目标：以 2022-2025 官网展示区为主抽样约 20 篇近届论文（2023-2025 每年每题 A-E 尽量至少 1 篇，2022 年 3-5 篇对照），并补充 2019-2021 每年 2-3 篇，存入 `corpus/2022-2025/` 与 `corpus/2019-2021/`。

抓取时间：2026-07-03

## Step 1: 官方展示区逐年定位（dxs.moe.gov.cn）

各年份展示页均存在、可访问：

- 2022：`https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2022qgdxssxjmjslwzs/` → 分题子页 `2022atlw/`～`2022etlw/`
- 2023：`https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2023qgdxssxjmjslwzs/` → 分题子页同规律
- 2024：`https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2024qgdxssxjmjslwzs/` → 首页即列出 A163/A242/A178/A016/A053、B159/B195/B196、C038/C234/C063/C094、D033、E010/E218/E061 等详情页
- 2025：`https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2025qgdxssxjmjslwzs/` → 首页列出 A196、B060/B157、C132/C023、D037、E030 等详情页
- 分题列表子页（如 `2022atlw/`）正文内容为 JS 动态加载，WebFetch 直接抓取时拿不到文章链接列表；但可以通过 WebSearch（`site:dxs.moe.gov.cn <年份>qgdxssxjmjslwzs`）检索到具体详情页 URL，等价可用。
- 另发现 2019 年官方展示区存在、且 URL 规律不同：`qkt_sxjm_lw_2019qgdxssxjmjslwzs`（如 `https://dxs.moe.gov.cn/zx/a/qkt_sxjm_lw_2019qgdxssxjmjslwzs/191029/1529313.shtml`，由 2019-A 国一论文作者仓库 README 提供）。

**关键失败（决定性）：官方详情页论文一律以 JPG 图片形式嵌入，无法提取文本。** 实测三个不同年份的详情页：

- 2022-A001（`/zx/a/hd_sxjm_sxjmlw_2022qgdxssxjmjslwzs/221106/1820295.shtml`）——37 页扫描图（`A001_页面_01.jpg`～`_37.jpg`），无文本层；
- 2023-A0165（`/zx/a/hd_sxjm_sxjmlw_2023qgdxssxjmjslwzs_2023atlw/231104/1865112.shtml`）——45 页图片；
- 2025-A196（`/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025atlw/251101/2022729.shtml`）——98 页图片（腾讯云图床）。

判定为该站统一发布形式（论文以图片形式嵌入，无法提取文本），不再逐篇重试，全部年份改用 WebSearch 寻找文字版公开转载。官方页面仅用于核对"该年该题确有展示论文"及奖项背景，不作为正文来源。

## Step 2: 实际采用的正文来源（GitHub 公开转载）

CSDN（HTTP 521 反爬）与知乎（HTTP 403）直接抓取均失败（见失败记录），实际全部正文来自 GitHub 上参赛队伍自己开源的论文仓库或论文合集仓库：下载 PDF/LaTeX 原文件后本地提取（`pdftotext -enc UTF-8` 为主，个别文件 pypdf 效果更好则用 pypdf；LaTeX 源码直接收录）。每篇均核对论文标题/主题与官方赛题一致后收录；奖项一律按仓库 README/描述原文标注，未标注的写"优秀论文（奖项等级未标注）"，不虚构。

### 成功收录 —— corpus/2022-2025/（14 篇，均 completeness: full）

| 文件 | 年/题 | 论文标题 | 奖项（来源标注） | 来源仓库 | 提取方式 |
|---|---|---|---|---|---|
| `2022-A.md` | 2022-A | 波浪能最大输出功率优化设计 | 国家一等奖 | zjuyfy/CUMCM | pdftotext |
| `2022-B-1.md` | 2022-B | 基于纯方位无源定位的无人机三角定位模型 | 未标注 | G-Pegasus/2022-CUMCM-B | pdftotext |
| `2022-B-2.md` | 2022-B | 无人机遂行编队飞行中的纯方位无源定位 | 省二等奖（黑龙江） | KomorebiCN/2022CUMCM | pdftotext |
| `2022-C.md` | 2022-C | 古代玻璃制品的成分分析与鉴别 | 省二等奖 | Sunkanghong-Wang/CUMCM2022 | pdftotext |
| `2023-A.md` | 2023-A | 定日镜场优化设计模型 | 国家一等奖 | linggm3/2023_CUMCM_National-First-Prize | pdftotext |
| `2023-B.md` | 2023-B | 基于多目标规划的多波束测线布设模型 | 国家二等奖 | zhangzeyu2002/2023_CUMCM_Problem_B | pdftotext（注意：期刊投稿重排版，非竞赛原排版） |
| `2023-C.md` | 2023-C | 基于优化模型的蔬菜类商品自动定价与补货决策 | 省二等奖（上海） | kalipolis/CUMCM2023_C | pdftotext |
| `2024-A-1.md` | 2024-A | "板凳龙"表演的运动学分析 | 国家一等奖 | Arctic1010/CUMCM2024-A | pdftotext |
| `2024-A-2.md` | 2024-A | "板凳龙"链式结构在等距螺线形运动中路径与速度模型的研究 | 未获奖（卡点提交失败未完赛，赛后开源） | Austinggg/24-MCM-A | pdftotext |
| `2024-B.md` | 2024-B | 基于抽样检测与优化决策的企业生产过程质量控制模型研究 | 省一等奖（江苏，推断，见文件 note） | yan-fanyu/CUMCM-Paper-And-SourceCode | pdftotext |
| `2024-C-1.md` | 2024-C | 基于非线性规划的蒙特卡洛模拟种植方案求解 | 省二等奖（广东） | Autumnair007/2024-CUMCM-ProblemC | pdftotext |
| `2024-C-2.md` | 2024-C | 基于提升华北山区农作物种植方案的经济效益的优化策略 | 未标注 | yan-fanyu/CUMCM-Paper-And-SourceCode | pdftotext |
| `2025-A.md` | 2025-A | 无人机投放烟幕干扰弹模型与优化策略研究 | 省一等奖（四川） | Yipintianxia-MiddleRingRoad/2025CUMCM_... | LaTeX 源码（zip 内 template.tex） |
| `2025-C.md` | 2025-C | 基于数学建模方法的 NIPT 的时点选择与胎儿的异常判定分析 | 省一等奖（辽宁） | Aiden-DUT/CUMCM2025-C-NIPT-Problem | pdftotext |

年题覆盖：2022 A/B/B/C（4 篇，含 1 篇国一）；2023 A/B/C（3 篇，含 1 篇国一、1 篇国二）；2024 A/A/B/C/C（5 篇，含 1 篇国一）；2025 A/C（2 篇，均省一）。

### 成功收录 —— corpus/2019-2021/（8 篇，均 completeness: full，详见该目录 `_fetch-log.md`）

2019 A/B（含 1 篇国一官方范文）、2020 B/B/C（含 1 篇国一 LaTeX 源码）、2021 A/B/C。

## Step 2/3: 目标 vs 实际

- 2022-2025 目标约 20 篇 → **实际 14 篇**。缺口全部在 D/E 题：**2022-2025 四年 D/E 题一篇未得**（原本想拿 2023/2024/2025 每年 D、E 各 1 篇，共 6+ 篇）。原因：D/E 为专科组赛题，参赛队伍在 GitHub/博客公开完整论文的数量远少于本科组 A/B/C，多轮检索（GitHub 仓库搜索 `CUMCM 2024 D题`、`CUMCM E题 论文` 等均 0 结果；WebSearch 检索专科组优秀论文全文）未找到任何可提取全文的公开转载；官方展示区虽有 D/E 详情页（如 2024-D033、2025-D037/E030）但均为图片嵌入。
- 2025-B 曾获取到省二论文 PDF（Chang-Liu6/CUMCM2025）但字体混淆提取失败（见下），2025 年仅收 A/C 两篇。
- 2019-2021 目标每年 2-3 篇 → 实际 2019×2、2020×3、2021×3，达标。

## 失败记录

- [失败] 官方展示区全部论文详情页（2022/2023/2025 三个年份实测，判定全站同构） —— 论文以图片形式嵌入，无法提取文本。涉及 2022-A001、2023-A0165、2025-A196 等（URL 见 Step 1）。
- [失败] 官方分题列表页（如 `.../2022qgdxssxjmjslwzs/2022atlw/`）—— 列表内容 JS 动态加载，WebFetch 取不到文章链接（改用 WebSearch site: 检索绕过，不影响定位）。
- [失败] `https://zhuanlan.zhihu.com/p/718610103`（知乎"2024数学建模国赛C题完整论文"）—— HTTP 403 Forbidden（知乎反爬）。
- [失败] `https://blog.csdn.net/qq_37345758/article/details/134295998`（CSDN"2023年数学建模国赛优秀获奖论文"聚合帖）—— HTTP 521（CSDN 反爬，与 Task 2 记录一致）。
- [失败] `gbh1234/CUMCM2024B` 仓库 `论文/基于抽样检测与优化决策的企业生产过程质量控制模型研究.pdf`（2024-B 江苏省一）—— PDF 内嵌字体经混淆处理，pdftotext/pypdf 提取均为乱码（0 个可读汉字）。后在 yan-fanyu 合集仓库找到同名论文的可提取副本，已收录为 `2024-B.md`（奖项按同名对应关系推断，文件 note 有说明）。
- [失败] `Elysia415/CUMCM2024-C` 仓库 `CUMCM.pdf`（2024-C 省一）—— 13MB 扫描图 PDF，文本层只有"中国人民大学"水印字样反复出现，正文不可提取。已改用 Autumnair007（广东省二）与 yan-fanyu 合集替代。
- [失败] `Chang-Liu6/CUMCM2025` 仓库 `thesis/基于红外干涉法测量碳化硅外延层厚度的研究.pdf`（2025-B 省二）—— 字体混淆，提取乱码（0 个可读汉字）。未找到 2025-B 替代文字源，2025-B 缺口。
- [失败] `Yipintianxia-MiddleRingRoad/...` 仓库编译版 PDF `2025国赛_四川省一_论文PDF_YYL_ZCY_LJT.pdf`（2025-A）—— 同样字体混淆提取乱码；改从同仓库 LaTeX 源码 zip 解出 `template.tex` 收录（`2025-A.md`），正文完整。
- [失败] `Robin567-Li/CUMCM2025A` —— 仓库内只有"AI工具使用详情.pdf"，无论文正文。
- [失败] `cyzChen1362/CUMCM2025C`、`zz-wolf/CUMCM2021-C`（全国二等奖）、`Liesy/CUMCM2021` —— 仓库只有代码/README，无论文文件。
- [失败] 2022-2025 全部 D/E 题 —— 专科组赛题公开全文转载缺失，多轮 GitHub/WebSearch 检索无果（详见"目标 vs 实际"）。
- [失败] `seanys/CUMCM2020-Desert-Game` 的编译版论文 PDF 不在仓库内（仓库只有 LaTeX 源码 `paper/example.tex`），已直接收录 LaTeX 源码（`2019-2021/2020-B-1.md`）。

## 复核说明

- 所有收录正文均为从 `source_url` 实际下载文件中提取的文本，无任何编造/摘写内容。
- 每篇论文标题/主题均与官方赛题名称逐一比对（比对结果写在各文件 YAML `note` 字段）。发现并纠正一处来源错标：`gtoxlili/CUMCM2019` 仓库自称"C题论文"，实际内容为 2019-B《"同心协力"策略研究》，已按实际内容归档为 `2019-2021/2019-B.md`。
- `2024-A-2.md` 来源队伍因提交超时未完赛、论文未经评审，收录时已在 award/note 字段如实标注，使用该篇时注意其质量无竞赛评审背书。
