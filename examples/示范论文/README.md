# 示范论文：区域农产品仓储选址与配送优化

这是**一篇跑通了的完整论文**，不是模板。10 页，正文里每一个数字都由 `compute.py`
真实算出来，没有一处是编的。版式与工具箱模板统一为 B226 竞赛型风格。用途有两个：

1. **看范例**——新队员想知道「一篇能拿奖的论文长什么样」，打开 [demo.pdf](demo.pdf) 从头翻到尾。
2. **看接线**——想知道工具箱的 `snippets/` 怎么串成一条完整链路，读 `compute.py` 就够了。

## 怎么重跑

在仓库任意目录下执行都可以，脚本自己定位仓库根：

```bash
.venv/bin/python examples/示范论文/compute.py     # 算数 → results.json + 四张图
.venv/bin/python examples/示范论文/gen_paper.py   # 读 JSON → demo.tex
cd examples/示范论文 && xelatex demo.tex && xelatex demo.tex   # 跑两趟，第二趟解交叉引用
```

没建 venv 的先看仓库根 [README.md](../../README.md) 的安装一节——**不要用系统 `pip3 install`**，
这台机器上会被 PEP 668 拦住。

## 为什么要 `compute.py → results.json → gen_paper.py` 这么绕

因为「论文里的数字和代码输出对不上」是国赛最容易被抓、也最难自查的硬伤。
[checklist/manual_verification.md](../../checklist/manual_verification.md) 把它列为必查项，
但人工核对几十个数字，四天三夜里根本查不完。

这条链把核对这件事**从人手上拿掉了**：`gen_paper.py` 里所有数字都是 f-string 从
`results.json` 插值出来的，没有任何一处手工转抄。改了数据重跑两个脚本，论文自动跟着变。
物理上不可能出现「代码改了论文忘了改」。

比赛时建议照抄这个结构。多花的半小时，换的是最后一天不用逐个数字回头对。

## 论文覆盖了什么

| 环节 | 用的方法 | 调用的 snippet |
|---|---|---|
| 数据预处理 | 线性插值补缺测、IQR 查异常 | `preprocessing` |
| 问题一 预测 | GM(1,1) + 级比检验 + 残差检验 | `grey_prediction`、`model_validation` |
| 问题二 评价 | 熵权法 + TOPSIS，含两种正向化对比 | `topsis_entropy` |
| 问题三 优化 | 最小生成树、最短路、线性规划 | `graph_shortest_path`、`linear_programming` |
| 通用环节 | 单因素灵敏度分析、四张配图（含研究流程图） | `model_validation`、`plotting` |

写作上也按 [analysis/paper-structure.md](../../analysis/paper-structure.md) 的节次顺序走了一遍：
摘要独占首页、符号说明表、模型假设编号、灵敏度分析独立成节、模型评价分优缺点、
附录含支撑材料清单——这些都是评委的固定检查项。

## 有意留下的两个「教学点」

**问题二对比了两种成本型指标正向化。** 同一份数据，`max(x)-x` 法让「建设投资」这一列的
熵权冲到 0.9614，几乎独占权重，选址结论跟着被单一指标绑架；倒数法 $1/x$ 下最大权重 0.4904，
结论才是四个指标共同作用的。论文里把两组权重并排列出来了。这个坑写在
[snippets/topsis_entropy/README.md](../../snippets/topsis_entropy/README.md) 常见坑第 3 条。

**问题一没有跳过级比检验。** GM(1,1) 不做级比检验就直接建模，是灰色预测最常见的扣分点。
论文里把 5 个级比值和容许区间都列了出来。

## 文件说明

| 文件 | 是什么 | 要不要改 |
|---|---|---|
| `compute.py` | 全部计算，输出 `results.json` 和四张图 | 换题目时改这个 |
| `gen_paper.py` | 读 JSON 生成 `demo.tex` | 换题目时改这个 |
| `results.json` | 计算结果，代码产物 | 不要手改 |
| `demo.tex` | 论文源码，代码产物 | 不要手改，改了会被覆盖 |
| `demo.pdf` | 编译结果，10 页 | 产物 |
| `fig*.png` | 四张配图，代码产物 | 产物 |

产物一并入库，是为了让人不装 LaTeX 也能直接翻 PDF。
