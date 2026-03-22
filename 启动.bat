@echo off
chcp 65001 > nul
title NetInspector - 网络设备自动化巡检工具

echo ============================================
echo   NetInspector - 网络设备自动化巡检工具
echo   V1.0.1
echo ============================================
echo.

:: 检查Python是否安装
python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8 或以上版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/2] 正在检查并安装依赖包...
pip install -r requirements.txt -q --no-warn-script-location

echo [2/2] 启动程序...
echo.
python main.py

if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出，请检查错误信息
    pause
)
