import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_corpus import scan_corpus


def test_scan_corpus_reads_yaml_front_matter(tmp_path):
    paper = tmp_path / "2020-A.md"
    paper.write_text(
        "---\nyear: 2020\nproblem: A\naward: 国家一等奖\n"
        "source_url: https://example.com\npaper_title: 示例论文\ncompleteness: full\n---\n\n正文\n",
        encoding="utf-8",
    )
    result = scan_corpus(str(tmp_path))
    assert len(result) == 1
    assert result[0]["year"] == 2020
    assert result[0]["problem"] == "A"
    assert result[0]["award"] == "国家一等奖"


def test_scan_corpus_skips_non_markdown(tmp_path):
    (tmp_path / "_fetch-log.md").write_text("---\nyear: x\n---\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")
    result = scan_corpus(str(tmp_path))
    assert result == []


def test_scan_corpus_skips_incomplete_metadata(tmp_path, capsys):
    paper = tmp_path / "2023-A.md"
    paper.write_text("---\nyear: 2023\nproblem: A\n---\n\n正文\n", encoding="utf-8")
    assert scan_corpus(str(tmp_path)) == []
    assert "award" in capsys.readouterr().err


def test_scan_corpus_accepts_official_local_source(tmp_path):
    paper = tmp_path / "A092.md"
    paper.write_text(
        "---\nyear: 2023\nproblem: A\naward: 官方优秀论文\n"
        "source_path: 建模/2023/A092.pdf\npaper_title: 定日镜场的优化设计\n"
        "completeness: full\n---\n\n正文\n",
        encoding="utf-8",
    )
    result = scan_corpus(str(tmp_path))
    assert len(result) == 1
    assert result[0]["source_path"].endswith("A092.pdf")
