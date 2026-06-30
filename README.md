<div align="center">

# 📚 BioPaperMiner

**生物文献挖掘系统 — PubMed 检索 → PDF 下载 → MinerU 解析 → LLM 分析 → 报告生成**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

</div>

---

## 📖 简介

BioPaperMiner 是一个端到端的生物文献挖掘工具链，自动完成从文献检索到结构化分析的全流程：

```
PubMed 检索 → PDF 下载 → MinerU 解析 → LLM 分析 → 报告 (JSON/CSV/MD/HTML)
```

提供三种交互方式：

- **🖥️ CLI** — 命令行，适合批量处理和脚本自动化
- **📟 TUI** — 终端交互菜单，无需记忆命令
- **🪟 GUI** — 图形界面，鼠标操作，可视化运行

适用于生物信息学、基因组学、系统发育学、基因编辑、合成生物学等领域的文献批量分析。

---

## ✨ 功能特性

| 特性 | 说明 |
|---|---|
| 🔍 **PubMed 检索** | 按关键词检索，支持日期筛选、代理、API Key |
| 📥 **PDF 下载** | 通过 Unpaywall / Sci-Hub 等渠道批量下载 |
| 📄 **MinerU 解析** | 使用 MinerU API 将 PDF 转为结构化 Markdown |
| 🧠 **LLM 分析** | 支持 DeepSeek / Agnes / Ollama / OpenAI 兼容接口 |
| 📊 **报告生成** | JSON / CSV / Markdown / HTML 交互式报告（含图表、筛选、收藏） |
| 🔄 **断点续传** | 已成功的跳过，只重试失败的，支持 `--retry-failed` |
| ⚡ **并发加速** | 多线程并发 LLM 分析，大幅提升批量处理速度 |
| 🖥️ **三端一致** | CLI / TUI / GUI 功能完全对齐 |


### 智能分类体系

| 维度 | 数量 | 示例 |
|---|---|---|
| 主分类 | 9 个 | 多组学分析、基因组学、光合作用、大语言模型、AI Agent…… |
| 副分类 | 23 个 | 深度学习、Transformer、**基因编辑与CRISPR**、**合成生物学**、**高通量表型**…… |
| 内容类型 | 6 个 | 原创研究、综述、算法开发、数据集论文…… |
| 研究阶段 | 5 个 | 基础理论与机制探索 → 算法与模型设计 → 实验与数据验证 → 工具开发 → 行业落地 |

---

## 🚀 快速开始

### 前置：API Key 配置

```bash
# 方法一：环境变量（推荐，安全性好）
export AGNES_API_KEY="sk-你的Key"
export MINERU_API_TOKEN="你的MinerU令牌"

# 方法二：运行后通过 TUI/GUI 配置
#   python3 main.py tui → 5 → 填入 → 保存
```

| 环境变量 | 说明 | 必需 |
|---|---|---|
| `AGNES_API_KEY` | Agnes AI API Key | 使用 Agnes 时必填 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 使用 DeepSeek 时必填 |
| `MINERU_API_TOKEN` | MinerU API 令牌 | PDF 解析时必填 |
| `HTTPS_PROXY` | 代理地址（可选） | 网络受限环境 |

### 安装方式

#### 方式 A：pip 安装（推荐，一行命令）

```bash
# 1. 克隆
git clone https://github.com/sunning03/biopaperminer.git
cd biopaperminer

# 2. 安装（自动安装所有依赖 + 注册命令）
pip install .

# 3. 运行（任何目录下可直接使用）
biopaperminer pipeline --pdf-dir ./pdfs/ --out ./results/
```

#### 方式 B：Conda 环境（隔离性好）

```bash
# 1. 克隆
git clone https://github.com/sunning03/biopaperminer.git
cd biopaperminer

# 2. 创建环境
conda env create -f environment.yml
conda activate biopaperminer

# 3. 安装包
pip install -e .

# 4. 运行
biopaperminer tui
```

#### 方式 C：源码直接运行（无需安装）

```bash
pip install -r requirements.txt
python main.py pipeline --pdf-dir ./pdfs/ --out ./results/
```

---

## 🖥️ 三种使用方式

### 方式一：CLI 命令行

```bash
# 查看帮助
biopaperminer --help

# 全流程分析
biopaperminer pipeline --pdf-dir ./pdfs/ --out ./results/
biopaperminer pipeline --pdf-dir ./pdfs/ --out ./results/ --retry-failed
biopaperminer pipeline --pdf-dir ./pdfs/ --out ./results/ --skip-llm

# PubMed 搜索
biopaperminer search "CRISPR gene editing" -n 20
biopaperminer search "plant genomics" -n 50 --mindate 2023/01/01 --maxdate 2024/12/31

# PDF 下载
biopaperminer download papers.csv -o ./pdfs
```

### 方式二：TUI 终端菜单

```bash
biopaperminer tui
```

屏幕菜单：

