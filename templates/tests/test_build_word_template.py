import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_word_template import build_template

EXPECTED_HEADINGS = [
    "摘要", "问题重述", "问题分析", "模型假设", "符号说明",
    "模型的建立与求解", "灵敏度分析", "模型评价与推广", "参考文献",
]


def test_build_template_creates_all_headings(tmp_path):
    out = tmp_path / "paper_template.docx"
    build_template(str(out))
    from docx import Document

    doc = Document(str(out))
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    for expected in EXPECTED_HEADINGS:
        assert expected in headings
