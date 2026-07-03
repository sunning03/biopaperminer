#!/usr/bin/env python3
"""
BioPaperMiner 入口 — 双击打开 GUI，命令行参数时运行 CLI
"""
import sys
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# 有命令行参数 → 走 CLI（供打包后的子进程调用）
# 无参数 → 打开 GUI
if len(sys.argv) > 1 and sys.argv[1] in ("pipeline", "search", "download", "refs", "tui", "gui", "--help", "-h"):
    from biopaperminer.pipeline import main as cli_main
    cli_main()
else:
    from biopaperminer.gui import main
    main()
