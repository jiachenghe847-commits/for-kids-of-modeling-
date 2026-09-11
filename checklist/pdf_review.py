"""Conservative automated PDF/log review and explicit page rendering."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

try:  # package import (``from checklist.pdf_review import ...``)
    from .pdf_metrics import _count_characters, _extract_pdf, _issue, _sha256
except ImportError:  # direct script execution (``python checklist/pdf_review.py``)
    from pdf_metrics import _count_characters, _extract_pdf, _issue, _sha256


_MISSING_GLYPH = re.compile(r"Missing character: There is no .+? in font", re.IGNORECASE)
_UNDEFINED_REFERENCE = re.compile(
    r"(?:LaTeX Warning: Reference .+? undefined|There were undefined references)", re.IGNORECASE
)
_OVERFULL = re.compile(r"Overfull \\hbox\s*\(([^)]+too wide)\)", re.IGNORECASE)


def review_pdf(pdf_path: str | Path, log_path: str | Path | None = None) -> dict[str, Any]:
    """Audit a PDF and optional XeLaTeX log without creating rendered files."""
    path = Path(pdf_path)
    if not path.is_file():
        return {
            "pdf_sha256": None,
            "pages": None,
            "issues": [_issue("missing_pdf", f"PDF file does not exist: {path}", "fail")],
        }
    try:
        pdf_hash = _sha256(path)
    except OSError as exc:
        return {
            "pdf_sha256": None,
            "pages": None,
            "issues": [_issue("unreadable_pdf", f"Cannot read PDF: {exc}", "fail")],
        }
    try:
        total_pages, page_texts = _extract_pdf(path)
    except FileNotFoundError as exc:
        return {
            "pdf_sha256": pdf_hash,
            "pages": None,
            "issues": [_issue("poppler_missing", f"Required Poppler tool is missing: {exc.filename}", "fail")],
        }
    except subprocess.TimeoutExpired:
        return {
            "pdf_sha256": pdf_hash,
            "pages": None,
            "issues": [_issue("pdf_tool_timeout", "Poppler timed out while reading the PDF", "fail")],
        }
    except ValueError as exc:
        return {
            "pdf_sha256": pdf_hash,
            "pages": None,
            "issues": [_issue("invalid_pdf", f"Invalid or unsupported PDF: {exc}", "fail")],
        }

    issues: list[dict[str, str]] = []
    if log_path is not None:
        log = Path(log_path)
        if not log.is_file():
            issues.append(_issue("missing_log", f"XeLaTeX log file does not exist: {log}", "fail"))
        else:
            try:
                log_text = log.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                issues.append(_issue("unreadable_log", f"Cannot read XeLaTeX log: {exc}", "fail"))
            else:
                missing_glyphs = _MISSING_GLYPH.findall(log_text)
                if missing_glyphs:
                    issues.append(
                        _issue(
                            "missing_glyph",
                            f"XeLaTeX reported {len(missing_glyphs)} missing-character warning(s).",
                            "fail",
                        )
                    )
                undefined = _UNDEFINED_REFERENCE.findall(log_text)
                if undefined:
                    issues.append(
                        _issue(
                            "undefined_reference",
                            f"XeLaTeX reported {len(undefined)} undefined-reference warning(s).",
                            "fail",
                        )
                    )
                overfull = _OVERFULL.findall(log_text)
                if overfull:
                    details = ", ".join(overfull[:3])
                    issues.append(
                        _issue(
                            "overfull_box",
                            f"XeLaTeX reported {len(overfull)} overfull horizontal box(es): {details}.",
                            "needs_review",
                        )
                    )

    possible_blank = [index for index, text in enumerate(page_texts, start=1) if _count_characters(text) == 0]
    if possible_blank:
        pages = ", ".join(str(page) for page in possible_blank)
        issues.append(
            _issue(
                "possible_blank_page",
                f"Pages {pages} have no extractable letters or digits; they may be blank, scanned, or graphical and need visual review.",
                "needs_review",
            )
        )
    issues.append(
        _issue(
            "visual_inspection_required",
            "Automated checks do not establish visual quality; inspect every rendered page before delivery.",
            "needs_review",
        )
    )
    return {"pdf_sha256": pdf_hash, "pages": total_pages, "issues": issues}


def _contact_sheet(page_images: list[Path], destination: Path) -> None:
    thumbnails: list[Image.Image] = []
    try:
        for page in page_images:
            with Image.open(page) as image:
                thumbnail = image.convert("RGB")
                thumbnail.thumbnail((240, 320), Image.Resampling.LANCZOS)
                thumbnails.append(thumbnail.copy())
        columns = min(4, len(thumbnails))
        rows = (len(thumbnails) + columns - 1) // columns
        cell_width = max(image.width for image in thumbnails) + 20
        cell_height = max(image.height for image in thumbnails) + 40
        sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), "white")
        draw = ImageDraw.Draw(sheet)
        for index, thumbnail in enumerate(thumbnails):
            x = (index % columns) * cell_width + 10
            y = (index // columns) * cell_height + 25
            sheet.paste(thumbnail, (x, y))
            draw.text((x, 7 + (index // columns) * cell_height), f"Page {index + 1}", fill="black")
        sheet.save(destination, "PNG")
        sheet.close()
    finally:
        for thumbnail in thumbnails:
            thumbnail.close()


def render_pdf(pdf_path: str | Path, output_dir: str | Path, dpi: int = 120) -> dict[str, Any]:
    """Render page PNGs plus a contact sheet into a new directory.

    Existing output paths are rejected even when empty so prior review evidence
    can never be overwritten silently.
    """
    path = Path(pdf_path)
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"render output already exists: {output}")
    if isinstance(dpi, bool) or not isinstance(dpi, int) or dpi < 20 or dpi > 600:
        raise ValueError("dpi must be an integer between 20 and 600")
    if not path.is_file():
        raise FileNotFoundError(f"PDF file does not exist: {path}")
    try:
        total_pages, _ = _extract_pdf(path)
    except ValueError as exc:
        raise ValueError(f"Invalid or unsupported PDF: {exc}") from exc

    output.mkdir(parents=True)
    prefix = output / "page"
    try:
        completed = subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), str(path), str(prefix)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=180,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Required Poppler tool is missing: pdftoppm") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("pdftoppm timed out while rendering the PDF") from exc
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "pdftoppm failed")
    page_images = sorted(output.glob("page-*.png"), key=lambda item: int(item.stem.split("-")[-1]))
    if len(page_images) != total_pages:
        raise RuntimeError(f"pdftoppm rendered {len(page_images)} of {total_pages} pages")
    contact_sheet = output / "contact-sheet.png"
    _contact_sheet(page_images, contact_sheet)
    return {
        "pdf_sha256": _sha256(path),
        "pages": total_pages,
        "output_dir": str(output),
        "page_images": [str(image) for image in page_images],
        "contact_sheet": str(contact_sheet),
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description="Audit or explicitly render a PDF")
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit", help="run read-only automated checks")
    audit.add_argument("pdf")
    audit.add_argument("--log", help="optional XeLaTeX log")
    render = subparsers.add_parser("render", help="render to a new output directory")
    render.add_argument("pdf")
    render.add_argument("output_dir")
    render.add_argument("--dpi", type=int, default=120)
    args = parser.parse_args()
    if args.command == "audit":
        result = review_pdf(args.pdf, args.log)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if any(issue["status"] == "fail" for issue in result["issues"]) else 0
    try:
        result = render_pdf(args.pdf, args.output_dir, args.dpi)
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as exc:
        result = {"issues": [_issue("render_failed", str(exc), "fail")]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
