#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path
def digest(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('--repeat',type=int,default=2)
 a, command=ap.parse_known_args()
 a.command=command[1:] if command and command[0]=='--' else command
 root=Path(a.root).resolve(); art=root/'artifacts'; art.mkdir(exist_ok=True); runs=[]; success=True
 for i in range(max(1,a.repeat)):
  p=subprocess.run(a.command,cwd=root)
  ok=p.returncode==0; success &= ok
  result=art/'results.json'; runs.append({'index':i+1,'returncode':p.returncode,'results_sha256':digest(result) if result.is_file() and ok else None,'timestamp':time.time()})
 rec={'format_version':1,'command':a.command,'runs':runs,'reproducible':bool(success and len(runs)>=2 and len({r['results_sha256'] for r in runs})==1),'isolated':False}
 (art/'run-record.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); return 0 if success else 1
if __name__=='__main__': raise SystemExit(main())
