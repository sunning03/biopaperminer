#!/usr/bin/env python3
"""
BioPaperMiner — 生物文献挖掘系统

三种使用方式:
  1. CLI:   biopaperminer pipeline --pdf-dir ./pdfs/ --out ./results/
  2. TUI:   biopaperminer tui          (交互式终端界面)
  3. GUI:   biopaperminer gui          (图形界面，需要 tkinter/PyQt)

Tab 补全支持：
  bash:  source main_completion.bash
  zsh:   source main_completion.zsh
  fish:  fish main_completion.fish
"""

import sys
import os
from pathlib import Path

# 确保可以找到项目模块
_BASE = Path(__file__).resolve().parent  # biopaperminer/
_ROOT = _BASE.parent                      # 项目根目录
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ── Tab 补全脚本生成 ──────────────────────────────────

def _get_shell():
    """检测当前 shell"""
    shell_name = os.environ.get("SHELL", "")
    if "bash" in shell_name:
        return "bash"
    elif "zsh" in shell_name:
        return "zsh"
    elif "fish" in shell_name:
        return "fish"
    return None


def _install_completions():
    """自动安装 tab 补全到 shell 配置文件"""
    shell = _get_shell()
    if not shell:
        print("⚠️  无法检测 shell，请手动安装补全脚本")
        return

    comp_file = _ROOT / "completions" / f"main_completion.{shell}"

    if not comp_file.exists():
        print(f"⚠️  未找到 {shell} 补全脚本: {comp_file}")
        return

    comp_content = comp_file.read_text(encoding="utf-8")

    rc_file = None
    marker_start = "# >>> biopaperminer completions >>>"
    marker_end = "# <<< biopaperminer completions <<<"
    block = f"\n{marker_start}\n{comp_content}{marker_end}\n"

    if shell == "bash":
        rc_file = Path.home() / ".bashrc"
    elif shell == "zsh":
        rc_file = Path.home() / ".zshrc"
    elif shell == "fish":
        fish_config = Path.home() / ".config" / "fish"
        fish_config.mkdir(parents=True, exist_ok=True)
        rc_file = fish_config / "config.fish"

    if rc_file and rc_file.exists():
        rc_content = rc_file.read_text(encoding="utf-8")
        if marker_start not in rc_content:
            with open(rc_file, "a", encoding="utf-8") as f:
                f.write(block)
            print(f"\n✅ Tab 补全已安装到 {rc_file}")
            print(f"   运行 source {rc_file} 或重启终端生效\n")
        else:
            print(f"\nℹ️  补全已存在于 {rc_file}，无需重复安装\n")
    elif rc_file:
        rc_file.parent.mkdir(parents=True, exist_ok=True)
        with open(rc_file, "w", encoding="utf-8") as f:
            f.write(block)
        print(f"\n✅ Tab 补全已创建 {rc_file}")
        print(f"   运行 source {rc_file} 或重启终端生效\n")


# ── 子命令实现 ────────────────────────────────────────

def cmd_pipeline():
    """运行 pipeline"""
    from biopaperminer.pipeline import main
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    main()


def cmd_search():
    """PubMed 检索"""
    from biopaperminer.download_pubmed import main
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    main()


def cmd_download():
    """PDF 下载"""
    from biopaperminer.download_pdf import main
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    main()


def cmd_tui():
    """启动 TUI 交互式界面"""
    from biopaperminer.tui import main
    main()


def cmd_gui():
    """启动 GUI 图形界面"""
    from biopaperminer.gui import main
    main()


def cmd_refs():
    """提取参考文献"""
    from biopaperminer.extract_refs import main
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    main()


def show_help():
    print("BioPaperMiner — 生物文献挖掘系统")
    print()
    print("用法:")
    print("  biopaperminer <命令> [参数...]")
    print()
    print("命令:")
    print("  pipeline    全流程：PDF → MinerU → LLM → 报告")
    print("  search      PubMed 文献检索")
    print("  download    PDF 批量下载")
    print("  tui         交互式终端界面（图形化操作）")
    print("  gui         图形界面（需要 tkinter 或 PyQt6）")
    print("  refs        从 PMC HTML 提取参考文献")
    print()
    print("示例:")
    print("  biopaperminer pipeline --pdf-dir ./pdfs/ --out ./results/")
    print("  biopaperminer pipeline --retry-failed")
    print("  biopaperminer search \"CRISPR\" -n 20")
    print("  biopaperminer download papers.csv")
    print("  biopaperminer tui")
    print("  biopaperminer gui")
    print()
    print("Tab 补全:")
    print("  biopaperminer --install-completions   自动安装到 ~/.bashrc 或 ~/.zshrc")
    print("  或手动: source main_completion.bash / main_completion.zsh")


def main():
    """统一入口"""
    # 自动安装 tab 补全
    if len(sys.argv) > 1 and sys.argv[1] == "--install-completions":
        _install_completions()
        return

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        show_help()
        return

    cmd = sys.argv[1]
    dispatch = {
        "pipeline": cmd_pipeline,
        "search": cmd_search,
        "download": cmd_download,
        "tui": cmd_tui,
        "gui": cmd_gui,
        "refs": cmd_refs,
    }

    if cmd in dispatch:
        dispatch[cmd]()
    else:
        print(f"未知命令: {cmd}")
        print("可用命令: pipeline, search, download, refs, tui, gui")


if __name__ == "__main__":
    main()
