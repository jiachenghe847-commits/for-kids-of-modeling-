"""Export a publication figure and its data/source provenance."""
from __future__ import annotations

import json
from pathlib import Path
import re
import warnings

from matplotlib.text import Text

from checklist.quality_common import local_path, nonempty, number, sha256


def export_figure(figure, case_dir, figure_id, data_paths, producer, *, units,
                  evidence_ids, width_mm=150):
    """Return a registry row. Explicitly choose a new id when replacing a figure.

    Use includegraphics[width=<width_mm>mm] and label fig:<figure_id> in TeX.
    Data files and producer must already exist inside the case directory.
    """
    if not isinstance(figure_id, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", figure_id):
        raise ValueError("figure_id 仅允许英数字、下划线、连字符")
    width_mm = number(width_mm)
    if width_mm <= 0 or not data_paths or not units or not evidence_ids:
        raise ValueError("需要正宽度、数据来源、单位与证据 id")
    root = Path(case_dir).resolve()
    paths = {kind: f"paper/figures/{figure_id}.{kind}" for kind in ("pdf", "png", "json")}
    targets = {kind: local_path(root, path) for kind, path in paths.items()}
    if any(p.exists() for p in targets.values()):
        raise FileExistsError(f"图 {figure_id} 已存在；用新 id 导出以保留旧产物")
    inputs = {p: sha256(local_path(root, p)) for p in data_paths}
    producer_hash = sha256(local_path(root, producer))
    source_width_mm = float(figure.get_figwidth()) * 25.4
    figure.canvas.draw()
    sizes = [t.get_fontsize() for t in figure.findobj(Text) if t.get_visible() and t.get_text().strip()]
    axes = [{"x": ax.get_xlabel(), "y": ax.get_ylabel()} for ax in figure.axes]
    for p in targets.values():
        p.parent.mkdir(parents=True, exist_ok=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        # Fixed canvas width makes effective font-size calculations reproducible.
        figure.savefig(targets["pdf"], format="pdf", bbox_inches=None,
                       metadata={"CreationDate": None, "ModDate": None})
        figure.savefig(targets["png"], format="png", dpi=300, bbox_inches=None)
    row = {"id": figure_id, "label": "fig:" + figure_id, "path": paths["pdf"],
           "preview_path": paths["png"], "sha256": sha256(targets["pdf"]),
           "preview_sha256": sha256(targets["png"]), "producer": producer,
           "producer_sha256": producer_hash, "input_hashes": inputs,
           "evidence_ids": evidence_ids, "units": units, "width_mm": width_mm,
           "source_width_mm": source_width_mm,
           "min_font_pt": min(sizes) if sizes else None, "axes_labels": axes,
           "warnings": [str(w.message) for w in caught]}
    targets["json"].write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return row
