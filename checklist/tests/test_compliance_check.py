import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compliance_check import check_tex


def test_check_tex_flags_missing_abstract(tmp_path):
    tex = tmp_path / "paper.tex"
    tex.write_text(r"\documentclass{article}\begin{document}\section{正文}\end{document}", encoding="utf-8")
    result = check_tex(str(tex))
    assert any("abstract" in issue for issue in result["issues"])


def test_check_tex_flags_figure_without_caption(tmp_path):
    tex = tmp_path / "paper.tex"
    tex.write_text(
        r"\begin{abstract}x\end{abstract}"
        r"\begin{figure}\includegraphics{a.png}\end{figure}",
        encoding="utf-8",
    )
    result = check_tex(str(tex))
    assert any("caption" in issue for issue in result["issues"])


def test_check_tex_passes_clean_document(tmp_path):
    tex = tmp_path / "paper.tex"
    tex.write_text(
        r"\begin{abstract}x\end{abstract}"
        r"\begin{figure}\includegraphics{a.png}\caption{示意图}\end{figure}",
        encoding="utf-8",
    )
    result = check_tex(str(tex))
    assert result["issues"] == []
