#!/usr/bin/env python3
"""
PubMed 文献批量下载工具 (CLI 版本)
基于 NCBI E-utilities API

用法示例:
  python pubmed_cli.py search "CRISPR gene editing" -n 10
  python pubmed_cli.py search "cancer immunotherapy" -n 50 --mindate 2023/01/01 --maxdate 2024/12/31
  python pubmed_cli.py fetch 36921042 37587284 --output ./papers
  python pubmed_cli.py search "machine learning" --format json csv txt
  python pubmed_cli.py search "deep learning" --output ./my_papers --api-key YOUR_KEY --email you@example.com
"""

import argparse
import json
import os
import sys
import time
import csv
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional

try:
    import requests
except ImportError:
    print("❌ 需要安装 requests 库: pip install requests")
    sys.exit(1)


# ======================== 颜色输出 ========================

class Colors:
    HEADER  = "\033[95m"
    OKBLUE  = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL    = "\033[91m"
    ENDC    = "\033[0m"
    BOLD    = "\033[1m"


def cprint(msg, color=""):
    print(f"{color}{msg}{Colors.ENDC}")


# ======================== PubMed 下载器 ========================

class PubMedDownloader:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, api_key=None, email=None, tool="PubMedCLI", proxy=None):
        self.api_key = api_key
        self.email = email
        self.tool = tool
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"{tool}/1.0 (mailto:{email or 'unknown'})"
        })
        # 代理支持：优先参数，其次环境变量
        self.proxy = proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
        if self.proxy:
            self.session.proxies = {"http": self.proxy, "https": self.proxy}
            cprint(f"  使用代理: {self.proxy}", Colors.OKBLUE)

    def _build_params(self, extra=None):
        params = {"tool": self.tool}
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        if extra:
            params.update(extra)
        return params

    def _sleep(self):
        time.sleep(0.34 if not self.api_key else 0.11)

    # ---- ESearch ----
    def search(self, query, max_results=20, sort="relevance",
               mindate=None, maxdate=None, datetype="pdat"):
        params = self._build_params({
            "db": "pubmed", "term": query, "retmax": max_results,
            "sort": sort, "retmode": "json", "datetype": datetype,
        })
        if mindate:
            params["mindate"] = mindate
        if maxdate:
            params["maxdate"] = maxdate

        cprint(f"\n🔍 [ESearch] 正在搜索: {query}", Colors.OKBLUE)

        # 带重试的请求（应对网络超时）
        max_retries = 3
        last_error = None
        for attempt in range(max_retries):
            try:
                resp = self.session.get(
                    f"{self.BASE_URL}/esearch.fcgi", params=params, timeout=60
                )
                resp.raise_for_status()
                data = resp.json()
                pmids = data.get("esearchresult", {}).get("idlist", [])
                total = int(data.get("esearchresult", {}).get("count", 0))
                cprint(f"   共找到 {Colors.BOLD}{total}{Colors.ENDC} 条结果，获取了 {len(pmids)} 条 PMID", Colors.OKGREEN)
                self._sleep()
                return pmids
            except (requests.exceptions.ConnectTimeout,
                    requests.exceptions.ConnectionError) as e:
                last_error = e
                delay = 5 * (2 ** attempt)  # 5s, 10s, 20s
                cprint(f"   ⚠️  连接超时（{delay}s 后重试 {attempt+1}/{max_retries}）: {e}", Colors.WARNING)
                time.sleep(delay)
            except requests.exceptions.RequestException as e:
                raise  # 非超时错误直接抛出

        cprint(f"   ❌ 搜索失败，无法连接到 NCBI（已重试 {max_retries} 次）", Colors.FAIL)
        cprint(f"   💡 建议: 配置代理（--proxy 或 HTTPS_PROXY 环境变量）或检查网络", Colors.WARNING)
        raise last_error or ConnectionError("PubMed 连接失败")

    # ---- EFetch ----
    def fetch_fulltext_xml(self, pmids):
        params = self._build_params({
            "db": "pubmed", "id": ",".join(pmids),
            "retmode": "xml", "rettype": "abstract",
        })
        cprint(f"📥 [EFetch] 正在获取 {len(pmids)} 篇文献详情...", Colors.OKBLUE)
        resp = self.session.get(f"{self.BASE_URL}/efetch.fcgi", params=params, timeout=60)
        resp.raise_for_status()
        self._sleep()
        return resp.text

    # ---- ESummary ----
    def fetch_summary(self, pmids):
        params = self._build_params({
            "db": "pubmed", "id": ",".join(pmids), "retmode": "json",
        })
        cprint(f"📋 [ESummary] 正在获取 {len(pmids)} 篇摘要信息...", Colors.OKBLUE)
        resp = self.session.get(f"{self.BASE_URL}/esummary.fcgi", params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result", {})
        uids = result.get("uids", [])
        articles = [result[uid] for uid in uids if uid in result]
        self._sleep()
        return articles

    # ---- 解析 XML ----
    @staticmethod
    def parse_xml(xml_text):
        root = ET.fromstring(xml_text)
        articles = []
        for article in root.findall(".//PubmedArticle"):
            info = {
                "pmid": None, "title": None, "abstract": None,
                "authors": [], "journal": None, "pub_date": None,
                "doi": None, "keywords": [], "mesh_terms": [], "pub_types": [],
            }
            pmid_elem = article.find(".//PMID")
            if pmid_elem is not None:
                info["pmid"] = pmid_elem.text
            title_elem = article.find(".//ArticleTitle")
            if title_elem is not None:
                info["title"] = "".join(title_elem.itertext()).strip()
            abstract_parts = []
            for abs_text in article.findall(".//Abstract/AbstractText"):
                label = abs_text.get("Label", "")
                text = "".join(abs_text.itertext()).strip()
                abstract_parts.append(f"{label}: {text}" if label else text)
            if abstract_parts:
                info["abstract"] = "\n\n".join(abstract_parts)
            for author in article.findall(".//Author"):
                last = author.find("LastName")
                fore = author.find("ForeName")
                name_parts = []
                if fore is not None: name_parts.append(fore.text)
                if last is not None: name_parts.append(last.text)
                if name_parts:
                    info["authors"].append(" ".join(name_parts))
            journal_elem = article.find(".//Journal/Title")
            if journal_elem is not None:
                info["journal"] = journal_elem.text
            pub_date_elem = article.find(".//PubDate")
            if pub_date_elem is not None:
                date_parts = []
                for tag in ["Year", "Month", "Day"]:
                    elem = pub_date_elem.find(tag)
                    if elem is not None: date_parts.append(elem.text)
                info["pub_date"] = " ".join(date_parts) if date_parts else None
            for aid in article.findall(".//ArticleId"):
                if aid.get("IdType") == "doi":
                    info["doi"] = aid.text
                    break
            for kw in article.findall(".//Keyword"):
                if kw.text: info["keywords"].append(kw.text)
            for mesh in article.findall(".//MeshHeading/DescriptorName"):
                if mesh.text: info["mesh_terms"].append(mesh.text)
            for ptype in article.findall(".//PublicationType"):
                if ptype.text: info["pub_types"].append(ptype.text)
            articles.append(info)
        return articles

    # ---- 保存 ----
    def save_results(self, articles, output_dir, formats):
        os.makedirs(output_dir, exist_ok=True)
        saved_files = []

        if "json" in formats:
            path = os.path.join(output_dir, "results.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            cprint(f"  ✅ JSON  → {path}", Colors.OKGREEN)
            saved_files.append(path)

        if "csv" in formats:
            path = os.path.join(output_dir, "results.csv")
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=articles[0].keys())
                writer.writeheader()
                for art in articles:
                    row = {k: "; ".join(v) if isinstance(v, list) else v for k, v in art.items()}
                    writer.writerow(row)
            cprint(f"  ✅ CSV   → {path}", Colors.OKGREEN)
            saved_files.append(path)

        if "txt" in formats:
            path = os.path.join(output_dir, "results.txt")
            with open(path, "w", encoding="utf-8") as f:
                for art in articles:
                    f.write("=" * 80 + "\n")
                    f.write(f"PMID:     {art['pmid']}\n")
                    f.write(f"标题:     {art['title']}\n")
                    f.write(f"作者:     {'; '.join(art['authors'])}\n")
                    f.write(f"期刊:     {art['journal']}\n")
                    f.write(f"日期:     {art['pub_date']}\n")
                    f.write(f"DOI:      {art['doi']}\n")
                    f.write(f"关键词:   {'; '.join(art['keywords'])}\n")
                    f.write(f"MeSH词:   {'; '.join(art['mesh_terms'])}\n")
                    f.write(f"文献类型: {'; '.join(art['pub_types'])}\n")
                    f.write("-" * 40 + " 摘要 " + "-" * 35 + "\n")
                    f.write(f"{art['abstract'] or '(无摘要)'}\n")
                    f.write("=" * 80 + "\n\n")
            cprint(f"  ✅ TXT   → {path}", Colors.OKGREEN)
            saved_files.append(path)

        return saved_files


# ======================== CLI 命令处理 ========================

def cmd_search(args, downloader):
    """搜索并下载文献"""
    formats = args.format if args.format else ["json", "csv", "txt"]

    pmids = downloader.search(
        query=args.query,
        max_results=args.number,
        sort=args.sort,
        mindate=args.mindate,
        maxdate=args.maxdate,
    )
    if not pmids:
        cprint("⚠️  未找到相关文献。", Colors.WARNING)
        return

    # 分批获取
    batch_size = 100
    all_articles = []
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i: i + batch_size]
        xml_text = downloader.fetch_fulltext_xml(batch)
        articles = PubMedDownloader.parse_xml(xml_text)
        all_articles.extend(articles)

    cprint(f"\n📊 共解析 {len(all_articles)} 篇文献\n", Colors.HEADER)

    # 控制台预览
    preview_count = min(args.preview, len(all_articles))
    for i, art in enumerate(all_articles[:preview_count]):
        cprint(f"{'─' * 70}", Colors.ENDC)
        cprint(f" [{i+1}] PMID: {art['pmid']}", Colors.BOLD)
        cprint(f"     标题: {art['title']}", Colors.ENDC)
        authors_str = "; ".join(art["authors"][:3])
        if len(art["authors"]) > 3:
            authors_str += f" ... ({len(art['authors'])} authors)"
        print(f"     作者: {authors_str}")
        print(f"     期刊: {art['journal']}  ({art['pub_date']})")
        if art["doi"]:
            print(f"     DOI:  {art['doi']}")
        abstract = (art["abstract"] or "(无摘要)")[:200]
        print(f"     摘要: {abstract}...")
    cprint(f"{'─' * 70}\n", Colors.ENDC)

    # 保存
    if not args.no_save:
        cprint("💾 正在保存文件...", Colors.OKBLUE)
        downloader.save_results(all_articles, args.output, formats)

    cprint("✅ 完成!", Colors.OKGREEN)


