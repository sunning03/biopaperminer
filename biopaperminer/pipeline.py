#!/usr/bin/env python3
"""
pipeline.py — PDF → 分析报告 全流程（支持断点续传，优化版）

优化点：
- 减少 pipeline_state.json 的磁盘 I/O（批量写入而非逐篇写入）
- 简化新旧结果合并逻辑，避免重复的 dict↔PaperAnalysis 转换
- 统一报告生成路径，避免 config 全局变量污染
"""

import argparse
import json
import os
import sys
import time
import threading
from pathlib import Path
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

from biopaperminer.mineru_client import MinerUClient
from biopaperminer.analyzer import PaperAnalysis, ReportGenerator
from biopaperminer.prompts import build_analysis_prompt


STATE_FILE = "pipeline_state.json"
_STATE_CACHE: Dict[str, Any] = {}  # 全局状态缓存，避免反复读写磁盘


# ── 状态管理（优化：减少磁盘 I/O）───────────────────────

def _state_path(output_dir: Path) -> Path:
    return output_dir / STATE_FILE


def load_state(output_dir: Path) -> dict:
    """加载 pipeline 状态文件，带简单缓存"""
    sp = _state_path(output_dir)
    if sp.exists() and sp in _STATE_CACHE:
        return _STATE_CACHE[sp]
    if sp.exists():
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
            _STATE_CACHE[sp] = data
            return data
        except Exception:
            pass
    data = {"files": {}}
    _STATE_CACHE[sp] = data
    return data


def save_state(output_dir: Path, state: dict):
    """保存 pipeline 状态文件"""
    sp = _state_path(output_dir)
    state_path = output_dir / STATE_FILE
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _STATE_CACHE[state_path] = state


def get_file_state(state: dict, stem: str) -> dict:
    """获取单个文件的状态"""
    return state["files"].get(stem, {"mineru": "pending", "llm": "pending"})


def set_file_state(state: dict, stem: str, key: str, value: str, score: int = 0):
    """更新单个文件的状态字段"""
    if stem not in state["files"]:
        state["files"][stem] = {"mineru": "pending", "llm": "pending"}
    state["files"][stem][key] = value
    if score:
        state["files"][stem]["importance_score"] = score


# ── Step 1: MinerU ────────────────────────────────────

def _collect_pdf_files(pdf_dir=None, pdf_files_list=None) -> list:
    """收集 PDF 文件列表：支持目录、单文件、多文件"""
    seen = set()
    pdf_files = []

    if pdf_dir:
        pdf_path = Path(pdf_dir)
        if pdf_path.is_dir():
            for pattern in ("*.pdf", "**/*.pdf"):
                for p in sorted(pdf_path.glob(pattern)):
                    if p.resolve() not in seen:
                        seen.add(p.resolve())
                        pdf_files.append(p)
        else:
            print(f"  ⚠️  目录不存在: {pdf_dir}")

    if pdf_files_list:
        for f in pdf_files_list:
            p = Path(f)
            if p.is_file() and p.suffix.lower() == ".pdf":
                if p.resolve() not in seen:
                    seen.add(p.resolve())
                    pdf_files.append(p)
            else:
                print(f"  ⚠️  跳过（非 PDF 或不存在）: {f}")

    return pdf_files


