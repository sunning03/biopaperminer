"""BioPaperMiner — 共享 LLM Prompt 模板"""

from typing import List


def build_analysis_prompt(text: str, github_links: List[str] = None) -> str:
    """构建文献分析 prompt（统一的，供 pipeline 和 analyzer 共用）。

    Args:
        text: 论文全文 / Markdown 文本
        github_links: 可选的 GitHub 链接列表
    """
    from biopaperminer.config import (
        PRIMARY_CATEGORIES, SECONDARY_CATEGORIES,
        CONTENT_TYPES, RESEARCH_STAGES, MAX_TEXT_LENGTH,
    )

    # 截断文本
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH] + "\n...[文本已截断]..."

    primary_opts = "、".join(PRIMARY_CATEGORIES)
    secondary_opts = "、".join(SECONDARY_CATEGORIES)
    content_opts = "、".join(CONTENT_TYPES)
    stage_opts = "、".join(RESEARCH_STAGES)

    github_info = "\n".join(github_links) if github_links else "未找到"

    return f"""你是一位专业的生物学与人工智能交叉领域文献分析专家。请仔细分析以下文献，并以JSON格式输出结构化分析结果。

## 已提取的GitHub链接：
{github_info}

## 论文内容：
{text}

## 分析要求：
请提取并分析以下信息，以严格的JSON格式返回：

```json
{{
"title": "论文英文标题",
"title_cn": "论文中文标题（翻译）",
"authors": ["作者1", "作者2"],
"publication_year": "发表年份",
"journal_conference": "期刊或会议名称",
"doi": "DOI号（如有）",
"abstract": "从论文中提取的原始摘要文本（英文原文，不要修改或重写）",
"abstract_cn": "将上述原始摘要翻译成中文",
"paper_link": "论文链接（优先使用DOI链接，如 https://doi.org/…）",
"research_objective": "研究目标（一句话概括）",
"methodology": "基于论文 Methods 部分的精准且详尽的结构化总结：1) 识别章节内小标题；2) 提取实验样本/材料、设备型号、试剂浓度、关键参数、操作步骤、统计方法；3) 保留原始小标题作为普通文本（不用#），每个小标题下用连字符'-'作为列表符号",
"key_findings": ["关键发现1", "关键发现2", "关键发现3"],
"innovations": ["创新点1", "创新点2"],
"limitations": ["局限性1", "局限性2"],
"future_work": "未来工作方向",
"primary_category": "主分类（从以下选择：{primary_opts}）",
"secondary_categories": ["副分类1", "副分类2"],
"content_type": "内容类型（从以下选择：{content_opts}）",
"research_stage": "研究阶段（从以下选择：{stage_opts}）",
"keywords": ["英文关键词1", "英文关键词2", "英文关键词3", "英文关键词4", "英文关键词5"],
"keywords_cn": ["中文关键词1", "中文关键词2", "中文关键词3"],
"diseases": ["研究对象/物种/靶点1", "研究对象/物种/靶点2"],
"technologies": ["使用技术1", "使用技术2", "使用技术3"],
"datasets": ["使用数据集1", "使用数据集2"],
"metrics": {{"指标名称1": "数值或描述", "指标名称2": "数值或描述"}},
"importance_score": 7,
"importance_reason": "重要性评分理由（考虑创新性、对生物学或AI领域的贡献、方法学突破等）",
"clinical_impact": "领域影响分析（对生物学研究或AI发展的潜在影响，50字以内）",
"potential_applications": ["潜在应用1", "潜在应用2"]
}}
```

## 注意事项：
1. 严格使用JSON格式，确保可以被解析
2. 所有字段都必须填写，如无信息请填"未提及"或空数组[]
3. 重要性评分1-10，其中8-10为高重要性
4. 关键词提取要精准、专业
5. 标签分类要准确匹配预定义选项
6. 只输出JSON，不要有其他解释文字
7. methodology 字段可以包含换行符和列表符号（- 或 *）
8. 不要混入非原文方法信息：只从 Methods 部分抽取
"""
