"""Check figure provenance and publication size; visual review is separate."""
from __future__ import annotations

from pathlib import Path
import re

from PIL import Image

try:
    from .quality_common import issue, local_path, nonempty, number, sha256
    from .paper_audit import read_tex
except ImportError:
    from quality_common import issue, local_path, nonempty, number, sha256
    from paper_audit import read_tex


def audit_figures(case_dir, manifest):
    rows = manifest.get("figures", [])
    if not isinstance(rows, list) or not rows:
        return [issue("figure.none", "尚无图像登记；需复核是否缺少关键可视化", "needs_review")]
    issues, seen = [], set()
    evidence = {e.get("id") for e in manifest.get("evidence", []) if isinstance(e, dict)}
    try:
        tex_path = local_path(case_dir, manifest.get("paper", {}).get("tex_path"))
        text = read_tex(case_dir, tex_path)
    except (ValueError, OSError) as exc:
        return [issue("figure.source", str(exc))]
    graphics = re.findall(r"\\includegraphics(?:\[([^]]*)\])?\{([^}]+)\}", text)
    for row in rows:
        fid = row.get("id") if isinstance(row, dict) else None
        try:
            if not nonempty(fid) or fid in seen:
                raise ValueError("图 id 为空或重复")
            seen.add(fid)
            path = local_path(case_dir, row.get("path"))
            preview = local_path(case_dir, row.get("preview_path"))
            hashes = row.get("input_hashes")
            if not isinstance(hashes, dict) or not hashes:
                raise ValueError("缺图像数据来源")
            targets = [(path, row.get("sha256")), (preview, row.get("preview_sha256")),
                       (local_path(case_dir, row.get("producer")), row.get("producer_sha256"))]
            targets += [(local_path(case_dir, p), h) for p, h in hashes.items()]
            if any(not p.is_file() or sha256(p) != h for p, h in targets):
                issues.append(issue("figure.stale", f"{fid}: 图片/数据/绘图代码哈希不一致"))
            ids = row.get("evidence_ids")
            if not isinstance(ids, list) or not ids or any(e not in evidence for e in ids):
                issues.append(issue("figure.evidence", f"{fid}: 未绑定有效证据"))
            if not isinstance(row.get("units"), dict) or not row["units"] or not all(nonempty(v) for v in row["units"].values()):
                issues.append(issue("figure.units", f"{fid}: 缺单位声明"))
            width = number(row.get("width_mm"))
            original = number(row.get("source_width_mm"))
            if width <= 0 or original <= 0:
                raise ValueError("图片宽度必须为正")
            minimum = row.get("min_font_pt")
            if minimum is None:
                issues.append(issue("figure.font_unknown", f"{fid}: 无法测量图内文字", "needs_review"))
            elif number(minimum) * width / original < 8:
                issues.append(issue("figure.font", f"{fid}: 最终尺寸的最小字号低于 8 pt"))
            with Image.open(preview) as image:
                if image.width / (width / 25.4) < 299:
                    issues.append(issue("figure.resolution", f"{fid}: 预览图按插入尺寸不足 300 dpi"))
            options = [opts for opts, relative in graphics if (tex_path.parent / relative).resolve() == path]
            matches = [re.search(r"(?:^|,)\s*width\s*=\s*([0-9.]+)mm\s*(?:,|$)", opts) for opts in options]
            if not matches or any(m is None or abs(float(m.group(1)) - width) > 0.01 for m in matches):
                issues.append(issue("figure.placement", f"{fid}: 正文未按登记的 {width:g}mm 宽度插图"))
            if r"\label{" + str(row.get("label")) + "}" not in text:
                issues.append(issue("figure.label", f"{fid}: 图标签不在正文中"))
            if any("Glyph" in w or "glyph" in w for w in row.get("warnings", [])):
                issues.append(issue("figure.glyph", f"{fid}: 导出记录存在缺字警告"))
            if any(not labels.get("x") or not labels.get("y") for labels in row.get("axes_labels", [])):
                issues.append(issue("figure.axes", f"{fid}: 存在缺轴标签的坐标图；示意图请说明", "needs_review"))
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            issues.append(issue("figure.invalid", f"{fid}: {exc}"))
    return issues