def cmd_fetch(args, downloader):
    """通过 PMID 直接获取文献"""
    pmids = args.pmids
    formats = args.format if args.format else ["json", "csv", "txt"]

    xml_text = downloader.fetch_fulltext_xml(pmids)
    articles = PubMedDownloader.parse_xml(xml_text)

    cprint(f"\n📊 共解析 {len(articles)} 篇文献\n", Colors.HEADER)

    for i, art in enumerate(articles):
        cprint(f"{'─' * 70}", Colors.ENDC)
        cprint(f" [{i+1}] PMID: {art['pmid']}", Colors.BOLD)
        cprint(f"     标题: {art['title']}", Colors.ENDC)
        authors_str = "; ".join(art["authors"][:3])
        if len(art["authors"]) > 3:
            authors_str += f" ... ({len(art['authors'])} authors)"
        print(f"     作者: {authors_str}")
        print(f"     期刊: {art['journal']}  ({art['pub_date']})")
        if art["doi"]:
            print(f"     DOI:  {art['doi']}")
        print(f"     摘要: {(art['abstract'] or '(无摘要)')[:200]}...")
    cprint(f"{'─' * 70}\n", Colors.ENDC)

    if not args.no_save:
        cprint("💾 正在保存文件...", Colors.OKBLUE)
        downloader.save_results(articles, args.output, formats)

    cprint("✅ 完成!", Colors.OKGREEN)


