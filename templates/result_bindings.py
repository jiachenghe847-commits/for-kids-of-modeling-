"""Generate hash-checkable TeX values from registered numeric results."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from checklist.quality_common import json_pointer, local_path, number, read_json


def render_bindings(case_dir, manifest):
    results = read_json(local_path(case_dir, manifest.get("results_path")))
    lines = [r"\providecommand{\ResultValue}[1]{\csname result@#1\endcsname}"]
    seen = set()
    for claim in manifest.get("claims", []):
        cid = claim.get("id", "")
        if not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9:_-]*", cid) or cid in seen:
            raise ValueError("claim id 必须唯一且仅含英数字、冒号、下划线和连字符")
        seen.add(cid)
        record = json_pointer(results, claim.get("result_pointer"))
        if not isinstance(record, dict) or record.get("unit") != claim.get("unit") or not record.get("unit"):
            raise ValueError(f"{cid}: results 中需要 {{value, unit}} 且单位须一致")
        value = number(record.get("value"))
        fmt = claim.get("format", ".6g")
        if not isinstance(fmt, str) or not re.fullmatch(r"\.(?:[0-9]|1[0-2])[fge]", fmt):
            raise ValueError("只允许 .0f 至 .12f 等有限精度 f/g/e 数字格式")
        lines.append(r"\expandafter\def\csname result@" + cid + r"\endcsname{" + format(value, fmt) + "}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="由 case.json 的 claims 生成论文数值绑定")
    parser.add_argument("case_dir", type=Path)
    args = parser.parse_args()
    manifest = read_json(args.case_dir / "case.json")
    output = local_path(args.case_dir, manifest["paper"]["bindings_path"])
    content = render_bindings(args.case_dir, manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
