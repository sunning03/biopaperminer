#!/usr/bin/env python3
"""
BioPaperMiner GUI — 图形界面

用法:
  python3 gui.py
  python3 main.py gui

注意：需要 tkinter 支持。conda 环境的 Python 自带 tkinter，
     pyenv 编译的 Python 可能缺少 tkinter。
"""

import sys
import os
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog, scrolledtext
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    print("❌ tkinter / tkinterdnd2 不可用。")
    print()
    print("安装依赖: pip install tkinterdnd2")
    print()
    print("conda 环境: conda activate biopaperminer && pip install tkinterdnd2")
    print()
    print("或者使用 TUI 模式（无需 GUI）：")
    print("  python main.py tui")
    sys.exit(1)


# ═══════════════════════════════════════════════════════
# 淡蓝色配色方案
# ═══════════════════════════════════════════════════════

COLORS = {
    "bg_primary":     "#F7F9F7",   # 页面背景 - 柔和米白
    "bg_header":      "#2E7D32",   # 顶部标题栏 - 生命绿
    "bg_button":      "#E8F0E8",   # 导航按钮 - 极浅绿
    "bg_button_hover": "#C8E6C9",  # 导航悬停 - 浅绿
    "bg_active":      "#81C784",   # 选中状态 - 辅助绿
    "bg_entry":       "#FFFFFF",   # 输入框 - 纯白
    "bg_log":         "#F7F9F7",   # 日志区 - 柔和米白
    "bg_panel":       "#F0F4F0",   # 面板标题 - 极浅绿灰
    "fg_text":        "#4B5563",   # 正文 - 柔和深灰
    "fg_heading":     "#1F2937",   # 标题文字 - 深灰黑
    "fg_accent":      "#1E88E5",   # 强调色 - 信息蓝
    "fg_success":     "#2E7D32",   # 成功文字 - 森林绿
    "fg_error":       "#E53935",   # 错误文字 - 红
    "fg_warning":     "#FFB300",   # 警告文字 - 琥珀
    "fg_dim":         "#6B7280",   # 辅助文字 - 中灰
    "border":         "#E6E8E6",   # 边框 - 极淡灰
    "run_bg":         "#2E7D32",   # 运行按钮 - 森林绿
    "run_fg":         "#1F2937",   # 运行按钮文字 - 深灰黑
    "stop_bg":        "#f05a46",   # 停止按钮 - 橙红
    "stop_fg":        "#FFFFFF",   # 停止按钮文字 - 白
}

# ── DPI 感知字体缩放（用户可额外调节） ──
FONT_SCALE = 1.0

def _load_font_scale():
    """从配置加载用户字体缩放倍数"""
    from biopaperminer.config_editor import get
    try:
        return float(get("FONT_SCALE", "1.0"))
    except Exception:
        return 1.0

def _init_fonts(root):
    """根据 DPI 缩放字体"""
    global FONT_SCALE, FONT_TITLE, FONT_LABEL, FONT_ENTRY, FONT_LOG, FONT_BTN, FONT_HEADING
    try:
        dpi_scale = float(root.tk.call('tk', 'scaling'))
        if sys.platform == "win32":
            dpi_scale = max(1.0, dpi_scale / 1.0)
        elif sys.platform == "darwin":
            dpi_scale = max(1.0, dpi_scale / 1.333)
        else:
            dpi_scale = 1.0
    except Exception:
        dpi_scale = 1.0

    user_scale = _load_font_scale()
    FONT_SCALE = dpi_scale * user_scale

    def fs(size):
        return max(int(size * FONT_SCALE + 0.5), size)

    FONT_TITLE   = ("Helvetica", fs(22), "bold")
    FONT_LABEL   = ("Helvetica", fs(11), "bold")
    FONT_ENTRY   = ("Helvetica", fs(11))
    FONT_LOG     = ("Consolas", fs(11))
    FONT_BTN     = ("Helvetica", fs(12))
    FONT_HEADING = ("Helvetica", fs(12), "bold")


# 初始默认值（`_init_fonts` 会覆盖）
FONT_TITLE = ("Helvetica", 22, "bold")
FONT_LABEL = ("Helvetica", 11, "bold")
FONT_ENTRY = ("Helvetica", 11)
FONT_LOG   = ("Consolas", 11)
FONT_BTN   = ("Helvetica", 12)
FONT_HEADING = ("Helvetica", 12, "bold")


# ═══════════════════════════════════════════════════════
# 独立模块面板 — 仅负责参数收集 + 日志输出
# ═══════════════════════════════════════════════════════

