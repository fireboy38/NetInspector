#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口 - NetInspector 网络设备自动化巡检工具
现代化界面：侧边栏导航 + 内容区
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QFileDialog, QMessageBox, QSplitter, QFrame, QProgressBar,
    QAction, QToolBar, QStatusBar, QAbstractItemView, QCheckBox,
    QScrollArea, QSizePolicy, QStackedWidget, QListWidget, QListWidgetItem,
    QListView, QDesktopWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QRect
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QTextCursor, QBrush, QPainter, QLinearGradient

from core.inspector import InspectionEngine, DeviceInfo
from utils.excel_parser import parse_excel, generate_template
from utils.snapshot_manager import SnapshotManager
from ui.dialogs import CommandEditorDialog, TimerDialog, AboutDialog, AddDeviceDialog, AiConfigDialog, ReportCustomDialog
from ui.dialogs_snapshot import SnapshotManagerDialog, SnapshotCompareDialog

logger = logging.getLogger(__name__)


# ─── 信号中继（线程安全） ─────────────────────────────────────────────
class InspectionSignals(QThread):
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int)
    task_done_signal = pyqtSignal(str, str)
    all_done_signal = pyqtSignal(int, int)

    def run(self):
        pass


# ─── 颜色常量 ─────────────────────────────────────────────────────────
COLORS = {
    'sidebar_bg': '#0F172A',
    'sidebar_selected': '#1E40AF',
    'sidebar_hover': '#1E3A5F',
    'sidebar_text': '#E2E8F0',
    'sidebar_text_dim': '#94A3B8',
    'main_bg': '#F1F5F9',
    'card_bg': '#FFFFFF',
    'primary': '#3B82F6',
    'primary_hover': '#2563EB',
    'success': '#10B981',
    'warning': '#F59E0B',
    'danger': '#EF4444',
    'text_primary': '#1E293B',
    'text_secondary': '#64748B',
    'border': '#E2E8F0',
    'log_bg': '#0F172A',
    'log_text': '#10B981',
}


