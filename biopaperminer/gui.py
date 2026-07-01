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
except ImportError:
    print("❌ tkinter 不可用。")
    print()
    print("conda 环境（推荐）: conda activate biopaperminer && python main.py gui")
    print("pyenv 环境: brew install tcl-tk 后重装 Python")
    print()
    print("或者使用 TUI 模式（无需 tkinter）：")
    print("  python main.py tui")
    sys.exit(1)


# ═══════════════════════════════════════════════════════
# 淡蓝色配色方案
# ═══════════════════════════════════════════════════════

COLORS = {
    "bg_primary":     "#e8f4f8",
    "bg_header":      "#b8d8e8",
    "bg_button":      "#7ec8e3",
    "bg_button_hover": "#5bb5d8",
    "bg_active":      "#4aa3df",
    "bg_entry":       "#ffffff",
    "bg_log":         "#f0f8fb",
    "bg_panel":       "#dceaf2",
    "fg_text":        "#1a3a4a",
    "fg_heading":     "#0d4f6e",
    "fg_accent":      "#2196f3",
    "fg_success":     "#2e7d32",
    "fg_error":       "#c62828",
    "fg_warning":     "#f57f17",
    "fg_dim":         "#7a9aaa",
    "border":         "#8ec5d9",
    "run_bg":         "#43a047",
    "run_fg":         "#1a3a4a",
    "stop_bg":        "#e53935",
    "stop_fg":        "#1a3a4a",
}

