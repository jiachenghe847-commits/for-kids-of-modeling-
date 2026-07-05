from docx import Document

_HEADINGS = [
    "摘要", "问题重述", "问题分析", "模型假设", "符号说明",
    "模型的建立与求解", "灵敏度分析", "模型评价与推广", "参考文献",
]


def build_template(out_path: str) -> None:
    doc = Document()
    doc.add_heading("论文标题", level=0)
    for heading in _HEADINGS:
        doc.add_heading(heading, level=1)
        doc.add_paragraph("（占位段落，赛时替换为正文）")
    doc.save(out_path)


if __name__ == "__main__":
    import sys

    build_template(sys.argv[1] if len(sys.argv) > 1 else "paper_template.docx")
