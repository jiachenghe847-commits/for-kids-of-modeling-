import sys
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pdf_review import render_pdf, review_pdf


def _make_pdf(path: Path, pages: list[list[str]]) -> Path:
    with PdfPages(path) as pdf:
        for lines in pages:
            figure = plt.figure(figsize=(6, 8))
            for index, line in enumerate(lines):
                figure.text(0.08, 0.92 - index * 0.07, line, fontsize=12)
            pdf.savefig(figure)
            plt.close(figure)
    return path


def test_review_reports_log_defects_possible_blank_and_visual_gate(tmp_path):
    """Dropping any required diagnostic or claiming visual completion must fail."""
    pdf = _make_pdf(tmp_path / "paper.pdf", [["Visible page"], []])
    log = tmp_path / "paper.log"
    log.write_text(
        "Missing character: There is no X in font Test!\n"
        "LaTeX Warning: Reference `missing' on page 1 undefined on input line 2.\n"
        "Overfull \\hbox (4.0pt too wide) in paragraph at lines 3--4\n",
        encoding="utf-8",
    )

    result = review_pdf(pdf, log)

    assert result["pages"] == 2
    assert result["pdf_sha256"] and len(result["pdf_sha256"]) == 64
    codes = {issue["code"]: issue["status"] for issue in result["issues"]}
    assert codes == {
        "missing_glyph": "fail",
        "undefined_reference": "fail",
        "overfull_box": "needs_review",
        "possible_blank_page": "needs_review",
        "visual_inspection_required": "needs_review",
    }
    assert "2" in next(issue["message"] for issue in result["issues"] if issue["code"] == "possible_blank_page")


def test_review_handles_missing_invalid_pdf_and_missing_requested_log(tmp_path):
    """Bad inputs must be structured failures rather than uncaught subprocess errors."""
    missing = review_pdf(tmp_path / "missing.pdf")
    assert missing["pages"] is None
    assert missing["pdf_sha256"] is None
    assert missing["issues"][0]["code"] == "missing_pdf"
    assert missing["issues"][0]["status"] == "fail"

    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    invalid = review_pdf(bad)
    assert invalid["pages"] is None
    assert any(issue["code"] == "invalid_pdf" and issue["status"] == "fail" for issue in invalid["issues"])

    pdf = _make_pdf(tmp_path / "good.pdf", [["Page"]])
    missing_log = review_pdf(pdf, tmp_path / "absent.log")
    assert any(issue["code"] == "missing_log" and issue["status"] == "fail" for issue in missing_log["issues"])


def test_render_writes_page_images_and_contact_sheet_to_new_directory(tmp_path):
    """Breaking page export or contact-sheet assembly must fail on real output files."""
    pdf = _make_pdf(tmp_path / "paper.pdf", [["Page one"], ["Page two"]])
    output = tmp_path / "rendered"

    result = render_pdf(pdf, output, dpi=40)

    assert result["pages"] == 2
    assert result["output_dir"] == str(output)
    page_images = [Path(path) for path in result["page_images"]]
    assert [path.name for path in page_images] == ["page-1.png", "page-2.png"]
    assert all(path.is_file() for path in page_images)
    contact_sheet = Path(result["contact_sheet"])
    assert contact_sheet.is_file()
    with Image.open(contact_sheet) as image:
        assert image.width > 0 and image.height > 0

    with pytest.raises(FileExistsError):
        render_pdf(pdf, output, dpi=40)
