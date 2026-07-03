import re
from pathlib import Path

_FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_SKIP_NAMES = {"manifest.md", "_fetch-log.md"}


def _parse_front_matter(text: str) -> dict:
    match = _FRONT_MATTER.match(text)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    if "year" in fields:
        try:
            fields["year"] = int(fields["year"])
        except ValueError:
            pass
    return fields


def scan_corpus(corpus_dir: str) -> list[dict]:
    results = []
    for path in sorted(Path(corpus_dir).rglob("*.md")):
        if path.name in _SKIP_NAMES:
            continue
        fields = _parse_front_matter(path.read_text(encoding="utf-8", errors="replace"))
        if not fields:
            continue
        fields["path"] = str(path)
        results.append(fields)
    return results


if __name__ == "__main__":
    import sys

    entries = scan_corpus(sys.argv[1] if len(sys.argv) > 1 else "corpus")
    print(f"共 {len(entries)} 篇")
    for e in entries:
        print(f"  {e.get('year')} {e.get('problem')} {e.get('award')} -> {e['path']}")
