import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from case_audit import audit_case

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "templates"))
from init_contest_case import initialize_case


AUDIT_SCRIPT = Path(__file__).resolve().parents[1] / "case_audit.py"


def _touch(case_dir: Path, relative: str, content: str = "{}\n") -> None:
    path = case_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _complete_optimization_case(tmp_path: Path) -> Path:
    case_dir = tmp_path / "complete"
    initialize_case(case_dir, "fixture", 1)
    for relative in (
        "official_input/problem.pdf",
        "tests/test_model.py",
        "artifacts/results.json",
        "artifacts/baseline.json",
        "artifacts/primary.json",
        "artifacts/convergence.json",
        "artifacts/constraints.json",
        "artifacts/independent.json",
        "artifacts/seeds.json",
        "artifacts/result_table.csv",
    ):
        _touch(case_dir, relative)
    _touch(case_dir, "paper/paper.tex", r"\section{问题一：联合优化模型}")

    manifest_path = case_dir / "case.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["inputs"]["sources"] = [
        {"path": "official_input/problem.pdf", "kind": "official"}
    ]
    question = manifest["questions"][0]
    question.update(
        {
            "task_type": "optimization",
            "target_quantity": "总成本最小值",
            "constraint_audit": "artifacts/constraints.json",
        }
    )
    question["interpretation"] = {
        "ambiguities_reviewed": True,
        "ambiguities": [],
        "candidate_metrics": ["总成本"],
        "selected_metric": "总成本",
        "rationale": "与题目中的最小费用要求一致",
    }
    question["model"] = {
        "decision_variables": ["x"],
        "parameters": ["c"],
        "objective": "min c*x",
        "constraints": ["x >= 0"],
        "assumptions": ["单位成本在规划期内不变"],
        "discretized": False,
        "equation_code_map": [
            {
                "equation": "objective",
                "implementation": "src/compute.py:main",
                "test": "tests/test_model.py",
            }
        ],
    }
    question["solvers"] = {
        "baseline": {
            "method": "grid search",
            "entrypoint": "src/compute.py",
            "result_path": "artifacts/baseline.json",
        },
        "primary": {
            "method": "differential evolution",
            "entrypoint": "src/compute.py",
            "result_path": "artifacts/primary.json",
            "iterative": True,
            "stochastic": True,
            "seeds": [1, 2, 3],
            "convergence_trace": "artifacts/convergence.json",
        },
    }
    question["validations"] = [
        {
            "type": "independent_solver",
            "artifact": "artifacts/independent.json",
            "finding": "两种算法目标值相差 0.2%",
        },
        {
            "type": "multi_seed_stability",
            "artifact": "artifacts/seeds.json",
            "finding": "三次运行标准差小于 0.1",
        },
    ]
    question["paper"] = {
        "section": "问题一：联合优化模型",
        "evidence_displays": [
            {"type": "table", "artifact": "artifacts/result_table.csv"}
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return case_dir


def test_initialized_case_reports_actionable_warnings(tmp_path):
    case_dir = tmp_path / "incomplete"
    initialize_case(case_dir, "incomplete", 1)
    report = audit_case(case_dir)
    codes = {item["code"] for item in report["warnings"]}
    assert "inputs.sources" in codes
    assert "question.task_type" in codes
    assert "results.path" in codes


def test_complete_optimization_case_has_no_warnings(tmp_path):
    report = audit_case(_complete_optimization_case(tmp_path))
    assert report["warnings"] == []
    assert report["metrics"]["questions"] == 1


def test_blind_case_flags_corpus_reference(tmp_path):
    case_dir = tmp_path / "blind"
    initialize_case(case_dir, "blind", 1)
    manifest_path = case_dir / "case.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["inputs"]["sources"] = ["corpus/2025-A.md"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    codes = {item["code"] for item in audit_case(case_dir)["warnings"]}
    assert "inputs.corpus" in codes


def test_cli_warns_without_blocking_and_strict_blocks(tmp_path):
    case_dir = tmp_path / "cli"
    initialize_case(case_dir, "cli", 1)
    normal = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), str(case_dir)], capture_output=True, text=True
    )
    strict = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), str(case_dir), "--strict"],
        capture_output=True,
        text=True,
    )
    assert normal.returncode == 0
    assert "警告" in normal.stdout
    assert strict.returncode == 1