class ModernButton(QPushButton):
    """现代化按钮"""
    def __init__(self, text, icon=None, color='primary', parent=None):
        super().__init__(text, parent)
        self.color_type = color
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style()

    def _apply_style(self):
        colors = {
            'primary': (COLORS['primary'], COLORS['primary_hover']),
            'success': ('#10B981', '#059669'),
            'danger': ('#EF4444', '#DC2626'),
            'secondary': ('#64748B', '#475569'),
            'outline': ('transparent', '#F1F5F9'),
        }
        bg, bg_hover = colors.get(self.color_type, colors['primary'])

        if self.color_type == 'outline':
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {bg};
                    color: {COLORS['text_primary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: {bg_hover};
                    border-color: {COLORS['primary']};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {bg};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background: {bg_hover};
                }}
                QPushButton:disabled {{
                    background: #CBD5E1;
                    color: #94A3B8;
                }}
            """)


class NavigationItem(QWidget):
    """导航项组件"""
    clicked = pyqtSignal(str)

    def __init__(self, icon_text, label, page_id, parent=None):
        super().__init__(parent)
        self.page_id = page_id
        self.icon_text = icon_text
        self.label_text = label
        self.is_selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        self.icon_label = QLabel(self.icon_text)
        self.icon_label.setFont(QFont("Segoe UI Emoji", 14))
        self.icon_label.setFixedWidth(24)
        layout.addWidget(self.icon_label)

        self.text_label = QLabel(self.label_text)
        self.text_label.setFont(QFont("Segoe UI", 13))
        layout.addWidget(self.text_label)
        layout.addStretch()

    def set_selected(self, selected):
        self.is_selected = selected
        self.update_style()

    def update_style(self):
        if self.is_selected:
            self.setStyleSheet(f"""
                NavigationItem {{
                    background: {COLORS['sidebar_selected']};
                    border-left: 3px solid {COLORS['primary']};
                }}
                QLabel {{
                    color: white;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                NavigationItem {{
                    background: transparent;
                }}
                NavigationItem:hover {{
                    background: {COLORS['sidebar_hover']};
                }}
                QLabel {{
                    color: {COLORS['sidebar_text']};
                }}
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.page_id)


class Sidebar(QWidget):
    """侧边栏"""
    page_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 'dashboard'
        self.nav_items = {}
        self._init_ui()
        self._populate_nav()
        self._select_page('dashboard')

    def _init_ui(self):
        self.setFixedWidth(220)
        self.setStyleSheet(f"""
            QWidget {{
                background: {COLORS['sidebar_bg']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo区域
        logo_frame = QFrame()
        logo_frame.setFixedHeight(64)
        logo_frame.setStyleSheet(f"""
            background: {COLORS['sidebar_bg']};
            border-bottom: 1px solid rgba(255,255,255,0.1);
        """)
        logo_layout = QHBoxLayout(logo_frame)
        logo_layout.setContentsMargins(16, 0, 16, 0)

        logo_label = QLabel("NetInspector")
        logo_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        logo_label.setStyleSheet("color: white;")
        logo_layout.addWidget(logo_label)

        logo_layout.addStretch()
        version_label = QLabel("v1.0")
        version_label.setFont(QFont("Segoe UI", 10))
        version_label.setStyleSheet(f"color: {COLORS['sidebar_text_dim']};")
        logo_layout.addWidget(version_label)

        layout.addWidget(logo_frame)

        # 导航列表
        self.nav_container = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_container)
        self.nav_layout.setContentsMargins(0, 8, 0, 8)
        self.nav_layout.setSpacing(2)
        layout.addWidget(self.nav_container, 1)

        # 底部信息
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet(f"""
            border-top: 1px solid rgba(255,255,255,0.1);
        """)
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(16, 12, 16, 12)

        status_label = QLabel("就绪")
        status_label.setFont(QFont("Segoe UI", 11))
        status_label.setStyleSheet(f"color: {COLORS['sidebar_text_dim']};")
        bottom_layout.addWidget(status_label)

        layout.addWidget(bottom_frame)

    def _populate_nav(self):
        nav_items = [
            ("dashboard", "仪表盘"),
            ("devices", "设备管理"),
            ("inspection", "巡检任务"),
            ("schedule", "定时设置"),
            ("snapshot", "快照管理"),
            ("ai", "AI 配置"),
            ("report", "报表定制"),
            ("about", "关于"),
        ]

        for page_id, label in nav_items:
            item = NavigationItem("", label, page_id)
            item.clicked.connect(self._on_item_clicked)
            self.nav_layout.addWidget(item)
            self.nav_items[page_id] = item

    def _on_item_clicked(self, page_id):
        self._select_page(page_id)
        self.page_changed.emit(page_id)

    def _select_page(self, page_id):
        self.current_page = page_id
        for pid, item in self.nav_items.items():
            item.set_selected(pid == page_id)


class StatusBar(QWidget):
    """自定义状态栏"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setFixedHeight(32)
        self.setStyleSheet(f"""
            background: {COLORS['card_bg']};
            border-top: 1px solid {COLORS['border']};
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)

        self.status_label = QLabel("就绪")
        self.status_label.setFont(QFont("Segoe UI", 11))
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")

        self.progress_label = QLabel("")
        self.progress_label.setFont(QFont("Segoe UI", 11))
        self.progress_label.setStyleSheet(f"color: {COLORS['text_secondary']};")

        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.progress_label)

    def set_status(self, text):
        self.status_label.setText(text)

    def set_progress(self, text):
        self.progress_label.setText(text)


class PageDashboard(QWidget):
    """仪表盘页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"background: {COLORS['main_bg']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # 标题
        title = QLabel("仪表盘")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title)

        # 统计卡片
        stats_layout = QHBoxLayout()

        self.card_devices = self._create_stat_card("设备总数", "0", COLORS['primary'])
        self.card_online = self._create_stat_card("在线设备", "0", COLORS['success'])
        self.card_tasks = self._create_stat_card("巡检任务", "0", COLORS['warning'])
        self.card_alerts = self._create_stat_card("异常告警", "0", COLORS['danger'])

        stats_layout.addWidget(self.card_devices)
        stats_layout.addWidget(self.card_online)
        stats_layout.addWidget(self.card_tasks)
        stats_layout.addWidget(self.card_alerts)
        layout.addLayout(stats_layout)

        # 最近巡检记录
        recent_frame = self._create_card("最近巡检记录")
        recent_layout = QVBoxLayout(recent_frame)

        self.recent_list = QTextEdit()
        self.recent_list.setReadOnly(True)
        self.recent_list.setFont(QFont("JetBrains Mono", 10))
        self.recent_list.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['main_bg']};
                border: none;
                color: {COLORS['text_primary']};
            }}
        """)
        recent_layout.addWidget(self.recent_list)
        layout.addWidget(recent_frame, 1)

    def _create_stat_card(self, title, value, color):
        card = QFrame()
        card.setFixedHeight(100)
        card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['card_bg']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 12))
        title_label.setStyleSheet(f"color: {COLORS['text_secondary']};")

        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 28, QFont.Bold))
        value_label.setStyleSheet(f"color: {color};")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addStretch()

        return card

    def _create_card(self, title):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['card_bg']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title_label)

        return card

    def update_stats(self, devices=0, online=0, tasks=0, alerts=0):
        self._update_card_value(self.card_devices, str(devices))
        self._update_card_value(self.card_online, str(online))
        self._update_card_value(self.card_tasks, str(tasks))
        self._update_card_value(self.card_alerts, str(alerts))

    def _update_card_value(self, card, value):
        # 找到第二个子widget的value label
        layout = card.layout()
        if layout.count() >= 2:
            value_label = layout.itemAt(1).widget()
            if value_label:
                value_label.setText(value)


class PageDevices(QWidget):
    """设备管理页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"background: {COLORS['main_bg']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题栏
        header = QHBoxLayout()
        title = QLabel("设备管理")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header.addWidget(title)
        header.addStretch()

        self.btn_import = ModernButton("导入设备", color='primary')
        self.btn_add = ModernButton("添加设备", color='outline')
        self.btn_delete = ModernButton("删除选中", color='danger')
        self.btn_clear = ModernButton("清空列表", color='secondary')

        header.addWidget(self.btn_import)
        header.addWidget(self.btn_add)
        header.addWidget(self.btn_delete)
        header.addWidget(self.btn_clear)

        layout.addLayout(header)

        # 设备表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(['设备名称', '设备类型', 'IP地址', '端口', '连接类型', '用户名', '密码', '状态'])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {COLORS['card_bg']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                gridline-color: {COLORS['border']};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QHeaderView::section {{
                background: {COLORS['sidebar_bg']};
                color: white;
                padding: 10px;
                font-weight: 600;
                border: none;
            }}
            QTableWidget::item:selected {{
                background: {COLORS['primary']};
                color: white;
            }}
        """)
        layout.addWidget(self.table, 1)

    def get_table(self):
        return self.table


class PageInspection(QWidget):
    """巡检任务页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"background: {COLORS['main_bg']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题栏
        header = QHBoxLayout()
        title = QLabel("巡检任务")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header.addWidget(title)
        header.addStretch()

        layout.addLayout(header)

        # 配置卡片
        config_card = QFrame()
        config_card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['card_bg']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
                padding: 20px;
            }}
        """)
        config_layout = QGridLayout(config_card)

        # 项目名称
        config_layout.addWidget(QLabel("项目名称:"), 0, 0)
        self.edit_project = QLineEdit()
        self.edit_project.setPlaceholderText("请输入项目名称")
        self.edit_project.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px 12px;
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
            }}
        """)
        config_layout.addWidget(self.edit_project, 0, 1)

        # 输出格式
        config_layout.addWidget(QLabel("输出格式:"), 0, 2)
        self.combo_format = QComboBox()
        self.combo_format.addItems(["HTML", "TXT"])
        self.combo_format.setStyleSheet(f"""
            QComboBox {{
                padding: 8px 12px;
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
        """)
        config_layout.addWidget(self.combo_format, 0, 3)

        # 并发线程
        config_layout.addWidget(QLabel("并发线程:"), 1, 0)
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 50)
        self.spin_threads.setValue(10)
        self.spin_threads.setStyleSheet(f"""
            QSpinBox {{
                padding: 8px 12px;
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
        """)
        config_layout.addWidget(self.spin_threads, 1, 1)

        # 保存目录
        config_layout.addWidget(QLabel("保存目录:"), 2, 0)
        self.edit_output_dir = QLineEdit()
        self.edit_output_dir.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px 12px;
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
        """)
        config_layout.addWidget(self.edit_output_dir, 2, 1, 1, 3)

        config_layout.setColumnStretch(1, 1)
        config_layout.setColumnStretch(3, 1)
        config_layout.setHorizontalSpacing(16)
        config_layout.setVerticalSpacing(12)

        layout.addWidget(config_card)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_start = ModernButton("开始巡检", color='success')
        self.btn_stop = ModernButton("停止巡检", color='danger')
        self.btn_stop.setEnabled(False)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {COLORS['border']};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: {COLORS['primary']};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        # 日志面板
        log_card = QFrame()
        log_card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['card_bg']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        log_layout = QVBoxLayout(log_card)

        log_title = QLabel("执行日志")
        log_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        log_title.setStyleSheet(f"color: {COLORS['text_primary']}; padding: 12px 16px 0;")
        log_layout.addWidget(log_title)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("JetBrains Mono", 10))
        self.log_view.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['log_bg']};
                color: {COLORS['log_text']};
                border: none;
                border-radius: 0 0 12px 12px;
                padding: 12px;
                font-size: 12px;
            }}
        """)
        log_layout.addWidget(self.log_view, 1)

        layout.addWidget(log_card, 1)