def step_mineru(pdf_files: list, output_dir: Path, token: str,
                state: dict) -> list:
    """
    MinerU 解析：跳过已成功的，可选的只重试失败的。
    pdf_files: 已收集好的 PDF 路径列表（来自 _collect_pdf_files）
    返回 [(md_path, pdf_stem), ...]
    """
    print(f"\n{'='*60}")
    print("Step 1: MinerU 文档解析")
    print(f"{'='*60}")

    client = MinerUClient(api_token=token)

    if not pdf_files:
        print("  ⚠️  未找到 PDF 文件")
        return []

    results: List[tuple] = []
    total = len(pdf_files)
    skipped = 0

    for i, pdf_path in enumerate(pdf_files):
        stem = pdf_path.stem
        fs = get_file_state(state, stem)
        md_out = output_dir / f"{stem}_mineru"
        md_path = md_out / "full.md"

        # ── 跳过已成功的 ──
        if fs.get("mineru") == "done" and md_path.exists():
            print(f"\n  [{i+1}/{total}] {stem} — ✅ 已有缓存，跳过")
            results.append((md_path, stem))
            skipped += 1
            continue

        print(f"\n  [{i+1}/{total}] {stem}")

        # ── 执行 MinerU ──
        md_text = client.pdf_to_md(pdf_path, output_dir=md_out)

        if md_text:
            set_file_state(state, stem, "mineru", "done")
            print(f"    ✅ → {md_path} ({len(md_text)} 字符)")
            results.append((md_path, stem))
        else:
            # 尝试 PyMuPDF fallback
            try:
                from biopaperminer.analyzer import PDFExtractor
                text, github_links, _ = PDFExtractor.extract(pdf_path)
                md_out.mkdir(parents=True, exist_ok=True)
                md_path.write_text(text, encoding="utf-8")
                set_file_state(state, stem, "mineru", "done")
                print(f"    ⚠️  PyMuPDF fallback → {md_path} ({len(text)} 字符)")
                results.append((md_path, stem))
            except Exception as e:
                set_file_state(state, stem, "mineru", "failed")
                print(f"    ❌ 解析失败: {e}")

        # 每 5 篇保存一次状态，减少 I/O
        if (i + 1) % 5 == 0:
            save_state(output_dir, state)

    # 最终保存
    save_state(output_dir, state)

    print(f"\n  ✅ MinerU 完成: 成功 {len(results)}, 跳过 {skipped}, 总文件 {total}")
    return results


# ── Step 2: LLM 分析 ──────────────────────────────────

def _analyze_single_file(md_path: Path, pdf_stem: str, idx: int, total: int,
                         state: dict, output_dir: Path, state_lock: threading.Lock,
                         retry_failed: bool = False) -> Optional[PaperAnalysis]:
    """分析单个文件（供线程池调用）"""
    from biopaperminer.config import MAX_RETRIES, RETRY_DELAY, MAX_TEXT_LENGTH

    fs = get_file_state(state, pdf_stem)

    # 跳过已成功的
    if fs.get("llm") == "done" and not retry_failed:
        print(f"  [{idx}/{total}] {pdf_stem} — ✅ 已有缓存，跳过")
        return None
    if retry_failed and fs.get("llm") == "done":
        print(f"  [{idx}/{total}] {pdf_stem} — ✅ 已成功，跳过")
        return None

    print(f"  [{idx}/{total}] {pdf_stem} — 分析中...")

    # 读取 Markdown 文本
    try:
        md_text = md_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"    ❌ [{pdf_stem}] 读取 MD 失败: {e}")
        with state_lock:
            set_file_state(state, pdf_stem, "llm", "failed")
            _periodic_save(output_dir, state, state_lock)
        return None

    if len(md_text) > MAX_TEXT_LENGTH:
        md_text = md_text[:MAX_TEXT_LENGTH] + "\n...[文本已截断]..."

    # 调用 LLM（每次线程创建独立 client，避免共享状态问题）
    from biopaperminer.llm_client import get_llm_client
    client = get_llm_client()

    for attempt in range(MAX_RETRIES):
        try:
            prompt = build_analysis_prompt(md_text)
            response_text = client.chat(prompt)

            if response_text:
                parsed = _safe_parse_json(response_text)
                if parsed:
                    pa = _dict_to_paper(parsed, md_path, pdf_stem, md_text)
                    if pa:
                        with state_lock:
                            set_file_state(state, pdf_stem, "llm", "done",
                                          pa.importance_score)
                            _periodic_save(output_dir, state, state_lock)
                        print(f"    ✅ [{pdf_stem}] 分析成功 — 评分: {pa.importance_score}")
                        return pa
            else:
                print(f"    ⚠️  [{pdf_stem}] 返回空结果，重试 {attempt + 1}/{MAX_RETRIES}")
        except Exception as e:
            print(f"    ⚠️  [{pdf_stem}] 请求错误: {e}，重试 {attempt + 1}/{MAX_RETRIES}")

        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAY * (2 ** attempt)
            time.sleep(delay)

    print(f"    ❌ [{pdf_stem}] 分析失败（{MAX_RETRIES} 次重试后）")
    with state_lock:
        set_file_state(state, pdf_stem, "llm", "failed")
        _periodic_save(output_dir, state, state_lock)
    return None


