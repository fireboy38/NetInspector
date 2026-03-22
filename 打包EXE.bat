@echo off
chcp 65001 > nul
title NetInspector - 打包为EXE

echo ============================================
echo   打包 NetInspector 为独立可执行文件
echo ============================================
echo.

pip install pyinstaller -q

pyinstaller --noconfirm --onefile --windowed ^
    --name "NetInspector" ^
    --add-data "config_commands.txt;." ^
    --hidden-import paramiko ^
    --hidden-import openpyxl ^
    --hidden-import PyQt5 ^
    main.py

echo.
echo 打包完成！可执行文件位于 dist\NetInspector.exe
pause
