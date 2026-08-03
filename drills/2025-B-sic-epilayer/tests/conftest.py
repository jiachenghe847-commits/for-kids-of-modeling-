import sys
from pathlib import Path

# src/ 里的模块互相以顶层名字 import（optics / spectra / inversion），
# 因此测试和 compute.py 都把 src/ 直接挂到 sys.path 上。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