FONT_TITLE = ("Helvetica", 22, "bold")
FONT_LABEL = ("Helvetica", 11)
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
        tk.Label(hdr, text="📚 BioPaperMiner", font=FONT_TITLE,
                 fg=COLORS["fg_heading"], bg=COLORS["bg_header"]).pack(side=tk.LEFT)
        tk.Label(hdr, text="PubMed 检索 → PDF 下载 → MinerU 解析 → LLM 分析 → 报告生成",
                 font=("Helvetica", 11), fg=COLORS["fg_dim"],
                 bg=COLORS["bg_header"]).pack(side=tk.LEFT, padx=(10, 0))

        # 主内容
        main = tk.Frame(self.root, bg=COLORS["bg_primary"])
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # ── 左侧导航 ──
        nav = tk.LabelFrame(main, text="  功能导航  ", font=FONT_HEADING,
                            fg=COLORS["fg_heading"], bg=COLORS["bg_panel"],
                            bd=1, relief=tk.RAISED, padx=10, pady=8)
        nav.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        self.nav_var = tk.StringVar(value="search")
        self.nav_items = []
        nav_callbacks = [
            ("🔍 PubMed 检索", "search", self._activate_search),
            ("📥 PDF 下载", "download", self._activate_download),
            ("🔄 全流程 Pipeline", "pipeline", self._activate_pipeline),
            ("📊 查看报告", "report", self._activate_report),
            ("⚙️  配置", "config", self._activate_config),
        ]
        for text, key, callback in nav_callbacks:
            rb = tk.Radiobutton(nav, text=text, font=FONT_BTN,
                                fg=COLORS["fg_text"],
                                bg=COLORS["bg_button"],
                                activebackground=COLORS["bg_button_hover"],
                                activeforeground="white",
                                selectcolor=COLORS["bg_active"],
                                relief=tk.RAISED, bd=1,
                                cursor="hand2", width=20, anchor=tk.W,
                                value=key,
                                variable=self.nav_var,
                                command=callback)
            rb.pack(pady=(4, 2), fill=tk.X)
            self.nav_items.append(rb)

        # ── 右侧内容区 ──
        self.content = tk.Frame(main, bg=COLORS["bg_primary"])
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 创建 5 个模块面板
        self.panels = {
            "search":   ModulePanel(self.content, self.root, "PubMed 检索"),
            "download": ModulePanel(self.content, self.root, "PDF 下载"),
            "pipeline": ModulePanel(self.content, self.root, "全流程 Pipeline"),
            "report":   ModulePanel(self.content, self.root, "查看报告"),
            "config":   ModulePanel(self.content, self.root, "配置"),
        }

        # 初始化各面板参数
        self._init_search_panel()
        self._init_download_panel()
        self._init_pipeline_panel()
        self._init_report_panel()
        self._init_config_panel()

        # 全局运行/停止按钮
        btn_bar = tk.Frame(self.content, bg=COLORS["bg_primary"])
        btn_bar.pack(fill=tk.X, pady=(0, 4))

        self.run_btn = tk.Button(btn_bar, text="▶ 运行",
            font=("Helvetica", 13, "bold"), fg=COLORS["run_fg"],
            bg=COLORS["run_bg"], activebackground="#388e3c",
            relief=tk.RAISED, bd=1, cursor="hand2", width=12,
            command=self._on_run)
        self.run_btn.pack(side=tk.LEFT)

        self.stop_btn = tk.Button(btn_bar, text="⏹ 停止",
            font=("Helvetica", 13, "bold"), fg=COLORS["stop_fg"],
            bg=COLORS["stop_bg"], activebackground="#c62828",
            relief=tk.RAISED, bd=1, cursor="hand2", width=12,
            command=self._on_stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(8, 0))

        # 默认激活搜索
        self._activate_search()

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
        p.add_field(1, "输出目录:", "./pdfs")

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
        p.add_field(2, "输出目录:", "./results")

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
        p.add_field(0, "结果目录:", "./results")

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
        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        p.clear_log()

        # 绑定执行函数
        exec_map = {
            "search":   self._do_search,
            "download": self._do_download,
            "pipeline": self._do_pipeline,
            "report":   self._do_report,
            "config":   self._do_config,
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

    def _run_task(self, executor, panel: ModulePanel):
        """在线程中执行具体任务"""
        try:
            executor(panel)
        except Exception as e:
            panel.log(f"执行出错: {e}", "error")
        finally:
            self._process = None
            self._running = False
            self.root.after(0, self._reset_buttons)

    def _reset_buttons(self):
        self.run_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

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
        out = p.param_vars[1].get() if len(p.param_vars) > 1 else "./pdfs"

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
        out_dir = p.param_vars[out_idx].get() if len(p.param_vars) > out_idx else "./results"

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
        rd = p.param_vars[0].get() if len(p.param_vars) > 0 else "./results"
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

    # ── 命令执行 ──

    def _exec_cmd(self, cmd: list, panel: ModulePanel):
        panel.log(f"执行命令: {' '.join(cmd)}")
        try:
            # 使用 Popen 直接读取行，避免缓冲导致日志延迟
            # 继承父进程环境变量，强制子进程无缓冲输出
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            if sys.platform == "win32":
                env["PYTHONIOENCODING"] = "utf-8"
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                text=False,
                cwd=str(Path(__file__).parent.parent),
                env=env,
            )
            while True:
                line = self._process.stdout.readline()
                if not line:
                    if self._process.poll() is not None:
                        break
                    continue
                try:
                    decoded = line.decode("utf-8", errors="replace").rstrip()
                except Exception:
                    decoded = str(line).rstrip()
                if not decoded:
                    continue
                if "✅" in decoded or "success" in decoded.lower():
                    panel.log(decoded, "success")
                elif "❌" in decoded or "error" in decoded.lower() or "failed" in decoded.lower():
                    panel.log(decoded, "error")
                elif "⚠" in decoded or "warn" in decoded.lower():
                    panel.log(decoded, "warning")
                else:
                    panel.log(decoded)
            self._process.wait()
            if self._process.returncode == 0:
                panel.log("执行完成", "success")
            else:
                panel.log(f"执行结束，返回码: {self._process.returncode}", "warning")
        except Exception as e:
            panel.log(f"执行失败: {e}", "error")
        finally:
            self._process = None


def main():
    root = tk.Tk()
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    BioPaperMinerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
