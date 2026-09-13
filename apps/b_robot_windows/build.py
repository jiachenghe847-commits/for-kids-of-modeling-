"""Build a Windows directory bundle with provenance, without simulator access."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import zipfile
import pybind11

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'frozen'))
from strategy import BUILD_VERSION


def main():
    if sys.platform != 'win32':
        raise SystemExit('Build on Windows x64 with Python 3.14.')
    native=ROOT/'frozen/rollout_cpp.cpp'
    native_hash=hashlib.sha256(native.read_bytes()).hexdigest()
    binary=ROOT/'frozen'/('_rollout_cpp'+sysconfig.get_config_var('EXT_SUFFIX'))
    subprocess.run(['cl','/O2','/std:c++17','/EHsc','/LD','/fp:strict',f'/DROLLOUT_SOURCE_SHA256="{native_hash}"',
                    f'/I{pybind11.get_include()}',f'/I{sysconfig.get_path("include")}',str(native),'/link',
                    f'/OUT:{binary}',f'/LIBPATH:{Path(sys.base_prefix)/"libs"}'],check=True,cwd=ROOT)
    subprocess.run([sys.executable,'check_native.py'],cwd=ROOT,check=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    tracked = ['launcher.py', 'session.py', 'build.py', 'requirements-build.txt','check_native.py','native-fixtures.json']
    tracked += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / 'frozen').iterdir()) if p.suffix in ('.py','.cpp','.json')]
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in tracked}
    (ROOT / 'build-info.json').write_text(json.dumps(dict(version=BUILD_VERSION, commit=commit,
        python=sys.version, source_sha256=hashes,native=dict(source_sha256=native_hash,
            binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),precision='double',fast_math=False,flags=['/O2','/std:c++17','/fp:strict'])), indent=2), encoding='utf8')
    with zipfile.ZipFile(ROOT / 'source_snapshot.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in tracked + ['build-info.json']:
            archive.write(ROOT / name, name)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
        '--console', '--name', 'B-Robot', '--paths', str(ROOT / 'frozen'),
        '--collect-submodules', 'scipy._external.array_api_compat',
        '--hidden-import','rollout_strategy','--hidden-import','_rollout_cpp',
        '--add-data','frozen:.',
        '--add-data', 'source_snapshot.zip:.', '--add-data', 'build-info.json:.',
        '--distpath', 'dist', '--workpath', 'build', 'launcher.py'], cwd=ROOT, check=True)
    target = ROOT / 'dist' / 'B-Robot'
    shutil.copy2(ROOT / 'README.md', target / 'README.txt')
    shutil.copy2(ROOT / 'build-info.json', target / 'build-info.json')
    shutil.copy2(ROOT / 'native-check.json', target / 'native-check.json')
    with (target / 'SHA256SUMS.txt').open('w', encoding='utf8') as output:
        for path in sorted(target.rglob('*')):
            if path.is_file() and path.name != 'SHA256SUMS.txt':
                output.write(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(target).as_posix()}\n')


if __name__ == '__main__':
    main()
