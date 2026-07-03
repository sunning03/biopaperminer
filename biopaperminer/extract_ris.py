#!/usr/bin/env python3
"""
extract_ris.py
从 RIS 文件中提取参考文献，输出为 CSV 文件（Tab 分隔）。

CSV 列: pmid, title, abstract, authors, journal, pub_date, doi,
        keywords, mesh_terms, pub_types

用法:
    python extract_ris.py input.ris
    python extract_ris.py input.ris -o references.csv

依赖: 无第三方依赖（纯标准库）
"""

import argparse
import csv
import re
import sys
from pathlib import Path


# ===============================================================
# RIS 标签 -> CSV 列 的映射规则
# ===============================================================
MULTIVALUE_TAGS = {"AU", "A1", "A2", "A3", "KW"}
SINGLEVALUE_TAGS = {"TY", "TI", "JO", "PY", "DA", "DO", "UR", "AB", "ID"}


# ===============================================================
# 解析 RIS 文件，返回字典列表
# ===============================================================
def parse_ris(ris_path: str) -> list[dict]:
    """
    解析 RIS 文件，返回每条参考文献的字典列表。
    每条记录以 "TY -" 开始，以 "ER -" 结束。
    """
    content = Path(ris_path).read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()

    records = []
    current_record = None

    for line in lines:
        line = line.rstrip("\n\r")
        match = re.match(r'^([A-Z]{2}\d?)\s*-\s?(.*)$', line)

        if match:
            tag = match.group(1).strip()
            value = match.group(2).strip()

            if tag == "TY":
                current_record = {"AU": [], "KW": []}
                current_record["TY"] = value
                continue
            if tag == "ER":
                if current_record is not None:
                    records.append(current_record)
                    current_record = None
                continue

            if current_record is not None:
                if tag in MULTIVALUE_TAGS:
                    field = "AU" if tag in ("A1", "A2", "A3") else tag
                    if field not in current_record:
                        current_record[field] = []
                    current_record[field].append(value)
                elif tag in SINGLEVALUE_TAGS:
                    current_record[tag] = value
                else:
                    current_record[tag] = value
        else:
            if current_record is not None and line.strip():
                last_key = next(iter(current_record.keys()), None)
                if last_key:
                    if isinstance(current_record[last_key], list):
                        if current_record[last_key]:
                            current_record[last_key][-1] += " " + line.strip()
                    else:
                        current_record[last_key] += " " + line.strip()

    if current_record is not None:
        records.append(current_record)

    return records


# ===============================================================
# 从 RIS 记录字典中提取各 CSV 字段
# ===============================================================
def record_to_row(record: dict) -> dict:
    """将一条 RIS 记录转换为 CSV 行字典。"""
    authors_list = record.get("AU", [])
    authors = "; ".join(authors_list) if isinstance(authors_list, list) else str(authors_list)

    title = record.get("TI", "")
    journal = record.get("JO", "") or record.get("JF", "") or record.get("JA", "")
    pub_date = record.get("DA", "") or record.get("PY", "")
    doi = record.get("DO", "")
    if not doi:
        ur = record.get("UR", "")
        if ur and "doi.org/" in ur:
            doi = ur.split("doi.org/")[-1].strip()

    pmid = ""
    ur = record.get("UR", "")
    if ur:
        pm_match = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', ur)
        if pm_match:
            pmid = pm_match.group(1)
    if not pmid:
        id_val = record.get("ID", "")
        if id_val and id_val.isdigit() and len(id_val) >= 6:
            pmid = id_val

    kw_list = record.get("KW", [])
    keywords = "; ".join(kw_list) if isinstance(kw_list, list) else str(kw_list)
    abstract = record.get("AB", "") or record.get("N2", "")
    pub_types = record.get("TY", "")

    return {
        "pmid": pmid, "title": title, "abstract": abstract,
        "authors": authors, "journal": journal, "pub_date": pub_date,
        "doi": doi, "keywords": keywords, "mesh_terms": "", "pub_types": pub_types,
    }


def extract_ris(ris_path: str) -> list[dict]:
    """从 RIS 文件提取参考文献，返回行字典列表。"""
    records = parse_ris(ris_path)
    return [record_to_row(r) for r in records]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="从 RIS 文件中提取参考文献，输出为 CSV（Tab 分隔）"
    )
    parser.add_argument("ris_file", help="输入的 RIS 文件路径")
    parser.add_argument("-o", "--output",
                        help="输出 CSV 文件路径（默认 references_from_ris.csv）",
                        default="references_from_ris.csv")
    args = parser.parse_args()

    rows = extract_ris(args.ris_file)
    if not rows:
        print("未找到参考文献记录。", file=sys.stderr)
        sys.exit(1)

    headers = ["pmid","title","abstract","authors","journal","pub_date",
               "doi","keywords","mesh_terms","pub_types"]
    with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"CSV 文件已生成: {args.output}")
    print(f"共 {len(rows)} 条参考文献")
