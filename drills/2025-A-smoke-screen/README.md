# 2025 A 题盲测演练：烟幕干扰弹的投放策略

本目录只以组委会发布的 `official_input/A题.pdf` 和
`official_templates/` 下三个空白结果模板为输入，未使用项目语料库中的同题论文或策略数据。官方赛题来源：
`https://www.mcm.edu.cn/html_cn/node/03c91a444e62eee81a3740fa97a461a6.html`。

## 复现

在仓库根目录运行：

```bash
.venv/bin/python drills/2025-A-smoke-screen/solve.py
.venv/bin/python drills/2025-A-smoke-screen/make_artifacts.py
cd drills/2025-A-smoke-screen/output
xelatex -interaction=nonstopmode -halt-on-error ../paper.tex
xelatex -interaction=nonstopmode -halt-on-error ../paper.tex
```

优化使用固定随机种子 `2025`。默认运行约需数十秒，输出包括：

- `output/paper.pdf`：完整模拟论文；
- `output/results.json`：五问全部参数、坐标、区间和时长；
- `output/result1.xlsx`、`result2.xlsx`、`result3.xlsx`：填写后的官方模板；
- `output/fig*.png`：论文图。

## 模型口径

- 云团有效时，导弹到圆柱目标上下圆周边界采样点的全部视线段必须被至少一个烟幕球截断。
- 多弹结果按遮蔽时间集合的并集计量，重叠区间不重复累计。
- 问题五以三枚导弹各自有效时长之和为目标；“每架至多 3 枚”允许不投放无正边际收益的弹。
- 问题五采用分层配对和边际追加，是可复现的启发式可行解，不声称严格全局最优。
