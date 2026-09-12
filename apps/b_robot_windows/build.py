"""Build a Windows directory bundle with provenance, without simulator access."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent


def main():
    if sys.platform != 'win32':
        raise SystemExit('Build on Windows x64 with Python 3.14.')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    tracked = ['launcher.py', 'session.py', 'build.py', 'requirements-build.txt']
    tracked += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / 'frozen').glob('*.py'))]
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in tracked}
    (ROOT / 'build-info.json').write_text(json.dumps(dict(version='v4-windows-1', commit=commit,
        python=sys.version, source_sha256=hashes), indent=2), encoding='utf8')
    with zipfile.ZipFile(ROOT / 'source_snapshot.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in tracked + ['build-info.json']:
            archive.write(ROOT / name, name)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
        '--windowed', '--name', 'B-Robot', '--paths', str(ROOT / 'frozen'),
        '--add-data', 'source_snapshot.zip:.', '--add-data', 'build-info.json:.',
        '--distpath', 'dist', '--workpath', 'build', 'launcher.py'], cwd=ROOT, check=True)
    target = ROOT / 'dist' / 'B-Robot'
    shutil.copy2(ROOT / 'README.md', target / 'README.txt')
    shutil.copy2(ROOT / 'build-info.json', target / 'build-info.json')
    with (target / 'SHA256SUMS.txt').open('w', encoding='utf8') as output:
        for path in sorted(target.rglob('*')):
            if path.is_file() and path.name != 'SHA256SUMS.txt':
                output.write(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(target).as_posix()}\n')


if __name__ == '__main__':
    main()
