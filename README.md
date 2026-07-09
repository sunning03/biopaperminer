<div align="center">

# 📚 BioPaperMiner

**生物文献挖掘系统 — PubMed 检索 → PDF 下载 → MinerU 解析 → LLM 分析 → 报告生成**

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

</div>

---

## 📖 简介

BioPaperMiner 是一个端到端的生物文献挖掘工具链，自动完成从文献检索到结构化分析的全流程：

```
PubMed 检索 → PDF 下载 → MinerU 解析 → LLM 分析 → 报告 → 智能重命名
```

提供三种交互方式：

- **🖥️ CLI** — 命令行，适合批量处理和脚本自动化
- **📟 TUI** — 终端交互菜单，无需记忆命令
- **🪟 GUI** — 图形界面，鼠标操作，可视化运行

---

## ✨ 功能特性

| 特性 | 说明 |
|---|---|
| 🔍 **PubMed 检索** | 按关键词检索，支持日期筛选、代理、API Key |
| 📥 **PDF 下载** | 通过 Unpaywall / Sci-Hub / PMC 等 14 个数据源下载 |
| 📄 **MinerU 解析** | 使用 MinerU API 将 PDF 转为结构化 Markdown |
| 🧠 **LLM 分析** | 支持 DeepSeek / Agnes / Ollama / OpenAI 兼容接口 |
| 📊 **报告生成** | JSON / CSV / Markdown / HTML 交互式报告（含图表、筛选、收藏） |
| 🔄 **断点续传** | 已成功的跳过，只重试失败的，支持 `--retry-failed` |
| ⚡ **并发加速** | 多线程并发 LLM 分析，大幅提升批量处理速度 |
| 📄 **参考文献提取** | 从 PMC HTML 或 RIS 文件中提取参考文献，输出 CSV |
| 🏷️ **PDF 智能重命名** | LLM + 期刊缩写库提取元数据，自动重命名为标准格式 |
| 🖥️ **三端一致** | CLI / TUI / GUI 功能完全对齐 |
| 📦 **一键打包** | 支持 PyInstaller 打包为单文件 exe |

### 智能分类体系

| 维度 | 数量 | 示例 |
|---|---|---|
| 主分类 | 9 个 | 多组学分析、基因组学、光合作用、大语言模型、AI Agent…… |
| 副分类 | 23 个 | 深度学习、Transformer、**基因编辑与CRISPR**、**合成生物学**、**高通量表型**…… |
| 内容类型 | 6 个 | 原创研究、综述、算法开发、数据集论文…… |
| 研究阶段 | 5 个 | 基础理论与机制探索 → 算法与模型设计 → 实验与数据验证 → 工具开发 → 行业落地 |

---

## 🚀 快速开始

### 安装方式

#### 方式 A：pip 安装（推荐）

```bash
git clone https://github.com/sunning03/biopaperminer.git
cd biopaperminer
pip install .
biopaperminer pipeline --pdf-dir ./pdfs/ --out ./pdf_analysis_results/
```

#### 方式 B：Conda 环境

```bash
git clone https://github.com/sunning03/biopaperminer.git
cd biopaperminer
conda env create -f environment.yml
conda activate biopaperminer
pip install -e .
biopaperminer tui
```

#### 方式 C：下载打包好的可执行文件