class PageSchedule(QWidget):
    """定时设置页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"background: {COLORS['main_bg']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("定时设置")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title)

        # 定时配置卡片
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['card_bg']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
                padding: 24px;
            }}
        """)
        card_layout = QVBoxLayout(card)

        self.chk_timer = QCheckBox("启用定时巡检")
        self.chk_timer.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.chk_timer.setStyleSheet(f"""
            QCheckBox {{
                spacing: 10px;
                color: {COLORS['text_primary']};
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid {COLORS['border']};
            }}
            QCheckBox::indicator:checked {{
                background: {COLORS['primary']};
                border-color: {COLORS['primary']};
            }}
        """)

        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("执行时间:"))
        self.time_edit = QComboBox()
        for h in range(24):
            self.time_edit.addItem(f"{h:02d}:00")
        self.time_edit.setCurrentText("22:00")
        self.time_edit.setStyleSheet(f"""
            QComboBox {{
                padding: 8px 12px;
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
        """)
        time_layout.addWidget(self.time_edit)
        time_layout.addStretch()

        self.btn_save_timer = ModernButton("保存设置", color='primary')

        card_layout.addWidget(self.chk_timer)
        card_layout.addLayout(time_layout)
        card_layout.addWidget(self.btn_save_timer)
        card_layout.addStretch()

        layout.addWidget(card)


