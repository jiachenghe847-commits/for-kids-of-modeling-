import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_tex_cjk_counts_are_not_judged_against_pdf_alphanumeric_mean(tmp_path):
    from checklist.paper_completeness import completeness_report
    paper = tmp_path / "paper.tex"
    paper.write_text(r"\section{模型建立}ABC123中文")
    row = next(x for x in completeness_report(paper)["items"] if x["key"] == "body_chars")
    assert row["verdict"] == "仅测量"
    assert row["band"] is None
