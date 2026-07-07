# 绘图脚手架

配图类型选择、章节位置、美观规范见 `analysis/figure-guide.md`；本目录只提供画图函数。

**什么时候用哪个函数**：

- `sensitivity_curve`：灵敏度/参数扫描（多条曲线+可选基准线）
- `heatmap`：空间分布、方案矩阵、相关系数
- `fit_comparison`：数据点+拟合曲线+残差子图
- `convergence_curve`：迭代算法的损失/误差收敛
- `multi_panel`：同构指标并排小图（small multiples）

**用法**：先调用一次 `style.apply_cumcm_style()`（设置中文字体链、300dpi、配色循环），再调用 `plots.py` 里的函数拿到 `Figure`，自己 `fig.savefig(path)`。

```python
from snippets.plotting.style import apply_cumcm_style
from snippets.plotting.plots import sensitivity_curve

apply_cumcm_style()
fig = sensitivity_curve(x, {"开角100°": y1, "开角120°": y2}, "测线距中心点的距离/m", "覆盖宽度/m")
fig.savefig("figs/图6_覆盖宽度随开角的变化.png")
```

**常见坑**：
- 中文字体链里的字体如果系统都没装（`fc-list | grep -i simhei` 确认），会静默回退到默认字体导致中文变方块——本机没有目标字体时装一个 Noto Sans CJK 或改 `style.py` 里的字体列表顺序
- `heatmap` 的 `annotate=True` 在矩阵较大（>15×15）时格内数字会挤在一起，改 `annotate=False` 或调小 `fontsize`
- 不要把诊断/调试图直接当正文图用——先看 `figure-guide.md` 的"结果图"一节，正文图应该是从多次调试里精选出来、带清晰解读的

## AI 生图（gptimage2 等）备用路径

仅用于**不含任何数据、坐标轴、数值的物理场景示意图**，且必须按官方规定在正文标注、参考文献列出所用工具（2025 年试行规定，见 `figure-guide.md` 工具选型一节）。数据图、结果图一律用本目录的函数从真实计算结果生成，不要用 AI 生成。
