@echo off
chcp 65001 > nul
echo ========================================
echo  BioPaperMiner - Windows 打包脚本
echo ========================================
echo.

:: 检查 Python
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

:: 安装依赖
echo 📦 安装依赖...
pip install -r requirements.txt
pip install pyinstaller

:: 清理旧构建
echo 🧹 清理旧构建...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: 打包
echo 🔨 开始打包（这可能需要几分钟）...
pyinstaller biopaperminer.spec

:: 检查结果
if %errorlevel% equ 0 (
    echo.
    echo ✅ 打包成功！
    echo 📁 可执行文件: dist\biopaperminer.exe
    echo.
    echo 运行方法:
    echo   dist\biopaperminer tui
    echo   dist\biopaperminer gui
    echo   dist\biopaperminer pipeline --help
) else (
    echo ❌ 打包失败，请检查错误信息
)

pause