class ModulePanel:
    """单个功能模块：参数区 + 日志区，不含运行/停止按钮"""

    def __init__(self, parent, root, title: str):
        self.title = title
        self.param_vars = []

        # 参数区
        self.param_frame = tk.LabelFrame(
            parent,
            text=f"  {title}  ",
            font=FONT_HEADING,
            fg=COLORS["fg_heading"],
            bg=COLORS["bg_panel"],
            bd=1,
            relief=tk.RAISED,
            padx=10,
            pady=6,
        )
        self.param_frame.pack(fill=tk.X, pady=(0, 4))

        # 日志区
        self.log_frame = tk.LabelFrame(
            parent,
            text="  运行日志  ",
            font=FONT_HEADING,
            fg=COLORS["fg_heading"],
            bg=COLORS["bg_panel"],
            bd=1,
            relief=tk.RAISED,
            padx=6,
            pady=4,
        )
        self.log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            self.log_frame,
            height=10,
            font=FONT_LOG,
            fg=COLORS["fg_text"],
            bg=COLORS["bg_log"],
            insertbackground=COLORS["fg_text"],
            relief=tk.FLAT,
            state=tk.DISABLED,
            bd=0,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self._root = root

    # ── 日志（线程安全，通过 root.after 写入 UI） ──

    def log(self, msg: str, level: str = "info"):
        self._root.after(0, self._log_safe, msg, level)

    def _log_safe(self, msg: str, level: str):
        ts = datetime.now().strftime("%H:%M:%S")
        ct = level if level in ("error", "success", "warning", "info") else "info"
        self.log_text.config(state=tk.NORMAL)
        self.log_text.tag_config(ct, foreground={
            "error": COLORS["fg_error"],
            "success": COLORS["fg_success"],
            "warning": COLORS["fg_warning"],
            "info": COLORS["fg_text"],
        }[ct])
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n", ct)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    # ── 粘贴路径右键菜单（替代拖放） ──

    def _add_path_menu(self, widget, var: tk.StringVar):
        """给路径输入框添加右键粘贴菜单"""
        menu = tk.Menu(widget, tearoff=0, bg=COLORS["bg_panel"],
                       fg=COLORS["fg_text"], font=("Helvetica", 10))
        menu.add_command(label="粘贴路径", command=lambda: self._paste_path(var))
        menu.add_separator()
        menu.add_command(label="清除", command=lambda: var.set(""))

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)

    def _on_drop(self, event, var: tk.StringVar):
        """处理文件拖放"""
        if event.data:
            # tkinterdnd2 返回路径用 {} 包裹多文件，用空格分隔
            raw = event.data.strip()
            # 移除花括号
            raw = raw.replace('{', '').replace('}', '')
            # 取第一个路径
            path = raw.split()[0].strip() if raw else ""
            if path:
                var.set(path)

    def _paste_path(self, var: tk.StringVar):
        """从剪贴板粘贴路径"""
        try:
            clip = self._root.clipboard_get()
            # 取第一行（多行粘贴时只取第一行）
            path = clip.strip().split('\n')[0].strip()
            # 去掉首尾引号
            path = path.strip('"').strip("'")
            if path:
                var.set(path)
        except Exception:
            pass

    # ── 参数 ──

    def add_field(self, row: int, label: str, default: str = "",
                  secret: bool = False, choices: list = None,
                  show_when: str = "*", file_ext: str = None) -> tk.StringVar:
        lbl = tk.Label(
            self.param_frame, text=label, font=FONT_LABEL,
            fg=COLORS["fg_text"], bg=COLORS["bg_primary"],
        )
        lbl.grid(row=row, column=0, sticky=tk.W, pady=2)

        var = tk.StringVar(value=default)

        # 下拉框（select 类型）
        if choices:
            widget = ttk.Combobox(
                self.param_frame, textvariable=var, font=FONT_ENTRY,
                values=choices, state="readonly", width=43,
            )
        else:
            widget = tk.Entry(
                self.param_frame, textvariable=var, font=FONT_ENTRY,
                fg=COLORS["fg_text"], bg=COLORS["bg_entry"],
                relief=tk.RAISED, bd=1, insertbackground=COLORS["fg_text"],
                width=45,
            )

        widget.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        # 给路径类型字段添加拖放 + 右键粘贴
        if "目录" in label or "文件" in label or "路径" in label or "输出" in label:
            self._add_path_menu(widget, var)
            # 注册拖放目标
            if hasattr(self._root, 'drop_target_register'):
                try:
                    widget.drop_target_register(DND_FILES)
                    widget.dnd_bind('<<Drop>>', lambda e, v=var: self._on_drop(e, v))
                except Exception:
                    pass

        btn = None
        if "目录" in label:
            btn = tk.Button(
                self.param_frame, text="📂", font=("Helvetica", 11),
                fg=COLORS["fg_text"], bg=COLORS["bg_button"],
                relief=tk.RAISED, bd=1, cursor="hand2",
                command=lambda v=var: self._browse(v),
                width=2,
            )
            btn.grid(row=row, column=2, padx=(5, 0), pady=2)

        elif file_ext:
            btn = tk.Button(
                self.param_frame, text="📄", font=("Helvetica", 11),
                fg=COLORS["fg_text"], bg=COLORS["bg_button"],
                relief=tk.RAISED, bd=1, cursor="hand2",
                command=lambda v=var, ext=file_ext: self._browse_files(v, ext),
                width=2,
            )
            btn.grid(row=row, column=2, padx=(5, 0), pady=2)

        elif secret:
            widget.config(show="*")
            btn = tk.Button(
                self.param_frame, text="👁", font=("Helvetica", 11),
                fg=COLORS["fg_text"], bg=COLORS["bg_button"],
                relief=tk.RAISED, bd=1, cursor="hand2",
                width=2,
            )
            btn.grid(row=row, column=2, padx=(5, 0), pady=2)

            def toggle(e=widget, b=btn):
                if e.cget("show") == "*":
                    e.config(show="")
                    b.config(text="🙈")
                else:
                    e.config(show="*")
                    b.config(text="👁")
            btn.config(command=toggle)

        self.param_frame.columnconfigure(1, weight=1)
        # 记录 var + 所有相关控件，供动态显隐使用
        self.param_vars.append(var)
        if not hasattr(self, '_param_widgets'):
            self._param_widgets = []
            self._param_labels = []
            self._param_btns = []
            self._param_show_when = []
        self._param_widgets.append(widget)
        self._param_labels.append(lbl)
        self._param_btns.append(btn)
        self._param_show_when.append(show_when)
        return var

    # 类级记忆：上次打开的目录
    _last_dir = os.getcwd()

    def _browse(self, var: tk.StringVar):
        # 优先从当前输入框的值推断起始目录
        cur = var.get().strip()
        if cur:
            p = Path(cur)
            if p.is_dir():
                start_dir = str(p)
            elif p.parent.is_dir():
                start_dir = str(p.parent)
            else:
                start_dir = ModulePanel._last_dir
        else:
            start_dir = ModulePanel._last_dir

        d = filedialog.askdirectory(title="选择目录", initialdir=start_dir)
        if d:
            var.set(d)
            ModulePanel._last_dir = d

    def _browse_files(self, var: tk.StringVar, ext: str = "*.pdf"):
        """多文件选择器（用 ; 分隔路径）"""
        # macOS 要求 filetypes 不能含分号，拆成多条
        exts = ext.split(";")
        type_name_map = {"*.pdf": "PDF 文件", "*.csv": "CSV 文件", "*.xlsx": "Excel 文件",
                         "*.xls": "Excel 文件"}
        filetypes = []
        for e in exts:
            name = type_name_map.get(e, "文件")
            filetypes.append((name, e))
        filetypes.append(("所有文件", "*.*"))

        files = filedialog.askopenfilenames(
            title="选择文件",
            filetypes=filetypes,
            initialdir=ModulePanel._last_dir,
        )
        if files:
            paths = ";".join(files)
            var.set(paths)
            ModulePanel._last_dir = str(Path(files[0]).parent)


