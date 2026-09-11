from __future__ import annotations
import hashlib, json, shutil
from pathlib import Path
CURATED=('requirements.txt','runtime','templates','snippets','checklist','notation.md')
def export_toolkit(source,target):
 source=Path(source).resolve(); target=Path(target).resolve(); target.mkdir(parents=True,exist_ok=True)
 for name in CURATED:
  src=source/name
  if not src.exists(): continue
  dst=target/name
  if src.is_dir(): shutil.copytree(src,dst,ignore=shutil.ignore_patterns('test_*.py','__pycache__','.pytest_cache'))
  else: shutil.copy2(src,dst)
 files=[]; h=hashlib.sha256()
 for p in sorted(target.rglob('*')):
  if p.is_file():
   rel=str(p.relative_to(target)); data=p.read_bytes(); files.append({'path':rel,'sha256':hashlib.sha256(data).hexdigest()}); h.update(rel.encode()); h.update(data)
 manifest={'format_version':1,'files':files,'toolkit_sha256':h.hexdigest()}
 (target/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); return manifest
