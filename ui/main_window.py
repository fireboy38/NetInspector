#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口 - NetInspector 网络设备自动化巡检工具
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
    QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QTextCursor

from core.inspector import InspectionEngine, DeviceInfo
from utils.excel_parser import parse_excel, generate_template
from utils.snapshot_manager import SnapshotManager
from ui.dialogs import CommandEditorDialog, TimerDialog, AboutDialog, AddDeviceDialog, AiConfigDialog, ReportCustomDialog
from ui.dialogs_snapshot import SnapshotManagerDialog, SnapshotCompareDialog

logger = logging.getLogger(__name__)


# ─── 信号中继（线程安全） ───────────────────────────────────────────────
class InspectionSignals(QThread):
    log_signal = pyqtSignal(str, str)       # level, message
    progress_signal = pyqtSignal(int, int)  # completed, total
    task_done_signal = pyqtSignal(str, str) # host, status
    all_done_signal = pyqtSignal(int, int)  # success, failed

    def run(self):
        pass


# ─── 颜色常量 ─────────────────────────────────────────────────────────
# 工业/实用主义配色方案 - 专业工具风格
COLOR_BG = "#F5F7FA"                    # 主背景 - 浅灰蓝
COLOR_CARD = "#FFFFFF"                  # 卡片背景
COLOR_HEADER = "#1A365D"                # 深海蓝 - 主色调
COLOR_ACCENT = "#2563EB"                # 科技蓝 - 强调色
COLOR_SUCCESS = "#059669"               # 深绿 - 成功
COLOR_DANGER = "#DC2626"                # 红 - 危险/错误
COLOR_WARNING = "#D97706"               # 琥珀 - 警告
COLOR_TEXT_PRIMARY = "#1F2937"          # 主要文字
COLOR_TEXT_SECONDARY = "#6B7280"        # 次要文字
COLOR_BORDER = "#E5E7EB"                # 边框
COLOR_LOG_BG = "#0F172A"                # 日志背景 - 深蓝黑
COLOR_LOG_INFO = "#34D399"              # 日志信息 - 翠绿
COLOR_LOG_DEBUG = "#60A5FA"             # 日志调试 - 浅蓝
COLOR_LOG_ERROR = "#F87171"             # 日志错误 - 浅红
COLOR_LOG_WARN = "#FBBF24"              # 日志警告 - 金黄


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = InspectionEngine()
        self.signals = InspectionSignals()
        self.devices = []
        self.commands_map = {}
        self.is_running = False
        self.timer_active = False
        self.timer_mode = 'daily'
        self.timer_hour = 22
        self.timer_min = 0
        self.timer_weekdays = []
        self.timer_obj = QTimer()
        self.output_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'NetInspector', '巡检结果')

        # 快照管理器
        self.snapshot_manager = SnapshotManager()

        # AI 配置
        self.ai_config = {
            'enabled':  False,
            'endpoint': '',
            'apikey':   '',
            'model':    '',
            'prompt':   '',
        }

        # 报表定制配置
        self.report_config = {
            'company':        '四川新数信息技术有限公司',
            'theme_color':    '#2C3E50',
            'accent_color':   '#3498DB',
            'show_logo':      False,
            'logo_path':      '',
            'cover_title':    '',
            'footer_text':    '© 2024-2025 四川新数信息技术有限公司  版权所有  未经授权禁止复制或分发',
            'show_device_info':   True,
            'show_cmd_output':    True,
            'show_ai_section':    True,
            'show_edit_hint':     True,
            'report_font':        'Microsoft YaHei',
            'watermark':          '',
            'custom_css':         '',
        }

        self._load_commands()
        self._init_ui()
        self._connect_signals()
        self._apply_style()

        self._append_log('INFO', '四川新数网络设备巡检系统 已启动  V1.0.1')
        self._append_log('INFO', f'已加载命令配置，包含 {len(self.commands_map)} 种设备类型的命令')

    # ═══════════════════════════════════════════════════════════════════
    #  命令配置加载
    # ═══════════════════════════════════════════════════════════════════
    def _load_commands(self):
        """加载 config_commands.txt"""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg = os.path.join(base, 'config_commands.txt')
        self.commands_map = {}
        self.commands_file = cfg
        if os.path.exists(cfg):
            self._parse_commands_file(cfg)

    def _parse_commands_file(self, path: str):
        """解析命令配置文件"""
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

    # ═══════════════════════════════════════════════════════════════════
    #  UI 初始化
    # ═══════════════════════════════════════════════════════════════════
    def _init_ui(self):
        self.setWindowTitle("四川新数 · 网络设备巡检系统 V1.0.1")
        self.setMinimumSize(1160, 760)
        self.resize(1360, 840)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(6)

        # ── 顶部工具栏 ──
        main_layout.addWidget(self._build_toolbar())
        # ── 功能按钮行 ──
        main_layout.addWidget(self._build_action_bar())
        # ── 中间内容区（设备表 + 日志） ──
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._build_device_panel())
        splitter.addWidget(self._build_log_panel())
        # 使用 stretch factor 替代固定像素，让布局自适应
        splitter.setStretchFactor(0, 6)  # 设备表占比大一些
        splitter.setStretchFactor(1, 4)  # 日志区占比小一些
        main_layout.addWidget(splitter, 1)
        # ── 底部状态栏 ──
        self._build_status_bar()

    def _build_toolbar(self) -> QWidget:
        """顶部配置工具栏（双行布局）"""
        bar = QFrame()
        bar.setObjectName("toolbar")
        outer = QVBoxLayout(bar)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(6)

        # ── 第一子行：项目名称 + 输出格式 + 操作按钮 ──
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        lbl_proj = QLabel("项目名称:")
        lbl_proj.setFixedWidth(64)
        row1.addWidget(lbl_proj)

        self.edit_project = QLineEdit()
        self.edit_project.setPlaceholderText("请输入项目名称（将写入报告标题）")
        self.edit_project.setMinimumWidth(220)
        self.edit_project.setFixedHeight(32)
        row1.addWidget(self.edit_project, 2)

        row1.addWidget(self._vline())

        lbl_fmt = QLabel("输出格式:")
        lbl_fmt.setFixedWidth(58)
        row1.addWidget(lbl_fmt)
        self.combo_format = QComboBox()
        self.combo_format.addItems(["HTML", "TXT"])
        self.combo_format.setFixedSize(74, 32)
        row1.addWidget(self.combo_format)

        row1.addWidget(self._vline())

        lbl_thr = QLabel("并发线程:")
        lbl_thr.setFixedWidth(58)
        row1.addWidget(lbl_thr)
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 50)
        self.spin_threads.setValue(10)
        self.spin_threads.setFixedSize(62, 32)
        row1.addWidget(self.spin_threads)

        row1.addStretch()

        # 开始/停止 放在最右侧
        self.btn_start = QPushButton("开始巡检")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setFixedSize(100, 36)
        self.btn_start.clicked.connect(self._start_inspection)
        row1.addWidget(self.btn_start)

        self.btn_stop = QPushButton("停止巡检")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setFixedSize(100, 36)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_inspection)
        row1.addWidget(self.btn_stop)

        outer.addLayout(row1)

        # ── 第二子行：保存目录 + 定时 ──
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        lbl_dir = QLabel("保存目录:")
        lbl_dir.setFixedWidth(64)
        row2.addWidget(lbl_dir)

        self.edit_output_dir = QLineEdit(self.output_dir)
        self.edit_output_dir.setFixedHeight(28)
        row2.addWidget(self.edit_output_dir, 3)

        btn_browse = QPushButton("浏览")
        btn_browse.setObjectName("btn_secondary")
        btn_browse.setFixedSize(56, 28)
        btn_browse.clicked.connect(self._browse_output_dir)
        row2.addWidget(btn_browse)

        btn_open = QPushButton("打开目录")
        btn_open.setObjectName("btn_secondary")
        btn_open.setFixedSize(76, 28)
        btn_open.clicked.connect(self._open_output_dir)
        row2.addWidget(btn_open)

        row2.addWidget(self._vline())

        self.btn_timer = QPushButton("定时巡检")
        self.btn_timer.setObjectName("btn_secondary")
        self.btn_timer.setFixedSize(80, 28)
        self.btn_timer.clicked.connect(self._show_timer_dialog)
        row2.addWidget(self.btn_timer)

        row2.addStretch()

        outer.addLayout(row2)

        return bar

    def _build_action_bar(self) -> QWidget:
        """第二行：导入/编辑命令等"""
        bar = QFrame()
        bar.setObjectName("actionbar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        btn_import = QPushButton("导入设备清单")
        btn_import.setObjectName("btn_action")
        btn_import.clicked.connect(self._import_devices)
        layout.addWidget(btn_import)

        btn_add = QPushButton("手动添加设备")
        btn_add.setObjectName("btn_action")
        btn_add.clicked.connect(self._add_device_manually)
        layout.addWidget(btn_add)

        btn_del = QPushButton("删除选中")
        btn_del.setObjectName("btn_action")
        btn_del.clicked.connect(self._delete_selected)
        layout.addWidget(btn_del)

        btn_clear = QPushButton("清空列表")
        btn_clear.setObjectName("btn_action")
        btn_clear.clicked.connect(self._clear_devices)
        layout.addWidget(btn_clear)

        btn_template = QPushButton("下载模板")
        btn_template.setObjectName("btn_action")
        btn_template.clicked.connect(self._download_template)
        layout.addWidget(btn_template)

        layout.addWidget(self._vline())

        btn_cmd = QPushButton("编辑巡检命令")
        btn_cmd.setObjectName("btn_action")
        btn_cmd.clicked.connect(self._edit_commands)
        layout.addWidget(btn_cmd)

        layout.addWidget(self._vline())

        # 报表定制按钮
        self.btn_report_custom = QPushButton("报表定制")
        self.btn_report_custom.setObjectName("btn_action_highlight")
        self.btn_report_custom.clicked.connect(self._show_report_custom)
        layout.addWidget(self.btn_report_custom)

        layout.addWidget(self._vline())

        # AI 配置按钮（带状态指示）
        self.btn_ai = QPushButton("AI 配置")
        self.btn_ai.setObjectName("btn_ai_off")
        self.btn_ai.clicked.connect(self._show_ai_config)
        layout.addWidget(self.btn_ai)

        layout.addWidget(self._vline())

        # 快照管理按钮
        self.btn_snapshot = QPushButton("快照管理")
        self.btn_snapshot.setObjectName("btn_action")
        self.btn_snapshot.clicked.connect(self._show_snapshot_manager)
        layout.addWidget(self.btn_snapshot)

        layout.addStretch()

        btn_about = QPushButton("关于")
        btn_about.setObjectName("btn_action")
        btn_about.clicked.connect(self._show_about)
        layout.addWidget(btn_about)

        return bar

    def _build_device_panel(self) -> QWidget:
        """设备列表面板"""
        panel = QFrame()
        panel.setObjectName("device_panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # 标题行
        title_row = QHBoxLayout()
        icon_label = QLabel("设备列表")
        icon_label.setObjectName("section_title")
        title_row.addWidget(icon_label)
        title_row.addStretch()
        self.lbl_device_count = QLabel("共 0 台设备")
        self.lbl_device_count.setObjectName("device_count")
        title_row.addWidget(self.lbl_device_count)
        layout.addLayout(title_row)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # 表格
        self.table = QTableWidget()
        self.table.setObjectName("device_table")
        headers = ['设备名称', '设备类型', 'IP地址', '端口号', '连接类型', '用户名', '密码', '状态']
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.table.verticalHeader().setDefaultSectionSize(36)
        layout.addWidget(self.table)

        return panel

    def _build_log_panel(self) -> QWidget:
        """日志面板"""
        panel = QFrame()
        panel.setObjectName("log_panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        title_row = QHBoxLayout()
        icon_label = QLabel("执行日志")
        icon_label.setObjectName("section_title")
        title_row.addWidget(icon_label)
        title_row.addStretch()

        btn_clear_log = QPushButton("清空日志")
        btn_clear_log.setObjectName("btn_tiny")
        btn_clear_log.clicked.connect(lambda: self.log_view.clear())
        title_row.addWidget(btn_clear_log)
        layout.addLayout(title_row)

        self.log_view = QTextEdit()
        self.log_view.setObjectName("log_view")
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_view)

        return panel

    def _build_status_bar(self):
        """底部状态栏"""
        sb = self.statusBar()
        sb.setObjectName("status_bar")

        self.lbl_status_completed = QLabel("已完成: 0/0")
        self.lbl_status_success = QLabel("成功: 0")
        self.lbl_status_failed = QLabel("失败: 0")

        sb.addWidget(self.lbl_status_completed)
        sb.addWidget(QLabel("  |  "))
        sb.addWidget(self.lbl_status_success)
        sb.addWidget(QLabel("  |  "))
        sb.addWidget(self.lbl_status_failed)
        sb.addPermanentWidget(QLabel("关于"))

        self._reset_status()

    # ═══════════════════════════════════════════════════════════════════
    #  信号连接
    # ═══════════════════════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════════════════════
    #  槽函数
    # ═══════════════════════════════════════════════════════════════════
    def _on_log(self, level: str, msg: str):
        color_map = {
            'INFO': COLOR_LOG_INFO,
            'DEBUG': COLOR_LOG_DEBUG,
            'ERROR': COLOR_LOG_ERROR,
            'WARNING': COLOR_LOG_WARN,
            'WARN': COLOR_LOG_WARN,
        }
        color = color_map.get(level.upper(), COLOR_LOG_INFO)
        ts = datetime.now().strftime('%H:%M:%S')
        html = (f'<span style="color:#888">[{ts}]</span> '
                f'<span style="color:{color};font-weight:bold">[{level}]</span> '
                f'<span style="color:#DDD">{msg}</span>')
        self.log_view.append(html)
        # 自动滚动到底部
        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_view.setTextCursor(cursor)

    def _on_progress(self, completed: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(completed)
        self.lbl_status_completed.setText(f"已完成: {completed}/{total}")

    def _on_task_done(self, host: str, status: str):
        # 更新表格中的状态列
        for row in range(self.table.rowCount()):
            item_ip = self.table.item(row, 2)
            if item_ip and item_ip.text() == host:
                status_item = QTableWidgetItem()
                if status == 'success':
                    status_item.setText('成功')
                    status_item.setForeground(QColor(COLOR_SUCCESS))
                elif status == 'failed':
                    status_item.setText('失败')
                    status_item.setForeground(QColor(COLOR_DANGER))
                else:
                    status_item.setText('取消')
                    status_item.setForeground(QColor(COLOR_WARNING))
                status_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 7, status_item)
                break

        # 更新底部统计
        success = sum(1 for row in range(self.table.rowCount())
                      if self.table.item(row, 7) and '成功' in (self.table.item(row, 7).text() or ''))
        failed = sum(1 for row in range(self.table.rowCount())
                     if self.table.item(row, 7) and '失败' in (self.table.item(row, 7).text() or ''))
        self.lbl_status_success.setText(f"成功: {success}")
        self.lbl_status_failed.setText(f"失败: {failed}")

    def _on_all_done(self, success: int, failed: int):
        self.is_running = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.lbl_status_success.setText(f"成功: {success}")
        self.lbl_status_failed.setText(f"失败: {failed}")
        self._append_log('INFO', f'巡检任务已完成 — 成功 {success} 台，失败 {failed} 台')

        # AI 分析
        if self.ai_config.get('enabled') and self.ai_config.get('apikey'):
            self._append_log('INFO', '正在调用 AI 分析巡检报告，请稍候...')
            self._run_ai_analysis()

        # 保存巡检结果用于快照
        self._last_inspection_results = getattr(self.engine, 'completed_tasks', [])

        msg = QMessageBox(self)
        msg.setWindowTitle("巡检完成")
        msg.setText(f"巡检任务已全部完成！\n\n成功: {success} 台\n失败: {failed} 台")
        msg.setIcon(QMessageBox.Information)
        open_btn = msg.addButton("打开结果目录", QMessageBox.ActionRole)
        snapshot_btn = msg.addButton("保存快照", QMessageBox.ActionRole)
        msg.addButton("确定", QMessageBox.AcceptRole)
        msg.exec_()
        if msg.clickedButton() == open_btn:
            self._open_output_dir()
        elif msg.clickedButton() == snapshot_btn:
            self._save_inspection_snapshot()

    def _append_log(self, level: str, msg: str):
        self.signals.log_signal.emit(level, msg)

    def _reset_status(self):
        self.lbl_status_completed.setText("已完成: 0/0")
        self.lbl_status_success.setText("成功: 0")
        self.lbl_status_failed.setText("失败: 0")

    # ═══════════════════════════════════════════════════════════════════
    #  设备管理
    # ═══════════════════════════════════════════════════════════════════
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
                QMessageBox.warning(self, "提示", "未能从文件中解析到任何设备信息，请检查文件格式。")
                return
            self._load_devices_to_table(devices)
            self._append_log('INFO', f"成功导入 {len(devices)} 台设备，来自: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"文件解析错误：\n{str(e)}")
            self._append_log('ERROR', f"导入设备清单失败: {e}")

    def _load_devices_to_table(self, devices: list, append: bool = False):
        if not append:
            self.table.setRowCount(0)
            self.devices = []

        for d in devices:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.devices.append(d)

            self.table.setItem(row, 0, QTableWidgetItem(d.get('name', '')))
            self.table.setItem(row, 1, QTableWidgetItem(d.get('platform', '')))
            self.table.setItem(row, 2, QTableWidgetItem(d.get('host', '')))
            port_item = QTableWidgetItem(str(d.get('port', '')))
            port_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, port_item)
            proto_item = QTableWidgetItem(d.get('protocol', 'ssh'))
            proto_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, proto_item)
            self.table.setItem(row, 5, QTableWidgetItem(d.get('username', '')))
            # 密码显示为星号
            pwd_item = QTableWidgetItem('*' * min(len(d.get('password', '')), 10) or '未设置')
            pwd_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 6, pwd_item)
            status_item = QTableWidgetItem('待巡检')
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(QColor('#888'))
            self.table.setItem(row, 7, status_item)

        self.lbl_device_count.setText(f"共 {self.table.rowCount()} 台设备")

    def _add_device_manually(self):
        dlg = AddDeviceDialog(self)
        if dlg.exec_():
            d = dlg.get_device()
            if d:
                self._load_devices_to_table([d], append=True)
                self._append_log('INFO', f"已手动添加设备: {d['name']} ({d['host']})")

    def _delete_selected(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()), reverse=True)
        if not rows:
            return
        for row in rows:
            self.table.removeRow(row)
            if row < len(self.devices):
                self.devices.pop(row)
        self.lbl_device_count.setText(f"共 {self.table.rowCount()} 台设备")

    def _clear_devices(self):
        if QMessageBox.question(self, "确认", "确定要清空设备列表吗？",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.table.setRowCount(0)
            self.devices.clear()
            self.lbl_device_count.setText("共 0 台设备")

    def _download_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存模板文件", "设备清单模板.xlsx",
            "Excel文件 (*.xlsx)"
        )
        if not path:
            return
        try:
            generate_template(path)
            QMessageBox.information(self, "成功", f"模板已保存至:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "失败", f"模板生成失败:\n{e}")

    # ═══════════════════════════════════════════════════════════════════
    #  巡检控制
    # ═══════════════════════════════════════════════════════════════════
    def _start_inspection(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "提示", "请先导入或添加设备清单！")
            return

        output_dir = self.edit_output_dir.text().strip() or self.output_dir
        fmt = self.combo_format.currentText().lower()
        max_workers = self.spin_threads.value()

        # 重置状态列
        for row in range(self.table.rowCount()):
            item = QTableWidgetItem('巡检中...')
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QColor(COLOR_WARNING))
            self.table.setItem(row, 7, item)

        self._reset_status()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(self.table.rowCount())
        self.progress_bar.setVisible(True)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.is_running = True

        # 构建设备列表
        device_list = []
        for row in range(self.table.rowCount()):
            def cell(c):
                item = self.table.item(row, c)
                return item.text() if item else ''

            # 密码从原始数据中取
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

        self._append_log('INFO', f'开始巡检 {len(device_list)} 台设备，线程数: {max_workers}，格式: {fmt.upper()}')

        # 把项目名称和 AI 配置传给引擎
        project_name = self.edit_project.text().strip() or '未命名项目'
        self.engine.start(
            devices=device_list,
            commands_map=self.commands_map,
            output_dir=output_dir,
            output_format=fmt,
            max_workers=max_workers,
            project_name=project_name,
            report_config=self.report_config,
        )

    def _stop_inspection(self):
        self.engine.stop()
        self.btn_stop.setEnabled(False)
        self.btn_start.setEnabled(True)
        self.is_running = False
        self.progress_bar.setVisible(False)
        self._append_log('WARNING', '用户已手动停止巡检')

    # ═══════════════════════════════════════════════════════════════════
    #  其他功能
    # ═══════════════════════════════════════════════════════════════════
    def _browse_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存目录", self.output_dir)
        if path:
            self.edit_output_dir.setText(path)
            self.output_dir = path

    def _open_output_dir(self):
        path = self.edit_output_dir.text().strip() or self.output_dir
        os.makedirs(path, exist_ok=True)
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.call(['open', path])
        else:
            subprocess.call(['xdg-open', path])

    def _edit_commands(self):
        dlg = CommandEditorDialog(self.commands_file, self)
        if dlg.exec_():
            self._parse_commands_file(self.commands_file)
            self._append_log('INFO', f'成功加载命令配置，包含 {len(self.commands_map)} 种设备类型的命令...')

    def _show_timer_dialog(self):
        dlg = TimerDialog(self)
        if dlg.exec_():
            settings = dlg.get_settings()
            self.timer_active = settings.get('enabled', False)
            self.timer_mode = settings.get('mode', 'daily')
            self.timer_hour = settings.get('hour', 22)
            self.timer_min = settings.get('minute', 0)
            self.timer_weekdays = settings.get('weekdays', [])

            if self.timer_active:
                mode_text = {'daily': '每日', 'weekly': '每周', 'once': '单次'}.get(self.timer_mode, '每日')
                self._append_log('INFO', f'定时巡检已开启 - {mode_text} {self.timer_hour:02d}:{self.timer_min:02d} 执行')
            else:
                self._append_log('INFO', '定时巡检已关闭')

    def _show_about(self):
        dlg = AboutDialog(self)
        dlg.exec_()

    def _show_report_custom(self):
        dlg = ReportCustomDialog(self.report_config, self)
        if dlg.exec_():
            self.report_config = dlg.get_config()
            self._append_log('INFO', '报表定制配置已更新，下次巡检将使用新样式')

    def _show_ai_config(self):
        dlg = AiConfigDialog(self.ai_config, self)
        if dlg.exec_():
            self.ai_config = dlg.get_config()
            # 更新按钮样式
            if self.ai_config.get('enabled'):
                self.btn_ai.setObjectName("btn_ai_on")
                self.btn_ai.setText("AI 已开启")
                self._append_log('INFO', f"AI 分析已启用：{self.ai_config.get('model','')}")
            else:
                self.btn_ai.setObjectName("btn_ai_off")
                self.btn_ai.setText("AI 配置")
            # 刷新样式
            self.btn_ai.style().unpolish(self.btn_ai)
            self.btn_ai.style().polish(self.btn_ai)

    def _show_snapshot_manager(self):
        """显示快照管理对话框"""
        dlg = SnapshotManagerDialog(self.snapshot_manager, self)
        dlg.exec_()

    def _save_inspection_snapshot(self):
        """保存本次巡检结果为快照"""
        tasks = getattr(self.engine, 'completed_tasks', [])
        if not tasks:
            QMessageBox.information(self, "提示", "没有可保存的巡检结果")
            return

        saved_count = 0
        for task in tasks:
            if task.status == 'success' and task.results:
                try:
                    self.snapshot_manager.create_snapshot(
                        device_name=task.device.name,
                        device_host=task.device.host,
                        commands_output=task.results,
                        description=f"巡检快照 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    )
                    saved_count += 1
                except Exception as e:
                    self._append_log('ERROR', f"保存快照失败 {task.device.host}: {e}")

        if saved_count > 0:
            QMessageBox.information(self, "成功", f"已保存 {saved_count} 个设备的配置快照")
            self._append_log('INFO', f"已保存 {saved_count} 个设备的配置快照")
        else:
            QMessageBox.information(self, "提示", "没有成功保存任何快照")

    def _run_ai_analysis(self):
        """调用 AI 分析所有已生成的报告（整合后统一分析）"""
        import threading
        import time
        output_dir = self.edit_output_dir.text().strip() or self.output_dir
        project_name = self.edit_project.text().strip() or '未命名项目'

        def worker():
            try:
                from utils.ai_analyzer import AiAnalyzer
                analyzer = AiAnalyzer(self.ai_config)

                # 找到本次生成的报告文件（最近10分钟内）
                now = time.time()
                report_files = []
                if os.path.isdir(output_dir):
                    for fn in os.listdir(output_dir):
                        fp = os.path.join(output_dir, fn)
                        # 只收集单个设备报告，不收集已整合的报告
                        if os.path.isfile(fp) and (now - os.path.getmtime(fp)) < 600 \
                           and not fn.startswith('汇总_') and not fn.startswith('整合_') \
                           and not fn.startswith('merged_'):
                            # 只处理 HTML 和 TXT 报告
                            if fn.lower().endswith(('.html', '.txt')):
                                report_files.append(fp)

                if not report_files:
                    self.signals.log_signal.emit('WARNING', 'AI 分析：未找到最近生成的报告文件')
                    return

                self.signals.log_signal.emit('INFO', f'AI 分析：正在整合 {len(report_files)} 个设备报告...')

                # 生成整合报告文件路径
                timestamp = time.strftime('%Y%m%d_%H%M%S')
                merge_filename = f'整合巡检报告_{timestamp}.html'
                merge_path = os.path.join(output_dir, merge_filename)

                # 整合所有报告
                merge_file = analyzer.merge_reports(report_files, merge_path, project_name)
                if not merge_file:
                    self.signals.log_signal.emit('ERROR', 'AI 分析：整合报告失败')
                    return

                self.signals.log_signal.emit('INFO', f'AI 分析：整合报告已生成，正在调用 AI 分析...')

                # 调用 AI 分析整合后的报告
                result = analyzer.analyze_report(merge_file, project_name)
                if result:
                    # 将 AI 结果写入整合报告
                    analyzer.append_ai_section(merge_file, result)
                    self.signals.log_signal.emit('INFO', f'AI 分析完成！结果已写入: {os.path.basename(merge_file)}')

                    # 同时也将 AI 结果写入各单个设备报告
                    for fp in report_files:
                        analyzer.append_ai_section(fp, result)
                    self.signals.log_signal.emit('INFO', f'AI 分析结果已同步到所有 {len(report_files)} 个设备报告')
                else:
                    self.signals.log_signal.emit('ERROR', 'AI 分析调用失败，请检查 API 配置')

            except Exception as e:
                import traceback
                self.signals.log_signal.emit('ERROR', f'AI 分析失败: {e}')
                traceback.print_exc()

        threading.Thread(target=worker, daemon=True).start()

    def _vline(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setFixedWidth(2)
        return line

    # ═══════════════════════════════════════════════════════════════════
    #  样式
    # ═══════════════════════════════════════════════════════════════════
    def _apply_style(self):
        self.setStyleSheet(f"""
            /* ============================================================
               NetInspector - 工业实用主义风格样式表
               ============================================================ */
            
            QMainWindow {{
                background: {COLOR_BG};
            }}
            QWidget {{
                font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
                font-size: 13px;
                color: {COLOR_TEXT_PRIMARY};
            }}
            
            /* 顶部工具栏 */
            QFrame#toolbar {{
                background: {COLOR_HEADER};
                border-radius: 8px;
            }}
            QFrame#toolbar QLabel {{
                color: #CBD5E1;
                font-size: 12px;
            }}
            QFrame#toolbar QLineEdit {{
                background: rgba(255,255,255,0.1);
                color: #F1F5F9;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 4px;
                padding: 4px 10px;
                selection-background-color: {COLOR_ACCENT};
            }}
            QFrame#toolbar QLineEdit:focus {{
                border: 1px solid {COLOR_ACCENT};
            }}
            
            /* 操作按钮栏 */
            QFrame#actionbar {{
                background: {COLOR_CARD};
                border-radius: 8px;
                border: 1px solid {COLOR_BORDER};
            }}
            
            /* 设备面板和日志面板 - 卡片式设计 */
            QFrame#device_panel, QFrame#log_panel {{
                background: {COLOR_CARD};
                border-radius: 10px;
                border: 1px solid {COLOR_BORDER};
            }}
            
            QLabel#section_title {{
                font-size: 13px;
                font-weight: 600;
                color: {COLOR_HEADER};
                padding: 4px 0;
            }}
            QLabel#device_count {{
                color: {COLOR_TEXT_SECONDARY};
                font-size: 12px;
            }}
            
            /* 表格样式 - 清晰专业 */
            QTableWidget#device_table {{
                border: none;
                gridline-color: {COLOR_BORDER};
                selection-background-color: {COLOR_ACCENT};
                alternate-background-color: #F8FAFC;
                background: white;
                font-size: 13px;
            }}
            QTableWidget#device_table QHeaderView::section {{
                background: {COLOR_HEADER};
                color: white;
                padding: 8px 10px;
                font-weight: 600;
                font-size: 12px;
                border: none;
                border-right: 1px solid rgba(255,255,255,0.1);
            }}
            QTableWidget#device_table::item {{
                padding: 6px 10px;
                border-bottom: 1px solid {COLOR_BORDER};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QTableWidget#device_table::item:selected {{
                background: {COLOR_ACCENT};
                color: white;
            }}
            
            /* 日志视图 - 深色主题 */
            QTextEdit#log_view {{
                background: {COLOR_LOG_BG};
                color: {COLOR_LOG_INFO};
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-family: "JetBrains Mono", "Consolas", monospace;
                font-size: 12px;
                line-height: 1.5;
            }}
            
            /* 主要按钮 - 开始巡检 */
            QPushButton#btn_start {{
                background: {COLOR_SUCCESS};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#btn_start:hover {{
                background: #047857;
            }}
            QPushButton#btn_start:disabled {{
                background: #9CA3AF;
            }}
            
            /* 次要按钮 - 停止巡检 */
            QPushButton#btn_stop {{
                background: {COLOR_DANGER};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#btn_stop:hover {{
                background: #B91C1C;
            }}
            QPushButton#btn_stop:disabled {{
                background: #9CA3AF;
            }}
            
            /* 工具栏次要按钮 */
            QPushButton#btn_secondary {{
                background: rgba(255,255,255,0.1);
                color: #E2E8F0;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QPushButton#btn_secondary:hover {{
                background: rgba(255,255,255,0.2);
                color: white;
            }}
            
            /* 操作按钮 */
            QPushButton#btn_action {{
                background: {COLOR_CARD};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 5px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton#btn_action:hover {{
                background: #EFF6FF;
                border-color: {COLOR_ACCENT};
                color: {COLOR_ACCENT};
            }}
            
            /* 高亮操作按钮 */
            QPushButton#btn_action_highlight {{
                background: #EFF6FF;
                color: {COLOR_ACCENT};
                border: 1px solid #BFDBFE;
                border-radius: 5px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#btn_action_highlight:hover {{
                background: #DBEAFE;
                border-color: {COLOR_ACCENT};
            }}
            
            /* 小按钮 */
            QPushButton#btn_tiny {{
                background: transparent;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 11px;
            }}
            QPushButton#btn_tiny:hover {{
                color: {COLOR_ACCENT};
                border-color: {COLOR_ACCENT};
            }}
            
            /* AI 配置按钮 - 关闭状态 */
            QPushButton#btn_ai_off {{
                background: {COLOR_CARD};
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 5px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton#btn_ai_off:hover {{
                background: #FFFBEB;
                border-color: {COLOR_WARNING};
                color: {COLOR_WARNING};
            }}
            
            /* AI 配置按钮 - 开启状态 */
            QPushButton#btn_ai_on {{
                background: {COLOR_ACCENT};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#btn_ai_on:hover {{
                background: #1D4ED8;
            }}
            
            /* 数字输入框 */
            QSpinBox {{
                background: rgba(255,255,255,0.1);
                color: #F1F5F9;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 4px;
                padding: 3px 6px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: rgba(255,255,255,0.1);
                border: none;
            }}
            
            /* 下拉框 */
            QComboBox {{
                background: rgba(255,255,255,0.1);
                color: #F1F5F9;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 4px;
                padding: 3px 10px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background: {COLOR_HEADER};
                color: white;
                selection-background-color: {COLOR_ACCENT};
                border: 1px solid rgba(255,255,255,0.1);
            }}
            
            /* 进度条 */
            QProgressBar {{
                border: none;
                border-radius: 3px;
                background: #E2E8F0;
                height: 6px;
            }}
            QProgressBar::chunk {{
                background: {COLOR_ACCENT};
                border-radius: 3px;
            }}
            
            /* 状态栏 */
            QStatusBar {{
                background: #F8FAFC;
                border-top: 1px solid {COLOR_BORDER};
                font-size: 12px;
                color: {COLOR_TEXT_SECONDARY};
            }}
            
            /* 分隔器 */
            QSplitter::handle {{
                background: {COLOR_BORDER};
                height: 3px;
            }}
            QSplitter::handle:hover {{
                background: {COLOR_ACCENT};
            }}
        """)
