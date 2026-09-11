"""Reject plausible-looking but empty, stale, or numerically false evidence."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def fixture(tmp_path, kind="validation", data=None):
    for name, content in (("input.txt", "observations"), ("compute.py", "# implementation")):
        (tmp_path / name).write_text(content)
    (tmp_path / "e.json").write_text(json.dumps(data if data is not None else {
        "units": {"error": "m"}, "checks": [{"name": "analytic", "observed": 0.01,
        "expected": 0, "atol": 0.02, "rtol": 0, "unit": "m"}],
    }))
    hashes = {p: hashlib.sha256((tmp_path / p).read_bytes()).hexdigest()
              for p in ("input.txt", "compute.py", "e.json")}
    units = (data or {}).get("units", {"error": "m"})
    entry = {"id": "v1", "question_id": "Q1", "kind": kind, "path": "e.json",
             "sha256": hashes["e.json"], "producer": "compute.py",
             "producer_sha256": hashes["compute.py"], "input_hashes": {"input.txt": hashes["input.txt"]},
             "units": units}
    return {"schema_version": 2, "questions": [{"id": "Q1"}], "evidence": [entry]}


def audit(tmp_path, manifest):
    from checklist.evidence_audit import audit_evidence
    return audit_evidence(tmp_path, manifest)


def test_valid_numeric_check_is_accepted(tmp_path):
    assert audit(tmp_path, fixture(tmp_path)) == []


@pytest.mark.parametrize("data", [{}, {"x": float("nan")}, {"units": {"error": "m"}, "checks": []}])
def test_empty_nonfinite_and_empty_checks_cannot_pass(tmp_path, data):
    assert any(i["status"] == "fail" for i in audit(tmp_path, fixture(tmp_path, data=data)))


def test_changing_raw_input_invalidates_evidence(tmp_path):
    manifest = fixture(tmp_path)
    (tmp_path / "input.txt").write_text("changed")
    assert "evidence.stale" in {i["code"] for i in audit(tmp_path, manifest)}


def test_false_pass_boolean_does_not_override_numeric_failure(tmp_path):
    manifest = fixture(tmp_path, data={"units": {"error": "m"}, "checks": [
        {"name": "wrong", "observed": 5, "expected": 0, "atol": 0.01,
         "rtol": 0, "unit": "m", "passed": True}]})
    assert "evidence.validation_failed" in {i["code"] for i in audit(tmp_path, manifest)}


def test_unit_mismatch_rejected(tmp_path):
    manifest = fixture(tmp_path)
    manifest["evidence"][0]["units"] = {"error": "cm"}
    assert "evidence.units" in {i["code"] for i in audit(tmp_path, manifest)}


def test_multi_seed_requires_distinct_seeds(tmp_path):
    manifest = fixture(tmp_path, "multi_seed", {"units": {"error": "m"},
        "runs": [{"seed": 1, "value": 1}, {"seed": 1, "value": 1}, {"seed": 2, "value": 2}]})
    assert "evidence.seeds" in {i["code"] for i in audit(tmp_path, manifest)}


def test_escape_path_and_unknown_kind_are_rejected(tmp_path):
    manifest = fixture(tmp_path)
    manifest["evidence"][0]["path"] = "../outside.json"
    assert any(i["status"] == "fail" for i in audit(tmp_path, manifest))
    manifest["evidence"][0]["path"] = "e.json"
    manifest["evidence"][0]["kind"] = "made_up"
    assert "evidence.kind" in {i["code"] for i in audit(tmp_path, manifest)}


def test_constraint_violation_not_masked_by_positive_residual_convention(tmp_path):
    manifest = fixture(tmp_path, "constraints", {"units": {"error": "m"}, "constraints": [
        {"name": "capacity", "lhs": 12, "rhs": 10, "sense": "<=", "atol": 0, "unit": "m"}]})
    assert "evidence.constraint_failed" in {i["code"] for i in audit(tmp_path, manifest)}


def test_convergence_requires_ordered_nonempty_trace(tmp_path):
    manifest = fixture(tmp_path, "convergence", {"units": {"error": "m"},
        "iterations": [1, 0], "values": [2, 1], "termination_reason": "budget"})
    assert "evidence.trace" in {i["code"] for i in audit(tmp_path, manifest)}


def test_time_limited_optimization_cannot_claim_optimum(tmp_path):
    data = {
        "units": {"objective": "count"},
        "solver": "highs-milp",
        "termination_reason": "time_limit",
        "objective_sense": "max",
        "incumbent_feasible": True,
        "optimality_proven": False,
        "claims_optimal": True,
        "objective": 119,
        "relative_gap": 0.12,
    }
    manifest = fixture(tmp_path, "optimization", data)
    codes = {i["code"] for i in audit(tmp_path, manifest)}
    assert "evidence.optimality_claim" in codes


def test_closed_optimization_evidence_is_accepted(tmp_path):
    data = {
        "units": {"objective": "count"},
        "solver": "highs-milp",
        "termination_reason": "optimal",
        "objective_sense": "max",
        "incumbent_feasible": True,
        "optimality_proven": True,
        "claims_optimal": True,
        "objective": 119,
        "relative_gap": 0,
    }
    assert audit(tmp_path, fixture(tmp_path, "optimization", data)) == []
