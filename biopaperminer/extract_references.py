#!/usr/bin/env python3
"""
extract_references.py
从 PMC 格式的 HTML 文件中提取参考文献，输出为 CSV 文件。

CSV 列: pmid, title, abstract, authors, journal, pub_date, doi, keywords, mesh_terms, pub_types
关注 DOI 和 title 列，其他列留空。

用法:
    biopaperminer refs input.html
    biopaperminer refs input.html -o references.csv

依赖:
    pip install beautifulsoup4 lxml
"""

import argparse
import csv
import re
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    print("请先安装依赖: pip install beautifulsoup4 lxml", file=sys.stderr)
    sys.exit(1)


# ===============================================================
# 数据结构
# ===============================================================
class Reference:
    """单条参考文献，包含编号、正文、标题、DOI、PMID。"""
    def __init__(self, number: str, text: str,
                 doi: str = "", pmid: str = "", title: str = ""):
        self.number = number
        self.text = text
        self.doi = doi
        self.pmid = pmid
        self.title = title


# ===============================================================
# 从参考文献正文中启发式提取标题
# ===============================================================
def extract_title(text: str) -> str:
    """
    从参考文献正文中启发式提取论文标题。

    核心思路:
      参考文献通常遵循 "Authors. Title. Journal. Year;Vol:Pages." 格式。
      1. 先清除内联 DOI 文本，避免干扰分段。
      2. 定位年份（19xx/20xx 后跟 ; . , 空格 ) ] 等）。
      3. 取年份之前的文本，按 ". " 分段：
         - 第一段 = 作者列表
         - 最后一段 = 期刊名
         - 中间所有段 = 标题
      4. 如果找不到年份，回退到 "et al." 定位作者结尾。
      5. 如果分段数异常（>6 段说明格式非标准），返回空字符串。
    """
    cleaned = text

    # --- 步骤1: 清除内联 DOI ---
    cleaned = re.sub(r'\s*10\.\d{4,}/[^\s\]]+', '', cleaned)

    # --- 步骤2: 定位年份 ---
    # 匹配 19xx 或 20xx 后跟 ; . , 空格 ) ] 等
    year_match = re.search(
        r'(?<!\d)((?:19|20)\d{2})\s*[;,.\s)\]]',
        cleaned
    )

    if year_match:
        before_year = cleaned[:year_match.start()].rstrip(". ")
        parts = before_year.split(". ")

        if len(parts) >= 3 and len(parts) <= 6:
            # 标题 = 中间所有段（索引 1 到 -2）
            title = ". ".join(parts[1:-1])
            return title.strip()

        if len(parts) == 2:
            # 只有作者和标题（期刊可能与年份合并）
            return parts[1].strip()

    # --- 步骤3: 回退 — 使用 "et al." 定位作者结尾 ---
    et_al_match = re.search(
        r'et al\.\s+(.+?)(?:\.\s+[A-Z]|$)',
        cleaned, re.DOTALL
    )
    if et_al_match:
        title = et_al_match.group(1).strip()
        # 去除末尾多余的句点
        title = re.sub(r'\.$', '', title).strip()
        return title

    # --- 步骤4: 无法提取 ---
    return ""


# ===============================================================
# 从 <li> 元素解析单条参考文献
# ===============================================================
def parse_reference_li(li: Tag):
    """
    解析 PMC HTML 中单个 <li> 参考文献条目，
    提取编号、正文、DOI、PMID、标题。
    """
    doi_url = ""
    pmid = ""

    for a in li.find_all("a", href=True):
        href = a["href"].strip()

        # 提取 DOI
        if "doi.org" in href:
            doi_url = href
        # 提取 PubMed 链接中的 PMID
        if "pubmed.ncbi.nlm.nih.gov" in href:
            match = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', href)
            if match:
                pmid = match.group(1)

    # 提取正文：克隆 <li>，移除 <a> 标签后取纯文本
    li_copy = BeautifulSoup(str(li), "lxml").find("li")
    for a in li_copy.find_all("a"):
        a.decompose()

    raw_text = li_copy.get_text(separator=" ", strip=True)
    raw_text = re.sub(r'\s+', ' ', raw_text)

    # 去除残留的方括号标签文字
    raw_text = re.sub(
        r'\[\s*(?:DOI|PubMed|Google Scholar|PMC free article)\s*\]',
        '', raw_text, flags=re.IGNORECASE
    )
    raw_text = re.sub(r'\s+', ' ', raw_text).strip()

    # 提取编号
    num_match = re.match(r'^(\d+)[\.\)]?\s*(.*)', raw_text)
    if not num_match:
        return None

    number = num_match.group(1)
    text = num_match.group(2).strip()
    text = re.sub(r'\[\s*\]?\s*$', '', text).strip()

    if not text:
        return None

    # 提取标题
    title = extract_title(text)

    return Reference(
        number=number, text=text,
        doi=doi_url, pmid=pmid, title=title
    )


