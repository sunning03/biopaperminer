#!/usr/bin/env python3
"""
BioPaperMiner TUI — 基于 rich 的交互式终端界面

用法:
  python3 tui.py
  python3 main.py tui
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.text import Text
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.markdown import Markdown
except ImportError:
    print("❌ 需要安装 rich: pip install rich")
    sys.exit(1)

console = Console()


# ── 菜单渲染 ──────────────────────────────────────────

def show_header():
    """显示顶部标题"""
    title = Text.assemble(
        ("📚 ", "bold cyan"),
        ("BioPaperMiner", "bold white"),
        (" — 生物文献挖掘系统", "dim"),
    )
    subtitle = Text(
        "PubMed 检索 → PDF 下载 → MinerU 解析 → LLM 分析 → 报告生成",
        style="dim blue",
    )
    console.print(Panel(
        title,
        subtitle=subtitle,
        border_style="cyan",
        padding=(0, 1),
    ))


def show_main_menu():
    """显示主菜单"""
    menu = Table(show_header=False, box=None, padding=(0, 1))
    menu.add_column("[bold yellow]#", width=3, style="yellow")
    menu.add_column("[bold cyan]选项", width=20, style="cyan")
    menu.add_column("[dim]说明", style="dim")

    menu.add_row("1", "🔍 PubMed 检索", "按关键词搜索文献")
    menu.add_row("2", "📥 PDF 下载", "从 CSV/Excel 批量下载 PDF")
    menu.add_row("3", "🔄 全流程 Pipeline", "PDF → MinerU → LLM → 报告")
    menu.add_row("4", "📊 查看报告", "打开生成的分析报告")
    menu.add_row("5", "⚙️  配置", "查看/修改配置")
    menu.add_row("6", "📄 提取参考文献", "从 PMC HTML 提取参考文献")
    menu.add_row("0", "🚪 退出", "")

    console.print(Panel(menu, border_style="cyan", title="主菜单", title_align="left"))


def show_sub_menu(title: str, items: list, back_label: str = "返回主菜单"):
    """显示子菜单"""
    menu = Table(show_header=False, box=None, padding=(0, 1))
    menu.add_column("[bold yellow]#", width=3, style="yellow")
    menu.add_column("[bold cyan]选项", width=30, style="cyan")
    menu.add_column("[dim]说明", style="dim")

    for i, (label, desc) in enumerate(items, 1):
        menu.add_row(str(i), label, desc)
    menu.add_row("0", back_label, "")

    console.print(Panel(menu, border_style="cyan", title=title, title_align="left"))


# ── 功能模块 ──────────────────────────────────────────

def run_pipeline(pdf_dir: Optional[str] = None, out_dir: Optional[str] = None):
    """运行全流程 Pipeline（含可选跳过步骤）"""
    if pdf_dir is None:
        pdf_dir = Prompt.ask("📂 请输入 PDF 目录路径", default="./pdfs")
    if out_dir is None:
        out_dir = Prompt.ask("📂 请输入输出目录路径", default="./pdf_analysis_results")

    pdf_path = Path(pdf_dir)
    if not pdf_path.is_dir():
        console.print(f"[red]❌ 目录不存在: {pdf_dir}[/red]")
        return

    skip_mineru = Confirm.ask("⏭  跳过 MinerU 解析？(直接用已有 MD)", default=False)
    skip_llm = Confirm.ask("⏭  跳过 LLM 分析？(只跑 MinerU)", default=False)
    retry_failed = Confirm.ask("🔁 只重试失败文件？", default=False)

    console.print(f"\n[cyan]▶ 开始 Pipeline: {pdf_dir} → {out_dir}[/cyan]")
    console.print("[dim]步骤: MinerU 解析 → LLM 分析 → 报告生成[/dim]\n")

    cmd = [
        sys.executable, "-m", "biopaperminer.pipeline", "pipeline",
        "--pdf-dir", pdf_dir,
        "--out", out_dir,
    ]
    if skip_mineru:
        cmd.append("--skip-mineru")
    if skip_llm:
        cmd.append("--skip-llm")
    if retry_failed:
        cmd.append("--retry-failed")

    result = subprocess.run(cmd, cwd=str(Path(__file__).parent.parent))
    if result.returncode == 0:
        console.print(f"\n[green]✅ Pipeline 完成！报告位于: {out_dir}[/green]")
        console.print(f"   在浏览器中打开: {out_dir}/interactive_report.html")
    else:
        console.print(f"\n[yellow]⚠️  Pipeline 未完成，返回码: {result.returncode}[/yellow]")


def search_pubmed():
    """PubMed 检索（含日期筛选、代理）"""
    query = Prompt.ask("🔍 请输入搜索关键词", default="CRISPR gene editing")
    n = IntPrompt.ask("📊 最大结果数", default=20)
    output = Prompt.ask("📂 输出目录", default="./pubmed_results")
    mindate = Prompt.ask("📅 起始日期 (YYYY/MM/DD，留空不限)", default="")
    maxdate = Prompt.ask("📅 截止日期 (YYYY/MM/DD，留空不限)", default="")
    proxy = Prompt.ask("🌐 代理地址 (留空不使用)", default="")

    console.print(f"\n[cyan]▶ 搜索 PubMed: \"{query}\" (最多 {n} 条)[/cyan]")

    cmd = [
        sys.executable, "-m", "biopaperminer.pipeline", "search",
        query, "-n", str(n), "--output", output,
    ]
    if mindate:
        cmd += ["--mindate", mindate]
    if maxdate:
        cmd += ["--maxdate", maxdate]
    if proxy:
        cmd += ["--proxy", proxy]

    result = subprocess.run(cmd, cwd=str(Path(__file__).parent.parent))
    if result.returncode == 0:
        console.print(f"\n[green]✅ 搜索完成！结果保存在: {output}[/green]")
    else:
        console.print(f"\n[yellow]⚠️  搜索未完成，返回码: {result.returncode}[/yellow]")


def download_pdfs():
    """PDF 下载"""
    input_file = Prompt.ask("📂 输入文件路径 (CSV/Excel)", default="./papers.csv")
    output_dir = Prompt.ask("📂 输出目录", default="./pdf_download_results")

    console.print(f"\n[cyan]▶ 下载 PDF: {input_file} → {output_dir}[/cyan]")

    cmd = [
        sys.executable, "-m", "biopaperminer.pipeline", "download",
        input_file, "-o", output_dir,
    ]

    result = subprocess.run(cmd, cwd=str(Path(__file__).parent.parent))
    if result.returncode == 0:
        console.print(f"\n[green]✅ 下载完成！PDF 保存在: {output_dir}[/green]")
    else:
        console.print(f"\n[yellow]⚠️  下载未完成，返回码: {result.returncode}[/yellow]")


def view_reports():
    """查看报告"""
    results_dir = Prompt.ask("📂 结果目录", default="./pdf_analysis_results")
    results_path = Path(results_dir)

    if not results_path.exists():
        console.print(f"[red]❌ 目录不存在: {results_dir}[/red]")
        return

    # 列出可用的报告文件
    table = Table(title=f"📂 {results_dir} 目录内容")
    table.add_column("文件名", style="cyan")
    table.add_column("大小", style="dim")
    table.add_column("类型", style="yellow")

    for f in sorted(results_path.iterdir()):
        if f.is_file():
            size = f"{f.stat().st_size / 1024:.1f} KB" if f.stat().st_size < 1024*1024 else f"{f.stat().st_size / (1024*1024):.1f} MB"
            if f.suffix == ".json":
                ftype = "JSON"
            elif f.suffix == ".csv":
                ftype = "CSV"
            elif f.suffix == ".md":
                ftype = "Markdown"
            elif f.suffix == ".html":
                ftype = "HTML 报告"
            else:
                ftype = ftype
            table.add_row(f.name, size, ftype)

    console.print(table)

    # 询问是否打开 HTML 报告
    html_file = results_path / "interactive_report.html"
    if html_file.exists():
        if Confirm.ask("🌐 是否用浏览器打开交互式报告?", default=True):
            console.print(f"\n[dim]正在打开: {html_file}[/dim]")
            if sys.platform == "darwin":
                subprocess.run(["open", str(html_file)])
            elif sys.platform == "win32":
                os.startfile(str(html_file))
            else:
                subprocess.run(["xdg-open", str(html_file)])


def extract_refs():
    """从 PMC HTML 或 RIS 文件提取参考文献"""
    fmt = Prompt.ask("📄 输入格式", choices=["PMC HTML", "RIS"], default="PMC HTML")
    ext = "*.html" if fmt == "PMC HTML" else "*.ris"
    input_file = Prompt.ask(f"📄 请输入 {ext} 文件路径", default="")
    if not input_file or not Path(input_file).is_file():
        console.print("[red]❌ 文件不存在[/red]")
        return
    output = Prompt.ask("📂 输出目录", default="./references_output")

    console.print(f"\n[cyan]▶ 提取参考文献 ({fmt}): {input_file} → {output}[/cyan]")

    cmd = [
        sys.executable, "-m", "biopaperminer.pipeline", "refs",
        input_file, "-o", output,
    ]
    if fmt == "RIS":
        cmd += ["--format", "ris"]
    result = subprocess.run(cmd, cwd=str(Path(__file__).parent.parent))
    if result.returncode == 0:
        console.print(f"[green]✅ 参考文献已提取到: {output}[/green]")
    else:
        console.print(f"[yellow]⚠️  提取未完成，返回码: {result.returncode}[/yellow]")


def show_config():
    """交互式配置编辑（动态显隐 + 密码打码 + 连通测试）"""
    from biopaperminer.config_editor import EDITABLE_FIELDS, load, save

    current = load()
    console.print("[bold cyan]⚙️  配置编辑器[/bold cyan]\n")

    # ── 显示当前值 ──
    table = Table(title="📋 当前配置")
    table.add_column("配置项", style="cyan")
    table.add_column("当前值", style="white")
    for key, label, _type, default, show_when, *_ in EDITABLE_FIELDS:
        val = current.get(key) or os.environ.get(key, default)
        display = val if _type != "secret" or not val else val[:6] + "******"
        table.add_row(label, display)
    console.print(table)

    if not Confirm.ask("✏️  是否修改配置?", default=False):
        return

    # ── 先获取提供商，确定显示哪些字段 ──
    provider_choices = [c for c in (EDITABLE_FIELDS[0][5] if len(EDITABLE_FIELDS[0]) > 5 else [])]
    provider = Prompt.ask(
        "  选择 LLM 提供商",
        choices=provider_choices,
        default=current.get("LLM_PROVIDER") or os.environ.get("LLM_PROVIDER", "agnes"),
    )
    updates = {}
    if provider != (current.get("LLM_PROVIDER") or os.environ.get("LLM_PROVIDER", "")):
        updates["LLM_PROVIDER"] = provider

    # ── 依次询问可见字段 ──
    for key, label, _type, default, show_when, *extra in EDITABLE_FIELDS:
        if key == "LLM_PROVIDER":
            continue  # 已问过
        # 动态显隐：只显示匹配当前 provider 或永远显示的字段
        if show_when != "*" and show_when != provider:
            continue

        cur = current.get(key) or os.environ.get(key, default)

        if _type == "select":
            choices = extra[0] if extra else []
            val = Prompt.ask(f"  {label}", choices=choices, default=cur)
        elif _type == "secret":
            hint = " (回车保留当前值)" if cur else ""
            masked = cur[:4] + "****" if cur else ""
            Prompt.ask(f"  {label} [{masked}]", password=True, default="")
            # password=True 不显示默认值，单独处理
            entered = Prompt.ask(f"  {label} (输入新值，留空保留)", default="")
            val = entered if entered else cur
        elif _type == "number":
            val = Prompt.ask(f"  {label}", default=str(cur) if cur else default)
        else:
            val = Prompt.ask(f"  {label}", default=cur if cur else default)

        if val and val != cur:
            updates[key] = val

    # ── 保存 ──
    if not updates:
        console.print("[yellow]没有需要保存的修改[/yellow]")
        return

    save(updates)
    console.print(f"[green]✅ 已保存 {len(updates)} 项配置[/green]")

    # ── 连通测试 ──
    if Confirm.ask("🔄  是否测试 LLM 连接？", default=True):
        console.print("[dim]正在测试，请稍候...[/dim]")
        try:
            from biopaperminer.analyzer import OllamaAnalyzer
            analyzer = OllamaAnalyzer()
            ok = analyzer.check_connection()
            if ok:
                console.print("[green]✅ LLM 服务连接成功！配置可用[/green]")
            else:
                console.print("[red]❌ LLM 服务连接失败，请检查 API Key 和网络[/red]")
        except Exception as e:
            console.print(f"[yellow]⚠️  连接测试异常: {e}[/yellow]")


# ── TUI 主循环 ────────────────────────────────────────

def main():
    """TUI 主入口"""
    console.clear()

    while True:
        show_header()
        show_main_menu()

        choice = Prompt.ask(
            "请选择操作",
            choices=["0", "1", "2", "3", "4", "5"],
            default="0",
        )

        if choice == "0":
            console.print("\n[bold green]👋 再见！[/bold green]")
            break
        elif choice == "1":
            search_pubmed()
        elif choice == "2":
            download_pdfs()
        elif choice == "3":
            run_pipeline()
        elif choice == "4":
            view_reports()
        elif choice == "5":
            show_config()
        elif choice == "6":
            extract_refs()

        console.print("\n[dim]按 Enter 继续...[/dim]")
        input()
        console.clear()


if __name__ == "__main__":
    main()
