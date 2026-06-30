# ╭──────────────────────────────────────────────────────╮
# │                                                      │
# │  ██╗  ██╗  ██╗██╗      ████████╗██╗  ██╗             │
# │  ██║  ╚██╗██╔╝██║      ╚══██╔══╝╚██╗██╔╝             │
# │  ██║  ╚███╔╝ ██║         ██║   ╚███╔╝              │
# │  ██║  ██╔██╗ ██║         ██║   ██╔██╗              │
# │  ███████╗██╔╝ ██╗███████╗██║   ██╔╝ ██╗             │
# │  ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝   ╚═╝  ╚═╝             │
# │                                                      │
# │  Author: LXLTX-Lab                                   │
# │  GitHub: https://github.com/lxltx2025                │
# │  Date: 2025-12-23                                    │
# │  License: MIT                                        │
# │                                                      │
# ╰──────────────────────────────────────────────────────╯
""" 配置文件 - 生物学与AI文献分析系统 """

import os
import json
from pathlib import Path

# ── 用户配置覆盖（从 user_config.json 加载，UI 可编辑）──

_USER_CONFIG_PATH = Path(__file__).parent / "user_config.json"

def _load_user_config():
    """加载 user_config.json 并写入 os.environ（TUI/GUI 保存的配置在此生效）"""
    if _USER_CONFIG_PATH.exists():
        try:
            data = json.loads(_USER_CONFIG_PATH.read_text(encoding="utf-8"))
            for key, value in data.items():
                if isinstance(value, str) and value:
                    os.environ[key] = value
        except Exception:
            pass

_load_user_config()

# ============ 路径配置 ============
# PDF文件夹路径（可通过命令行参数 -i 覆盖）
PDF_FOLDER = Path("./pdfs")
# 输出文件夹（可通过命令行参数 -o 覆盖）
OUTPUT_FOLDER = Path("./output")

# ============ LLM 大模型配置 ============
# 提供商类型: ollama / deepseek / agnes / openai_compatible
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "agnes")

# —— 通用生成参数 ——
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "300"))

# —— Ollama 本地模型（LLM_PROVIDER="ollama" 时生效）——
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:26b")

# —— DeepSeek API（LLM_PROVIDER="deepseek" 时生效）——
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-xxx")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

# —— Agnes AI（LLM_PROVIDER="agnes" 时生效）——
AGNES_API_KEY = os.getenv("AGNES_API_KEY", "sk-xxx")
AGNES_BASE_URL = os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")
AGNES_MODEL = os.getenv("AGNES_MODEL", "agnes-2.0-flash")

# —— 通用 OpenAI 兼容接口（LLM_PROVIDER="openai_compatible" 时生效）——
OPENAI_COMPAT_API_KEY = os.getenv("OPENAI_COMPAT_API_KEY", "sk-your-api-key")
OPENAI_COMPAT_BASE_URL = os.getenv("OPENAI_COMPAT_BASE_URL", "https://api.openai.com/v1")
OPENAI_COMPAT_MODEL = os.getenv("OPENAI_COMPAT_MODEL", "gpt-4o")
# MinerU 解析（可选，若不配置则走原有 PDF 文本提取）
MINERU_API_TOKEN = os.getenv("MINERU_API_TOKEN", "")
# 旧版配置保留兼容
REQUEST_TIMEOUT = LLM_TIMEOUT
MAX_RETRIES = 3
RETRY_DELAY = 5

# ============ PDF处理配置 ============
MAX_PAGES_TO_ANALYZE = int(os.getenv("MAX_PAGES_TO_ANALYZE", "100"))
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "300000"))
MIN_TEXT_LENGTH = int(os.getenv("MIN_TEXT_LENGTH", "100"))

# ============ 并发配置 ============
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))

# ============ 分类标签配置 ============
# 根据你的专业领域重新定义主分类（保持稳定，提供顶层框架）
PRIMARY_CATEGORIES = [
    "多组学分析",
    "基因组学与转录组学",
    "结构生物学",
    "光合作用研究",
    "系统发育与进化生物学",
    "大语言模型",
    "AI Agent与多智能体",
    "深度学习方法论",
    "其他"
]

# 副分类（技术与方法）—— 按领域分组，共 23 个
# 【AI 核心架构】深度学习、Transformer、图神经网络、强化学习、多模态学习、联邦学习
# 【生物信息学】RNA-seq、单细胞、蛋白质结构预测、分子动力学、进化树构建、系统发育分析
# 【LLM 应用】Prompt工程、微调技术、智能体编排、可解释AI
# 【基础建设】基准测试、数据集构建、开源工具、综述
# 【交叉与前沿应用 ★ 新增】基因编辑与CRISPR系统、合成生物学与代谢工程、高通量表型与植物AI视觉
SECONDARY_CATEGORIES = [
    # ── AI 核心架构 ──
    "深度学习",
    "Transformer架构",
    "图神经网络",
    "强化学习",
    "多模态学习",
    "联邦学习",
    # ── 生物信息学 ──
    "RNA-seq分析",
    "单细胞分析",
    "蛋白质结构预测",
    "分子动力学",
    "进化树构建",
    "系统发育分析",
    # ── LLM 应用 ──
    "Prompt工程",
    "微调技术",
    "智能体编排",
    "可解释AI",
    # ── 基础建设 ──
    "基准测试",
    "数据集构建",
    "开源工具",
    "综述",
    # ── 交叉与前沿应用 ★ ──
    "基因编辑与CRISPR系统",
    "合成生物学与代谢工程",
    "高通量表型与植物AI视觉",
]

CONTENT_TYPES = [
    "原创研究",
    "综述文章",
    "方法论文",
    "算法开发",
    "技术报告",
    "数据集论文"
]

RESEARCH_STAGES = [
    "基础理论与机制探索",
    "算法与模型设计",
    "实验与数据验证",
    "工具开发与开源",
    "行业应用与落地"
]

# ============ 输出文件名 ============
JSON_OUTPUT = OUTPUT_FOLDER / "analysis_results.json"
CSV_OUTPUT = OUTPUT_FOLDER / "analysis_results.csv"
MARKDOWN_OUTPUT = OUTPUT_FOLDER / "summary_report.md"
HTML_OUTPUT = OUTPUT_FOLDER / "interactive_report.html"