def cmd_summary(args, downloader):
    """获取文献摘要信息 (ESummary)"""
    pmids = args.pmids
    articles = downloader.fetch_summary(pmids)

    cprint(f"\n📊 共获取 {len(articles)} 篇文献摘要\n", Colors.HEADER)

    for i, art in enumerate(articles):
        cprint(f"{'─' * 70}", Colors.ENDC)
        cprint(f" [{i+1}] PMID: {art.get('uid', 'N/A')}", Colors.BOLD)
        cprint(f"     标题: {art.get('title', 'N/A')}", Colors.ENDC)
        authors = [a.get("name", "") for a in art.get("authors", [])[:3]]
        print(f"     作者: {'; '.join(authors)}")
        print(f"     期刊: {art.get('fulljournalname', 'N/A')}")
        print(f"     日期: {art.get('pubdate', 'N/A')}")
    cprint(f"{'─' * 70}\n", Colors.ENDC)

    if not args.no_save:
        cprint("💾 正在保存文件...", Colors.OKBLUE)
        os.makedirs(args.output, exist_ok=True)
        path = os.path.join(args.output, "summary.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        cprint(f"  ✅ JSON  → {path}", Colors.OKGREEN)

    cprint("✅ 完成!", Colors.OKGREEN)


# ======================== argparse 构建 ========================

def build_parser():
    # 1. 定义公共参数 (全局参数)
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--api-key", default="dd527302afc390c4c5db14b0de7bb0982a08", help="NCBI API Key (可选，提升限速到10次/秒)")
    common_parser.add_argument("--email", default="sunning@njfu.edu.cn", help="你的邮箱 (NCBI建议提供)")
    common_parser.add_argument("--output", "-o", default="./pubmed_results", help="输出目录 (默认: ./pubmed_results)")
    common_parser.add_argument("--format", "-f", nargs="+", choices=["json", "csv", "txt", "xml"],
                               default=None, help="保存格式 (默认: json csv txt)")
    common_parser.add_argument("--no-save", action="store_true", help="不保存文件，仅控制台输出")
    common_parser.add_argument("--preview", type=int, default=5, help="控制台预览篇数 (默认: 5)")
    common_parser.add_argument("--proxy", type=str, default=None,
                               help="HTTP/HTTPS 代理地址，如 http://127.0.0.1:7897")

    # 2. 主 parser
    parser = argparse.ArgumentParser(
        prog="pubmed_cli",
        description="PubMed 文献批量下载工具 (CLI) — 基于 NCBI E-utilities API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],  # 主 parser 也包含这些参数
        epilog="""
使用示例:
  %(prog)s search "CRISPR gene editing" -n 10
  %(prog)s search "cancer immunotherapy" -n 50 --mindate 2023/01/01 --maxdate 2024/12/31
  %(prog)s fetch 36921042 37587284 --output ./papers
  %(prog)s summary 36921042 37587284
  %(prog)s search "deep learning" --format json csv --api-key YOUR_KEY --email you@example.com
  %(prog)s search "AI drug discovery" --no-save --preview 5
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 3. 子命令继承公共参数 parents=[common_parser]
    # ---- search ----
    sp_search = subparsers.add_parser("search", help="按关键词搜索并下载文献", parents=[common_parser])
    sp_search.add_argument("query", help='搜索词，如 "CRISPR gene editing"')
    sp_search.add_argument("-n", "--number", type=int, default=20, help="下载篇数 (默认: 20)")
    sp_search.add_argument("--sort", choices=["relevance", "pub_date", "Author"], default="relevance",
                           help="排序方式 (默认: relevance)")
    sp_search.add_argument("--mindate", default=None, help="起始日期 YYYY/MM/DD")
    sp_search.add_argument("--maxdate", default=None, help="结束日期 YYYY/MM/DD")
    sp_search.add_argument("--datetype", choices=["pdat", "edat"], default="pdat",
                           help="日期类型: pdat=发表日期, edat=收录日期 (默认: pdat)")

    # ---- fetch ----
    sp_fetch = subparsers.add_parser("fetch", help="通过 PMID 直接获取文献详情", parents=[common_parser])
    sp_fetch.add_argument("pmids", nargs="+", help="一个或多个 PMID，如 36921042 37587284")

    # ---- summary ----
    sp_summary = subparsers.add_parser("summary", help="通过 PMID 获取摘要信息", parents=[common_parser])
    sp_summary.add_argument("pmids", nargs="+", help="一个或多个 PMID")

    return parser


# ======================== 主入口 ========================

def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # 创建下载器
    downloader = PubMedDownloader(
        api_key=args.api_key,
        email=args.email,
        proxy=args.proxy,
    )

    cprint("\n" + "=" * 60, Colors.HEADER)
    cprint("  PubMed 文献下载工具 CLI", Colors.BOLD)
    cprint("=" * 60, Colors.HEADER)

    # 分发命令
    if args.command == "search":
        cmd_search(args, downloader)
    elif args.command == "fetch":
        cmd_fetch(args, downloader)
    elif args.command == "summary":
        cmd_summary(args, downloader)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