# ===============================================================
# 正则兜底：从全文提取参考文献（无法提取链接时）
# ===============================================================
def extract_by_regex(soup: BeautifulSoup) -> list[Reference]:
    """正则兜底策略，从纯文本中提取参考文献编号和正文。"""
    references = []
    full_text = soup.get_text(separator="\n")

    ref_start = re.search(r'References\s*\n', full_text, re.IGNORECASE)
    search_text = full_text[ref_start.end():] if ref_start else full_text

    pattern = re.compile(
        r'(\d+)\.\s*([^\n]{15,}?)(?=\n\s*\d+\.|\Z)',
        re.DOTALL
    )
    for m in pattern.finditer(search_text):
        number = m.group(1)
        text = re.sub(r'\s+', ' ', m.group(2)).strip()
        title = extract_title(text)
        references.append(Reference(
            number=number, text=text, title=title
        ))

    return references


# ===============================================================
# 主提取函数
# ===============================================================
def extract_references(html_path: str) -> list[Reference]:
    """从 HTML 文件中提取参考文献列表。"""
    html_content = Path(html_path).read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html_content, "lxml")

    references: list[Reference] = []

    # ---- 策略1: 定位 "References" 标题，提取其后的 <li> 列表项 ----
    ref_section = soup.find(id="references")
    if not ref_section:
        for header in soup.find_all(["h1", "h2", "h3", "h4"]):
            if header.get_text(strip=True).lower().strip().rstrip(":") == "references":
                ref_section = header
                break

    if ref_section:
        parent = ref_section.find_parent()
        if parent:
            collecting = False
            for sibling in parent.children:
                if sibling == ref_section:
                    collecting = True
                    continue
                if collecting and isinstance(sibling, Tag):
                    if sibling.name in ("h1", "h2", "h3", "h4"):
                        break
                    for li in sibling.find_all("li"):
                        ref = parse_reference_li(li)
                        if ref:
                            references.append(ref)

    # ---- 策略2: 查找全文 <ol> 列表 ----
    if len(references) < 2:
        references = []
        for ol in soup.find_all("ol"):
            items = ol.find_all("li", recursive=False)
            if len(items) >= 3:
                for li in items:
                    ref = parse_reference_li(li)
                    if ref:
                        references.append(ref)
                if len(references) >= 3:
                    break

    # ---- 策略3: 正则兜底 ----
    if len(references) < 2:
        references = extract_by_regex(soup)

    # 去重 + 排序
    seen = set()
    unique_refs = []
    for ref in references:
        if ref.number not in seen:
            seen.add(ref.number)
            unique_refs.append(ref)
    unique_refs.sort(key=lambda r: int(r.number) if r.number.isdigit() else 0)

    return unique_refs


# ===============================================================
# 输出 CSV
# ===============================================================
def write_csv(references: list[Reference], output_path: str):
    """
    将参考文献列表写入 CSV 文件（Tab 分隔）。
    关注 DOI 和 title 列，其他列留空。

    列: pmid, title, abstract, authors, journal, pub_date, doi,
        keywords, mesh_terms, pub_types
    """
    headers = [
        "pmid", "title", "abstract", "authors", "journal",
        "pub_date", "doi", "keywords", "mesh_terms", "pub_types"
    ]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t")
        writer.writeheader()

        for ref in references:
            # 从 DOI URL 中提取纯 DOI 字符串
            doi_value = ref.doi
            if doi_value and "doi.org/" in doi_value:
                doi_value = doi_value.split("doi.org/")[-1]

            writer.writerow({
                "pmid": ref.pmid,
                "title": ref.title,
                "abstract": "",
                "authors": "",
                "journal": "",
                "pub_date": "",
                "doi": doi_value,
                "keywords": "",
                "mesh_terms": "",
                "pub_types": ""
            })


# ===============================================================
# 命令行入口
# ===============================================================
def main():
    parser = argparse.ArgumentParser(
        description="从 PMC HTML 文件中提取参考文献，输出为 CSV（关注 DOI 和 title 列）"
    )
    parser.add_argument("html_file", help="输入的 HTML 文件路径")
    parser.add_argument(
        "-o", "--output",
        help="输出 CSV 文件路径（默认 references.csv）",
        default="references.csv"
    )
    args = parser.parse_args()

    references = extract_references(args.html_file)

    if not references:
        print("未找到参考文献。", file=sys.stderr)
        sys.exit(1)

    write_csv(references, args.output)

    print(f"CSV 文件已生成: {args.output}")
    print(f"共 {len(references)} 条参考文献")
    print()

    # 同时在屏幕上预览
    for ref in references:
        doi_display = ref.doi if ref.doi else "(无 DOI)"
        pmid_display = f"PMID:{ref.pmid}" if ref.pmid else ""
        title_display = ref.title if ref.title else "(无标题)"
        print(f"[{ref.number}] {pmid_display}")
        print(f"    DOI:   {doi_display}")
        print(f"    Title: {title_display}")
        print()


if __name__ == "__main__":
    main()
