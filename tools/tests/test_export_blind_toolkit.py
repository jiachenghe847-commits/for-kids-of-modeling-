from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "tools" / "export_blind_toolkit.py"


def load_exporter():
    spec = importlib.util.spec_from_file_location("export_blind_toolkit", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load export_blind_toolkit")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_export_copies_only_curated_runtime(tmp_path):
    exporter = load_exporter()
    target = tmp_path / "blind-toolkit"

    manifest = exporter.export_toolkit(REPO_ROOT, target)

    assert (target / "requirements.txt").is_file()
    assert (target / "runtime" / "WORKFLOW.md").is_file()
    assert (target / "templates" / "init_contest_case.py").is_file()
    assert (target / "snippets" / "linear_programming" / "model.py").is_file()
    assert not (target / "corpus").exists()
    assert not (target / "drills").exists()
    assert not (target / "analysis").exists()
    assert not any(target.rglob("test_*.py"))
    assert manifest["format_version"] == 1
    assert manifest["files"]
    assert manifest["toolkit_sha256"]
