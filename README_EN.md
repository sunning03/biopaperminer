<div align="center">

# 📚 BioPaperMiner

**Bio Literature Mining System — PubMed Search → PDF Download → MinerU Parse → LLM Analysis → Report Generation**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

</div>

---

## 📖 Overview

BioPaperMiner is an end-to-end bio-literature mining toolchain that automates the complete workflow from literature retrieval to structured analysis:

```
PubMed Search → PDF Download → MinerU Parse → LLM Analysis → Reports (JSON/CSV/MD/HTML)
```

Three interaction modes available:

- **🖥️ CLI** — Command line, ideal for batch processing and scripting
- **📟 TUI** — Terminal UI with interactive menus, no commands to memorize
- **🪟 GUI** — Graphical interface with mouse-driven visual operation

Designed for bioinformatics, genomics, phylogenetics, gene editing, synthetic biology, and related fields requiring batch literature analysis.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **PubMed Search** | Keyword search with date filtering, proxy support, API Key |
| 📥 **PDF Download** | Bulk download via Unpaywall / Sci-Hub and other sources |
| 📄 **MinerU Parsing** | Convert PDFs to structured Markdown via MinerU API |
| 🧠 **LLM Analysis** | Supports DeepSeek / Agnes / Ollama / OpenAI-compatible APIs |
| 📊 **Reports** | JSON / CSV / Markdown / interactive HTML (charts, filters, favorites) |
| 🔄 **Resume Support** | Skip completed, retry only failed files (`--retry-failed`) |
| ⚡ **Concurrent** | Multi-threaded LLM analysis for faster batch processing |
| 🖥️ **Cross-platform** | Windows / macOS / Linux — identical functionality |


### Classification System

| Dimension | Count | Examples |
|---|---|---|
| Primary Categories | 9 | Multi-omics, Genomics, Photosynthesis, LLM, AI Agent… |
| Secondary Categories | 23 | Deep Learning, Transformer, **CRISPR**, **Synthetic Biology**, **High-throughput Phenotyping**… |
| Content Types | 6 | Original Research, Review, Algorithm, Dataset… |
| Research Stages | 5 | Theory → Algorithm → Experiment → Tool → Application |

---

## 🚀 Quick Start

### Prerequisites: API Keys

```bash
# Via environment variables
export AGNES_API_KEY="sk-your-key"
export MINERU_API_TOKEN="your-mineru-token"

# Or configure through TUI/GUI after running:
#   biopaperminer tui → option 5 → fill in → save
```

| Variable | Description | Required |
|---|---|---|
| `AGNES_API_KEY` | Agnes AI API Key | For Agnes provider |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | For DeepSeek provider |
| `MINERU_API_TOKEN` | MinerU API Token | For PDF parsing |
| `HTTPS_PROXY` | Proxy URL (optional) | Restricted networks |

### Installation

#### Option A: pip install (recommended, one-liner)

```bash
git clone https://github.com/sunning03/biopaperminer.git
cd biopaperminer
pip install .                          # installs deps + registers command
biopaperminer pipeline --pdf-dir ./pdfs/ --out ./results/
```

#### Option B: Conda environment (isolated)

```bash
git clone https://github.com/sunning03/biopaperminer.git
cd biopaperminer
conda env create -f environment.yml
conda activate biopaperminer
pip install -e .
biopaperminer tui
```

#### Option C: Run from source (no install)

```bash
pip install -r requirements.txt
python main.py pipeline --pdf-dir ./pdfs/ --out ./results/
```

---

## 🖥️ Three Ways to Use

### 1. CLI

```bash
biopaperminer --help
biopaperminer pipeline --pdf-dir ./pdfs/ --out ./results/
biopaperminer pipeline --pdf-dir ./pdfs/ --out ./results/ --retry-failed
biopaperminer search "CRISPR gene editing" -n 20
biopaperminer search "plant genomics" -n 50 --mindate 2023/01/01
biopaperminer download papers.csv -o ./pdfs
```

### 2. TUI (Terminal UI)

```bash
biopaperminer tui
```

