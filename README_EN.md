<div align="center">

# 📚 BioPaperMiner

**Bio Literature Mining System — PubMed Search → PDF Download → MinerU Parse → LLM Analysis → Report Generation**

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

</div>

---

## 📖 Overview

BioPaperMiner is an end-to-end bio-literature mining toolchain that automates the complete workflow from literature retrieval to structured analysis:

```
PubMed Search → PDF Download → MinerU Parse → LLM Analysis → Reports → Smart Rename
```

Three interaction modes:
- **🖥️ CLI** — Command line, ideal for batch processing and scripting
- **📟 TUI** — Terminal UI with interactive menus
- **🪟 GUI** — Graphical interface with mouse-driven visual operation

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **PubMed Search** | Keyword search with date filtering, proxy support |
| 📥 **PDF Download** | Bulk download via 14 sources (Unpaywall, Sci-Hub, PMC, etc.) |
| 📄 **MinerU Parsing** | Convert PDFs to structured Markdown |
| 🧠 **LLM Analysis** | Supports DeepSeek / Agnes / Ollama / OpenAI-compatible APIs |
| 📊 **Reports** | JSON / CSV / Markdown / interactive HTML with charts & filters |
| 🔄 **Resume Support** | Skip completed, retry only failed files |
| ⚡ **Concurrent** | Multi-threaded LLM analysis for faster batch processing |
| 📄 **Reference Extraction** | Extract references from PMC HTML or RIS files |
| 🏷️ **PDF Smart Rename** | Auto-rename PDFs using LLM + journal abbreviation lookup |
| 🖥️ **Cross-platform** | Windows / macOS / Linux — identical functionality |
| 📦 **One-click Build** | Package as single executable via PyInstaller |

---

## 🚀 Quick Start

### Installation

#### Option A: pip install (recommended)

```bash
git clone https://github.com/sunning03/biopaperminer.git
cd biopaperminer
pip install .
biopaperminer pipeline --pdf-dir ./pdfs/ --out ./pdf_analysis_results/
```

#### Option B: Conda environment

```bash
git clone https://github.com/sunning03/biopaperminer.git
cd biopaperminer
conda env create -f environment.yml
conda activate biopaperminer
pip install -e .
biopaperminer tui
```

#### Option C: Download executable

Download from [Releases](https://github.com/sunning03/biopaperminer/releases). Double-click to run.

### API Key Configuration

```bash
export AGNES_API_KEY="sk-your-key"
export MINERU_API_TOKEN="your-mineru-token"
```

| Variable | Description | Required |
|---|---|---|
| `AGNES_API_KEY` | Agnes AI API Key | For Agnes provider |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | For DeepSeek provider |
| `MINERU_API_TOKEN` | MinerU API Token | For PDF parsing |
| `HTTPS_PROXY` | Proxy URL | Restricted networks |

---

## 🖥️ Three Ways to Use

### 1. CLI

```bash
# Pipeline
biopaperminer pipeline --pdf-dir ./pdfs/ --out ./pdf_analysis_results/

# PubMed Search
biopaperminer search "CRISPR" -n 20

# PDF Download
biopaperminer download papers.csv -o ./pdf_download_results/

# Reference Extraction
biopaperminer refs article.html
biopaperminer refs references.ris -o ./refs_output/

# PDF Rename
biopaperminer rename ./pdfs/ -o ./renamed_pdfs/ --dry-run
biopaperminer rename ./pdfs/ -o ./renamed_pdfs/ --copy
```

### 2. TUI

```bash
biopaperminer tui
```

### 3. GUI

```bash
biopaperminer gui
```

---

## 📂 Outputs

### Pipeline Results
```
pdf_analysis_results/
├── analysis_results.json      Structured paper data
├── analysis_results.csv       CSV table
├── summary_report.md          Markdown summary
└── interactive_report.html    Interactive HTML report
```

### PDF Rename Format
```
[FirstAuthor]_[Year]_[JournalAbbr]_[KeywordsEN]_[KeywordsCN].pdf
```
Example: `Smith_2023_Nature_CRISPR-gene_editing_基因编辑.pdf`

### Reference Extraction
```
references_output/
├── references.csv             All references (tab-separated)
└── missing_fields.log         Records missing DOI or title
```

---

## 📦 Build Executable

```bash
pip install pyinstaller

# Windows
scripts\build_windows.bat

# macOS
bash scripts/build_macos.sh
```

Or push a tag to trigger GitHub Actions:
```bash
git tag v2.0.0
git push origin v2.0.0
```

---

## ❓ FAQ

| Problem | Solution |
|---|---|
| PubMed connection timeout | Use `--proxy` or set `HTTPS_PROXY` |
| Emoji display issues | Windows: `chcp 65001` |
| `tkinter not available` (GUI) | Linux: `sudo apt install python3-tk` |
| `biopaperminer: command not found` | Run `pip install .` first |
