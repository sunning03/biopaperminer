#!/usr/bin/env python3
"""
rename_pdfs.py — PDF 文件智能重命名

格式: [第一作者]_[年份]_[来源简称]_[英文关键词1]-[英文关键词2]_[中文关键词1]-[中文关键词2].pdf

用法:
    biopaperminer rename ./pdfs/
    biopaperminer rename paper.pdf -o ./renamed/
"""

import re
import os
import sys
import json
from pathlib import Path
from typing import Optional


# ── 期刊缩写加载 ──

_JOURNAL_ABBR_CACHE = None

def _load_journal_abbr():
    """加载 journal_abbr_list.txt，返回 {小写标准化名: 缩写} 的字典"""
    global _JOURNAL_ABBR_CACHE
    if _JOURNAL_ABBR_CACHE is not None:
        return _JOURNAL_ABBR_CACHE

    abbr_path = Path(__file__).parent / "journal_abbr_list.txt"
    _JOURNAL_ABBR_CACHE = {}

    if not abbr_path.exists():
        return _JOURNAL_ABBR_CACHE

    for line in abbr_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            full = parts[0].strip()
            abbr = parts[2].strip()
            if full and abbr:
                # 存多个 key 提高匹配率
                key = _normalize(full)
                _JOURNAL_ABBR_CACHE[key] = abbr
                # 也存缩写本身（方便精确匹配）
                key_abbr = _normalize(abbr)
                _JOURNAL_ABBR_CACHE[key_abbr] = abbr

    return _JOURNAL_ABBR_CACHE


def _normalize(text: str) -> str:
    """标准化：小写、去标点、合并空格"""
    text = re.sub(r'[&,/.:;()\[\]!?\'\"-]', ' ', text)
    text = re.sub(r'\s+', ' ', text.strip().lower())
    return text


def lookup_journal_abbr(journal_name: str) -> str:
    """查找期刊缩写，找不到返回原名称"""
    if not journal_name:
        return journal_name

    abbr_dict = _load_journal_abbr()
    if not abbr_dict:
        return journal_name

    # 如果已经是缩写格式（全大写+点或全大写无空格），直接返回
    if re.match(r'^[A-Z][A-Za-z0-9.&\s]+$', journal_name.strip()) and len(journal_name) < 30:
        return journal_name

    query = _normalize(journal_name)

    # 精确匹配
    if query in abbr_dict:
        return abbr_dict[query]

    # 模糊匹配：查询词是某个 key 的子串或反向
    matches = []
    for key, abbr in abbr_dict.items():
        # 查询包含 key 或 key 包含查询
        if query in key or key in query:
            matches.append((len(key), abbr))
        # 分词匹配（大部分词重叠）
        else:
            q_words = set(query.split())
            k_words = set(key.split())
            common = q_words & k_words
            if len(common) >= min(len(q_words), len(k_words)) * 0.6 and len(common) >= 2:
                matches.append((len(key), abbr))

    if matches:
        # 选最长的匹配（最精确）
        matches.sort(key=lambda x: -x[0])
        return matches[0][1]

    return journal_name


def sanitize(text: str, max_len: int = 40) -> str:
    """清理文本：去特殊字符，空格→下划线，限长"""
    text = re.sub(r'[&/:?*"<>|]', '', text)
    text = re.sub(r'\s+', '_', text.strip())
    text = text.strip('_')[:max_len].rstrip('_')
    return text if text else "Unknown"


def build_filename(first_author: str, year: str, source: str,
                   en_kw: list, cn_kw: list) -> str:
    """按规范格式构建文件名"""
    fa = sanitize(first_author.split()[-1] if first_author else "Unknown", 20)
    yr = year[:4] if year and year[:4].isdigit() else "0000"
    # 使用期刊缩写
    src = sanitize(lookup_journal_abbr(source), 20) if source else "Unknown"

    en_part = "-".join(sanitize(k, 20) for k in en_kw[:2] if k)
    cn_part = "-".join(sanitize(k, 10) for k in cn_kw[:2] if k)

    parts = [fa, yr, src]
    if en_part:
        parts.append(en_part)
    if cn_part:
        parts.append(cn_part)

    return "_".join(parts) + ".pdf"


def extract_metadata_from_text(text: str) -> dict:
    """从 PDF 文本中启发式提取第一作者、年份、来源"""
    first_author = ""
    year = ""
    source = ""

    lines = text.split('\n')
    for i, line in enumerate(lines[:50]):
        line = line.strip()
        if not year:
            m = re.search(r'\b((?:19|20)\d{2})\b', line)
            if m:
                year = m.group(1)
        if not first_author and i < 5:
            m = re.search(r'^([A-Z][a-zéèêëàâùûüôöîïç]+)', line)
            if m:
                first_author = m.group(1)

    return {"first_author": first_author, "year": year, "source": source}


def load_analysis_cache(analysis_json: str = None) -> dict:
    """加载已有的分析结果缓存（按 file_hash 索引）"""
    if analysis_json and Path(analysis_json).exists():
        try:
            data = json.loads(Path(analysis_json).read_text(encoding="utf-8"))
            return {item.get("file_hash", ""): item for item in data if item.get("file_hash")}
        except Exception:
            pass
    return {}