从 [Releases](https://github.com/sunning03/biopaperminer/releases) 页面下载对应平台的版本，双击即用。

### API Key 配置

```bash
# 环境变量（推荐）
export AGNES_API_KEY="sk-你的Key"
export MINERU_API_TOKEN="你的MinerU令牌"

# 或通过 TUI/GUI 配置：运行后进入配置界面填入
```

| 环境变量 | 说明 | 必需 |
|---|---|---|
| `AGNES_API_KEY` | Agnes AI API Key | 使用 Agnes 时必填 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 使用 DeepSeek 时必填 |
| `MINERU_API_TOKEN` | MinerU API 令牌 | PDF 解析时必填 |
| `HTTPS_PROXY` | 代理地址 | 网络受限环境 |

---

## 🖥️ 三种使用方式

### 方式一：CLI 命令行

```bash
# 全流程分析
biopaperminer pipeline --pdf-dir ./pdfs/ --out ./pdf_analysis_results/

# PubMed 搜索
biopaperminer search "CRISPR" -n 20
biopaperminer search "plant genomics" -n 50 --mindate 2023/01/01

# PDF 下载
biopaperminer download papers.csv -o ./pdf_download_results/

# 参考文献提取
biopaperminer refs article.html
biopaperminer refs references.ris -o ./refs_output/

# PDF 智能重命名
biopaperminer rename ./pdfs/ -o ./renamed_pdfs/ --dry-run  # 预览
biopaperminer rename ./pdfs/ -o ./renamed_pdfs/ --copy     # 复制模式
```

### 方式二：TUI 终端菜单

```bash
biopaperminer tui
```

```
┌──────────────────────────────────────────────┐
│  📚 BioPaperMiner — 生物文献挖掘系统          │
├──────────────────────────────────────────────┤
│  1. 🔍 PubMed 检索                           │
│  2. 📄 提取参考文献                          │
│  3. 📥 PDF 下载                              │
│  4. 🔄 全流程 Pipeline                       │
│  5. 🏷️ PDF 重命名                            │
│  6. 📊 查看报告                              │
│  7. ⚙️  配置                                 │
│  0. 🚪 退出                                  │
└──────────────────────────────────────────────┘
```

### 方式三：GUI 图形界面

```bash
biopaperminer gui
```

7 个功能模块，所有模块日志实时输出，支持停止运行中的任务。

---

## 📂 输出说明

### Pipeline 输出
```
pdf_analysis_results/
├── analysis_results.json      所有文献的结构化数据
├── analysis_results.csv       CSV 表格
├── summary_report.md          Markdown 汇总报告
└── interactive_report.html    HTML 交互式报告
```

### PDF 重命名格式
```
[第一作者]_[年份]_[期刊缩写]_[英文关键词1]-[英文关键词2]_[中文关键词1]-[中文关键词2].pdf
```
示例：`Smith_2023_Nature_CRISPR-gene_editing_基因编辑.pdf`
- 期刊缩写从 `journal_abbr_list.txt` 查询
- 关键词自动包含物种名称
- 支持 `--copy` 复制模式

### 参考文献提取
```
references_output/
├── references.csv             所有参考文献（Tab 分隔）
└── missing_fields.log         缺少 DOI 或标题的记录
```

---

## 🗂️ 项目结构

```
biopaperminer/
├── main.py                      根级入口
├── gui_entry.py                 GUI 入口（双击打开）
├── pyproject.toml               pip 安装配置
├── requirements.txt             pip 依赖列表
├── environment.yml              Conda 环境配置
├── biopaperminer.spec           PyInstaller 打包配置
│
├── biopaperminer/               主包
│   ├── main.py                  CLI 入口
│   ├── config.py                配置（全部参数可通过环境变量覆盖）
│   ├── config_editor.py         配置读写工具（TUI/GUI 共享）
│   ├── models.py                PaperAnalysis 数据模型
│   ├── prompts.py               共享 LLM Prompt 模板
│   ├── session_pool.py          HTTP Session 连接池
│   ├── pdf_extractor.py         PDF 文本提取
│   ├── mineru_client.py         MinerU API 客户端
│   ├── llm_client.py            LLM 统一客户端
│   ├── analyzer.py              分析引擎 + 报告生成
│   ├── pipeline.py              全流程编排（断点续传 + 并发）
│   ├── download_pubmed.py       PubMed 检索
│   ├── download_pdf.py          PDF 批量下载（14 个数据源）
│   ├── extract_references.py    PMC HTML 参考文献提取
│   ├── extract_ris.py           RIS 参考文献提取
│   ├── extract_refs.py          统一参考文献提取入口
│   ├── rename_pdfs.py           PDF 智能重命名
│   ├── journal_abbr_list.txt    期刊缩写查询表
│   ├── tui.py                   TUI 界面
│   ├── gui.py                   GUI 界面
│   └── templates/
│       └── report.html          HTML 报告模板
│
├── scripts/                     构建脚本
│   ├── build_windows.bat
│   └── build_macos.sh
│
└── .github/workflows/
    └── build.yml                GitHub Actions 自动构建
```

---

## ⚙️ 配置说明

所有配置参数**优先读环境变量**，其次读 `user_config.json`，最后用默认值。

```python
# LLM 提供商: agnes / deepseek / ollama / openai_compatible
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "agnes")
AGNES_API_KEY = os.getenv("AGNES_API_KEY", "sk-xxx")
MINERU_API_TOKEN = os.getenv("MINERU_API_TOKEN", "")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
```

---

## 📦 打包为可执行文件

```bash
# 安装 PyInstaller
pip install pyinstaller

# Windows
scripts\build_windows.bat

# macOS
bash scripts/build_macos.sh
```

或推送 tag 触发 GitHub Actions 自动构建：
```bash
git tag v2.0.0
git push origin v2.0.0
```

---

## ❓ 常见问题

| 问题 | 解决 |
|---|---|
| PubMed 连接超时 | `--proxy http://127.0.0.1:7897` 或设 `HTTPS_PROXY` |
| emoji 显示乱码 | Windows 终端运行 `chcp 65001` |
| `tkinter` 不可用 | Linux: `sudo apt install python3-tk` |
| `biopaperminer: command not found` | 运行 `pip install .` |
