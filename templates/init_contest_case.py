"""Initialize a traceable CUMCM contest workspace.

The generated case.json is the contract between problem interpretation,
implementation, experiments, and the paper.  It deliberately contains no
fabricated model or numerical result.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TASK_TYPES = ("unclassified", "direct", "mechanism", "simulation", "optimization", "prediction", "evaluation")


def question_card(index: int) -> dict:
    return {
        "id": f"Q{index}",
        "task_type": "unclassified",
        "target_quantity": "",
        "interpretation": {
            "ambiguities_reviewed": False,
            "ambiguities": [],
            "candidate_metrics": [],
            "selected_metric": "",
            "rationale": "",
        },
        "model": {
            "decision_variables": [],
            "parameters": [],
            "objective": "",
            "constraints": [],
            "assumptions": [],
            "discretized": False,
            "equation_code_map": [],
        },
        "decomposition": {
            "used": False,
            "method": "",
            "rationale": "",
            "joint_benchmark": "",
        },
        "solvers": {
            "baseline": {"method": "", "entrypoint": "", "result_path": ""},
            "primary": {
                "method": "",
                "entrypoint": "",
                "result_path": "",
                "iterative": False,
                "stochastic": False,
                "seeds": [],
                "convergence_trace": "",
            },
        },
        "constraint_audit": "",
        "validations": [],
        "paper": {"section": "", "evidence_displays": []},
    }


def build_manifest(case_id: str, questions: int, input_mode: str = "official-only") -> dict:
    if questions < 1:
        raise ValueError("questions must be at least 1")
    return {
        "schema_version": 1,
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


COMPUTE_STUB = '''"""Run every model and write artifacts/results.json.

Do not hand-edit numerical values in the paper.  Replace this stub only after
the problem interpretation and model cards in case.json have been reviewed.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    raise NotImplementedError("implement the verified computation pipeline")


if __name__ == "__main__":
    main()
'''


PAPER_STUB = '''"""Generate paper/paper.tex exclusively from artifacts/results.json."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    raise NotImplementedError("generate the paper after verified results exist")


if __name__ == "__main__":
    main()
'''


def initialize_case(target: Path, case_id: str, questions: int, input_mode: str = "official-only") -> Path:
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
    parser = argparse.ArgumentParser(description="initialize a traceable CUMCM case")
    parser.add_argument("target", type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--questions", type=int, required=True)
    parser.add_argument("--input-mode", choices=("official-only", "open"), default="official-only")
    args = parser.parse_args()
    path = initialize_case(args.target, args.case_id, args.questions, args.input_mode)
    print(path)


if __name__ == "__main__":
    main()
