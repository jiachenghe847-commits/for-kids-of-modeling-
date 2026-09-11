import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def fixture(tmp_path, fontsize=12):
    from snippets.plotting.publication import export_figure
    (tmp_path / "input.json").write_text('[1, 2, 3]')
    (tmp_path / "plot.py").write_text("# plot source")
    figure, ax = plt.subplots(figsize=(6, 4))
    ax.plot([1, 2, 3], [1, 4, 9], label="measured")
    ax.set_xlabel("Time (s)", fontsize=fontsize)
    ax.set_ylabel("Distance (m)", fontsize=fontsize)
    ax.tick_params(labelsize=fontsize)
    row = export_figure(figure, tmp_path, "trajectory", ["input.json"], "plot.py",
                        units={"x": "s", "y": "m"}, evidence_ids=["e1"], width_mm=150)
    plt.close(figure)
    tex = tmp_path / "paper/paper.tex"
    tex.write_text(r"\includegraphics[width=150mm]{figures/trajectory.pdf}\label{fig:trajectory}")
    return {"figures": [row], "evidence": [{"id": "e1"}], "paper": {"tex_path": "paper/paper.tex"}}


def test_vector_export_has_preview_and_auditable_provenance(tmp_path):
    from checklist.figure_audit import audit_figures
    manifest = fixture(tmp_path)
    assert (tmp_path / "paper/figures/trajectory.pdf").read_bytes().startswith(b"%PDF")
    assert (tmp_path / "paper/figures/trajectory.png").is_file()
    assert audit_figures(tmp_path, manifest) == []


def test_changed_source_and_too_small_font_rejected(tmp_path):
    from checklist.figure_audit import audit_figures
    manifest = fixture(tmp_path, fontsize=4)
    (tmp_path / "input.json").write_text('[9]')
    codes = {x["code"] for x in audit_figures(tmp_path, manifest)}
    assert "figure.stale" in codes and "figure.font" in codes


def test_false_placement_and_unknown_evidence_rejected(tmp_path):
    from checklist.figure_audit import audit_figures
    manifest = fixture(tmp_path)
    manifest["figures"][0]["width_mm"] = 300
    manifest["figures"][0]["evidence_ids"] = ["missing"]
    codes = {x["code"] for x in audit_figures(tmp_path, manifest)}
    assert "figure.placement" in codes and "figure.evidence" in codes


def test_export_never_overwrites_existing_image(tmp_path):
    from snippets.plotting.publication import export_figure
    fixture(tmp_path)
    fig = plt.figure()
    with pytest.raises(FileExistsError):
        export_figure(fig, tmp_path, "trajectory", ["input.json"], "plot.py",
                      units={"x": "s"}, evidence_ids=["e1"])
    plt.close(fig)
