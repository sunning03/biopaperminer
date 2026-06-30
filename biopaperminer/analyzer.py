# ╭──────────────────────────────────────────────────────╮
# │                                                      │
# │   ██╗     ██╗  ██╗██╗  ████████╗██╗  ██╗             │
# │   ██║     ╚██╗██╔╝██║  ╚══██╔══╝╚██╗██╔╝             │
# │   ██║      ╚███╔╝ ██║     ██║    ╚███╔╝              │
# │   ██║      ██╔██╗ ██║     ██║    ██╔██╗              │
# │   ███████╗██╔╝ ██╗███████╗██║   ██╔╝ ██╗             │
# │   ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝   ╚═╝  ╚═╝             │
# │                                                      │
# │   Author: LXLTX-Lab                                  │
# │   GitHub: https://github.com/lxltx2025               │
# │   Date: 2025-12-23                                   │
# │   License: MIT                                       │
# │                                                      │
# ╰──────────────────────────────────────────────────────╯

"""
AI文献批量分析系统

功能：
- 批量分析PDF文献
- 生成结构化摘要、标签、关键词
- 提取GitHub代码链接
- 输出JSON/CSV/Markdown/HTML报告
"""

import os
import sys
import json
import re
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

# 第三方库
import requests
import pandas as pd
from tqdm import tqdm
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

# 项目模块
from biopaperminer.models import PaperAnalysis
from biopaperminer.pdf_extractor import PDFExtractor

# 配置
try:
    import biopaperminer.config as config
except ImportError:
    print("请确保config.py在同一目录下")
    sys.exit(1)


console = Console()

# ============ Ollama API调用 ============

class OllamaAnalyzer:
    """LLM 分析器（支持多模型）"""

    def __init__(self):
        # 引入之前创建的 llm_client.py
        from biopaperminer.llm_client import get_llm_client
        from biopaperminer.config import LLM_PROVIDER
        
        self.client = get_llm_client()
        self.provider_name = {
            "ollama": "Ollama", 
            "deepseek": "DeepSeek", 
            "agnes": "Agnes", 
            "openai_compatible": "OpenAI-Compat"
        }.get(LLM_PROVIDER, LLM_PROVIDER)

    def check_connection(self) -> bool:
        """检查 LLM 服务连接"""
        from biopaperminer.config import LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL
        
        if LLM_PROVIDER == "ollama":
            try:
                response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    if any(OLLAMA_MODEL in name for name in model_names):
                        return True
                    console.print(f"[yellow]模型 {OLLAMA_MODEL} 未找到，可用模型: {model_names}[/yellow]")
                    return False
            except Exception as e:
                console.print(f"[red]连接Ollama失败: {e}[/red]")
                return False
        else:
            # 云端 API 连通性测试（轻量请求，避免 "ping" 浪费配额）
            try:
                test = self.client.chat("Hi")
                if test:
                    console.print(f"[green]✓ {self.provider_name} 接口连通成功[/green]")
                    return True
            except Exception as e:
                console.print(f"[red]无法连接 {self.provider_name} API: {e}[/red]")
                return False

    
    def _create_analysis_prompt(self, text: str, github_links: List[str]) -> str:
        """创建分析提示词（委托给共享模块）"""
        from biopaperminer.prompts import build_analysis_prompt
        return build_analysis_prompt(text, github_links)
   
    def analyze(self, text: str, github_links: List[str]) -> Dict[str, Any]:
        """调用大模型分析论文（支持 Ollama / DeepSeek / Agnes 等）"""
        prompt = self._create_analysis_prompt(text, github_links)
        
        for attempt in range(config.MAX_RETRIES):
            try:
                # 统一调用 self.client.chat() 方法
                response_text = self.client.chat(prompt)
                
                if response_text:
                    # 解析JSON
                    return self._parse_response(response_text)
                else:
                    console.print(f"[yellow]{self.provider_name} 返回空结果，重试 {attempt + 1}/{config.MAX_RETRIES}[/yellow]")
                    
            except Exception as e:
                console.print(f"[yellow]请求错误: {e}，重试 {attempt + 1}/{config.MAX_RETRIES}[/yellow]")
            
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(config.RETRY_DELAY)
        
        return {}

    @staticmethod
    def _clean_json(text: str) -> str:
        """尝试修复常见的 JSON 格式问题"""
        # 1. 找到第一个 { 和最后一个 }
        start = text.find('{')
        end = text.rfind('}') + 1
        if start == -1 or end <= start:
            return text
        text = text[start:end]

        # 2. 去掉注释（// 和 /* */）
        text = re.sub(r'//[^\n]*', '', text)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

        # 3. 去掉尾随逗号（, 后面跟着 } 或 ]）
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)

        return text

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """解析 LLM 响应中的 JSON（带自动修复）"""
        if not response_text:
            return {}

        # 尝试 4 种解析策略
        strategies = [
            # 策略1: 直接解析
            lambda t: json.loads(t),
            # 策略2: 提取 ```json ... ``` 块后解析
            lambda t: json.loads(_extract_block(t, r'```json\s*([\s\S]*?)\s*```')),
            # 策略3: 提取 ``` ... ``` 块后解析
            lambda t: json.loads(_extract_block(t, r'```\s*([\s\S]*?)\s*```')),
            # 策略4: 提取最外层 {} 后解析
            lambda t: json.loads(_extract_outer_braces(t)),
        ]

        for strategy in strategies:
            try:
                return strategy(response_text)
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

        # 如果上面都失败，尝试清理 JSON 后再试一次
        cleaned = self._clean_json(response_text)
        for strategy in strategies:
            try:
                return strategy(cleaned)
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

        # 最后尝试：按行处理，去掉不可见字符
        try:
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', cleaned)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 所有策略都失败 - 打印前 500 字符以便排查
        preview = response_text[:500].replace("\n", "\\n")
        console.print(f"[yellow]无法解析JSON响应（前500字符: {preview}）[/yellow]")
        return {}


