"""Small shared primitives for read-only quality checks."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


def issue(code, message, status="fail"):
    return {"code": code, "message": message, "status": status}


def local_path(root, value):
    if not isinstance(value, str) or not value.strip() or Path(value).is_absolute():
        raise ValueError(f"需要案例内相对路径：{value!r}")
    root = Path(root).resolve()
    result = (root / value).resolve()
    if not result.is_relative_to(root):
        raise ValueError(f"路径越出案例目录：{value}")
    return result


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    def invalid(token):
        raise ValueError(f"非有限数值：{token}")
    result = json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=invalid)
    require_finite(result)
    return result


def require_finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("非有限数值")
    if isinstance(value, dict):
        for item in value.values():
            require_finite(item)
    elif isinstance(value, list):
        for item in value:
            require_finite(item)


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"需要有限数值：{value!r}")
    return value


def nonempty(value):
    return isinstance(value, str) and bool(value.strip()) and not value.strip().startswith("<")


def json_pointer(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("结果索引必须是以 / 开始的 JSON Pointer")
    for token in pointer[1:].split("/"):
        key = token.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def status_of(issues):
    if any(item["status"] == "fail" for item in issues):
        return "fail"
    return "needs_review" if issues else "pass"