def get_llm_metadata(pdf_path: Path, text: str) -> dict:
    """调用 LLM 提取元数据"""
    from biopaperminer.llm_client import get_llm_client

    prompt = f"""从以下论文文本中提取 5 个信息，以 JSON 格式返回：
{{
  "first_author": "第一作者姓氏",
  "year": "发表年份(4位数字)",
  "source": "期刊/会议全称（如 Nature、Science、PNAS、Proceedings of the National Academy of Sciences）",
  "title_keywords_en": ["英文关键词1", "英文关键词2"],
  "title_keywords_cn": ["中文关键词1", "中文关键词2"]
}}

要求：
- title_keywords_en 和 title_keywords_cn 中**必须包含论文研究的物种/生物名称**（如 Arabidopsis thaliana、水稻、人类、小鼠、大肠杆菌等）
- 关键词选 2-4 个最能体现论文核心内容的实词，物种名称排第一位

只输出 JSON，不要其他文字。

论文文本（前 3000 字符）：
{text[:3000]}
"""
    client = get_llm_client()
    resp = client.chat(prompt)
    if resp:
        import json as j
        try:
            m = re.search(r'\{.*\}', resp, re.DOTALL)
            if m:
                return j.loads(m.group())
        except Exception:
            pass
    return {}


def get_metadata(pdf_path: Path, text: str,
                 analysis_cache: dict = None) -> dict:
    """获取元数据：优先分析缓存 → LLM → 启发式"""
    if analysis_cache:
        import hashlib
        h = hashlib.md5(pdf_path.read_bytes()).hexdigest()[:12]
        if h in analysis_cache:
            item = analysis_cache[h]
            en_kw = item.get("keywords", [])
            cn_kw = item.get("keywords_cn", [])
            return {
                "first_author": (item.get("authors") or [""])[0] if item.get("authors") else "",
                "year": item.get("publication_year", ""),
                "source": item.get("journal_conference", ""),
                "title_keywords_en": en_kw[:2],
                "title_keywords_cn": cn_kw[:2],
            }

    meta = get_llm_metadata(pdf_path, text)
    if meta.get("year") or meta.get("first_author"):
        return meta

    return extract_metadata_from_text(text)


def rename_pdf(pdf_path: Path, output_dir: Path = None,
               dry_run: bool = False, analysis_cache: dict = None,
               copy_mode: bool = False) -> Optional[Path]:
    """重命名单个 PDF，返回新路径"""
    import shutil
    from biopaperminer.pdf_extractor import PDFExtractor

    text, _, _ = PDFExtractor.extract(pdf_path)
    if not text or len(text) < 50:
        print(f"  [WARN]  无法提取文本: {pdf_path.name}")
        return None

    meta = get_metadata(pdf_path, text, analysis_cache)
    new_name = build_filename(
        meta.get("first_author", ""),
        meta.get("year", ""),
        meta.get("source", ""),
        meta.get("title_keywords_en", []),
        meta.get("title_keywords_cn", []),
    )

    target = (output_dir or pdf_path.parent) / new_name

    if dry_run:
        print(f"   {pdf_path.name} → {new_name}")
        return target

    counter = 1
    orig = target
    while target.exists():
        stem = orig.stem + f"_{counter}"
        target = orig.with_stem(stem)
        counter += 1

    if copy_mode:
        shutil.copy2(pdf_path, target)
        print(f"  [DONE] {pdf_path.name} → {target.name}（已复制）")
    else:
        pdf_path.rename(target)
        print(f"  [DONE] {pdf_path.name} → {target.name}（已移动）")
    return target


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="PDF 智能重命名 — [作者]_[年份]_[来源]_[关键词]_[关键词中文].pdf"
    )
    parser.add_argument("input", nargs="+", help="PDF 文件或目录路径")
    parser.add_argument("-o", "--output", help="输出目录（默认同目录）")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不实际重命名")
    parser.add_argument("--copy", action="store_true", help="复制文件而不是移动")
    parser.add_argument("--analysis-json", help="analysis_results.json 路径（可选）")
    args = parser.parse_args()

    pdf_files = []
    for inp in args.input:
        p = Path(inp)
        if p.is_dir():
            pdf_files.extend(sorted(p.glob("*.pdf")))
        elif p.is_file() and p.suffix.lower() == ".pdf":
            pdf_files.append(p)

    if not pdf_files:
        print("[ERR] 未找到 PDF 文件")
        sys.exit(1)

    analysis_cache = load_analysis_cache(args.analysis_json)
    output_dir = Path(args.output) if args.output else None

    print(f" 共 {len(pdf_files)} 个 PDF 文件\n" if not args.dry_run else
          f" 预览 {len(pdf_files)} 个 PDF 文件（--dry-run）\n")

    renamed = 0
    for pdf in pdf_files:
        result = rename_pdf(pdf, output_dir, dry_run=args.dry_run,
                            analysis_cache=analysis_cache,
                            copy_mode=args.copy)
        if result:
            renamed += 1

    if not args.dry_run:
        print(f"\n[DONE] 已重命名 {renamed}/{len(pdf_files)} 个文件")
    else:
        print(f"\n📋 预览完成，共 {renamed} 个文件")


if __name__ == "__main__":
    main()