# 周期性保存计数器（线程安全）
_save_counter = 0


def _periodic_save(output_dir: Path, state: dict, lock: threading.Lock):
    """每 5 次成功/失败触发一次保存"""
    global _save_counter
    _save_counter += 1
    if _save_counter % 5 == 0:
        save_state(output_dir, state)


def step_llm(md_files: list, output_dir: Path, state: dict,
             retry_failed: bool = False) -> list:
    """
    LLM 分析：并发处理，跳过已成功的，可选的只重试失败的。
    返回 PaperAnalysis 对象列表
    """
    print(f"\n{'='*60}")
    print("Step 2: LLM 结构化分析（并发模式）")
    print(f"{'='*60}")

    from biopaperminer.config import MAX_WORKERS

    global _save_counter
    _save_counter = 0
    state_lock = threading.Lock()
    results: List[PaperAnalysis] = []
    total = len(md_files)

    # 使用线程池并发分析
    workers = min(MAX_WORKERS, total) if total > 0 else 1
    print(f"  并发数: {workers}")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for i, (md_path, pdf_stem) in enumerate(md_files, 1):
            future = executor.submit(
                _analyze_single_file,
                md_path, pdf_stem, i, total,
                state, output_dir, state_lock,
                retry_failed,
            )
            futures[future] = pdf_stem

        for future in as_completed(futures):
            pdf_stem = futures[future]
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception as e:
                print(f"    ❌ [{pdf_stem}] 线程异常: {e}")

    # 最终保存
    save_state(output_dir, state)

    skipped = total - len(results)
    print(f"\n  ✅ LLM 分析完成: 成功 {len(results)}, 跳过/失败 {skipped}, 总文件 {total}")
    return results


def _safe_parse_json(response: str) -> Optional[dict]:
    """安全地解析 LLM 返回的 JSON"""
    import re
    # 尝试提取 ```json ... ``` 块
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
    if match:
        response = match.group(1)
    
    # 尝试直接解析
    import json
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # 尝试找到第一个 { 和最后一个 }
    start = response.find('{')
    end = response.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(response[start:end+1])
        except json.JSONDecodeError:
            pass
    
    return None


