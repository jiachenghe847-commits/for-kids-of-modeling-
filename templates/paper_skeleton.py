"""生成每问四小节的论文骨架，把契约要求的每个元素变成看得见的 TODO 槽位。

**为什么要有这个**：2025 B 题演练的论文里，问题一的「算法设计与求解」只有 59 个汉字，
而 `analysis/modeling-workflow.md` §6 契约第 3 条要求这一节交代「输入输出、步骤、
停止条件、复杂度或降维依据」——四样一样都没有。漏写的时候论文里什么都不会发生，
它只是安静地短了一截，编译照样通过、审计照样 0 警告。

骨架把每个必需元素写成一行 `% TODO(小节/元素): ...` 注释。漏写时它留在源码里，
`missing_slots()` 能查出来，`checklist/case_audit.py` 会报残留数。TODO 是 LaTeX 注释，
不进 PDF，所以填了就删、没填也不会污染排版。

**它不替你写内容**。让 AI 照着模式把 3934 字灌成 9800 字，产出的是注水不是论证，
和「所有数字必须来自真实计算」是同一条底线。骨架只负责让缺口看得见。

用法：

```python
from paper_skeleton import paper_skeleton
tex = paper_skeleton([
    {"id": "Q1", "title": "问题一：单次反射情形下的干涉厚度模型", "task_type": "mechanism"},
    {"id": "Q2", "title": "问题二：厚度反演算法与计算结果", "task_type": "optimization"},
])
```

或命令行：`python templates/paper_skeleton.py --questions 3 -o paper/skeleton.tex`
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

# 四个小节与各自的必需元素。小节名与 templates/paper.tex 的版式一致，
# 元素取自 analysis/modeling-workflow.md §6 契约与 analysis/exposition-guide.md 第一节。
SUBSECTIONS: list[tuple[str, tuple[str, ...]]] = [
    ("模型建立", (
        "变量与参数的定义、单位",
        "目标函数或判定式的数学化过程（写推导本身，不是结果）",
        "约束及其来源：题目给定 / 物理决定 / 团队假设",
        "新增假设影响什么",
    )),
    ("算法设计与求解", (
        "输入输出：吃什么数据、吐什么量，含维度与单位",
        "步骤：Step 式逐条列，每步一个动作加依据",
        "停止条件：迭代到什么时候停、为什么是这个判据",
        "复杂度或降维依据；用了分解/贪心要说清代价",
    )),
    ("结果分析", (
        "结果是多少：数值、单位、不确定度",
        "为什么可信：残差 / 置信区间 / 变异系数（snippets/statistics）",
        "相对基线或对照改善多少",
    )),
    ("模型验证", (
        "用的是哪一类验证（见 modeling-workflow.md §5 分类验证表）",
        "判据与阈值来源",
        "结论；没通过要写没通过",
    )),
]

# analysis/modeling-workflow.md §5「按任务类型验证」表的最低验证组合。
# 任务类型已知时，把对应组合直接填进「模型验证」的槽位，省得回去翻表。
VALIDATION_BY_TYPE: dict[str, str] = {
    "direct": "手算/解析结果或第二段独立实现",
    "mechanism": "量纲检查 + 解析特例/独立实现；有离散时再做步长或网格收敛",
    "simulation": "量纲检查 + 解析特例/独立实现；有离散时再做步长或网格收敛",
    "optimization": "基线 + 多种子稳定性（随机算法）+ 逐约束审计 + 第二算法/缩小规模精确解/上下界之一",
    "prediction": "基准模型 + 留出或交叉验证 + 残差分析",
    "evaluation": "标准化/赋权敏感性 + 排序稳定性",
}

_SLOT = re.compile(r"^[ \t]*%[ \t]*TODO\(([^/]+)/([^)]*)\):[ \t]*(.*)$", re.MULTILINE)


def _slot(section: str, element: str) -> str:
    return f"% TODO({section}/{element}): "


def question_skeleton(qid: str, title: str, task_type: str | None = None) -> str:
    """生成一问的四个小节骨架，每个必需元素一行 TODO 槽位。

    ``task_type`` 取 modeling-workflow.md §5 的六类之一；给了就把该类的最低验证组合
    直接写进「模型验证」的第一个槽位。给了不认识的类型不报错——按未知处理，
    留通用槽位，因为题目分类本来就允许人工判断。
    """
    lines = [f"\\subsection{{{title}}}", f"% ---- {qid} ----", ""]
    for section, elements in SUBSECTIONS:
        lines.append(f"\\subsubsection{{{section}}}")
        for element in elements:
            hint = ""
            if section == "模型验证" and element.startswith("用的是哪一类验证"):
                known = VALIDATION_BY_TYPE.get(task_type or "")
                if known:
                    hint = f"本题为 {task_type}，最低组合：{known}"
            lines.append(_slot(section, element) + hint)
        lines.append("")
    return "\n".join(lines)


def paper_skeleton(questions: list[dict]) -> str:
    """拼多问骨架。``questions`` 每项含 id / title，可选 task_type。"""
    blocks = [
        question_skeleton(
            q.get("id", f"Q{i + 1}"),
            q.get("title", f"问题{i + 1}"),
            q.get("task_type"),
        )
        for i, q in enumerate(questions)
    ]
    return "\n".join(blocks)


def missing_slots(tex_text: str) -> list[dict]:
    """反查还没填掉的 TODO 槽位。

    判定「未填」的口径：槽位注释还在源码里。填完内容后把这一行删掉即可；
    留着注释、正文另起一段写也算未填——注释是给人看的待办，不是给人留着当装饰的。
    """
    out = []
    for match in _SLOT.finditer(tex_text):
        out.append({
            "section": match.group(1).strip(),
            "element": match.group(2).strip(),
            "hint": match.group(3).strip(),
            "line": tex_text[: match.start()].count("\n") + 1,
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="生成每问四小节的论文骨架（含 TODO 槽位）")
    parser.add_argument("--questions", type=int, default=3, help="问题数量")
    parser.add_argument("--titles", nargs="*", default=None, help="逐问标题，缺省用「问题N」")
    parser.add_argument("--types", nargs="*", default=None,
                        help=f"逐问任务类型，可选：{'/'.join(VALIDATION_BY_TYPE)}")
    parser.add_argument("-o", "--output", type=Path, help="写入文件；不给就打到标准输出")
    args = parser.parse_args()

    titles = args.titles or [f"问题{i + 1}" for i in range(args.questions)]
    types = args.types or []
    questions = [
        {"id": f"Q{i + 1}",
         "title": titles[i] if i < len(titles) else f"问题{i + 1}",
         "task_type": types[i] if i < len(types) else None}
        for i in range(args.questions)
    ]
    text = paper_skeleton(questions)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"已写入 {args.output}（{len(missing_slots(text))} 个待填槽位）")
    else:
        print(text)


if __name__ == "__main__":
    main()
