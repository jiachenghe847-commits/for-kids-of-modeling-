"""Measure submission PDFs and aggregate like-for-like reference profiles.

Both candidates and references use the same Poppler text extraction and the
same CJK/Latin-letter/digit counting rule.  Page boundaries may be supplied as
a mapping or JSON file.  ``body_start_text`` and ``body_end_text`` optionally
cut a shared boundary page at the first exact occurrence of the marker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


_METRIC_KEYS = (
    "total_pages",
    "body_pages",
    "body_chars",
    "figures",
    "tables",
    "appendix_pages",
    "abstract_chars",
)
_PROFILE_METRICS = _METRIC_KEYS
_COUNTED_CHARACTER = re.compile(r"[A-Za-z0-9\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_ABSTRACT_HEADING = re.compile(r"(?im)^\s*(?:ABSTRACT|\u6458\s*\u8981)\s*$")
_REFERENCE_HEADING = re.compile(
    r"(?im)^\s*(?:REFERENCES?|BIBLIOGRAPHY|\u53c2\s*\u8003\s*\u6587\s*\u732e)\s*$"
)
_APPENDIX_HEADING = re.compile(r"(?im)^\s*(?:APPENDIX(?:ES)?|\u9644\s*\u5f55)(?:\s+[A-Z0-9]+)?\s*$")
_KEYWORDS_HEADING = re.compile(
    r"(?im)^\s*(?:KEY\s*WORDS?|\u5173\s*\u952e\s*\u8bcd)\s*[:\uff1a]?"
)
_FIGURE_CAPTION = re.compile(
    r"^\s*(?:Figure|Fig\.?|\u56fe)\s*(\d+(?:[.\-]\d+)*)"
    r"(?:\s*\([A-Za-z0-9]+\))?(?:\s*[:\uff1a.\-]?\s+)(\S.*)$",
    re.IGNORECASE,
)
_TABLE_CAPTION = re.compile(
    r"^\s*(?:Table|\u8868)\s*(\d+(?:[.\-]\d+)*)"
    r"(?:\s*\([A-Za-z0-9]+\))?(?:\s*[:\uff1a.\-]?\s+)(\S.*)$",
    re.IGNORECASE,
)


def _issue(code: str, message: str, status: str) -> dict[str, str]:
    return {"code": code, "message": message, "status": status}


def _empty_metrics(total_pages: int | None = None) -> dict[str, int | None]:
    metrics: dict[str, int | None] = {key: None for key in _METRIC_KEYS}
    metrics["total_pages"] = total_pages
    return metrics


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_poppler(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=60,
    )


def _extract_pdf(path: Path) -> tuple[int, list[str]]:
    info = _run_poppler(["pdfinfo", str(path)])
    if info.returncode != 0:
        raise ValueError(info.stderr.strip() or "pdfinfo could not read the file")
    match = re.search(r"(?m)^Pages:\s*(\d+)\s*$", info.stdout)
    if not match or int(match.group(1)) < 1:
        raise ValueError("pdfinfo did not report a positive page count")
    total_pages = int(match.group(1))

    extracted = _run_poppler(["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"])
    if extracted.returncode != 0:
        raise ValueError(extracted.stderr.strip() or "pdftotext could not read the file")
    pages = extracted.stdout.split("\f")
    if len(pages) > total_pages and not pages[-1].strip():
        pages.pop()
    if len(pages) < total_pages:
        pages.extend([""] * (total_pages - len(pages)))
    elif len(pages) > total_pages:
        pages = pages[: total_pages - 1] + ["\f".join(pages[total_pages - 1 :])]
    return total_pages, pages


def _load_boundaries(boundaries: Mapping[str, Any] | str | Path | None) -> dict[str, Any] | None:
    if boundaries is None:
        return None
    if isinstance(boundaries, Mapping):
        return dict(boundaries)
    path = Path(boundaries)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read boundary JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("boundary JSON must contain an object")
    return payload


def _heading_matches(pattern: re.Pattern[str], pages: Sequence[str]) -> list[tuple[int, re.Match[str]]]:
    matches: list[tuple[int, re.Match[str]]] = []
    for page_index, text in enumerate(pages):
        matches.extend((page_index, match) for match in pattern.finditer(text))
    return matches


def _auto_boundaries(pages: Sequence[str]) -> dict[str, Any] | None:
    abstracts = _heading_matches(_ABSTRACT_HEADING, pages)
    if len(abstracts) != 1:
        return None
    start_index, abstract = abstracts[0]
    references = [item for item in _heading_matches(_REFERENCE_HEADING, pages) if item[0] >= start_index]
    appendices = [item for item in _heading_matches(_APPENDIX_HEADING, pages) if item[0] >= start_index]
    endings = [(page, match, "reference") for page, match in references]
    endings.extend((page, match, "appendix") for page, match in appendices)
    if not endings:
        return None
    end_index, end_match, _kind = min(endings, key=lambda item: (item[0], item[1].start()))
    appendix_start = min((page + 1 for page, _ in appendices), default=None)
    result: dict[str, Any] = {
        "body_start_page": start_index + 1,
        "body_end_page": end_index + 1,
        "body_start_text": abstract.group(0).strip(),
        "body_end_text": end_match.group(0).strip(),
        "_auto": True,
    }
    if appendix_start is not None:
        result["appendix_start_page"] = appendix_start
    return result


def _marker(boundaries: Mapping[str, Any], key: str) -> str | None:
    value = boundaries.get(key, boundaries.get(key.replace("_text", "_marker")))
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _validate_boundaries(
    boundaries: Mapping[str, Any], total_pages: int, pages: Sequence[str]
) -> tuple[int, int, int | None, str | None, str | None]:
    start = boundaries.get("body_start_page")
    end = boundaries.get("body_end_page")
    if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int):
        raise ValueError("body_start_page and body_end_page must be integers")
    if not 1 <= start <= end <= total_pages:
        raise ValueError(f"body pages must satisfy 1 <= start <= end <= {total_pages}")

    appendix = boundaries.get("appendix_start_page")
    if appendix is not None:
        if isinstance(appendix, bool) or not isinstance(appendix, int) or not 1 <= appendix <= total_pages:
            raise ValueError(f"appendix_start_page must be between 1 and {total_pages}")
        if appendix < start:
            raise ValueError("appendix_start_page cannot precede the body")

    start_text = _marker(boundaries, "body_start_text")
    end_text = _marker(boundaries, "body_end_text")
    if start_text is not None and start_text not in pages[start - 1]:
        raise ValueError("body_start_text was not found on body_start_page")
    if end_text is not None and end_text not in pages[end - 1]:
        raise ValueError("body_end_text was not found on body_end_page")
    if start == end and start_text is not None and end_text is not None:
        if pages[start - 1].find(start_text) >= pages[end - 1].find(end_text):
            raise ValueError("body_start_text must precede body_end_text on a shared page")
    return start, end, appendix, start_text, end_text


def _slice_body(
    pages: Sequence[str], start: int, end: int, start_text: str | None, end_text: str | None
) -> tuple[str, list[str]]:
    selected = list(pages[start - 1 : end])
    if start_text is not None:
        selected[0] = selected[0][selected[0].find(start_text) :]
    if end_text is not None:
        selected[-1] = selected[-1][: selected[-1].find(end_text)]
    return "\n".join(selected), selected


def _count_characters(text: str) -> int:
    return len(_COUNTED_CHARACTER.findall(text))


def _count_captions(text: str, pattern: re.Pattern[str]) -> int:
    identifiers: set[str] = set()
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            identifiers.add(match.group(1).replace(".", "-").lstrip("0") or "0")
    return len(identifiers)


def _abstract_chars(text: str) -> int | None:
    heading = _ABSTRACT_HEADING.search(text)
    if not heading:
        return None
    keywords = _KEYWORDS_HEADING.search(text, heading.end())
    if keywords:
        fragment = text[heading.end() : keywords.start()]
    else:
        next_heading = re.search(
            r"(?im)^\s*(?:1(?:\.0?)?\s+)?(?:INTRODUCTION|\u5f15\s*\u8a00)\s*$", text[heading.end() :]
        )
        if not next_heading:
            return None
        fragment = text[heading.end() : heading.end() + next_heading.start()]
    return _count_characters(fragment)


def _detect_appendix_page(pages: Sequence[str], body_start: int) -> int | None:
    matches = [item for item in _heading_matches(_APPENDIX_HEADING, pages) if item[0] + 1 >= body_start]
    return min((page + 1 for page, _ in matches), default=None)


def measure_pdf(
    pdf_path: str | Path, boundaries: Mapping[str, Any] | str | Path | None = None
) -> dict[str, Any]:
    """Return PDF identity, measured metrics, and structured reliability issues."""
    path = Path(pdf_path)
    if not path.is_file():
        return {
            "pdf_sha256": None,
            "metrics": _empty_metrics(),
            "issues": [_issue("missing_pdf", f"PDF file does not exist: {path}", "fail")],
        }

    try:
        pdf_hash = _sha256(path)
    except OSError as exc:
        return {
            "pdf_sha256": None,
            "metrics": _empty_metrics(),
            "issues": [_issue("unreadable_pdf", f"Cannot read PDF: {exc}", "fail")],
        }

    try:
        total_pages, pages = _extract_pdf(path)
    except FileNotFoundError as exc:
        return {
            "pdf_sha256": pdf_hash,
            "metrics": _empty_metrics(),
            "issues": [_issue("poppler_missing", f"Required Poppler tool is missing: {exc.filename}", "fail")],
        }
    except subprocess.TimeoutExpired:
        return {
            "pdf_sha256": pdf_hash,
            "metrics": _empty_metrics(),
            "issues": [_issue("pdf_tool_timeout", "Poppler timed out while reading the PDF", "fail")],
        }
    except ValueError as exc:
        return {
            "pdf_sha256": pdf_hash,
            "metrics": _empty_metrics(),
            "issues": [_issue("invalid_pdf", f"Invalid or unsupported PDF: {exc}", "fail")],
        }

    try:
        supplied = _load_boundaries(boundaries)
    except ValueError as exc:
        return {
            "pdf_sha256": pdf_hash,
            "metrics": _empty_metrics(total_pages),
            "issues": [_issue("invalid_boundaries", str(exc), "fail")],
        }
    resolved = supplied if supplied is not None else _auto_boundaries(pages)
    if resolved is None:
        return {
            "pdf_sha256": pdf_hash,
            "metrics": _empty_metrics(total_pages),
            "issues": [
                _issue(
                    "body_boundary_needs_review",
                    "Could not reliably locate both the abstract and the end of the body; provide boundary annotations.",
                    "needs_review",
                )
            ],
        }

    try:
        start, end, appendix, start_text, end_text = _validate_boundaries(resolved, total_pages, pages)
    except ValueError as exc:
        return {
            "pdf_sha256": pdf_hash,
            "metrics": _empty_metrics(total_pages),
            "issues": [_issue("invalid_boundaries", str(exc), "fail")],
        }

    body_text, body_page_texts = _slice_body(pages, start, end, start_text, end_text)
    if end_text is not None and body_page_texts and _count_characters(body_page_texts[-1]) == 0:
        body_page_texts = body_page_texts[:-1]
    body_pages = len(body_page_texts)
    if any(_count_characters(page_text) == 0 for page_text in body_page_texts):
        metrics = _empty_metrics(total_pages)
        metrics["body_pages"] = body_pages
        if appendix is None:
            appendix = _detect_appendix_page(pages, start)
        metrics["appendix_pages"] = total_pages - appendix + 1 if appendix is not None else 0
        return {
            "pdf_sha256": pdf_hash,
            "metrics": metrics,
            "issues": [
                _issue(
                    "text_extraction_uncertain",
                    "At least one annotated body page has no extractable letters or digits; text-derived metrics are unknown.",
                    "needs_review",
                )
            ],
        }

    if appendix is None:
        appendix = _detect_appendix_page(pages, start)
    abstract_chars = _abstract_chars(body_text)
    issues: list[dict[str, str]] = []
    if abstract_chars is None:
        issues.append(
            _issue(
                "abstract_boundary_needs_review",
                "The abstract bounds were not clear, so abstract_chars is unknown.",
                "needs_review",
            )
        )
    metrics = {
        "total_pages": total_pages,
        "body_pages": body_pages,
        "body_chars": _count_characters(body_text),
        "figures": _count_captions(body_text, _FIGURE_CAPTION),
        "tables": _count_captions(body_text, _TABLE_CAPTION),
        "appendix_pages": total_pages - appendix + 1 if appendix is not None else 0,
        "abstract_chars": abstract_chars,
    }
    return {"pdf_sha256": pdf_hash, "metrics": metrics, "issues": issues}


def _is_reliable(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.lower() in {"reliable", "verified"})


def build_reference_profile(records: Sequence[Mapping[str, Any]], min_samples: int = 5) -> dict[str, Any]:
    """Build per-topic profiles; sparse samples remain explicitly insufficient."""
    if isinstance(min_samples, bool) or not isinstance(min_samples, int) or min_samples < 1:
        raise ValueError("min_samples must be a positive integer")
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for record in records:
        topic = record.get("topic_type")
        if isinstance(topic, str) and topic.strip():
            grouped.setdefault(topic.strip(), []).append(record)

    profiles: dict[str, Any] = {}
    for topic in sorted(grouped):
        topic_records = grouped[topic]
        reliable = [
            record
            for record in topic_records
            if _is_reliable(record.get("reliability"))
            and isinstance(record.get("source"), str)
            and bool(record["source"].strip())
            and isinstance(record.get("pdf_sha256", record.get("hash")), str)
            and bool(record.get("pdf_sha256", record.get("hash")).strip())
        ]
        identities = [
            {"source": record.get("source"), "pdf_sha256": record.get("pdf_sha256", record.get("hash"))}
            for record in reliable
        ]
        metric_profiles: dict[str, Any] = {}
        for key in _PROFILE_METRICS:
            values = [
                float(record["metrics"][key])
                for record in reliable
                if isinstance(record.get("metrics"), Mapping)
                and isinstance(record["metrics"].get(key), (int, float))
                and not isinstance(record["metrics"].get(key), bool)
                and math.isfinite(float(record["metrics"][key]))
            ]
            if len(values) < min_samples:
                metric_profiles[key] = {
                    "sample_count": len(values),
                    "status": "insufficient_evidence",
                    "q1": None,
                    "median": None,
                    "q3": None,
                }
            else:
                if len(values) == 1:
                    q1 = q3 = values[0]
                else:
                    q1, _q2, q3 = statistics.quantiles(values, n=4, method="inclusive")
                metric_profiles[key] = {
                    "sample_count": len(values),
                    "status": "calibrated",
                    "q1": q1,
                    "median": float(statistics.median(values)),
                    "q3": q3,
                }
        profiles[topic] = {"records": identities, "metrics": metric_profiles}
    return {"min_samples": min_samples, "profiles": profiles}


def _main() -> int:
    parser = argparse.ArgumentParser(description="Measure a PDF with conservative body boundaries")
    parser.add_argument("pdf")
    parser.add_argument("--boundaries", help="JSON file with one-based page boundaries")
    args = parser.parse_args()
    result = measure_pdf(args.pdf, args.boundaries)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if any(issue["status"] == "fail" for issue in result["issues"]) else 0


if __name__ == "__main__":
    raise SystemExit(_main())
