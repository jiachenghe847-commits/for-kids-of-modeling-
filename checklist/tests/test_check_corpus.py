import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_corpus import scan_corpus


def test_scan_corpus_reads_yaml_front_matter(tmp_path):
    paper = tmp_path / "2020-A.md"
    paper.write_text(
        "---\nyear: 2020\nproblem: A\naward: 国家一等奖\n"
        "source_url: https://example.com\n---\n\n正文\n",
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
