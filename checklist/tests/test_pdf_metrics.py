import json
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pdf_metrics import build_reference_profile, measure_pdf


SCRIPT = Path(__file__).resolve().parents[1] / "pdf_metrics.py"


def _make_pdf(path: Path, pages: list[list[str]]) -> Path:
    with PdfPages(path) as pdf:
        for lines in pages:
            figure = plt.figure(figsize=(6, 8))
            for index, line in enumerate(lines):
                figure.text(0.08, 0.92 - index * 0.07, line, fontsize=12)
            pdf.savefig(figure)
            plt.close(figure)
    return path


def test_explicit_boundaries_measure_hand_counted_body_and_unique_captions(tmp_path):
    """A wrong slice, character rule, or caption deduplication must change literals below."""
    pdf = _make_pdf(
        tmp_path / "paper.pdf",
        [
            ["COVER 999"],
            ["ABSTRACT", "Alpha 123", "KEYWORDS"],
            [
                "BODY_START",
                "Model A1",
                "Figure 1 Result plot",
                "As Figure 1 shows",
                "Figure 1 Result plot",
                "Figure 1(a) subpart",
                "Table 2 Data summary",
                "Table 2 Data summary",
                "BODY_END",
                "References",
                "Figure 99 cited",
            ],
            ["APPENDIX", "Appendix 777"],
        ],
    )

    result = measure_pdf(
        pdf,
        {
            "body_start_page": 2,
            "body_end_page": 3,
            "appendix_start_page": 4,
            "body_start_text": "ABSTRACT",
            "body_end_text": "BODY_END",
        },
    )

    assert result["issues"] == []
    assert result["pdf_sha256"] and len(result["pdf_sha256"]) == 64
    assert result["metrics"] == {
        "total_pages": 4,
        "body_pages": 2,
        "body_chars": 137,
        "figures": 1,
        "tables": 1,
        "appendix_pages": 1,
        "abstract_chars": 8,
    }


def test_clear_abstract_and_references_headings_are_auto_detected(tmp_path):
    """Removing automatic heading detection must leave body metrics unavailable."""
    pdf = _make_pdf(
        tmp_path / "auto.pdf",
        [
            ["Cover"],
            ["ABSTRACT", "Alpha 123", "KEYWORDS", "Introduction", "First body"],
            ["Conclusion", "Last body"],
            ["References", "One citation 2023"],
        ],
    )

    result = measure_pdf(pdf)

    assert result["issues"] == []
    assert result["metrics"]["body_pages"] == 2
    assert result["metrics"]["appendix_pages"] == 0
    assert result["metrics"]["abstract_chars"] == 8
    assert result["metrics"]["body_chars"] == 63


def test_unclear_boundaries_return_null_body_metrics_and_review_issue(tmp_path):
    """Guessing that an arbitrary page is the body would make this test fail."""
    pdf = _make_pdf(tmp_path / "unclear.pdf", [["Just a note 123"]])

    result = measure_pdf(pdf)

    assert result["metrics"]["total_pages"] == 1
    for key in ("body_pages", "body_chars", "figures", "tables", "appendix_pages", "abstract_chars"):
        assert result["metrics"][key] is None
    assert {issue["code"]: issue["status"] for issue in result["issues"]} == {
        "body_boundary_needs_review": "needs_review"
    }


def test_empty_extracted_body_is_unknown_not_zero(tmp_path):
    """Treating a scanned/empty extraction as measured zero must fail this test."""
    pdf = _make_pdf(tmp_path / "empty.pdf", [[]])

    result = measure_pdf(pdf, {"body_start_page": 1, "body_end_page": 1})

    assert result["metrics"]["body_pages"] == 1
    for key in ("body_chars", "figures", "tables", "abstract_chars"):
        assert result["metrics"][key] is None
    assert any(
        issue["code"] == "text_extraction_uncertain" and issue["status"] == "needs_review"
        for issue in result["issues"]
    )


