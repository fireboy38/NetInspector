#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络设备自动化巡检工具 - NetInspector V1.0.1
支持华为、H3C、Cisco、锐捷等主流厂商交换机
"""

import sys
import os

# 确保依赖可以找到
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from ui.main_window import MainWindow


def main():
    # 设置高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("网络设备自动化巡检")
    app.setApplicationVersion("1.0.0")

    window = MainWindow()
    # 先显示再最大化，确保布局正确计算
    window.show()
    window.showMaximized()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
