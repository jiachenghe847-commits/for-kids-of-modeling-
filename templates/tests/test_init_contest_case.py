import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from init_contest_case import build_manifest, initialize_case


def test_build_manifest_creates_question_cards():
    manifest = build_manifest("2026-A", 3)
    assert manifest["case_id"] == "2026-A"
    assert manifest["inputs"]["mode"] == "official-only"
    assert [item["id"] for item in manifest["questions"]] == ["Q1", "Q2", "Q3"]
    assert all(item["interpretation"]["ambiguities_reviewed"] is False for item in manifest["questions"])


def test_initialize_case_creates_traceable_workspace(tmp_path):
    target = tmp_path / "case"
    path = initialize_case(target, "2026-B", 2)
    manifest = json.loads(path.read_text(encoding="utf-8"))

    assert len(manifest["questions"]) == 2
    assert (target / "official_input").is_dir()
    assert (target / "artifacts" / "runs").is_dir()
    assert (target / "src" / "compute.py").is_file()
    assert (target / "paper" / "gen_paper.py").is_file()
    assert "NotImplementedError" in (target / "src" / "compute.py").read_text(encoding="utf-8")


def test_initialize_case_refuses_to_overwrite_manifest(tmp_path):
    target = tmp_path / "case"
    initialize_case(target, "2026-C", 1)
    with pytest.raises(FileExistsError):
        initialize_case(target, "2026-C", 1)


def test_build_manifest_rejects_zero_questions():
    with pytest.raises(ValueError):
        build_manifest("invalid", 0)