```
┌──────────────────────────────────────────────┐
│  📚 BioPaperMiner — Bio Literature Mining     │
│  PubMed → PDF → MinerU → LLM → Report        │
├──────────────────────────────────────────────┤
│  1. 🔍 PubMed Search                         │
│  2. 📥 PDF Download                          │
│  3. 🔄 Pipeline (Full Flow)                  │
│  4. 📊 View Reports                          │
│  5. ⚙️  Configuration                        │
│  0. 🚪 Exit                                  │
└──────────────────────────────────────────────┘
```

TUI Highlights:
- Interactive config editor with masked API keys and dynamic field visibility
- Connection test after saving configuration
- Pipeline skip options and retry control

### 3. GUI (Graphical Interface)

```bash
biopaperminer gui
```

GUI Highlights:
- Left navigation panel for switching modules
- Real-time color-coded log output
- Password masking with 👁 toggle for API Keys
- Provider dropdown with dynamic field show/hide
- Auto connection test on config save
- Directory browser with last-used-path memory
- Stop running pipeline with one click

---

## 📂 Output Reports

```
results/
├── analysis_results.json      Combined JSON (all papers' structured data)
├── analysis_results.csv       CSV table (open directly in Excel)
├── summary_report.md          Markdown summary
└── interactive_report.html    Interactive HTML report
```

**HTML Report Features:**
- 🔍 Full-text search (title, keywords, journal)
- 🏷️ Multi-dimensional filtering (category, type, stage, importance, code availability)
- ⭐ Bookmark papers + export favorites (JSON/CSV/MD/HTML)
- 📊 Category pie chart + keyword cloud
- 🌗 Dark/Light theme toggle
- ⚡ Click stats cards to quickly filter

---

## 🗂️ Project Structure

```
biopaperminer/
├── main.py                      Root entry
├── pyproject.toml               pip install config
├── requirements.txt             pip dependencies
├── environment.yml              Conda environment
├── README.md / README_EN.md     Documentation
│
├── biopaperminer/               Main package
│   ├── __init__.py
│   ├── main.py                  CLI entry
│   ├── config.py                Configuration (all params overridable via env)
│   ├── config_editor.py         Config read/write (shared by TUI/GUI)
│   ├── models.py                PaperAnalysis data model
│   ├── prompts.py               Shared LLM prompt templates
│   ├── session_pool.py          HTTP Session connection pool
│   ├── pdf_extractor.py         PDF text extraction
│   ├── mineru_client.py         MinerU API client
│   ├── llm_client.py            Unified LLM client (connection pool)
│   ├── analyzer.py              Analysis engine + report generation
│   ├── pipeline.py              Pipeline orchestration (resume + concurrent)
│   ├── download_pubmed.py       PubMed search
│   ├── download_pdf.py          PDF bulk download
│   ├── tui.py                   TUI interface
│   ├── gui.py                   GUI interface
│   └── templates/
│       └── report.html          HTML report template
│

```

---

## ⚙️ Configuration

All configuration parameters can be set via **environment variables** (highest priority), **`user_config.json`** (saved by TUI/GUI), or **`config.py`** (fallback defaults):

```python
# Provider: agnes / deepseek / ollama / openai_compatible
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "agnes")

# API Keys (read from env, then user_config.json)
AGNES_API_KEY = os.getenv("AGNES_API_KEY", "sk-xxx")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-xxx")
MINERU_API_TOKEN = os.getenv("MINERU_API_TOKEN", "")

# Parameters
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "300000"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
```

---

## ❓ FAQ

| Problem | Solution |
|---|---|
| PubMed connection timeout | Use `--proxy http://127.0.0.1:7897` or set `HTTPS_PROXY` |
| MinerU parse failure | Check token validity; file must be <200MB / <200 pages |
| LLM returns unparseable JSON | Retry once (`--retry-failed`) |
| `tkinter not available` (GUI) | Activate your virtual env first, then run `python main.py gui`; on Linux also `sudo apt install python3-tk` |
| `biopaperminer: command not found` | Run `pip install .` first |
| Chinese character display issues | Windows terminal: `chcp 65001` |

---

## 📄 License

[MIT License](LICENSE)
