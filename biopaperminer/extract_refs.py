#!/usr/bin/env python3
"""
extract_refs.py — 统一参考文献提取入口
支持 PMC HTML 和 RIS 两种格式，输出为 CSV。

用法:
    biopaperminer refs input.html                    # PMC HTML
    biopaperminer refs input.ris                     # RIS
    biopaperminer refs input.html --format html      # 显式指定
    biopaperminer refs input.ris --format ris -o ./output_dir
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="从 PMC HTML 或 RIS 文件中提取参考文献"
    )
    parser.add_argument("input_file", help="输入文件路径（.html 或 .ris）")
    parser.add_argument("--format", "-f",
                        choices=["html", "ris", "auto"],
                        default="auto",
                        help="输入格式（默认 auto: 根据扩展名自动识别）")
    parser.add_argument("-o", "--output",
                        default="./references_output",
                        help="输出目录（默认 ./references_output）")
    args = parser.parse_args()

    # 自动识别格式
    fmt = args.format
    if fmt == "auto":
        ext = Path(args.input_file).suffix.lower()
        if ext in (".ris",):
            fmt = "ris"
        elif ext in (".html", ".htm"):
            fmt = "html"
        else:
            print(f"❌ 无法自动识别格式，请使用 --format 指定（html/ris）", file=sys.stderr)
            sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "html":
        from biopaperminer.extract_references import extract_references, write_csv as write_html_csv
        references = extract_references(args.input_file)
        if not references:
            print("未找到参考文献。", file=sys.stderr)
            sys.exit(1)
        write_html_csv(references, output_dir)
        _print_summary_html(output_dir, references)

    elif fmt == "ris":
        from biopaperminer.extract_ris import extract_ris
        import csv
        rows = extract_ris(args.input_file)
        if not rows:
            print("未找到参考文献记录。", file=sys.stderr)
            sys.exit(1)
        _write_csv_rows(rows, output_dir)
        _print_summary_ris(output_dir, rows)


def _write_csv_rows(rows: list[dict], output_dir: Path):
    """将行字典列表写入 CSV + 日志文件"""
    import csv
    csv_path = output_dir / "references.csv"
    log_path = output_dir / "missing_fields.log"
    headers = ["pmid","title","abstract","authors","journal","pub_date",
               "doi","keywords","mesh_terms","pub_types"]

    missing_log = []
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t")
        writer.writeheader()
        for idx, row in enumerate(rows, 1):
            writer.writerow(row)
            reasons = []
            if not row.get("doi"):
                reasons.append("无 DOI")
            if not row.get("title"):
                reasons.append("无标题")
            if reasons:
                entry = f"[{idx}] {'、'.join(reasons)}"
                if row.get("doi"):
                    entry += f"  DOI: {row['doi']}"
                if row.get("title"):
                    entry += f"  Title: {row['title'][:100]}"
                if row.get("pmid"):
                    entry += f"  PMID: {row['pmid']}"
                missing_log.append(entry)

    if missing_log:
        log_path.write_text(
            "# 以下参考文献缺少 DOI 或标题\n"
            "# 可在浏览器打开 https://doi.org/DOI 手动查找\n\n"
            + "\n".join(missing_log),
            encoding="utf-8"
        )


def _print_summary_html(output_dir, references):
    csv_path = output_dir / "references.csv"
    log_path = output_dir / "missing_fields.log"
    print(f"📁 输出目录: {output_dir}/")
    print(f"   📄 references.csv       ({len(references)} 条)")
    if log_path.exists():
        missing = len(log_path.read_text(encoding="utf-8").strip().split("\n")) - 2
        print(f"   📋 missing_fields.log   ({missing} 条缺失记录)")
    print()
    for ref in references[:10]:
        doi = ref.doi.split("doi.org/")[-1] if ref.doi else "(无 DOI)"
        pmid = f"PMID:{ref.pmid}" if ref.pmid else ""
        title = ref.title if ref.title else "(无标题)"
        print(f"[{ref.number}] {pmid}")
        print(f"    DOI:   {doi}")
        print(f"    Title: {title}")
        print()
    if len(references) > 10:
        print(f"... 共 {len(references)} 条，完整列表见 {csv_path}")


def _print_summary_ris(output_dir, rows):
    csv_path = output_dir / "references.csv"
    log_path = output_dir / "missing_fields.log"
    print(f"📁 输出目录: {output_dir}/")
    print(f"   📄 references.csv       ({len(rows)} 条)")
    if log_path.exists():
        missing = len(log_path.read_text(encoding="utf-8").strip().split("\n")) - 2
        print(f"   📋 missing_fields.log   ({missing} 条缺失记录)")
    print()
    for i, row in enumerate(rows[:10], 1):
        title = row["title"][:70] + "..." if len(row["title"]) > 70 else row["title"]
        doi = row["doi"] if row["doi"] else "(无 DOI)"
        print(f"[{i}] {row['pub_types']}")
        print(f"    Title: {title}")
        print(f"    DOI:   {doi}")
        print()
    if len(rows) > 10:
        print(f"... 共 {len(rows)} 条，完整列表见 {csv_path}")


if __name__ == "__main__":
    main()
