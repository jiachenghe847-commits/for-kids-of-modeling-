import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from init_contest_case import build_manifest, initialize_case


def test_new_cases_require_evidence_and_all_content_roles():
    manifest = build_manifest("practice", 2)
    assert manifest["schema_version"] == 2
    assert manifest["evidence"] == []
    assert set(manifest["questions"][0]["paper"]["content"]) == {
        "analysis", "model", "algorithm", "results", "validation", "interpretation"}
    assert manifest["quality"]["profile"] == "reference-quality"
    assert manifest["quality"]["reviews_path"] == "reviews/review.json"


def test_initializer_never_overwrites_existing_source_without_manifest(tmp_path):
    (tmp_path / "src").mkdir()
    source = tmp_path / "src/compute.py"
    source.write_text("valuable existing work")
    with pytest.raises(FileExistsError):
        initialize_case(tmp_path, "new", 1)
    assert source.read_text() == "valuable existing work"
    assert not (tmp_path / "case.json").exists()


def test_initialization_provides_planning_and_review_stubs(tmp_path):
    initialize_case(tmp_path, "new", 1)
    assert (tmp_path / "paper/content-plan.md").is_file()
    assert json.loads((tmp_path / "reviews/review.json").read_text())["status"] == "pending"