def _extract_block(text: str, pattern: str) -> str:
    """从 code block 中提取内容，失败返回空字符串"""
    m = re.search(pattern, text, re.DOTALL)
    if m:
        return m.group(1)
    return ""


def _extract_outer_braces(text: str) -> str:
    """提取最外层的 {} 内容，无括号时返回空字符串（让 json.loads 失败）"""
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end > start:
        return text[start:end]
    return ""  # 返回空让 json.loads 抛出异常，继续尝试下一策略或 fallback


# ============ 文献分析器 ============

class PaperBatchAnalyzer:
    """批量文献分析器"""
    
    def __init__(self, pdf_folder: Path):
        self.pdf_folder = pdf_folder
        self.ollama = OllamaAnalyzer()
        self.results: List[PaperAnalysis] = []
        # ✅ 新增：加载缓存字典，用于断点续传
        self.cache_map = self._load_existing_cache()
        
    def _load_existing_cache(self) -> Dict[str, PaperAnalysis]:
        """加载已有的分析结果，用于缓存"""
        cache = {}
        if config.JSON_OUTPUT.exists():
            try:
                with open(config.JSON_OUTPUT, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        # 使用 file_hash 作为唯一标识
                        if item.get('status') == 'success':
                            cache[item.get('file_hash')] = PaperAnalysis(**item)
            except Exception as e:
                console.print(f"[yellow]加载缓存失败: {e}[/yellow]")
        return cache
        
    def get_pdf_files(self) -> List[Path]:
        """获取所有PDF文件"""
        pdf_files = list(self.pdf_folder.glob("**/*.pdf"))
        console.print(f"[green]找到 {len(pdf_files)} 个PDF文件[/green]")
        return pdf_files
    
    # 类级缓存：(mtime, size) -> hash，避免重复读文件
    _hash_cache: dict = {}

    def compute_file_hash(self, file_path: Path) -> str:
        """计算文件哈希（带缓存，避免重复计算）"""
        try:
            stat = file_path.stat()
            cache_key = f"{file_path.resolve()}:{stat.st_mtime}:{stat.st_size}"
            if cache_key in self._hash_cache:
                return self._hash_cache[cache_key]
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    hasher.update(chunk)
            h = hasher.hexdigest()[:12]
            self._hash_cache[cache_key] = h
            return h
        except Exception:
            return hashlib.md5(str(file_path.resolve()).encode()).hexdigest()[:12]
    
    def analyze_single_pdf(self, pdf_path: Path) -> PaperAnalysis:
        """分析单个PDF"""
        file_name = pdf_path.name
        file_hash = self.compute_file_hash(pdf_path)
        
        # 创建基础结果
        result = PaperAnalysis(
            file_name=file_name,
            file_path=str(pdf_path),
            file_hash=file_hash,
            analysis_time=datetime.now().isoformat()
        )
        
        try:
            # 提取文本和链接
            text, github_links, other_links = PDFExtractor.extract(pdf_path)
            result.raw_text_length = len(text)
            result.github_links = github_links
            result.other_links = other_links
            
            if len(text) < config.MIN_TEXT_LENGTH:
                result.status = "error"
                result.error_message = "提取的文本太短"
                return result
            
            # 调用Ollama分析
            analysis = self.ollama.analyze(text, github_links)
            
            if not analysis:
                result.status = "error"
                result.error_message = "LLM分析返回空结果"
                return result
            
            # 填充分析结果
            self._populate_result(result, analysis)
            result.status = "success"
            
        except Exception as e:
            result.status = "error"
            result.error_message = str(e)
            console.print(f"[red]分析 {file_name} 失败: {e}[/red]")
        
        return result
    
    def _populate_result(self, result: PaperAnalysis, analysis: Dict) -> None:
        """填充分析结果"""
        # 基本信息
        result.title = analysis.get("title", "")
        result.title_cn = analysis.get("title_cn", "")
        result.authors = analysis.get("authors", [])
        result.publication_year = analysis.get("publication_year", "")
        result.journal_conference = analysis.get("journal_conference", "")
        result.doi = analysis.get("doi", "")
        # 新增：处理论文链接
        result.paper_link = analysis.get("paper_link", "")
        if not result.paper_link and result.doi:
            result.paper_link = f"https://doi.org/{result.doi}"
        # 摘要
        result.abstract = analysis.get("abstract", "")
        result.abstract_cn = analysis.get("abstract_cn", "")
        result.research_objective = analysis.get("research_objective", "")
        result.methodology = analysis.get("methodology", "")
        result.key_findings = analysis.get("key_findings", [])
        result.innovations = analysis.get("innovations", [])
        result.limitations = analysis.get("limitations", [])
        result.future_work = analysis.get("future_work", "")
        
        # 标签
        result.primary_category = analysis.get("primary_category", "其他")
        result.secondary_categories = analysis.get("secondary_categories", [])
        result.content_type = analysis.get("content_type", "")
        result.research_stage = analysis.get("research_stage", "")
        
        # 关键词
        result.keywords = analysis.get("keywords", [])
        result.keywords_cn = analysis.get("keywords_cn", [])
        
        # 实体
        result.diseases = analysis.get("diseases", [])
        result.technologies = analysis.get("technologies", [])
        result.datasets = analysis.get("datasets", [])
        result.metrics = analysis.get("metrics", {})
        
        # 评估
        score = analysis.get("importance_score", 5)
        result.importance_score = max(1, min(10, int(score) if isinstance(score, (int, float)) else 5))
        result.importance_reason = analysis.get("importance_reason", "")
        
        # 影响
        result.clinical_impact = analysis.get("clinical_impact", "")
        result.potential_applications = analysis.get("potential_applications", [])
    
    def run(self) -> List[PaperAnalysis]:
        """运行批量分析 (优化：支持并发和缓存)"""
        
        # 1. 检查连接
        console.print(Panel("[bold]生物学与AI文献批量分析系统[/bold]", style="blue"))
        console.print(f"[cyan]检查 {self.ollama.provider_name} 服务...[/cyan]")
        if not self.ollama.check_connection():
            console.print("[red]无法连接到LLM服务，请确保服务已启动或API Key正确[/red]")
            return []
        console.print(f"[green]✓ {self.ollama.provider_name} 服务连接成功[/green]")

        # 2. 获取文件并过滤缓存
        pdf_files = self.get_pdf_files()
        if not pdf_files:
            return []
        
        pending_files = []
        skipped_count = 0
        
        for pdf_path in pdf_files:
            file_hash = self.compute_file_hash(pdf_path)
            if file_hash in self.cache_map:
                # 如果在缓存中，直接复用结果
                self.results.append(self.cache_map[file_hash])
                skipped_count += 1
            else:
                pending_files.append(pdf_path)
        
        if skipped_count > 0:
            console.print(f"[dim]♻️ 跳过已分析的文件: {skipped_count} 篇[/dim]")

        if not pending_files:
            console.print("[green]所有文件均已分析完毕[/green]")
            return self.results

        # 3. 并发分析
        console.print(f"\n[cyan]开始并发分析 {len(pending_files)} 个新文件...[/cyan]\n")
        
        # 动态调整 workers，不超过待处理文件数
        workers = min(config.MAX_WORKERS, len(pending_files))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[green]分析进度", total=len(pending_files))
            
            # 使用线程池并发执行
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_pdf = {
                    executor.submit(self.analyze_single_pdf, pdf): pdf 
                    for pdf in pending_files
                }
                
                for future in as_completed(future_to_pdf):
                    pdf_path = future_to_pdf[future]
                    try:
                        result = future.result()
                        self.results.append(result)
                        
                        # 更新缓存
                        if result.status == "success":
                            self.cache_map[result.file_hash] = result
                            
                        progress.update(task, description=f"[green]已完成: {result.file_name[:20]}...") 
                    except Exception as e:
                        console.print(f"[red]分析异常 {pdf_path.name}: {e}[/red]")
                        # 依然添加一个失败记录，避免后续报错
                        self.results.append(PaperAnalysis(
                            file_name=pdf_path.name,
                            file_path=str(pdf_path),
                            file_hash=self.compute_file_hash(pdf_path),
                            analysis_time=datetime.now().isoformat(),
                            status="error",
                            error_message=str(e)
                        ))
                    finally:
                        progress.advance(task)
        
        # 4. 保存结果
        success_count = sum(1 for r in self.results if r.status == "success")
        console.print(f"\n[green]分析完成: {success_count}/{len(self.results)} 成功[/green]")
        
        # 注意：这里不直接生成报告，让 main 函数控制
        return self.results


# ============ 报告生成器 ============

class ReportGenerator:
    """报告生成器"""
    
    # 类级缓存 HTML 模板，避免重复构建
    _html_template_cache: Optional[str] = None
    
    def __init__(self, results: List[PaperAnalysis]):
        # 统一转换为 PaperAnalysis 实例（避免 dict 和 dataclass 混用）
        normalized = []
        for r in results:
            if isinstance(r, dict):
                normalized.append(PaperAnalysis(**r))
            else:
                normalized.append(r)
        self.results = normalized
    
    def generate_all(self):
        """生成所有报告"""
        console.print("\n[cyan]生成报告...[/cyan]")
        
        self.generate_json()
        self.generate_csv()
        self.generate_markdown()
        self.generate_html()
        
        console.print(f"[green]✓ 所有报告已生成到 {config.OUTPUT_FOLDER}[/green]")
    
    def generate_json(self):
        """生成JSON报告"""
        data = [asdict(r) for r in self.results]
        with open(config.JSON_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        console.print(f"  [green]✓ JSON: {config.JSON_OUTPUT}[/green]")
    
    def _calculate_stats(self) -> Dict:
        """计算统计数据"""
        stats = {
            "total": len(self.results),
            "success": sum(1 for r in self.results if r.status == "success"),
            "high_importance": sum(1 for r in self.results if r.importance_score >= 8),
            "medium_importance": sum(1 for r in self.results if 5 <= r.importance_score < 8),
            "low_importance": sum(1 for r in self.results if r.importance_score < 5),
            "with_github": sum(1 for r in self.results if r.github_links and len(r.github_links) > 0),
            "without_github": sum(1 for r in self.results if not r.github_links or len(r.github_links) == 0),
            "primary_categories": {},
            "secondary_categories": {},
            "content_types": {},
            "research_stages": {},
            "keywords": {},
            "years": {},
            "diseases": {}  # 新增：疾病统计
        }
        
        for r in self.results:
            # 主分类
            cat = r.primary_category or "未分类"
            stats["primary_categories"][cat] = stats["primary_categories"].get(cat, 0) + 1
            
            # 副分类
            for sc in r.secondary_categories:
                stats["secondary_categories"][sc] = stats["secondary_categories"].get(sc, 0) + 1
            
            # 内容类型
            ct = r.content_type or "未知"
            stats["content_types"][ct] = stats["content_types"].get(ct, 0) + 1
            
            # 研究阶段
            rs = r.research_stage or "未知"
            stats["research_stages"][rs] = stats["research_stages"].get(rs, 0) + 1
            
            # 关键词
            for kw in r.keywords[:5]:
                stats["keywords"][kw] = stats["keywords"].get(kw, 0) + 1
            
            # 年份
            year = r.publication_year or "未知"
            stats["years"][year] = stats["years"].get(year, 0) + 1
            
            # 疾病/病种统计（新增）
            for disease in r.diseases:
                if disease and disease != "未提及":
                    stats["diseases"][disease] = stats["diseases"].get(disease, 0) + 1
        
        return stats
    
    def generate_csv(self):
        """生成CSV报告"""
        rows = []
        for r in self.results:
            row = {
                '文件名': r.file_name,
                '标题': r.title,
                '中文标题': r.title_cn,
                'DOI': r.doi,
                '论文链接': r.paper_link,  # ✅ 新增列
                '作者': '; '.join(r.authors),
                '年份': r.publication_year,
                '期刊/会议': r.journal_conference,
                'DOI': r.doi,
                '主分类': r.primary_category,
                '副分类': '; '.join(r.secondary_categories),
                '内容类型': r.content_type,
                '研究阶段': r.research_stage,
                '关键词': '; '.join(r.keywords),
                '中文关键词': '; '.join(r.keywords_cn),
                '疾病': '; '.join(r.diseases),
                '技术': '; '.join(r.technologies),
                '数据集': '; '.join(r.datasets),
                'GitHub链接': '; '.join(r.github_links),
                '重要性评分': r.importance_score,
                '重要性理由': r.importance_reason,
                '中文摘要': r.abstract_cn,
                '研究目标': r.research_objective,
                '关键发现': '; '.join(r.key_findings),
                '创新点': '; '.join(r.innovations),
                '临床影响': r.clinical_impact,
                '状态': r.status
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(config.CSV_OUTPUT, index=False, encoding='utf-8-sig')
        console.print(f"  [green]✓ CSV: {config.CSV_OUTPUT}[/green]")
    
    def generate_markdown(self):
        """生成Markdown报告"""
        lines = [
            "# 生物学与AI文献分析报告",
            f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n总计分析: {len(self.results)} 篇文献",
            "",
            "---",
            ""
        ]
        
        # 统计信息
        success_count = sum(1 for r in self.results if r.status == "success")
        high_importance = sum(1 for r in self.results if r.importance_score >= 8)
        
        lines.extend([
            "## 📊 统计概览",
            "",
            f"- **成功分析**: {success_count} 篇",
            f"- **高重要性(8-10分)**: {high_importance} 篇",
            ""
        ])
        
        # 分类统计
        categories = {}
        for r in self.results:
            cat = r.primary_category or "未分类"
            categories[cat] = categories.get(cat, 0) + 1
        
        lines.extend([
            "### 主分类分布",
            ""
        ])
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            lines.append(f"- {cat}: {count} 篇")
        
        lines.extend(["", "---", ""])
        
        # 文献详情
        lines.append("## 📚 文献详情")
        lines.append("")
        
        # 按重要性排序
        sorted_results = sorted(self.results, key=lambda x: -x.importance_score)
        
        for i, r in enumerate(sorted_results, 1):
            importance_emoji = "🔴" if r.importance_score >= 8 else ("🟡" if r.importance_score >= 5 else "🟢")
            
            lines.extend([
                f"### {i}. {r.title or r.file_name}",
                "",
                f"**中文标题**: {r.title_cn or '无'}",
                "",
                f"**重要性**: {importance_emoji} {r.importance_score}/10",
                "",
                f"**分类**: {r.primary_category} | {', '.join(r.secondary_categories)}",
                "",
                f"**关键词**: {', '.join(r.keywords)}",
                ""
            ])
            
            if r.abstract_cn:
                lines.extend([
                    "**摘要**:",
                    f"> {r.abstract_cn}",
                    ""
                ])
            
            if r.key_findings:
                lines.append("**关键发现**:")
                for finding in r.key_findings:
                    lines.append(f"- {finding}")
                lines.append("")
            
            if r.innovations:
                lines.append("**创新点**:")
                for inn in r.innovations:
                    lines.append(f"- {inn}")
                lines.append("")
            
            if r.github_links:
                lines.append("**代码链接**:")
                for link in r.github_links:
                    lines.append(f"- [{link}]({link})")
                lines.append("")
            
            lines.extend(["---", ""])
        
        with open(config.MARKDOWN_OUTPUT, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        console.print(f"  [green]✓ Markdown: {config.MARKDOWN_OUTPUT}[/green]")
    
    def generate_html(self):
        """生成HTML交互式报告"""
        # 准备数据
        data = [asdict(r) for r in self.results]
        data_json = json.dumps(data, ensure_ascii=False)
        
        # 统计数据
        stats = self._calculate_stats()
        stats_json = json.dumps(stats, ensure_ascii=False)
        
        html_content = self._get_html_template(data_json, stats_json)
        
        with open(config.HTML_OUTPUT, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        console.print(f"  [green]✓ HTML: {config.HTML_OUTPUT}[/green]")
    
    def _get_html_template(self, data_json: str, stats_json: str) -> str:
        """返回HTML模板（从外部文件加载，带类级缓存）"""
        if ReportGenerator._html_template_cache is None:
            tmpl_path = Path(__file__).parent / "templates" / "report.html"
            ReportGenerator._html_template_cache = tmpl_path.read_text(encoding="utf-8")
        html = ReportGenerator._html_template_cache
        html = html.replace('__PAPERS_DATA__', data_json)
        html = html.replace('__STATS_DATA__', stats_json)
        return html

# ============ 主程序入口 ============
def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="生物学与AI文献批量分析系统")
    parser.add_argument('-i', '--input', type=str, default=str(config.PDF_FOLDER))
    parser.add_argument('-o', '--output', type=str, default=str(config.OUTPUT_FOLDER))
    parser.add_argument('-p', '--provider', type=str, choices=['ollama', 'deepseek', 'agnes', 'openai_compatible'], default=config.LLM_PROVIDER)
    parser.add_argument('--max-pages', type=int, default=config.MAX_PAGES_TO_ANALYZE)
    parser.add_argument('--max-length', type=int, default=config.MAX_TEXT_LENGTH)
    parser.add_argument('--workers', type=int, default=config.MAX_WORKERS)
    args = parser.parse_args()
    # 动态更新配置
    config.PDF_FOLDER = Path(args.input)
    config.OUTPUT_FOLDER = Path(args.output)
    config.LLM_PROVIDER = args.provider
    config.MAX_PAGES_TO_ANALYZE = args.max_pages
    config.MAX_TEXT_LENGTH = args.max_length
    config.MAX_WORKERS = args.workers
    
    config.JSON_OUTPUT = config.OUTPUT_FOLDER / "analysis_results.json"
    config.CSV_OUTPUT = config.OUTPUT_FOLDER / "analysis_results.csv"
    config.MARKDOWN_OUTPUT = config.OUTPUT_FOLDER / "summary_report.md"
    config.HTML_OUTPUT = config.OUTPUT_FOLDER / "interactive_report.html"
    
    config.OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    console.print(Panel.fit(
        f"[bold cyan]生物学与AI文献批量分析系统[/bold cyan]\n"
        f"[dim]服务商: {config.LLM_PROVIDER}[/dim]\n"
        f"[dim]并发数: {config.MAX_WORKERS}[/dim]\n"
        f"[dim]最大长度: {config.MAX_TEXT_LENGTH} chars[/dim]",
        border_style="cyan"
    ))

    
    # 检查PDF文件夹
    if not config.PDF_FOLDER.exists():
        console.print(f"[red]错误: PDF文件夹不存在: {config.PDF_FOLDER}[/red]")
        console.print("[yellow]请使用 -i 参数指定正确的路径，或在 config.py 中修改[/yellow]")
        return

    # 创建分析器并运行 (传入 config.PDF_FOLDER)
    analyzer = PaperBatchAnalyzer(config.PDF_FOLDER)
    results = analyzer.run()

    if results:
        # 生成报告 (传入 config 中的输出路径)
        generator = ReportGenerator(results)
        generator.generate_all()

        # 显示结果摘要
        console.print("\n")
        table = Table(title="分析结果摘要")
        table.add_column("指标", style="cyan")
        table.add_column("数值", style="green")
        success = sum(1 for r in results if r.status == "success")
        high_imp = sum(1 for r in results if r.importance_score >= 8)
        with_github = sum(1 for r in results if r.github_links)
        table.add_row("总文档数", str(len(results)))
        table.add_row("成功分析", str(success))
        table.add_row("高重要性(8-10)", str(high_imp))
        table.add_row("包含GitHub链接", str(with_github))
        console.print(table)
        
        console.print(f"\n[bold green]✅ 分析完成！[/bold green]")
        console.print(f"[cyan]请查看输出文件夹: {config.OUTPUT_FOLDER}[/cyan]")
        console.print(f"[cyan]在浏览器中打开 {config.HTML_OUTPUT} 查看交互式报告[/cyan]")
    else:
        console.print("[yellow]没有成功分析任何文献[/yellow]")

if __name__ == "__main__":
    main()