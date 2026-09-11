import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
ROOT = Path(__file__).resolve().parents[2]


def make_case(tmp_path):
    (tmp_path / "official_input").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "official_input/input.txt").write_text("2")
    (tmp_path / "src/compute.py").write_text(
        "from pathlib import Path\nimport json\n"
        "x=int(Path('official_input/input.txt').read_text())\n"
        "Path('artifacts/results.json').write_text(json.dumps({'answer': x*x}))\n")
    manifest = {"schema_version": 2, "quality": {"run_record_path": "artifacts/run-record.json"},
                "results_path": "artifacts/results.json", "inputs": {"mode": "official-only", "sources": []}}
    (tmp_path / "case.json").write_text(json.dumps(manifest))
    return manifest


def test_explicit_run_records_real_repetition_and_detects_later_edits(tmp_path):
    from checklist.run_audit import audit_run
    manifest = make_case(tmp_path)
    completed = subprocess.run([sys.executable, str(ROOT / "tools/record_run.py"), str(tmp_path),
                                "--repeat", "2", "--", sys.executable, "src/compute.py"], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    record = json.loads((tmp_path / "artifacts/run-record.json").read_text())
    assert len(record["runs"]) == 2
    assert record["reproducible"] is True
    # Local execution is honestly not treated as an isolated blind run.
    assert {i["code"] for i in audit_run(tmp_path, manifest)} == {"run.isolation"}
    (tmp_path / "artifacts/results.json").write_text('{"answer":999}')
    assert "run.stale" in {i["code"] for i in audit_run(tmp_path, manifest)}


def test_failed_process_cannot_be_marked_reproducible(tmp_path):
    make_case(tmp_path)
    completed = subprocess.run([sys.executable, str(ROOT / "tools/record_run.py"), str(tmp_path),
                                "--repeat", "2", "--", sys.executable, "-c", "raise SystemExit(3)"], capture_output=True, text=True)
    assert completed.returncode != 0
    record = json.loads((tmp_path / "artifacts/run-record.json").read_text())
    assert record["reproducible"] is False


def test_pending_or_stale_reviews_never_pass(tmp_path):
    from checklist.review_audit import audit_review, snapshot_files
    make_case(tmp_path)
    (tmp_path / "reviews").mkdir()
    manifest = {"quality": {"reviews_path": "reviews/review.json"}, "figures": []}
    path = tmp_path / "reviews/review.json"
    path.write_text('{"status":"pending"}')
    assert "review.pending" in {i["code"] for i in audit_review(tmp_path, manifest, 1)}
    record = {"status": "complete", "reviewer": "independent-reader", "snapshot": snapshot_files(tmp_path),
              "scores": {key: {"score": 4, "reference_score": 4, "location": "page 1", "reason": "checked"}
                         for key in ("model", "algorithm", "validation", "figures", "organization")},
              "pages_reviewed": [1], "figures_reviewed": [], "findings": []}
    path.write_text(json.dumps(record))
    assert audit_review(tmp_path, manifest, 1) == []
    (tmp_path / "src/compute.py").write_text("changed")
    assert "review.stale" in {i["code"] for i in audit_review(tmp_path, manifest, 1)}


def test_reviews_require_every_page_and_each_rubric_dimension(tmp_path):
    from checklist.review_audit import audit_review, snapshot_files
    make_case(tmp_path)
    (tmp_path / "reviews").mkdir()
    manifest = {"quality": {"reviews_path": "reviews/review.json"}, "figures": [{"id": "f1"}]}
    (tmp_path / "reviews/review.json").write_text(json.dumps({"status": "complete", "reviewer": "r",
        "snapshot": snapshot_files(tmp_path), "scores": {}, "pages_reviewed": [1], "figures_reviewed": [], "findings": []}))
    codes = {i["code"] for i in audit_review(tmp_path, manifest, 2)}
    assert {"review.pages", "review.figures", "review.scores"} <= codes
