#!/usr/bin/env python3
"""BioPaperMiner GUI 入口 — 双击直接打开图形界面"""
import sys
import os
from pathlib import Path

# 确保能找到包
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from biopaperminer.gui import main
main()
