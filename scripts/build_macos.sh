#!/bin/bash
# BioPaperMiner - macOS/Linux 打包脚本
set -e

echo "========================================"
echo " BioPaperMiner - macOS/Linux 打包脚本"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装 Python 3.9+"
    exit 1
fi

# 安装依赖
echo "📦 安装依赖..."
pip3 install -r requirements.txt
pip3 install pyinstaller

# 清理旧构建
echo "🧹 清理旧构建..."
rm -rf build dist

# 打包
echo "🔨 开始打包（这可能需要几分钟）..."
pyinstaller biopaperminer.spec

# 检查结果
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 打包成功！"
    echo "📁 可执行文件: dist/biopaperminer"
    echo ""
    echo "运行方法:"
    echo "  ./dist/biopaperminer tui"
    echo "  ./dist/biopaperminer gui"
    echo "  ./dist/biopaperminer pipeline --help"
else
    echo "❌ 打包失败，请检查错误信息"
fi
