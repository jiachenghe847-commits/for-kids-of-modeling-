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
        r"\author{}"
        r"\begin{figure}\includegraphics{a.png}\caption{示意图}\end{figure}"
        r"本参赛队未使用任何AI工具。",
        encoding="utf-8",
    )
    result = check_tex(str(tex))
    assert result["issues"] == []


def test_check_tex_flags_identity_fields(tmp_path):
    tex = tmp_path / "paper.tex"
    tex.write_text(
        r"\begin{abstract}x\end{abstract}\author{张三}\hypersetup{pdfauthor={张三}}"
        r"参赛编号：20260001 本参赛队未使用任何AI工具。",
        encoding="utf-8",
    )
    issues = check_tex(str(tex))["issues"]
    assert any("author" in issue for issue in issues)
    assert any("身份字段" in issue for issue in issues)


def test_check_tex_flags_missing_ai_disclosure(tmp_path):
    tex = tmp_path / "paper.tex"
    tex.write_text(r"\begin{abstract}x\end{abstract}\author{}", encoding="utf-8")
    issues = check_tex(str(tex))["issues"]
    assert any("AI" in issue for issue in issues)


def test_check_tex_requires_ai_reference_metadata(tmp_path):
    tex = tmp_path / "paper.tex"
    tex.write_text(
        r"\begin{abstract}x\end{abstract}\author{}"
        r"\section*{AI工具使用声明}本参赛队使用 Codex 辅助整理文字。",
        encoding="utf-8",
    )
    issues = check_tex(str(tex))["issues"]
    assert any("参考文献" in issue for issue in issues)


def test_check_tex_accepts_complete_ai_disclosure(tmp_path):
    tex = tmp_path / "paper.tex"
    tex.write_text(
        r"\begin{abstract}x\end{abstract}\author{}"
        r"\section*{AI工具使用声明}本参赛队使用 Codex 辅助整理文字。"
        r"\begin{thebibliography}{9}\bibitem{ai} OpenAI. Codex CLI 0.146.0, 使用日期: 2026-08-02."
        r"\end{thebibliography}",
        encoding="utf-8",
    )
    assert check_tex(str(tex))["issues"] == []


def test_comments_do_not_trigger_or_satisfy_checks(tmp_path):
    tex = tmp_path / "paper.tex"
    tex.write_text(
        "\\begin{abstract}x\\end{abstract}\n\\author{}\n"
        "% 参赛编号：在这里填写\n% 本参赛队未使用任何AI工具\n",
        encoding="utf-8",
    )
    issues = check_tex(str(tex))["issues"]
    assert not any("身份字段" in issue for issue in issues)
    assert any("AI" in issue for issue in issues)
