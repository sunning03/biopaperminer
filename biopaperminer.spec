# -*- mode: python ; coding: utf-8 -*-
"""BioPaperMiner PyInstaller 打包配置"""
import sys
import os
import importlib
from pathlib import Path

block_cipher = None
# PyInstaller spec 中不能用 __file__，用当前工作目录
root = Path(os.getcwd())

# 查找 tkinterdnd2 的 tkdnd 本地库路径
_tkdnd_path = None
try:
    _tkdnd_mod = importlib.import_module('tkinterdnd2')
    _tkdnd_path = Path(_tkdnd_mod.__file__).parent / 'tkdnd'
except Exception:
    pass

a = Analysis(
    ['gui_entry.py'],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / 'biopaperminer' / 'templates' / 'report.html'),
         'biopaperminer/templates'),
    ] + ([(str(_tkdnd_path), 'tkinterdnd2/tkdnd')] if _tkdnd_path and _tkdnd_path.exists() else []),
    hiddenimports=[
        'biopaperminer', 'biopaperminer.main', 'biopaperminer.config',
        'biopaperminer.config_editor', 'biopaperminer.models',
        'biopaperminer.prompts', 'biopaperminer.session_pool',
        'biopaperminer.pdf_extractor', 'biopaperminer.mineru_client',
        'biopaperminer.llm_client', 'biopaperminer.analyzer',
        'biopaperminer.pipeline', 'biopaperminer.download_pubmed',
        'biopaperminer.download_pdf', 'biopaperminer.extract_references',
        'biopaperminer.extract_ris', 'biopaperminer.extract_refs',
        'biopaperminer.tui', 'biopaperminer.gui',
        'tkinterdnd2', 'tkinterdnd2.TkinterDnD',
    ],
    excludes=['tkinter.test', 'unittest', 'pdb', 'pycparser', 'setuptools'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='biopaperminer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # 隐藏终端窗口，只显示 GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
