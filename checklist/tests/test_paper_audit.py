import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def case(tmp_path):
    roles = ("analysis", "model", "algorithm", "results", "validation", "interpretation")
    (tmp_path / "paper").mkdir()
    (tmp_path / "results.json").write_text(json.dumps({"answer": {"value": 1.23456, "unit": "m"}}))
    manifest = {"results_path": "results.json", "evidence": [{"id": "e1", "question_id": "Q1"}],
        "questions": [{"id": "Q1", "paper": {"content": {
            r: {"label": "q1:" + r, "notes": "explain and substantiate", "evidence_ids": ["e1"]}
            for r in roles}}}],
        "claims": [{"id": "height", "question_id": "Q1", "result_pointer": "/answer",
                    "format": ".3f", "unit": "m", "evidence_ids": ["e1"], "label": "q1:results"}],
        "paper": {"tex_path": "paper/paper.tex", "bindings_path": "paper/results-values.tex"}}
    text = "\\input{results-values.tex}\n" + "\n".join(
        "\\subsection{" + r + "}\\label{q1:" + r + "}\nSufficient prose for the specific section."
        for r in roles) + "\n\\ResultValue{height}"
    (tmp_path / "paper/paper.tex").write_text(text)
    return manifest


def render(tmp_path, manifest):
    from templates.result_bindings import render_bindings
    return render_bindings(tmp_path, manifest)


def audit(tmp_path, manifest):
    from checklist.paper_audit import audit_paper
    return audit_paper(tmp_path, manifest)


def test_results_are_formatted_from_single_source(tmp_path):
    manifest = case(tmp_path)
    text = render(tmp_path, manifest)
    assert "{1.235}" in text
    (tmp_path / "paper/results-values.tex").write_text(text)
    assert audit(tmp_path, manifest) == []


def test_edited_binding_is_rejected(tmp_path):
    manifest = case(tmp_path)
    (tmp_path / "paper/results-values.tex").write_text(render(tmp_path, manifest).replace("1.235", "9.999"))
    assert "paper.bindings_stale" in {x["code"] for x in audit(tmp_path, manifest)}


def test_missing_roles_and_unknown_evidence_cannot_pass(tmp_path):
    manifest = case(tmp_path)
    (tmp_path / "paper/results-values.tex").write_text(render(tmp_path, manifest))
    manifest["questions"][0]["paper"]["content"]["algorithm"]["label"] = "not-in-paper"
    manifest["questions"][0]["paper"]["content"]["validation"]["evidence_ids"] = ["missing"]
    codes = {x["code"] for x in audit(tmp_path, manifest)}
    assert "paper.content" in codes and "paper.evidence" in codes


def test_commented_out_content_label_and_unused_result_rejected(tmp_path):
    manifest = case(tmp_path)
    (tmp_path / "paper/results-values.tex").write_text(render(tmp_path, manifest))
    path = tmp_path / "paper/paper.tex"
    path.write_text(path.read_text().replace("\\label{q1:algorithm}", "% \\label{q1:algorithm}")
                    .replace("\\ResultValue{height}", "% \\ResultValue{height}"))
    codes = {x["code"] for x in audit(tmp_path, manifest)}
    assert "paper.content" in codes and "paper.claim_unused" in codes


def test_results_unit_mismatch_rejected(tmp_path):
    manifest = case(tmp_path)
    (tmp_path / "paper/results-values.tex").write_text(render(tmp_path, manifest))
    manifest["claims"][0]["unit"] = "cm"
    assert "paper.bindings_invalid" in {x["code"] for x in audit(tmp_path, manifest)}


def test_missing_nested_input_is_reported(tmp_path):
    manifest = case(tmp_path)
    (tmp_path / "paper/results-values.tex").write_text(render(tmp_path, manifest))
    path = tmp_path / "paper/paper.tex"
    path.write_text(path.read_text() + "\n\\input{missing-section}")
    assert "paper.source" in {x["code"] for x in audit(tmp_path, manifest)}