def _dict_to_paper(data: dict, md_path: Path, pdf_stem: str,
                   md_text: str = "") -> Optional[PaperAnalysis]:
    """将 dict 转换为 PaperAnalysis 对象（接收已读取的 md_text 避免重复磁盘 IO）"""
    import hashlib
    from datetime import datetime
    
    # 计算 file_hash（基于 md 文本内容，避免重新读盘）
    file_hash = hashlib.md5(md_text.encode() if md_text else pdf_stem.encode()).hexdigest()[:12]
    
    try:
        return PaperAnalysis(
            file_name=pdf_stem + ".pdf",
            file_path=str(md_path.parent.parent),
            file_hash=file_hash,
            analysis_time=datetime.now().isoformat(),
            title=data.get("title", ""),
            title_cn=data.get("title_cn", ""),
            authors=data.get("authors", []),
            publication_year=data.get("publication_year", ""),
            journal_conference=data.get("journal_conference", ""),
            doi=data.get("doi", ""),
            abstract=data.get("abstract", ""),
            abstract_cn=data.get("abstract_cn", ""),
            paper_link=data.get("paper_link", ""),
            research_objective=data.get("research_objective", ""),
            methodology=data.get("methodology", ""),
            key_findings=data.get("key_findings", []),
            innovations=data.get("innovations", []),
            limitations=data.get("limitations", []),
            future_work=data.get("future_work", ""),
            primary_category=data.get("primary_category", "其他"),
            secondary_categories=data.get("secondary_categories", []),
            content_type=data.get("content_type", ""),
            research_stage=data.get("research_stage", ""),
            keywords=data.get("keywords", []),
            keywords_cn=data.get("keywords_cn", []),
            diseases=data.get("diseases", []),
            technologies=data.get("technologies", []),
            datasets=data.get("datasets", []),
            metrics=data.get("metrics", {}),
            github_links=data.get("github_links", []),
            other_links=data.get("other_links", []),
            importance_score=max(1, min(10, int(data.get("importance_score", 5)))),
            importance_reason=data.get("importance_reason", ""),
            clinical_impact=data.get("clinical_impact", ""),
            potential_applications=data.get("potential_applications", []),
            status="success",
            error_message="",
            raw_text_length=len(md_text) if md_text else 0,
        )
    except Exception as e:
        print(f"    ⚠️  构建 PaperAnalysis 失败: {e}")
        return None


# ── Step 3: 报告生成 ──────────────────────────────────

def step_report(paper_results: List[PaperAnalysis], output_dir: Path) -> None:
    """生成所有报告"""
    print(f"\n{'='*60}")
    print("Step 3: 报告生成")
    print(f"{'='*60}")

    import biopaperminer.config as config
    config.OUTPUT_FOLDER = output_dir
    config.JSON_OUTPUT = output_dir / "analysis_results.json"
    config.CSV_OUTPUT = output_dir / "analysis_results.csv"
    config.MARKDOWN_OUTPUT = output_dir / "summary_report.md"
    config.HTML_OUTPUT = output_dir / "interactive_report.html"

    generator = ReportGenerator(paper_results)
    generator.generate_all()


# ── 主函数 ────────────────────────────────────────────

