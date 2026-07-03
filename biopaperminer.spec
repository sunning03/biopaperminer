# -*- mode: python ; coding: utf-8 -*-
"""BioPaperMiner PyInstaller 打包配置"""
import sys
import os
from pathlib import Path

block_cipher = None
# PyInstaller spec 中不能用 __file__，用当前工作目录
root = Path(os.getcwd())

a = Analysis(
    ['main.py'],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / 'biopaperminer' / 'templates' / 'report.html'),
         'biopaperminer/templates'),
    ],
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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