# ═══════════════════════════════════════════════════════
# 主应用
# ═══════════════════════════════════════════════════════

class BioPaperMinerApp:
    """BioPaperMiner 主窗口 — 全局一组运行/停止按钮"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("BioPaperMiner — 生物文献挖掘系统")
        self.root.geometry("1000x800")
        self.root.minsize(750, 550)
        self.root.configure(bg=COLORS["bg_primary"])

        self._running = False
        self._process = None
        self._current_panel = None

        self._build_ui()

    # ── UI 构建 ──

    def _build_ui(self):
        # 顶部标题
        hdr = tk.Frame(self.root, bg=COLORS["bg_header"], padx=20, pady=10)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="BioPaperMiner", font=FONT_TITLE,
                 fg="#FFFFFF", bg=COLORS["bg_header"]).pack(side=tk.LEFT)
        tk.Label(hdr, text="PubMed 检索 → PDF 下载 → MinerU 解析 → LLM 分析 → 报告生成",
                 font=("Helvetica", 11), fg="#FFFFFF",
                 bg=COLORS["bg_header"]).pack(side=tk.LEFT, padx=(10, 0))

        # 主内容
        main = tk.Frame(self.root, bg=COLORS["bg_primary"])
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # ── 左侧导航 ──
        nav = tk.LabelFrame(main, text="  功能导航  ", font=FONT_HEADING,
                            fg=COLORS["fg_heading"], bg=COLORS["bg_primary"],
                            bd=1, relief=tk.RAISED, padx=10, pady=8)
        nav.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        self.nav_var = tk.StringVar(value="search")
        self.nav_items = []
        nav_callbacks = [
            ("PubMed文献检索", "search", self._activate_search),
            ("提取参考文献", "refs", self._activate_refs),
            ("PDF文献下载", "download", self._activate_download),
            ("PDF文献自动分析", "pipeline", self._activate_pipeline),
            ("PDF文献重命名", "rename", self._activate_rename),
            ("查看报告", "report", self._activate_report),
            ("设置", "settings", self._activate_settings),
            ("配置", "config", self._activate_config),
        ]
        self._nav_labels = {}
        for text, key, callback in nav_callbacks:
            lbl = tk.Label(nav, text=f"  {text}  ", font=FONT_BTN,
                           fg="#000000", bg=COLORS["bg_button"],
                           padx=8, pady=6, cursor="hand2",
                           anchor=tk.W, relief=tk.RAISED, bd=1)
            lbl.pack(pady=(4, 3), fill=tk.X, padx=2)
            lbl.bind("<Button-1>", lambda e, k=key: self._on_nav_click(k))
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(bg=COLORS["bg_button_hover"]))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(bg=COLORS["bg_button"]))
            self._nav_labels[key] = lbl

        # ── 右侧内容区 ──
        self.content = tk.Frame(main, bg=COLORS["bg_primary"])
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 创建 6 个模块面板
        self.panels = {
            "search":   ModulePanel(self.content, self.root, "PubMed 检索"),
            "download": ModulePanel(self.content, self.root, "PDF 下载"),
            "pipeline": ModulePanel(self.content, self.root, "全流程 Pipeline"),
            "report":   ModulePanel(self.content, self.root, "查看报告"),
            "config":   ModulePanel(self.content, self.root, "配置"),
            "refs":     ModulePanel(self.content, self.root, "提取参考文献"),
            "rename":   ModulePanel(self.content, self.root, "PDF 重命名"),
            "settings": ModulePanel(self.content, self.root, "设置"),
        }

        # 初始化各面板参数
        self._init_search_panel()
        self._init_download_panel()
        self._init_pipeline_panel()
        self._init_report_panel()
        self._init_config_panel()
        self._init_refs_panel()
        self._init_rename_panel()
        self._init_settings_panel()

        # 全局运行/停止按钮
        btn_bar = tk.Frame(self.content, bg=COLORS["bg_primary"])
        btn_bar.pack(fill=tk.X, pady=(0, 4))

        self.run_btn = tk.Label(btn_bar, text="  运行  ",
            font=("Helvetica", 15, "bold"), fg="#1F2937",
            bg=COLORS["run_bg"], padx=20, pady=6, cursor="hand2",
            relief=tk.RAISED, bd=1)
        self.run_btn.pack(side=tk.LEFT)
        self.run_btn.bind("<Button-1>", lambda e: self._on_run())
        self.run_btn.bind("<Enter>", lambda e: self.run_btn.config(bg="#388E3C"))
        self.run_btn.bind("<Leave>", lambda e: self.run_btn.config(bg=COLORS["run_bg"]))

        self.stop_btn = tk.Label(btn_bar, text="  停止  ",
            font=("Helvetica", 15, "bold"), fg="#FFFFFF",
            bg="#f05a46", padx=20, pady=6, cursor="hand2",
            relief=tk.RAISED, bd=1)
        self.stop_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.stop_btn.bind("<Button-1>", lambda e: self._on_stop())
        self.stop_btn.bind("<Enter>", lambda e: self.stop_btn.config(bg="#D32F2F"))
        self.stop_btn.bind("<Leave>", lambda e: self.stop_btn.config(bg="#f05a46"))

        # 默认激活搜索
        self._on_nav_click("search")

    # ── 面板初始化 ──

    def _init_search_panel(self):
        p = self.panels["search"]
        p.add_field(0, "搜索关键词:", "CRISPR gene editing")
        p.add_field(1, "最大结果数:", "20")
        p.add_field(2, "起始日期 (YYYY/MM/DD):", "")
        p.add_field(3, "截止日期 (YYYY/MM/DD):", "")
        p.add_field(4, "输出目录:", "./pubmed_results")

    def _init_download_panel(self):
        p = self.panels["download"]
        default_csv = "./papers.csv"
        rd = Path("./pubmed_results")
        if rd.exists():
            csvs = list(rd.glob("*.csv"))
            if csvs:
                default_csv = str(csvs[0])
        p.add_field(0, "输入文件 (CSV/Excel):", default_csv, file_ext="*.csv;*.xlsx;*.xls")
        p.add_field(1, "输出目录:", "./pdf_download_results")

    def _init_pipeline_panel(self):
        p = self.panels["pipeline"]
        pf = p.param_frame

        # Row 0: 输入模式选择
        tk.Label(pf, text="输入模式:", font=FONT_LABEL,
                 fg=COLORS["fg_text"], bg=COLORS["bg_primary"]).grid(
            row=0, column=0, sticky=tk.W, pady=2)
        p._mode_var = tk.StringVar(value="目录模式")
        mode_cb = ttk.Combobox(pf, textvariable=p._mode_var,
                               values=["目录模式", "文件模式"],
                               state="readonly", width=43)
        mode_cb.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        pf.columnconfigure(1, weight=1)

        # Row 1: PDF 目录 / 文件（根据模式显隐）
        p._dir_var = tk.StringVar(value="./pdfs")
        p._file_var = tk.StringVar(value="")
        p._dir_label = tk.Label(pf, text="PDF 目录:", font=FONT_LABEL,
                                fg=COLORS["fg_text"], bg=COLORS["bg_primary"])
        p._dir_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        p._dir_entry = tk.Entry(pf, textvariable=p._dir_var, font=FONT_ENTRY,
                                fg=COLORS["fg_text"], bg=COLORS["bg_entry"],
                                relief=tk.RAISED, bd=1, width=45)
        p._dir_entry.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        p._dir_btn = tk.Button(pf, text="📂", font=("Helvetica", 11),
                               fg=COLORS["fg_text"], bg=COLORS["bg_button"],
                               relief=tk.RAISED, bd=1, cursor="hand2",
                               command=lambda v=p._dir_var: p._browse(v), width=2)
        p._dir_btn.grid(row=1, column=2, padx=(5, 0), pady=2)

        p._file_label = tk.Label(pf, text="PDF 文件:", font=FONT_LABEL,
                                 fg=COLORS["fg_text"], bg=COLORS["bg_primary"])
        p._file_entry = tk.Entry(pf, textvariable=p._file_var, font=FONT_ENTRY,
                                 fg=COLORS["fg_text"], bg=COLORS["bg_entry"],
                                 relief=tk.RAISED, bd=1, width=45)
        p._file_btn = tk.Button(pf, text="📄", font=("Helvetica", 11),
                                fg=COLORS["fg_text"], bg=COLORS["bg_button"],
                                relief=tk.RAISED, bd=1, cursor="hand2",
                                command=lambda v=p._file_var: p._browse_files(v, "*.pdf"),
                                width=2)

        # 初始隐藏文件行
        for w in (p._file_label, p._file_entry, p._file_btn):
            w.grid_remove()

        # 模式切换事件
        def on_mode_change(*_):
            is_dir = p._mode_var.get() == "目录模式"
            for w in (p._dir_label, p._dir_entry, p._dir_btn):
                (w.grid if is_dir else w.grid_remove)()
            for w in (p._file_label, p._file_entry, p._file_btn):
                (w.grid if not is_dir else w.grid_remove)()
            if is_dir:
                p._dir_label.grid(row=1, column=0, sticky=tk.W, pady=2)
                p._dir_entry.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
                p._dir_btn.grid(row=1, column=2, padx=(5, 0), pady=2)
            else:
                p._file_label.grid(row=1, column=0, sticky=tk.W, pady=2)
                p._file_entry.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
                p._file_btn.grid(row=1, column=2, padx=(5, 0), pady=2)

        p._mode_var.trace_add("write", on_mode_change)

        p.param_vars = [p._dir_var, p._file_var]  # 供 _do_pipeline 读取

        # Row 2: 输出目录
        p.add_field(2, "输出目录:", "./pdf_analysis_results")

        # Row 3: 选项复选框（移到输出目录下方）
        cb = tk.Frame(p.param_frame, bg=COLORS["bg_primary"])
        cb.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=6)

        p._skip_mineru = tk.BooleanVar(value=False)
        tk.Checkbutton(cb, text="跳过 MinerU 解析", variable=p._skip_mineru,
                       bg=COLORS["bg_primary"], fg=COLORS["fg_text"],
                       selectcolor=COLORS["bg_button"]).pack(side=tk.LEFT, padx=(0, 12))

        p._skip_llm = tk.BooleanVar(value=False)
        tk.Checkbutton(cb, text="跳过 LLM 分析", variable=p._skip_llm,
                       bg=COLORS["bg_primary"], fg=COLORS["fg_text"],
                       selectcolor=COLORS["bg_button"]).pack(side=tk.LEFT, padx=(0, 12))

        p._retry_failed = tk.BooleanVar(value=False)
        tk.Checkbutton(cb, text="只重试失败文件", variable=p._retry_failed,
                       bg=COLORS["bg_primary"], fg=COLORS["fg_text"],
                       selectcolor=COLORS["bg_button"]).pack(side=tk.LEFT)

    def _init_report_panel(self):
        p = self.panels["report"]
        p.add_field(0, "结果目录:", "./pdf_analysis_results")

    def _init_refs_panel(self):
        p = self.panels["refs"]
        pf = p.param_frame
        # Row 0: 格式选择
        tk.Label(pf, text="输入格式:", font=FONT_LABEL,
                 fg=COLORS["fg_text"], bg=COLORS["bg_primary"]).grid(
            row=0, column=0, sticky=tk.W, pady=2)
        p._refs_fmt = tk.StringVar(value="PMC HTML")
        ttk.Combobox(pf, textvariable=p._refs_fmt,
                     values=["PMC HTML", "RIS"],
                     state="readonly", width=43).grid(
            row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        pf.columnconfigure(1, weight=1)

        # Row 1: 输入文件
        p._refs_file_var = tk.StringVar(value="")
        p._refs_file_label = tk.Label(pf, text="输入文件:", font=FONT_LABEL,
                                      fg=COLORS["fg_text"], bg=COLORS["bg_primary"])
        p._refs_file_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        p._refs_file_entry = tk.Entry(pf, textvariable=p._refs_file_var, font=FONT_ENTRY,
                                      fg=COLORS["fg_text"], bg=COLORS["bg_entry"],
                                      relief=tk.RAISED, bd=1, width=45)
        p._refs_file_entry.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        def browse_refs_file():
            fmt = p._refs_fmt.get()
            if fmt == "PMC HTML":
                exts = ["*.html", "*.htm"]
                label = "HTML 文件"
            else:
                exts = ["*.ris"]
                label = "RIS 文件"
            filetypes = [(label, e) for e in exts] + [("所有文件", "*.*")]
            files = filedialog.askopenfilenames(
                title=f"选择 {label}",
                filetypes=filetypes,
                initialdir=ModulePanel._last_dir,
            )
            if files:
                p._refs_file_var.set(";".join(files))
                ModulePanel._last_dir = str(Path(files[0]).parent)

        tk.Button(pf, text="📄", font=("Helvetica", 11),
                  fg=COLORS["fg_text"], bg=COLORS["bg_button"],
                  relief=tk.RAISED, bd=1, cursor="hand2",
                  command=browse_refs_file, width=2).grid(
            row=1, column=2, padx=(5, 0), pady=2)

        # Row 2: 输出目录
        p.add_field(2, "输出目录:", "./references_output")

    def _init_rename_panel(self):
        p = self.panels["rename"]
        p.add_field(0, "PDF 目录:", "./pdfs")
        p.add_field(1, "输出目录:", "./renamed_pdfs")
        p._analysis_json_var = tk.StringVar(value="./pdf_analysis_results/analysis_results.json")
        p._analysis_json_entry = tk.Entry(p.param_frame, textvariable=p._analysis_json_var,
                                          font=FONT_ENTRY, fg=COLORS["fg_text"],
                                          bg=COLORS["bg_entry"],
                                          relief=tk.RAISED, bd=1, width=45)
        p._analysis_json_label = tk.Label(p.param_frame, text="分析结果 JSON:", font=FONT_LABEL,
                                          fg=COLORS["fg_text"], bg=COLORS["bg_primary"])
        p._analysis_json_btn = tk.Button(p.param_frame, text="📄", font=("Helvetica", 11),
                                         fg=COLORS["fg_text"], bg=COLORS["bg_button"],
                                         relief=tk.RAISED, bd=1, cursor="hand2",
                                         command=lambda v=p._analysis_json_var: p._browse_files(v, "*.json"),
                                         width=2)
        # 默认隐藏 JSON 行
        for w in (p._analysis_json_label, p._analysis_json_entry, p._analysis_json_btn):
            w.grid_remove()

        cb = tk.Frame(p.param_frame, bg=COLORS["bg_primary"])
        cb.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=6)
        p._dry_run = tk.BooleanVar(value=False)
        tk.Checkbutton(cb, text="仅预览，不重命名", variable=p._dry_run,
                       bg=COLORS["bg_primary"], fg=COLORS["fg_text"],
                       selectcolor=COLORS["bg_button"]).pack(side=tk.LEFT)
        p._use_analysis = tk.BooleanVar(value=False)
        tk.Checkbutton(cb, text="使用已有分析结果加速", variable=p._use_analysis,
                       bg=COLORS["bg_primary"], fg=COLORS["fg_text"],
                       selectcolor=COLORS["bg_button"]).pack(side=tk.LEFT, padx=(10,0))
        p._copy_files = tk.BooleanVar(value=False)
        tk.Checkbutton(cb, text="复制文件（而不是移动）", variable=p._copy_files,
                       bg=COLORS["bg_primary"], fg=COLORS["fg_text"],
                       selectcolor=COLORS["bg_button"]).pack(side=tk.LEFT, padx=(10,0))

        # 勾选"使用分析结果"时显隐 JSON 路径行
        def toggle_json_field(*_):
            show = p._use_analysis.get()
            for w in (p._analysis_json_label, p._analysis_json_entry, p._analysis_json_btn):
                (w.grid if show else w.grid_remove)()
            if show:
                p._analysis_json_label.grid(row=3, column=0, sticky=tk.W, pady=2)
                p._analysis_json_entry.grid(row=3, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
                p._analysis_json_btn.grid(row=3, column=2, padx=(5, 0), pady=2)
        p._use_analysis.trace_add("write", toggle_json_field)

    def _init_settings_panel(self):
        p = self.panels["settings"]
        from biopaperminer.config_editor import get
        current = _load_font_scale()
        tk.Label(p.param_frame, text="字体大小:", font=FONT_LABEL,
                 fg=COLORS["fg_text"], bg=COLORS["bg_primary"]).grid(
            row=0, column=0, sticky=tk.W, pady=2)
        p._font_var = tk.StringVar(value=str(current))
        ttk.Combobox(p.param_frame, textvariable=p._font_var,
                     values=["0.8", "0.9", "1.0", "1.1", "1.2", "1.3", "1.5", "2.0"],
                     state="normal", width=43).grid(
            row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        p.param_frame.columnconfigure(1, weight=1)
        tk.Label(p.param_frame,
                 text="提示: 可选择预设值或直接输入(0.5~3.0)，点击 [运行] 生效",
                 font=FONT_LABEL, fg=COLORS["fg_text"],
                 bg=COLORS["bg_primary"]).grid(
            row=1, column=0, columnspan=3, sticky=tk.W, pady=(4,0))

    def _init_config_panel(self):
        from biopaperminer.config_editor import EDITABLE_FIELDS, get
        p = self.panels["config"]
        # 根据 EDITABLE_FIELDS 动态生成配置输入框
        provider_combobox = None
        for idx, (key, label, _type, default, show_when, *extra) in enumerate(EDITABLE_FIELDS):
            cur = get(key, default)
            is_secret = (_type == "secret")
            choices = extra[0] if extra else None
            p.add_field(idx, f"{label}:", cur, secret=is_secret,
                        choices=choices, show_when=show_when)
            # 记住 LLM 提供商的下拉框控件
            if key == "LLM_PROVIDER":
                provider_combobox = p._param_widgets[-1]
        # 记录总字段数
        p._config_field_count = len(EDITABLE_FIELDS)

        # ── 首次应用显隐，然后绑定切换事件 ──
        self._apply_provider_visibility(p)
        if provider_combobox:
            provider_combobox.bind("<<ComboboxSelected>>",
                                   lambda e: self._apply_provider_visibility(p))

    def _apply_provider_visibility(self, p):
        """根据选中的 LLM 提供商，显隐相关配置字段"""
        provider = p.param_vars[0].get() if p.param_vars else "agnes"
        for i in range(p._config_field_count):
            show_when = p._param_show_when[i]
            visible = (show_when == "*" or show_when == provider)
            # 标签和输入框必须成对显隐
            for w in (p._param_labels[i], p._param_widgets[i]):
                method = w.grid if visible else w.grid_remove
                method()
            if p._param_btns[i]:
                method = p._param_btns[i].grid if visible else p._param_btns[i].grid_remove
                method()

    # ── 导航切换 ──

    def _show_panel(self, key: str):
        """隐藏所有面板，只显示指定的"""
        for panel in self.panels.values():
            panel.param_frame.pack_forget()
            panel.log_frame.pack_forget()

        p = self.panels[key]
        p.param_frame.pack(in_=self.content, fill=tk.X, pady=(0, 4))
        p.log_frame.pack(in_=self.content, fill=tk.BOTH, expand=True)

        # 记录当前选中的模块
        self._current_panel = key

        # Radiobutton 通过 nav_var 自动管理选中态
        self.nav_var.set(key)

    def _on_nav_click(self, key):
        """导航点击处理：高亮选中项 + 打开对应面板"""
        for k, lbl in self._nav_labels.items():
            bg = COLORS["bg_active"] if k == key else COLORS["bg_button"]
            lbl.config(bg=bg)
        self.nav_var.set(key)
        {
            "search": self._activate_search,
            "refs": self._activate_refs,
            "download": self._activate_download,
            "pipeline": self._activate_pipeline,
            "rename": self._activate_rename,
            "report": self._activate_report,
            "settings": self._activate_settings,
            "config": self._activate_config,
        }[key]()

    def _activate_search(self):
        self._show_panel("search")
        self.panels["search"].log("切换到: PubMed 检索")

    def _activate_download(self):
        self._show_panel("download")
        self.panels["download"].log("切换到: PDF 下载")

    def _activate_pipeline(self):
        self._show_panel("pipeline")
        self.panels["pipeline"].log("切换到: 全流程 Pipeline")

    def _activate_report(self):
        self._show_panel("report")
        self.panels["report"].log("切换到: 查看报告")

    def _activate_refs(self):
        self._show_panel("refs")
        self.panels["refs"].log("切换到: 提取参考文献")

    def _activate_rename(self):
        self._show_panel("rename")
        self.panels["rename"].log("切换到: PDF 重命名")

    def _activate_settings(self):
        self._show_panel("settings")
        self.panels["settings"].log("切换到: 设置")

    def _activate_config(self):
        self._show_panel("config")
        self.panels["config"].log("切换到: 配置")

    # ── 全局运行 / 停止 ──

    def _on_run(self):
        if self._running:
            messagebox.showwarning("提示", "已有任务在运行中")
            return

        if not self._current_panel:
            messagebox.showwarning("提示", "请先选择一个功能模块")
            return

        key = self._current_panel
        p = self.panels[key]

        self._running = True
        self.run_btn.config(bg="#9E9E9E")
        self.stop_btn.config(bg="#f05a46")
        p.clear_log()

        # 绑定执行函数
        exec_map = {
            "search":   self._do_search,
            "download": self._do_download,
            "pipeline": self._do_pipeline,
            "report":   self._do_report,
            "settings": self._do_settings,
            "config":   self._do_config,
            "refs":     self._do_refs,
            "rename":   self._do_rename,
        }
        executor = exec_map.get(key)
        if not executor:
            self._running = False
            messagebox.showerror("错误", f"未知模块: {key}")
            return

        threading.Thread(target=self._run_task, args=(executor, p), daemon=True).start()

    def _on_stop(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self.panels[self._current_panel].log("已终止运行", "warning")
        else:
            self.panels[self._current_panel].log("没有正在运行的任务", "warning")
        self._reset_buttons()

    def _reset_buttons(self):
        self.run_btn.config(bg=COLORS["run_bg"])
        self.stop_btn.config(bg="#BDBDBD")

    # ── 各模块业务逻辑 ──

    def _do_search(self, p: ModulePanel):
        q = p.param_vars[0].get() if len(p.param_vars) > 0 else "CRISPR"
        n = p.param_vars[1].get() if len(p.param_vars) > 1 else "20"
        md = p.param_vars[2].get() if len(p.param_vars) > 2 else ""
        xd = p.param_vars[3].get() if len(p.param_vars) > 3 else ""
        out = p.param_vars[4].get() if len(p.param_vars) > 4 else "./pubmed_results"

        p.log(f'搜索关键词: "{q}"')
        p.log(f"最大结果数: {n}")

        cmd = [sys.executable, "-m", "biopaperminer.pipeline", "search", q, "-n", n, "--output", out]
        if md:
            cmd += ["--mindate", md]
        if xd:
            cmd += ["--maxdate", xd]

        self._exec_cmd(cmd, p)

    def _do_download(self, p: ModulePanel):
        inp = p.param_vars[0].get() if len(p.param_vars) > 0 else "./papers.csv"
        out = p.param_vars[1].get() if len(p.param_vars) > 1 else "./pdf_download_results"

        ip = Path(inp)
        if not ip.exists():
            p.log(f"❌ 路径不存在: {inp}", "error")
            self.root.after(0, messagebox.showerror, "错误", f"路径不存在:\n{inp}")
            return
        if ip.is_dir():
            cands = []
            for ext in ("*.csv", "*.xlsx", "*.xls"):
                cands.extend(ip.glob(ext))
            if not cands:
                p.log(f"❌ 目录中没有 CSV/Excel 文件: {inp}", "error")
                self.root.after(0, messagebox.showerror, "错误",
                               f"目录中没有找到 CSV/Excel 文件:\n{inp}")
                return
            csvs = [f for f in cands if f.suffix.lower() == ".csv"]
            chosen = csvs[0] if csvs else cands[0]
            p.log(f"📂 目录中检测到文件: {chosen.name}", "success")
            inp = str(chosen)
            p.log(f"   将使用: {inp}")
            if len(p.param_vars) > 0:
                p.param_vars[0].set(inp)

        if not Path(inp).is_file():
            p.log(f"❌ 输入路径不是文件: {inp}", "error")
            self.root.after(0, messagebox.showerror, "错误", f"输入路径不是文件:\n{inp}")
            return

        p.log(f"输入文件: {inp}")
        p.log(f"输出目录: {out}")
        cmd = [sys.executable, "-m", "biopaperminer.pipeline", "download", inp, "-o", out]
        self._exec_cmd(cmd, p)

    def _do_pipeline(self, p: ModulePanel):
        mode = getattr(p, "_mode_var", None)
        is_dir_mode = mode and mode.get() == "目录模式"

        out_idx = 2  # 输出目录始终是第 3 个字段（0-based）
        out_dir = p.param_vars[out_idx].get() if len(p.param_vars) > out_idx else "./pdf_analysis_results"

        cmd = [sys.executable, "-m", "biopaperminer.pipeline", "pipeline",
               "--out", out_dir]

        if is_dir_mode:
            pdf_dir = p._dir_var.get() if hasattr(p, "_dir_var") else "./pdfs"
            cmd += ["--pdf-dir", pdf_dir]
            p.log(f"PDF 目录: {pdf_dir}")
        else:
            pdf_files_raw = p._file_var.get().strip() if hasattr(p, "_file_var") else ""
            if pdf_files_raw:
                files = [f.strip() for f in pdf_files_raw.split(";") if f.strip()]
                cmd += ["--pdf-files"] + files
                p.log(f"PDF 文件: {len(files)} 个")
            else:
                p.log("⚠️  请选择 PDF 文件", "warning")
                return

        p.log(f"输出目录: {out_dir}")

        if getattr(p, "_skip_mineru", None) and p._skip_mineru.get():
            cmd.append("--skip-mineru")
        if getattr(p, "_skip_llm", None) and p._skip_llm.get():
            cmd.append("--skip-llm")
        if getattr(p, "_retry_failed", None) and p._retry_failed.get():
            cmd.append("--retry-failed")

        self._exec_cmd(cmd, p)

    def _do_report(self, p: ModulePanel):
        rd = p.param_vars[0].get() if len(p.param_vars) > 0 else "./pdf_analysis_results"
        p.log(f"结果目录: {rd}")
        hp = Path(rd) / "interactive_report.html"
        if hp.exists():
            p.log(f"正在打开: {hp}")
            if sys.platform == "darwin":
                subprocess.run(["open", str(hp)])
            elif sys.platform == "win32":
                os.startfile(str(hp))
            else:
                subprocess.run(["xdg-open", str(hp)])
            p.log("报告已在浏览器中打开", "success")
        else:
            p.log(f"报告不存在: {hp}", "error")

    def _do_refs(self, p: ModulePanel):
        fmt = getattr(p, "_refs_fmt", None)
        fmt_str = fmt.get() if fmt else "PMC HTML"
        input_file = p._refs_file_var.get().strip() if hasattr(p, "_refs_file_var") else ""
        output = p.param_vars[0].get().strip() if len(p.param_vars) > 0 else "./references_output"

        if not input_file:
            p.log("❌ 请选择输入文件", "error")
            return

        cmd = [sys.executable, "-m", "biopaperminer.pipeline", "refs", input_file, "-o", output]
        if fmt_str == "RIS":
            cmd += ["--format", "ris"]
        p.log(f"格式: {fmt_str}")
        p.log(f"输入文件: {input_file}")
        p.log(f"输出目录: {output}")
        self._exec_cmd(cmd, p)

    def _do_rename(self, p: ModulePanel):
        pdf_dir = p.param_vars[0].get() if len(p.param_vars) > 0 else "./pdfs"
        out_dir = p.param_vars[1].get() if len(p.param_vars) > 1 else "./renamed_pdfs"
        dry_run = getattr(p, "_dry_run", None) and p._dry_run.get()
        use_analysis = getattr(p, "_use_analysis", None) and p._use_analysis.get()
        copy_files = getattr(p, "_copy_files", None) and p._copy_files.get()

        p.log(f"PDF 目录: {pdf_dir}")
        p.log(f"输出目录: {out_dir}")
        p.log("🔍 仅预览（不重命名）" if dry_run else "✏️  即将重命名")
        if copy_files:
            p.log("📋 复制模式（保留原文件）")

        cmd = [sys.executable, "-m", "biopaperminer.pipeline", "rename", pdf_dir,
               "-o", out_dir]
        if dry_run:
            cmd.append("--dry-run")
        if copy_files:
            cmd.append("--copy")
        if use_analysis:
            aj_path = p._analysis_json_var.get().strip() if hasattr(p, "_analysis_json_var") else ""
            if aj_path and Path(aj_path).exists():
                cmd += ["--analysis-json", aj_path]
        self._exec_cmd(cmd, p)

    @staticmethod
    def _apply_all_fonts(widget, font_map: dict):
        """递归更新控件的字体"""
        try:
            cls = type(widget).__name__
            if cls in ('Label', 'Button', 'Radiobutton', 'Checkbutton'):
                f = font_map.get('label', font_map.get('btn'))
                if f:
                    widget.config(font=f)
            elif cls == 'Entry':
                f = font_map.get('entry')
                if f:
                    widget.config(font=f)
            elif cls == 'Combobox':
                f = font_map.get('entry')
                if f:
                    widget.config(font=f)
            elif cls == 'ScrolledText':
                import tkinter.scrolledtext
                f = font_map.get('log')
                if f:
                    widget.config(font=f)
            elif cls == 'LabelFrame':
                f = font_map.get('heading')
                if f:
                    widget.config(font=f)
            elif cls == 'Menu':
                pass
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                BioPaperMinerApp._apply_all_fonts(child, font_map)
        except Exception:
            pass

    def _do_settings(self, p: ModulePanel):
        from biopaperminer.config_editor import save
        val = p._font_var.get().strip()
        # 校验输入
        try:
            scale = float(val)
            if scale < 0.5 or scale > 3.0:
                p.log(f"请输入 0.5~3.0 之间的值", "error")
                return
        except ValueError:
            p.log(f"无效的数值: {val}", "error")
            return
        save({"FONT_SCALE": str(scale)})
        # 重新计算字体
        global FONT_SCALE, FONT_TITLE, FONT_LABEL, FONT_ENTRY, FONT_LOG, FONT_BTN, FONT_HEADING
        try:
            dpi = float(p._root.tk.call('tk', 'scaling'))
            if sys.platform == "win32":
                dpi = max(1.0, dpi / 1.0)
            elif sys.platform == "darwin":
                dpi = max(1.0, dpi / 1.333)
            else:
                dpi = 1.0
        except Exception:
            dpi = 1.0
        FONT_SCALE = dpi * scale

        def fs(size):
            return max(int(size * FONT_SCALE + 0.5), size)

        FONT_TITLE   = ("Helvetica", fs(22), "bold")
        FONT_LABEL   = ("Helvetica", fs(11), "bold")
        FONT_ENTRY   = ("Helvetica", fs(11))
        FONT_LOG     = ("Consolas", fs(11))
        FONT_BTN     = ("Helvetica", fs(12))
        FONT_HEADING = ("Helvetica", fs(12), "bold")

        # 实时应用到所有现有控件
        font_map = {
            'title': FONT_TITLE, 'label': FONT_LABEL, 'entry': FONT_ENTRY,
            'log': FONT_LOG, 'btn': FONT_BTN, 'heading': FONT_HEADING,
        }
        BioPaperMinerApp._apply_all_fonts(p._root, font_map)
        p._root.update()
        p.log(f"字体大小已实时调整为 {val} 倍", "success")

    def _do_config(self, p: ModulePanel):
        from biopaperminer.config_editor import EDITABLE_FIELDS, save

        field_count = getattr(p, "_config_field_count", len(EDITABLE_FIELDS))
        updates = {}
        for idx in range(field_count):
            if idx < len(EDITABLE_FIELDS):
                key, label, _type, default, *_ = EDITABLE_FIELDS[idx]
                val = p.param_vars[idx].get().strip() if idx < len(p.param_vars) else ""
                if val:
                    updates[key] = val

        if updates:
            save(updates)
            p.log(f"✅ 已保存 {len(updates)} 项配置到 user_config.json", "success")
            for key, val in updates.items():
                display = val if _type != "secret" else val[:4] + "****"
                p.log(f"  {key} = {display}")
        else:
            p.log("⚠️  没有需要保存的配置", "warning")

        # ── 连通性测试 ──
        p.log("🔄 正在测试连接，请稍候...", "info")
        try:
            from biopaperminer.analyzer import OllamaAnalyzer
            analyzer = OllamaAnalyzer()
            ok = analyzer.check_connection()
            if ok:
                p.log("✅ LLM 服务连接成功！配置可用", "success")
            else:
                p.log("❌ LLM 服务连接失败，请检查 API Key 和网络", "error")
        except Exception as e:
            p.log(f"⚠️  连接测试异常: {e}", "warning")

    # ── 命令执行（子进程，捕获输出到 GUI 日志） ──

    def _exec_cmd(self, cmd: list, panel: ModulePanel):
        # 打包环境下：替换为 exe 自身
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable] + cmd[3:]

        panel.log(f"执行: {' '.join(cmd)}")
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            if sys.platform == "win32":
                env["PYTHONIOENCODING"] = "utf-8"
            self._process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=0, text=False,  # 无缓冲二进制模式
                cwd=str(Path(__file__).parent.parent), env=env,
            )
            for line in iter(self._process.stdout.readline, b''):
                try:
                    decoded = line.decode("utf-8").rstrip()
                except UnicodeDecodeError:
                    if sys.platform == "win32":
                        decoded = line.decode("gbk", errors="replace").rstrip()
                    else:
                        decoded = line.decode("utf-8", errors="replace").rstrip()
                if not decoded:
                    continue
                level = "info"
                if "✅" in decoded or "success" in decoded.lower():
                    level = "success"
                elif "❌" in decoded or "error" in decoded.lower() or "failed" in decoded.lower():
                    level = "error"
                elif "⚠" in decoded or "warn" in decoded.lower():
                    level = "warning"
                panel.log(decoded, level)
            self._process.wait()
            rc = self._process.returncode
            panel.log("执行完成" if rc == 0 else f"执行结束，返回码: {rc}",
                      "success" if rc == 0 else "warning")
        except Exception as e:
            panel.log(f"执行失败: {e}", "error")
        finally:
            self._process = None

    def _run_task(self, executor, panel: ModulePanel):
        """在线程中运行"""
        try:
            executor(panel)
        except Exception as e:
            panel.log(f"❌ 出错: {e}", "error")
            import traceback
            panel.log(traceback.format_exc(), "error")
        finally:
            self._process = None
            self._running = False
            self.root.after(0, self._reset_buttons)


def main():
    root = TkinterDnD.Tk()
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    # 根据 DPI 缩放字体
    _init_fonts(root)
    BioPaperMinerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
