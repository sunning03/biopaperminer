"""BioPaperMiner — 论文分析数据模型"""

from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class PaperAnalysis:
    """论文分析结果数据模型"""
    # 基本信息
    file_name: str
    file_path: str
    file_hash: str
    analysis_time: str

    # 结构化摘要
    title: str = ""
    title_cn: str = ""  # 中文标题
    authors: List[str] = field(default_factory=list)
    publication_year: str = ""
    journal_conference: str = ""
    doi: str = ""

    # 摘要与核心内容
    abstract: str = ""           # 原文摘要（英文原文）
    abstract_cn: str = ""        # 中文摘要（原文摘要的翻译）
    paper_link: str = ""         # 论文链接 (优先DOI链接)
    research_objective: str = ""  # 研究目标
    methodology: str = ""        # 方法论
    key_findings: List[str] = field(default_factory=list)  # 关键发现
    innovations: List[str] = field(default_factory=list)   # 创新点
    limitations: List[str] = field(default_factory=list)   # 局限性
    future_work: str = ""        # 未来工作

    # 标准化标签
    primary_category: str = ""   # 主分类
    secondary_categories: List[str] = field(default_factory=list)  # 副分类
    content_type: str = ""       # 内容类型
    research_stage: str = ""     # 研究阶段

    # 核心关键词
    keywords: List[str] = field(default_factory=list)      # 英文关键词
    keywords_cn: List[str] = field(default_factory=list)   # 中文关键词

    # 实体信息
    diseases: List[str] = field(default_factory=list)       # 涉及疾病/物种
    technologies: List[str] = field(default_factory=list)   # 使用技术
    datasets: List[str] = field(default_factory=list)       # 使用数据集
    metrics: Dict[str, str] = field(default_factory=dict)   # 性能指标

    # 代码与资源链接
    github_links: List[str] = field(default_factory=list)
    other_links: List[str] = field(default_factory=list)

    # 评估信息
    importance_score: int = 5          # 1-10 重要性评分
    importance_reason: str = ""        # 评分理由

    # 影响与应用
    clinical_impact: str = ""          # 领域影响
    potential_applications: List[str] = field(default_factory=list)

    # 处理状态
    status: str = "success"            # success, error, partial
    error_message: str = ""
    raw_text_length: int = 0
