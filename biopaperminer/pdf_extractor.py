"""BioPaperMiner — PDF 文本提取器"""

import re
from pathlib import Path
from typing import Tuple, List

import fitz  # PyMuPDF
import pdfplumber
from rich.console import Console

from biopaperminer import config

console = Console()


class PDFExtractor:
    """PDF 文本提取器 — 优先 MinerU，回退 PyMuPDF/pdfplumber"""

    @staticmethod
    def extract_text_pymupdf(pdf_path: Path, max_pages: int = 15) -> str:
        """使用 PyMuPDF 提取文本"""
        try:
            doc = fitz.open(str(pdf_path))
            texts = []
            for page_num in range(min(len(doc), max_pages)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    texts.append(text)
            doc.close()
            return "\n\n".join(texts)
        except Exception as e:
            console.print(f"[yellow]PyMuPDF 提取失败: {e}[/yellow]")
            return ""

    @staticmethod
    def extract_text_pdfplumber(pdf_path: Path, max_pages: int = 15) -> str:
        """使用 pdfplumber 提取文本（备用）"""
        try:
            texts = []
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page_num, page in enumerate(pdf.pages[:max_pages]):
                    text = page.extract_text()
                    if text:
                        texts.append(text)
            return "\n\n".join(texts)
        except Exception as e:
            console.print(f"[yellow]pdfplumber 提取失败: {e}[/yellow]")
            return ""

    @staticmethod
    def extract_links(pdf_path: Path) -> Tuple[List[str], List[str]]:
        """提取 PDF 中的 GitHub/GitLab 及其他链接"""
        github_links = []
        other_links = []

        try:
            doc = fitz.open(str(pdf_path))
            for page in doc:
                # 提取注释链接
                for link in page.get_links():
                    uri = link.get("uri", "")
                    if uri:
                        if "github.com" in uri.lower() or "gitlab.com" in uri.lower():
                            if uri not in github_links:
                                github_links.append(uri)
                        elif uri.startswith("http"):
                            if uri not in other_links:
                                other_links.append(uri)

                # 从文本中提取链接
                text = page.get_text()
                github_pattern = r'https?://(?:www\.)?github\.com/[^\s\)\]\}"\'>]+'
                for match in re.finditer(github_pattern, text, re.IGNORECASE):
                    url = match.group().rstrip('.,;:')
                    if url not in github_links:
                        github_links.append(url)

                gitlab_pattern = r'https?://(?:www\.)?gitlab\.com/[^\s\)\]\}"\'>]+'
                for match in re.finditer(gitlab_pattern, text, re.IGNORECASE):
                    url = match.group().rstrip('.,;:')
                    if url not in github_links:
                        github_links.append(url)

            doc.close()
        except Exception as e:
            console.print(f"[yellow]链接提取失败: {e}[/yellow]")

        return github_links, other_links

    # PDF 文本提取缓存
    _pdf_text_cache: dict = {}

    @classmethod
    def extract(cls, pdf_path: Path) -> Tuple[str, List[str], List[str]]:
        """
        优先使用 MinerU 的 full.md；失败时回退到 PyMuPDF/pdfplumber。
        返回 (文本, github_links, other_links)
        """
        md_text = None

        # 尝试 MinerU
        try:
            from biopaperminer.mineru_client import MinerUClient
            md_text = MinerUClient(api_token=config.MINERU_API_TOKEN).pdf_to_md(
                pdf_path,
                output_dir=pdf_path.parent / f"{pdf_path.stem}_mineru",
            )
        except Exception as e:
            console.print(f"[yellow]MinerU 解析失败 {pdf_path.name}: {e}[/yellow]")

        if md_text:
            text = md_text
        else:
            # 缓存 PDF 文本提取结果，避免重复解析
            cache_key = str(pdf_path.resolve())
            if cache_key in cls._pdf_text_cache:
                text = cls._pdf_text_cache[cache_key]
            else:
                text = cls.extract_text_pymupdf(pdf_path, config.MAX_PAGES_TO_ANALYZE)
                if len(text) < config.MIN_TEXT_LENGTH:
                    text_alt = cls.extract_text_pdfplumber(pdf_path, config.MAX_PAGES_TO_ANALYZE)
                    if len(text_alt) > len(text):
                        text = text_alt
                cls._pdf_text_cache[cache_key] = text

        github_links, other_links = cls.extract_links(pdf_path)
        return text, github_links, other_links