def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="BioPaperMiner — 生物文献挖掘全流程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  biopaperminer pipeline --pdf-dir ./pdfs/ --out ./results/
  biopaperminer pipeline --md-dir ./md_files/ --out ./results/ --skip-mineru
  biopaperminer pipeline --pdf-dir ./pdfs/ --out ./results/ --retry-failed
  biopaperminer pipeline --pdf-dir ./pdfs/ --out ./results/ --force
        """,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # pipeline 子命令
    p_pipeline = subparsers.add_parser("pipeline", help="全流程：PDF → MinerU → LLM → 报告")
    p_pipeline.add_argument("--pdf-dir", type=str, help="PDF 文件目录")
    p_pipeline.add_argument("--pdf-files", type=str, nargs="+", default=None,
                            help="单个/多个 PDF 文件路径（与 --pdf-dir 二选一）")
    p_pipeline.add_argument("--md-dir", type=str, help="已有 Markdown 文件目录（跳过 MinerU）")
    p_pipeline.add_argument("--out", "-o", type=str, default="./pdf_analysis_results", help="输出目录")
    p_pipeline.add_argument("--skip-mineru", action="store_true", help="跳过 MinerU 解析")
    p_pipeline.add_argument("--skip-llm", action="store_true", help="跳过 LLM 分析（只跑 MinerU）")
    p_pipeline.add_argument("--retry-failed", action="store_true", help="只重试之前失败的文件")
    p_pipeline.add_argument("--force", action="store_true", help="强制重新全部处理")
    p_pipeline.add_argument("--token", type=str, default=None, help="MinerU API Token")
    p_pipeline.add_argument("--token-file", type=str, default=None, help="从文件读取 Token")
    
    # search 子命令
    p_search = subparsers.add_parser("search", help="PubMed 文献检索")
    p_search.add_argument("query", nargs="+", help="搜索关键词")
    p_search.add_argument("-n", type=int, default=20, help="最大结果数")
    p_search.add_argument("--mindate", type=str, help="起始日期 YYYY/MM/DD")
    p_search.add_argument("--maxdate", type=str, help="截止日期 YYYY/MM/DD")
    p_search.add_argument("--output", type=str, help="输出文件路径")
    p_search.add_argument("--api-key", type=str, help="NCBI API Key")
    p_search.add_argument("--email", type=str, help="邮箱地址")
    p_search.add_argument("--proxy", type=str, default=None,
                          help="HTTP/HTTPS 代理地址，如 http://127.0.0.1:7897")
    
    # download 子命令
    p_download = subparsers.add_parser("download", help="PDF 批量下载")
    p_download.add_argument("input_file", help="输入 CSV/JSON 文件")
    p_download.add_argument("--output", "-o", type=str, default="./pdf_download_results", help="输出目录")
    
    # refs 子命令
    p_refs = subparsers.add_parser("refs", help="从 PMC HTML 或 RIS 提取参考文献")
    p_refs.add_argument("input_file", help="输入文件路径（.html 或 .ris）")
    p_refs.add_argument("-f", "--format", type=str, default="auto",
                        choices=["auto", "html", "ris"],
                        help="输入格式（auto: 根据扩展名识别）")
    p_refs.add_argument("-o", "--output", type=str, default="./references_output",
                        help="输出目录（默认 ./references_output）")
    
    # rename 子命令
    p_rename = subparsers.add_parser("rename", help="PDF 智能重命名")
    p_rename.add_argument("input", nargs="+", help="PDF 文件或目录路径")
    p_rename.add_argument("-o", "--output", type=str, help="输出目录")
    p_rename.add_argument("--dry-run", action="store_true", help="仅预览，不重命名")
    p_rename.add_argument("--analysis-json", type=str,
                          help="analysis_results.json 路径（可选，加速提取）")
    
    args = parser.parse_args()
    
    # 如果没有子命令，显示帮助
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "pipeline":
        _run_pipeline(args)
    elif args.command == "search":
        _run_search(args)
    elif args.command == "download":
        _run_download(args)
    elif args.command == "refs":
        _run_refs(args)
    elif args.command == "rename":
        _run_rename(args)


def _run_pipeline(args):
    """执行 pipeline 全流程"""
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Token
    token = args.token or os.environ.get("MINERU_API_TOKEN", "")
    if args.token_file:
        token = Path(args.token_file).read_text().strip()
    if not token:
        try:
            from biopaperminer.config import MINERU_API_TOKEN
            token = MINERU_API_TOKEN or ""
        except Exception:
            pass

    # 状态
    if args.force:
        state = {"files": {}}
        _STATE_CACHE.clear()
    else:
        state = load_state(output_dir)

    md_files = []

    # Step 1: MinerU（支持目录 / 单文件 / 多文件）
    if not args.skip_mineru and (args.pdf_dir or args.pdf_files):
        if not token:
            print("❌ 需要 MinerU Token（--token / MINERU_API_TOKEN）")
            sys.exit(1)
        pdf_list = _collect_pdf_files(pdf_dir=args.pdf_dir, pdf_files_list=args.pdf_files)
        if not pdf_list:
            print("❌ 未找到任何 PDF 文件")
            sys.exit(1)
        md_files = step_mineru(pdf_list, output_dir, token, state)

    # 从 --md-dir 加载已有 MD
    if args.md_dir:
        md_dir = Path(args.md_dir)
        if md_dir.is_dir():
            for md_path in sorted(md_dir.rglob("full.md")):
                md_files.append((md_path, md_path.parent.stem.replace("_mineru", "")))
            if not md_files:
                for md_path in sorted(md_dir.glob("*.md")):
                    md_files.append((md_path, md_path.stem))

    if not md_files:
        print("⚠️  没有需要处理的文件")
        return

    # Step 2: LLM
    paper_results: List[PaperAnalysis] = []
    if not args.skip_llm:
        paper_results = step_llm(md_files, output_dir, state,
                                 retry_failed=args.retry_failed)

    if not paper_results:
        print("⚠️  本次没有新增分析结果")
        existing_json = output_dir / "analysis_results.json"
        if existing_json.exists():
            print("  但检测到已有结果文件，使用已有数据重新生成报告")
        else:
            print("  且无历史结果，跳过报告生成")
            return

    # Step 3: 合并结果 + 报告
    _merge_and_report(paper_results, output_dir, state)


def _merge_and_report(new_results: List[PaperAnalysis], output_dir: Path,
                      state: dict) -> None:
    """合并新旧结果并生成报告"""
    print(f"\n{'='*60}")
    print("Step 3: 合并结果 + 报告生成")
    print(f"{'='*60}")

    # 加载已有的结果
    existing_json = output_dir / "analysis_results.json"
    old_by_hash: dict = {}
    
    if existing_json.exists():
        try:
            old_data = json.loads(existing_json.read_text(encoding="utf-8"))
            for item in old_data:
                fh = item.get("file_hash", "")
                if fh:
                    old_by_hash[fh] = item
            print(f"  加载已有结果: {len(old_by_hash)} 篇")
        except Exception:
            pass

    # 新结果转为 hash -> record 映射
    new_by_hash = {r.file_hash: asdict(r) for r in new_results}

    # 如果新结果覆盖了旧结果，打印提示
    overlap = set(old_by_hash.keys()) & set(new_by_hash.keys())
    if overlap:
        print(f"  ⚠️  发现 {len(overlap)} 篇重复文献，将用新结果覆盖")

    # 合并：旧结果 + 新结果（新结果覆盖同 hash 的旧记录）
    merged = {**old_by_hash, **new_by_hash}
    all_results = list(merged.values())
    print(f"  合并后共 {len(all_results)} 篇（新增 {len(new_results)} 篇）")

    # 写回 JSON
    with open(existing_json, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 已追加写入: {existing_json}")

    # 用合并后的全部结果生成报告
    step_report(all_results, output_dir)


def _run_search(args):
    """执行 PubMed 搜索"""
    from biopaperminer.download_pubmed import main as search_main
    # Merge query parts into a single string
    query_str = ' '.join(args.query)
    sys.argv = ["download_doi_from_pubmed_cli", "search", query_str]
    if args.n:
        sys.argv += ["-n", str(args.n)]
    if args.mindate:
        sys.argv += ["--mindate", args.mindate]
    if args.maxdate:
        sys.argv += ["--maxdate", args.maxdate]
    if args.output:
        sys.argv += ["--output", args.output]
    if args.api_key:
        sys.argv += ["--api-key", args.api_key]
    if args.email:
        sys.argv += ["--email", args.email]
    if hasattr(args, 'proxy') and args.proxy:
        sys.argv += ["--proxy", args.proxy]
    search_main()


def _run_download(args):
    """执行 PDF 下载"""
    from biopaperminer.download_pdf import main as download_main
    sys.argv = ["download_pdf_from_csv_cli", "-i", args.input_file]
    if args.output:
        sys.argv += ["-o", args.output]
    download_main()


def _run_refs(args):
    """执行参考文献提取"""
    from biopaperminer.extract_refs import main as refs_main
    sys.argv = ["extract_refs", args.input_file, "-o", args.output]
    if args.format and args.format != "auto":
        sys.argv += ["--format", args.format]
    refs_main()


def _run_rename(args):
    """执行 PDF 智能重命名"""
    from biopaperminer.rename_pdfs import main as rename_main
    sys.argv = ["rename_pdfs"] + args.input
    if args.output:
        sys.argv += ["-o", args.output]
    if args.dry_run:
        sys.argv += ["--dry-run"]
    if args.analysis_json:
        sys.argv += ["--analysis-json", args.analysis_json]
    rename_main()


if __name__ == "__main__":
    main()
