"""初始化一个可追踪的国赛工作目录。

生成的 case.json 是「题意理解 — 代码实现 — 实验记录 — 论文」四者之间的契约，
里面不预置任何模型结论或数值结果。

字符串字段用尖括号占位符 `<...>` 给出填写口径，`checklist/case_audit.py`
的 `_blank()` 把这类值一律判为未填写，因此占位符不会伪装成已完成。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


HELP_NOTE = (
    "尖括号 <...> 为待填占位符，case_audit.py 一律判为未填写；"
    "字段含义与填写顺序见 analysis/modeling-workflow.md，"
    "validations 的可用 type 见 checklist/case_audit.py"
)


def question_card(index: int) -> dict:
    """生成一问的空白模型卡。列表字段留空表示「还没有任何一条」。

    `equation_code_map`、`validations`、`evidence_displays` 三个对象列表各放一条
    占位条目，用来展示条目应有的键；审计器对条目内字段逐项检查，占位条目照样报警告。
    其余纯字符串列表（假设、约束、候选指标等）保持真空列表——审计器对它们只做
    「有没有」的存在性检查，塞占位条目会让告警静默消失。
    """
    return {
        "id": f"Q{index}",
        "task_type": "unclassified",
        "target_quantity": "<待求量的数学定义，含单位与统计口径>",
        "interpretation": {
            "ambiguities_reviewed": False,
            "ambiguities": [],
            "candidate_metrics": [],
            "selected_metric": "<最终采用的指标，例：并集遮蔽时长（重叠区间不重复计）>",
            "rationale": "<选择依据：题目文字 / 物理含义 / 任务场景>",
        },
        "model": {
            "decision_variables": [],
            "parameters": [],
            "objective": "<目标函数或待求量的数学表达式>",
            "constraints": [],
            "assumptions": [],
            "discretized": False,
            "equation_code_map": [
                {
                    "equation": "<方程标识，例：式(3) 云团下沉状态方程>",
                    "implementation": "<实现位置，例：src/compute.py:cloud_centers>",
                    "test": "<对应测试，例：tests/test_model.py>",
                }
            ],
        },
        "decomposition": {
            "used": False,
            "method": "<分层 / 任务分配 / 贪心追加 / 滚动优化，未使用则留空>",
            "rationale": "<为什么可以这样分解，代价是什么>",
            "joint_benchmark": "<缩小规模联合优化对照的结果文件路径>",
        },
        "solvers": {
            "baseline": {
                "method": "<透明可快速复算的基线，例：网格枚举>",
                "entrypoint": "<运行入口，例：src/compute.py>",
                "result_path": "<基线结果，例：artifacts/baseline.json>",
            },
            "primary": {
                "method": "<主求解方法，例：差分进化>",
                "entrypoint": "<运行入口，例：src/compute.py>",
                "result_path": "<主结果，例：artifacts/primary.json>",
                "iterative": False,
                "stochastic": False,
                "seeds": [],
                "convergence_trace": "<逐代最优目标值，例：artifacts/convergence.json>",
            },
        },
        "constraint_audit": "<逐约束残差报告，例：artifacts/constraints.json>",
        "validations": [
            {
                "type": "<验证类型，例：independent_solver / multi_seed_stability>",
                "finding": "<结论，例：两种算法目标值相差 0.2%>",
                "artifact": "<证据文件，例：artifacts/independent.json>",
            }
        ],
        "paper": {
            "section": "<论文中对应的节标题，须与 paper.tex 中的写法完全一致>",
            "evidence_displays": [
                {
                    "type": "<figure 或 table>",
                    "artifact": "<图片或数据文件，例：artifacts/result_table.csv>",
                }
            ],
        },
    }


def build_manifest(case_id: str, questions: int, input_mode: str = "official-only") -> dict:
    """组装 case.json 的顶层结构。

    `inputs.sources` 保持空列表，好让审计报出「尚未登记官方题目或附件来源」；
    条目写成 `"official_input/A题.pdf"` 或 `{"path": ..., "kind": "official"}` 均可。
    """
    if questions < 1:
        raise ValueError("questions must be at least 1")
    return {
        "schema_version": 1,
        "_help": HELP_NOTE,
        "case_id": case_id,
        "phase": "blind",
        "inputs": {
            "mode": input_mode,
            "sources": [],
            "external_references": [],
        },
        "results_path": "artifacts/results.json",
        "paper": {
            "tex_path": "paper/paper.tex",
            "generator": "paper/gen_paper.py",
            "generated_from": "artifacts/results.json",
        },
        "questions": [question_card(index) for index in range(1, questions + 1)],
    }


COMPUTE_STUB = '''"""跑完全部模型，把所有进入论文的数值写进 artifacts/results.json。

论文里的数字一律不得手工转抄或手工修改。等 case.json 里的题意审计和模型卡
过了一遍，再动这个桩文件。
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    raise NotImplementedError("implement the verified computation pipeline")


if __name__ == "__main__":
    main()
'''


PAPER_STUB = '''"""只从 artifacts/results.json 生成 paper/paper.tex，不接受其他数据来源。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    raise NotImplementedError("generate the paper after verified results exist")


if __name__ == "__main__":
    main()
'''


def initialize_case(target: Path, case_id: str, questions: int, input_mode: str = "official-only") -> Path:
    """建目录、写 case.json 和两个生成脚本的桩；已存在 case.json 时拒绝覆盖。"""
    target = Path(target)
    manifest_path = target / "case.json"
    if manifest_path.exists():
        raise FileExistsError(f"refusing to overwrite {manifest_path}")

    for relative in (
        "official_input",
        "src",
        "tests",
        "artifacts/runs",
        "paper/figures",
    ):
        (target / relative).mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(case_id, questions, input_mode)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (target / "src" / "compute.py").write_text(COMPUTE_STUB, encoding="utf-8")
    (target / "paper" / "gen_paper.py").write_text(PAPER_STUB, encoding="utf-8")
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化一个可追踪的国赛工作目录")
    parser.add_argument("target", type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--questions", type=int, required=True)
    parser.add_argument("--input-mode", choices=("official-only", "open"), default="official-only")
    args = parser.parse_args()
    path = initialize_case(args.target, args.case_id, args.questions, args.input_mode)
    print(path)


if __name__ == "__main__":
    main()