def test_invalid_boundaries_and_bad_files_fail_cleanly(tmp_path):
    """Boundary inversions and malformed inputs must not raise or invent metrics."""
    pdf = _make_pdf(tmp_path / "valid.pdf", [["Body"]])
    inverted = measure_pdf(pdf, {"body_start_page": 2, "body_end_page": 1})
    assert inverted["metrics"]["body_chars"] is None
    assert any(issue["code"] == "invalid_boundaries" and issue["status"] == "fail" for issue in inverted["issues"])

    malformed_path = tmp_path / "bad.pdf"
    malformed_path.write_bytes(b"not a pdf")
    malformed = measure_pdf(malformed_path)
    missing = measure_pdf(tmp_path / "missing.pdf")
    assert any(issue["code"] == "invalid_pdf" and issue["status"] == "fail" for issue in malformed["issues"])
    assert any(issue["code"] == "missing_pdf" and issue["status"] == "fail" for issue in missing["issues"])


def test_reference_profile_uses_only_reliable_per_topic_samples(tmp_path):
    """Pooling topics or admitting an unreliable sixth value must change the profile."""
    records = []
    for index, value in enumerate((10, 20, 30, 40, 50), start=1):
        records.append(
            {
                "topic_type": "optimization",
                "source": f"official-{index}",
                "pdf_sha256": f"hash-{index}",
                "reliability": "reliable",
                "metrics": {"body_chars": value},
            }
        )
    records.extend(
        [
            {
                "topic_type": "optimization",
                "source": "bad-extraction",
                "pdf_sha256": "bad-hash",
                "reliability": "needs_review",
                "metrics": {"body_chars": 10000},
            },
            {
                "topic_type": "prediction",
                "source": "only-one",
                "pdf_sha256": "one-hash",
                "reliability": True,
                "metrics": {"body_chars": 999},
            },
        ]
    )

    profile = build_reference_profile(records, min_samples=5)

    assert "pooled" not in profile
    body = profile["profiles"]["optimization"]["metrics"]["body_chars"]
    assert body == {
        "sample_count": 5,
        "status": "calibrated",
        "q1": 20.0,
        "median": 30.0,
        "q3": 40.0,
    }
    sparse = profile["profiles"]["prediction"]["metrics"]["body_chars"]
    assert sparse == {
        "sample_count": 1,
        "status": "insufficient_evidence",
        "q1": None,
        "median": None,
        "q3": None,
    }
    assert profile["profiles"]["optimization"]["records"][0] == {
        "source": "official-1",
        "pdf_sha256": "hash-1",
    }


def test_reference_profile_requires_identity_and_handles_singleton_quartiles():
    """Identity-free records must not calibrate a profile; min_samples=1 must still work."""
    profile = build_reference_profile(
        [
            {
                "topic_type": "evaluation",
                "source": "official-one",
                "pdf_sha256": "hash-one",
                "reliability": "verified",
                "metrics": {"figures": 7},
            },
            {
                "topic_type": "evaluation",
                "source": "missing-hash",
                "reliability": "verified",
                "metrics": {"figures": 999},
            },
        ],
        min_samples=1,
    )

    figures = profile["profiles"]["evaluation"]["metrics"]["figures"]
    assert figures == {
        "sample_count": 1,
        "status": "calibrated",
        "q1": 7.0,
        "median": 7.0,
        "q3": 7.0,
    }


def test_cli_accepts_boundary_json_and_prints_json(tmp_path):
    """A CLI that does not share the library pipeline must fail this integration test."""
    pdf = _make_pdf(tmp_path / "cli.pdf", [["ABSTRACT", "Text 7", "KEYWORDS"]])
    boundaries = tmp_path / "boundaries.json"
    boundaries.write_text(
        json.dumps({"body_start_page": 1, "body_end_page": 1}), encoding="utf-8"
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(pdf), "--boundaries", str(boundaries)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["metrics"]["total_pages"] == 1
    assert payload["metrics"]["body_chars"] == 21