class PageAbout(QWidget):
    """关于页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"background: {COLORS['main_bg']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("关于")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['card_bg']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(16)

        card_layout.addWidget(QLabel("NetInspector"))
        desc = QLabel("网络设备自动化巡检工具\n\n版本: 1.0.1\n\n面向 IT 运维人员的专业网络设备巡检解决方案，支持多厂商设备批量巡检、定时任务、配置快照对比和 AI 智能分析。")
        desc.setFont(QFont("Segoe UI", 12))
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; line-height: 180%;")
        card_layout.addWidget(desc)
        card_layout.addStretch()

        layout.addWidget(card, 1)


class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.engine = InspectionEngine()
        self.signals = InspectionSignals()
        self.devices = []
        self.commands_map = {}
        self.is_running = False
        self.output_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'NetInspector', '巡检结果')
        self.snapshot_manager = SnapshotManager()

        self._load_commands()
        self._init_ui()
        self._connect_signals()
        self._append_log('INFO', '四川新数网络设备巡检系统 已启动')

    def _load_commands(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg = os.path.join(base, 'config_commands.txt')
        self.commands_file = cfg
        if os.path.exists(cfg):
            self._parse_commands_file(cfg)

    def _parse_commands_file(self, path: str):
        self.commands_map = {}
        current_platform = 'default'
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    current_platform = line[1:-1].lower()
                    self.commands_map.setdefault(current_platform, [])
                else:
                    self.commands_map.setdefault(current_platform, []).append(line)

    def _init_ui(self):
        self.setWindowTitle("NetInspector - 网络设备巡检系统")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)

        # 居中显示
        screen = QDesktopWidget().screenGeometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 侧边栏
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._on_page_changed)
        main_layout.addWidget(self.sidebar)

        # 内容区
        content = QWidget()
        content.setStyleSheet(f"background: {COLORS['main_bg']};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 页面堆栈
        self.pages = QStackedWidget()
        self.page_dashboard = PageDashboard()
        self.page_devices = PageDevices()
        self.page_inspection = PageInspection()
        self.page_schedule = PageSchedule()
        self.page_about = PageAbout()

        self.pages.addWidget(self.page_dashboard)
        self.pages.addWidget(self.page_devices)
        self.pages.addWidget(self.page_inspection)
        self.pages.addWidget(self.page_schedule)
        self.pages.addWidget(self.page_about)

        content_layout.addWidget(self.pages, 1)

        # 状态栏
        self.status_bar = StatusBar()
        content_layout.addWidget(self.status_bar)

        main_layout.addWidget(content, 1)

        # 连接设备页面按钮
        self.page_devices.btn_import.clicked.connect(self._import_devices)
        self.page_devices.btn_add.clicked.connect(self._add_device_manually)
        self.page_devices.btn_delete.clicked.connect(self._delete_selected)
        self.page_devices.btn_clear.clicked.connect(self._clear_devices)

        # 连接巡检页面按钮
        self.page_inspection.btn_start.clicked.connect(self._start_inspection)
        self.page_inspection.btn_stop.clicked.connect(self._stop_inspection)
        self.page_inspection.edit_output_dir.setText(self.output_dir)

        # 连接定时设置按钮
        self.page_schedule.btn_save_timer.clicked.connect(self._save_timer_settings)

        # 更新仪表盘
        self._update_dashboard()

    def _on_page_changed(self, page_id):
        page_map = {
            'dashboard': 0,
            'devices': 1,
            'inspection': 2,
            'schedule': 3,
            'about': 4,
        }
        self.pages.setCurrentIndex(page_map.get(page_id, 0))

        if page_id == 'dashboard':
            self._update_dashboard()

    def _update_dashboard(self):
        device_count = self.page_devices.table.rowCount()
        self.page_dashboard.update_stats(
            devices=device_count,
            online=0,
            tasks=0,
            alerts=0
        )

    def _connect_signals(self):
        self.signals.log_signal.connect(self._on_log)
        self.signals.progress_signal.connect(self._on_progress)
        self.signals.task_done_signal.connect(self._on_task_done)
        self.signals.all_done_signal.connect(self._on_all_done)

        self.engine.on_log = lambda level, msg: self.signals.log_signal.emit(level, msg)
        self.engine.on_progress = lambda c, t: self.signals.progress_signal.emit(c, t)
        self.engine.on_task_done = lambda task: self.signals.task_done_signal.emit(
            task.device.host, task.status)
        self.engine.on_all_done = lambda s, f: self.signals.all_done_signal.emit(s, f)

    def _on_log(self, level: str, msg: str):
        color_map = {
            'INFO': '#10B981',
            'DEBUG': '#60A5FA',
            'ERROR': '#F87171',
            'WARNING': '#FBBF24',
            'WARN': '#FBBF24',
        }
        color = color_map.get(level.upper(), '#10B981')
        ts = datetime.now().strftime('%H:%M:%S')
        html = f'<span style="color:#64748B;">[{ts}]</span> <span style="color:{color};font-weight:bold;">[{level}]</span> <span style="color:#E2E8F0;">{msg}</span>'
        self.page_inspection.log_view.append(html)

    def _on_progress(self, completed: int, total: int):
        self.page_inspection.progress_bar.setMaximum(total)
        self.page_inspection.progress_bar.setValue(completed)
        self.status_bar.set_progress(f"进度: {completed}/{total}")

    def _on_task_done(self, host: str, status: str):
        table = self.page_devices.table
        for row in range(table.rowCount()):
            item_ip = table.item(row, 2)
            if item_ip and item_ip.text() == host:
                status_item = QTableWidgetItem()
                if status == 'success':
                    status_item.setText('成功')
                    status_item.setForeground(QColor(COLORS['success']))
                elif status == 'failed':
                    status_item.setText('失败')
                    status_item.setForeground(QColor(COLORS['danger']))
                else:
                    status_item.setText('取消')
                    status_item.setForeground(QColor(COLORS['warning']))
                status_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 7, status_item)
                break

    def _on_all_done(self, success: int, failed: int):
        self.is_running = False
        self.page_inspection.btn_start.setEnabled(True)
        self.page_inspection.btn_stop.setEnabled(False)
        self.page_inspection.progress_bar.setVisible(False)
        self.status_bar.set_progress("")
        self._append_log('INFO', f'巡检完成 - 成功: {success}, 失败: {failed}')

        msg = QMessageBox(self)
        msg.setWindowTitle("巡检完成")
        msg.setText(f"巡检任务已完成！\n\n成功: {success} 台\n失败: {failed} 台")
        msg.setIcon(QMessageBox.Information)
        msg.addButton("确定", QMessageBox.AcceptRole)
        msg.exec_()

    def _append_log(self, level: str, msg: str):
        self.signals.log_signal.emit(level, msg)

    def _import_devices(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择设备清单文件", "",
            "Excel/CSV文件 (*.xlsx *.xls *.csv);;所有文件 (*)"
        )
        if not path:
            return
        try:
            devices = parse_excel(path)
            if not devices:
                QMessageBox.warning(self, "提示", "未能从文件中解析到任何设备信息")
                return
            self._load_devices_to_table(devices)
            self._append_log('INFO', f"成功导入 {len(devices)} 台设备")
            self._update_dashboard()
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _load_devices_to_table(self, devices: list, append: bool = False):
        table = self.page_devices.table
        if not append:
            table.setRowCount(0)

        for d in devices:
            row = table.rowCount()
            table.insertRow(row)
            self.devices.append(d)

            table.setItem(row, 0, QTableWidgetItem(d.get('name', '')))
            table.setItem(row, 1, QTableWidgetItem(d.get('platform', '')))
            table.setItem(row, 2, QTableWidgetItem(d.get('host', '')))
            port_item = QTableWidgetItem(str(d.get('port', '')))
            port_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 3, port_item)
            proto_item = QTableWidgetItem(d.get('protocol', 'ssh'))
            proto_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 4, proto_item)
            table.setItem(row, 5, QTableWidgetItem(d.get('username', '')))
            pwd_item = QTableWidgetItem('*' * min(len(d.get('password', '')), 10) or '未设置')
            pwd_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 6, pwd_item)
            status_item = QTableWidgetItem('待巡检')
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(QColor(COLORS['text_secondary']))
            table.setItem(row, 7, status_item)

    def _add_device_manually(self):
        dlg = AddDeviceDialog(self)
        if dlg.exec_():
            d = dlg.get_device()
            if d:
                self._load_devices_to_table([d], append=True)
                self._append_log('INFO', f"已添加设备: {d['name']}")

    def _delete_selected(self):
        table = self.page_devices.table
        rows = sorted(set(i.row() for i in table.selectedItems()), reverse=True)
        if not rows:
            return
        for row in rows:
            table.removeRow(row)
            if row < len(self.devices):
                self.devices.pop(row)
        self._update_dashboard()

    def _clear_devices(self):
        if QMessageBox.question(self, "确认", "确定要清空设备列表吗？") == QMessageBox.Yes:
            self.page_devices.table.setRowCount(0)
            self.devices.clear()
            self._update_dashboard()

    def _start_inspection(self):
        if self.page_devices.table.rowCount() == 0:
            QMessageBox.warning(self, "提示", "请先导入或添加设备！")
            return

        table = self.page_devices.table
        for row in range(table.rowCount()):
            item = QTableWidgetItem('巡检中...')
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QColor(COLORS['warning']))
            table.setItem(row, 7, item)

        self.page_inspection.progress_bar.setValue(0)
        self.page_inspection.progress_bar.setVisible(True)
        self.page_inspection.btn_start.setEnabled(False)
        self.page_inspection.btn_stop.setEnabled(True)
        self.is_running = True

        device_list = []
        for row in range(table.rowCount()):
            def cell(c):
                item = table.item(row, c)
                return item.text() if item else ''
            raw = self.devices[row] if row < len(self.devices) else {}
            dev = DeviceInfo(
                name=cell(0),
                platform=cell(1),
                host=cell(2),
                port=int(cell(3)) if cell(3).isdigit() else 22,
                protocol=cell(4),
                username=cell(5),
                password=raw.get('password', ''),
                enable_password=raw.get('enable_password', ''),
            )
            device_list.append(dev)

        project_name = self.page_inspection.edit_project.text().strip() or '未命名项目'
        output_dir = self.page_inspection.edit_output_dir.text().strip() or self.output_dir
        fmt = self.page_inspection.combo_format.currentText().lower()
        max_workers = self.page_inspection.spin_threads.value()

        self._append_log('INFO', f'开始巡检 {len(device_list)} 台设备')

        self.engine.start(
            devices=device_list,
            commands_map=self.commands_map,
            output_dir=output_dir,
            output_format=fmt,
            max_workers=max_workers,
            project_name=project_name,
            report_config={},
        )

    def _stop_inspection(self):
        self.engine.stop()
        self.page_inspection.btn_stop.setEnabled(False)
        self.page_inspection.btn_start.setEnabled(True)
        self.is_running = False
        self.page_inspection.progress_bar.setVisible(False)
        self._append_log('WARNING', '用户已停止巡检')

    def _save_timer_settings(self):
        enabled = self.page_schedule.chk_timer.isChecked()
        time_text = self.page_schedule.time_edit.currentText()
        if enabled:
            self._append_log('INFO', f'定时巡检已开启 - 每天 {time_text}')
        else:
            self._append_log('INFO', '定时巡检已关闭')
        QMessageBox.information(self, "保存成功", "定时设置已保存")