```
┌──────────────────────────────────────────────┐
│  📚 BioPaperMiner — 生物文献挖掘系统          │
│  PubMed 检索 → PDF → MinerU → LLM → 报告     │
├──────────────────────────────────────────────┤
│                                              │
│  1. 🔍 PubMed 检索                           │
│  2. 📥 PDF 下载                              │
│  3. 🔄 全流程 Pipeline                       │
│  4. 📊 查看报告                              │
│  5. ⚙️  配置                                 │
│  0. 🚪 退出                                  │
│                                              │
└──────────────────────────────────────────────┘
```

TUI 特色：
- 交互式配置编辑（API Key 打码输入，选提供商后只显示相关字段）
- 保存后自动测试 LLM 连通性
- Pipeline 支持跳过 MinerU/LLM、只重试失败

### 方式三：GUI 图形界面

```bash
biopaperminer gui
#如果报错❌ tkinter 不可用，运行
python main.py gui
```

GUI 特色：
- 左侧导航切换功能模块
- 实时日志输出（彩色标记成功/失败/警告）
- 配置界面密码打码 + 👁 切换显隐
- 下拉框选择 LLM 提供商，自动显隐对应字段
- 保存配置后自动测试连接
- 📂 目录选择器带记忆功能（记住上次打开的路径）
- 支持停止正在运行的 Pipeline

---

## 📂 输出报告

```
results/
├── analysis_results.json      合并 JSON（所有文献的结构化数据）
├── analysis_results.csv       CSV 表格（Excel 可直接打开）
├── summary_report.md          Markdown 汇总报告
└── interactive_report.html    HTML 交互式报告
```

**HTML 报告功能：**
- 🔍 全文搜索（标题、关键词、期刊）
- 🏷️ 多维度筛选（主分类、副分类、内容类型、研究阶段、重要性、有无代码）
- ⭐ 收藏标记 + 导出收藏文献（支持 JSON/CSV/MD/HTML）
- 📊 分类饼图 + 关键词云
- 🌗 深色/浅色主题切换
- ⚡ 统计卡片点击快速筛选

---

## 🗂️ 项目结构

```
biopaperminer/
├── main.py                      根级入口
├── pyproject.toml               pip 安装配置
├── requirements.txt             pip 依赖列表
├── environment.yml              Conda 环境配置
├── README.md / README_EN.md     文档
│
├── biopaperminer/               主包
│   ├── __init__.py
│   ├── main.py                  CLI 入口
│   ├── config.py                配置（全部参数可通过环境变量覆盖）
│   ├── config_editor.py         配置读写工具（TUI/GUI 共享）
│   ├── models.py                PaperAnalysis 数据模型
│   ├── prompts.py               共享 LLM Prompt 模板
│   ├── session_pool.py          HTTP Session 连接池
│   ├── pdf_extractor.py         PDF 文本提取（MinerU / PyMuPDF / pdfplumber）
│   ├── mineru_client.py         MinerU API 客户端
│   ├── llm_client.py            LLM 统一客户端（连接池复用）
│   ├── analyzer.py              核心分析引擎（LLM 分析 + 报告生成）
│   ├── pipeline.py              全流程编排（断点续传 + 并发分析）
│   ├── download_pubmed.py       PubMed 检索
│   ├── download_pdf.py          PDF 批量下载（高成功率）
│   ├── tui.py                   TUI 交互式终端界面
│   ├── gui.py                   GUI 图形界面
│   └── templates/
│       └── report.html          HTML 交互式报告模板
│

```

---

## ⚙️ 配置说明

编辑 `biopaperminer/config.py` 或通过 TUI/GUI 修改：

```python
# LLM 提供商: agnes / deepseek / ollama / openai_compatible
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "agnes")

# API Key（优先读环境变量，其次 user_config.json）
AGNES_API_KEY = os.getenv("AGNES_API_KEY", "sk-xxx")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-xxx")

# MinerU
MINERU_API_TOKEN = os.getenv("MINERU_API_TOKEN", "")

# 生成参数
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "300000"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
```

所有配置参数**优先读环境变量**，其次读 `user_config.json`（TUI/GUI 保存的文件），最后用默认值。你不用改 `config.py` 也能通过环境变量或界面配置。

---

## ❓ 常见问题

| 问题 | 解决 |
|---|---|
| PubMed 搜索连接超时 | `--proxy http://127.0.0.1:7897` 或设 `HTTPS_PROXY` |
| MinerU 解析失败 | 检查 Token 是否有效、文件是否超过 200MB/200 页 |
| LLM 返回 "无法解析JSON" | 重试一次（`--retry-failed`）即可 |
| `tkinter` 不可用（GUI 模式） | 先激活虚拟环境再运行 `python main.py gui`；Linux 还需 `sudo apt install python3-tk` |
| `biopaperminer: command not found` | 确保运行了 `pip install .` |
| emoji 显示乱码/报错 | Windows 终端运行 `chcp 65001` 切换 UTF-8，或直接用 `biopaperminer tui`（Rich 自动处理） |

---

## 📄 许可证

[MIT License](LICENSE)
