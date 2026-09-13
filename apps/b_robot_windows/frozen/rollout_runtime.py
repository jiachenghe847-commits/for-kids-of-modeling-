"""Versioned deployment choices and optional native-backend provenance."""
import hashlib
import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def source_hashes():
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.iterdir()) if p.suffix in ('.py','.cpp')}


def native_backend():
    path = ROOT/'rollout-backend-gate.json'
    if not path.exists():
        return None
    gate = json.loads(path.read_text(encoding='utf8'))
    if not gate.get('default_eligible') or gate.get('speedup',0)<2:
        return None
    hashes = gate['source_sha256']
    if hashlib.sha256((ROOT/'rollout_kernel.py').read_bytes()).hexdigest()!=hashes['rollout_kernel.py']:
        return None
    try:
        module = importlib.import_module('_rollout_cpp')
    except ImportError:
        return None
    return module if getattr(module,'source_sha256',None)==hashes['rollout_cpp.cpp'] else None


def selected_settings(question):
    path = ROOT/'rollout-defaults.json'
    if not path.exists():
        return dict(scheduler='adaptive')
    selection = json.loads(path.read_text(encoding='utf8'))
    choice = selection['questions'][str(question)]
    if not choice['accepted']:
        return dict(scheduler='adaptive')
    for name,expected in selection['runtime_source_sha256'].items():
        file = ROOT/name
        if not file.exists() or hashlib.sha256(file.read_bytes()).hexdigest()!=expected:
            return dict(scheduler='adaptive')
    if choice['rollout_backend']=='cpp' and native_backend() is None:
        return dict(scheduler='adaptive')
    return dict(scheduler='rollout',rollout_config=choice['rollout_config'],rollout_backend=choice['rollout_backend'])
