#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
各类对话框：命令编辑器、定时巡检、关于、手动添加设备、AI配置
"""

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QFormLayout,
    QGroupBox, QRadioButton, QTimeEdit, QCheckBox, QMessageBox,
    QFrame, QDialogButtonBox, QTabWidget, QWidget, QScrollArea
)
from PyQt5.QtCore import Qt, QTime
from PyQt5.QtGui import QFont


# ─── 颜色常量 ──────────────────────────────────────────
COLOR_HEADER = "#2C3E50"
COLOR_ACCENT = "#3498DB"


class CommandEditorDialog(QDialog):
    """巡检命令编辑器"""

    def __init__(self, commands_file: str, parent=None):
        super().__init__(parent)
        self.commands_file = commands_file
        self.setWindowTitle("编辑巡检命令")
        self.setMinimumSize(680, 520)
        self.resize(720, 560)
        self._init_ui()
        self._load_file()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 说明
        hint = QLabel(
            "按 [厂商] 分组定义巡检命令，每行一条命令。\n"
            "支持的厂商标识：[huawei] [h3c] [cisco] [ruijie] [default]"
        )
        hint.setStyleSheet("color:#666; font-size:12px; padding:4px;")
        layout.addWidget(hint)

        # 编辑器
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.setStyleSheet("""
            QTextEdit {
                background: #1E1E2E;
                color: #A8D8A8;
                border: 1px solid #3D5570;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.editor)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedWidth(80)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("保存")
        btn_save.setFixedWidth(80)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background: {COLOR_ACCENT};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #2980B9; }}
        """)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _load_file(self):
        try:
            if os.path.exists(self.commands_file):
                with open(self.commands_file, encoding='utf-8') as f:
                    self.editor.setPlainText(f.read())
        except Exception as e:
            QMessageBox.warning(self, "加载失败", str(e))

    def _save(self):
        try:
            content = self.editor.toPlainText()
            os.makedirs(os.path.dirname(self.commands_file), exist_ok=True)
            with open(self.commands_file, 'w', encoding='utf-8') as f:
                f.write(content)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))


class TimerDialog(QDialog):
    """定时巡检设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("定时巡检设置")
        self.setMinimumSize(480, 360)
        self.resize(500, 380)
        self._init_ui()
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background: white;
                font-family: "Microsoft YaHei", Arial;
            }
            QLabel {
                font-size: 13px;
                color: #333;
            }
            QCheckBox {
                font-size: 14px;
                font-weight: bold;
                color: #2C3E50;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QRadioButton {
                font-size: 13px;
                color: #333;
                spacing: 6px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QSpinBox {
                border: 1px solid #CCC;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 14px;
                color: #333;
                background: white;
                min-width: 60px;
            }
            QSpinBox:focus {
                border-color: #3498DB;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
                border: none;
                background: #3498DB;
                border-radius: 2px;
                margin: 1px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #2980B9;
            }
            QSpinBox::up-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 6px solid white;
            }
            QSpinBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid white;
            }
            QPushButton {
                background: #2C3E50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #3D5570;
            }
        """)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 12, 16, 12)

        # 启用开关
        self.chk_enable = QCheckBox("启用定时巡检")
        self.chk_enable.setChecked(False)
        self.chk_enable.toggled.connect(self._on_enable_toggled)
        layout.addWidget(self.chk_enable)

        # 模式选择
        mode_box = QHBoxLayout()
        mode_box.addWidget(QLabel("模式:"))

        self.rb_daily = QRadioButton("每日")
        self.rb_daily.setChecked(True)
        self.rb_weekly = QRadioButton("每周")
        self.rb_once = QRadioButton("单次")

        mode_box.addWidget(self.rb_daily)
        mode_box.addWidget(self.rb_weekly)
        mode_box.addWidget(self.rb_once)
        mode_box.addStretch()
        layout.addLayout(mode_box)

        # 星期选择（每周模式）
        self.week_row = QHBoxLayout()
        self.week_row.setSpacing(8)
        self.week_row.addWidget(QLabel("星期:"))

        self.week_checks = {}
        week_days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for day in week_days:
            chk = QCheckBox(day)
            chk.setChecked(True)
            chk.setStyleSheet("""
                QCheckBox {
                    font-size: 13px;
                    color: #333;
                    spacing: 4px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                }
            """)
            self.week_checks[day] = chk
            self.week_row.addWidget(chk)
        self.week_row.addStretch()

        self.week_widget = QWidget()
        self.week_widget.setLayout(self.week_row)
        self.week_widget.setEnabled(False)
        layout.addWidget(self.week_widget)

        # 时间选择（美化版）
        time_box = QHBoxLayout()
        time_box.addWidget(QLabel("巡检时间:"))
        time_box.addSpacing(8)

        # 时分选择容器
        time_container = QFrame()
        time_container.setStyleSheet("""
            QFrame {
                background: #F5F8FA;
                border: 1px solid #3498DB;
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        time_inner = QHBoxLayout(time_container)
        time_inner.setSpacing(6)
        time_inner.setContentsMargins(0, 0, 0, 0)

        self.spin_hour = QSpinBox()
        self.spin_hour.setRange(0, 23)
        self.spin_hour.setValue(22)
        self.spin_hour.setFixedWidth(65)
        self.spin_hour.setStyleSheet("""
            QSpinBox {
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-size: 16px;
                font-weight: bold;
                color: #2C3E50;
                background: white;
                text-align: center;
            }
            QSpinBox:focus {
                border: 2px solid #3498DB;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 18px;
                border: none;
                background: #3498DB;
                border-radius: 3px;
                margin: 2px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #2980B9;
            }
            QSpinBox::up-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 5px solid white;
            }
            QSpinBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid white;
            }
        """)
        time_inner.addWidget(self.spin_hour)

        sep = QLabel("<span style='font-size:18px; font-weight:bold; color:#3498DB;'>:</span>")
        time_inner.addWidget(sep)

        self.spin_min = QSpinBox()
        self.spin_min.setRange(0, 59)
        self.spin_min.setValue(0)
        self.spin_min.setFixedWidth(65)
        self.spin_min.setStyleSheet("""
            QSpinBox {
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-size: 18px;
                font-weight: bold;
                color: #2C3E50;
                background: white;
                text-align: center;
            }
            QSpinBox:focus {
                border: 2px solid #3498DB;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                border: none;
                background: #3498DB;
                border-radius: 3px;
                margin: 2px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #2980B9;
            }
            QSpinBox::up-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 5px solid white;
            }
            QSpinBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid white;
            }
        """)
        time_inner.addWidget(self.spin_min)

        time_box.addWidget(time_container)
        time_box.addStretch()
        layout.addLayout(time_box)

        layout.addStretch()

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedWidth(80)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("保存")
        btn_save.setFixedWidth(80)
        btn_save.clicked.connect(self.accept)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        # 连接信号
        self.rb_weekly.toggled.connect(self.week_widget.setEnabled)
        self._on_enable_toggled(False)

    def _on_enable_toggled(self, checked: bool):
        """启用状态改变"""
        self.rb_daily.setEnabled(checked)
        self.rb_weekly.setEnabled(checked)
        self.rb_once.setEnabled(checked)
        self.week_widget.setEnabled(checked and self.rb_weekly.isChecked())
        self.spin_hour.setEnabled(checked)
        self.spin_min.setEnabled(checked)

    def get_settings(self):
        # 获取选中的星期
        selected_days = [day for day, chk in self.week_checks.items() if chk.isChecked()]

        if self.rb_daily.isChecked():
            mode = 'daily'
        elif self.rb_weekly.isChecked():
            mode = 'weekly'
        else:
            mode = 'once'

        return {
            'enabled': self.chk_enable.isChecked(),
            'mode': mode,
            'hour': self.spin_hour.value(),
            'minute': self.spin_min.value(),
            'weekdays': selected_days,
        }

    def get_settings(self):
        # 获取选中的星期
        selected_days = [day for day, chk in self.week_checks.items() if chk.isChecked()]

        if self.rb_daily.isChecked():
            mode = 'daily'
        elif self.rb_weekly.isChecked():
            mode = 'weekly'
        else:
            mode = 'once'

        return {
            'enabled': self.chk_enable.isChecked(),
            'mode': mode,
            'hour': self.spin_hour.value(),
            'minute': self.spin_min.value(),
            'weekdays': selected_days,  # 周模式选中的星期
        }


class AddDeviceDialog(QDialog):
    """手动添加设备对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加设备")
        self.setFixedSize(460, 420)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("设备名称/备注")
        form.addRow("设备名称:", self.edit_name)

        self.combo_platform = QComboBox()
        self.combo_platform.addItems(["huawei", "h3c", "cisco", "ruijie", "default"])
        form.addRow("设备类型:", self.combo_platform)

        self.edit_host = QLineEdit()
        self.edit_host.setPlaceholderText("192.168.1.1")
        form.addRow("IP地址:", self.edit_host)

        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(22)
        form.addRow("端口号:", self.spin_port)

        self.combo_proto = QComboBox()
        self.combo_proto.addItems(["ssh", "telnet"])
        self.combo_proto.currentTextChanged.connect(self._on_proto_change)
        form.addRow("连接协议:", self.combo_proto)

        self.edit_user = QLineEdit()
        self.edit_user.setPlaceholderText("admin")
        self.edit_user.setText("admin")
        form.addRow("用户名:", self.edit_user)

        self.edit_pass = QLineEdit()
        self.edit_pass.setEchoMode(QLineEdit.Password)
        self.edit_pass.setPlaceholderText("登录密码")
        form.addRow("密码:", self.edit_pass)

        self.edit_enable = QLineEdit()
        self.edit_enable.setEchoMode(QLineEdit.Password)
        self.edit_enable.setPlaceholderText("仅Cisco/锐捷需要")
        form.addRow("特权密码:", self.edit_enable)

        layout.addLayout(form)
        layout.addStretch()

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedWidth(80)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_ok = QPushButton("添加")
        btn_ok.setFixedWidth(80)
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background: {COLOR_HEADER};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #3D5570; }}
        """)
        btn_ok.clicked.connect(self._validate_and_accept)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

        self._apply_style()

    def _on_proto_change(self, proto: str):
        self.spin_port.setValue(22 if proto == 'ssh' else 23)

    def _validate_and_accept(self):
        host = self.edit_host.text().strip()
        if not host:
            QMessageBox.warning(self, "提示", "IP地址不能为空！")
            return
        self.accept()

    def get_device(self):
        return {
            'name': self.edit_name.text().strip() or self.edit_host.text().strip(),
            'platform': self.combo_platform.currentText(),
            'host': self.edit_host.text().strip(),
            'port': self.spin_port.value(),
            'protocol': self.combo_proto.currentText(),
            'username': self.edit_user.text().strip(),
            'password': self.edit_pass.text(),
            'enable_password': self.edit_enable.text(),
        }

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background: white;
                font-family: "Microsoft YaHei", Arial;
            }
            QLabel { font-size: 13px; color: #333; }
            QLineEdit, QSpinBox, QComboBox {
                border: 1px solid #CCC;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 13px;
                color: #333;
                background: white;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #3498DB;
            }
            QLineEdit:disabled {
                background: #F5F5F5;
                color: #999;
            }
        """)


class AboutDialog(QDialog):
    """关于对话框 - 四川新数信息技术有限公司"""

    # 版本更新日志
    VERSION_HISTORY = """
    <h3>V1.0.1 (2026-03-22)</h3>
    <ul>
        <li>解决 SSH/Telnet 连接设备时 "-- More --" 分页卡顿问题</li>
        <li>优化定时巡检对话框界面配色和时间选择器样式</li>
        <li>修复窗口最大化启动时显示不全的问题</li>
        <li>公司名称由"四川新数网络科技有限公司"更名为"四川新数信息技术有限公司"</li>
    </ul>

    <h3>V1.0.0 (2025)</h3>
    <ul>
        <li>首发版本，支持华为、H3C、Cisco、锐捷等主流厂商设备巡检</li>
        <li>支持 SSH/Telnet 双协议连接</li>
        <li>多线程并发巡检</li>
        <li>HTML/TXT 双格式报告输出</li>
        <li>支持 AI 智能分析（兼容 OpenAI、DeepSeek、阿里云百炼等）</li>
        <li>定时巡检功能</li>
        <li>报表个性化定制（颜色主题、Logo、封面等）</li>
    </ul>
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 · 使用说明")
        self.setFixedSize(600, 600)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(0)

        # 顶部品牌 Banner
        banner = QFrame()
        banner.setStyleSheet(f"background: {COLOR_HEADER}; padding: 18px 24px;")
        b_layout = QVBoxLayout(banner)
        b_layout.setSpacing(4)

        title_lbl = QLabel("四川新数信息技术有限公司")
        title_lbl.setStyleSheet("color: white; font-size: 18px; font-weight: bold; background: transparent;")
        b_layout.addWidget(title_lbl)

        sub_lbl = QLabel("网络设备巡检系统  V1.0.1")
        sub_lbl.setStyleSheet("color: #A8C7E8; font-size: 13px; background: transparent;")
        b_layout.addWidget(sub_lbl)

        layout.addWidget(banner)

        # 内容
        content = QTextEdit()
        content.setReadOnly(True)
        content.setStyleSheet("""
            QTextEdit {
                border: none;
                background: #FAFAFA;
                font-size: 13px;
                color: #333;
                padding: 4px 8px;
            }
        """)
        content.setHtml("""
<style>
body { font-family: "Microsoft YaHei", Arial; font-size:13px; color:#333; margin:16px; }
h3 { color:#2C3E50; margin-top:14px; margin-bottom:6px; font-size:14px; }
p, li { line-height:1.8; margin:2px 0; }
b { color:#2980B9; }
.tip { background:#EBF5FB; border-left:3px solid #3498DB; padding:6px 10px;
       border-radius:3px; margin:8px 0; font-size:12px; color:#444; }
</style>

<h3>一、软件简介</h3>
<p>本系统是由四川新数信息技术有限公司自主研发的网络设备自动化巡检工具，
支持华为、H3C、思科、锐捷等主流厂商，通过多线程并发批量巡检，
帮助网络工程师高效完成设备配置采集、状态核查与隐患识别。</p>

<h3>二、快速上手</h3>
<ol>
<li><b>填写项目名称：</b>在顶部工具栏输入项目名称，该名称将写入巡检报告标题。</li>
<li><b>准备设备清单：</b>点击【下载模板】获取 Excel 模板，填写设备信息后点击【导入设备清单】。</li>
<li><b>配置巡检命令：</b>点击【编辑巡检命令】，在配置文件中按 [厂商] 分组定义命令。</li>
<li><b>可选 AI 分析：</b>点击【AI 配置】填入 API Key，开启后巡检完毕自动调用 AI 分析异常。</li>
<li><b>执行巡检：</b>设置线程数、输出格式，点击【开始巡检】。</li>
<li><b>查看报告：</b>巡检完成后点击【打开目录】，HTML 报告可用浏览器直接编辑后另存。</li>
</ol>

<h3>三、支持设备类型</h3>
<p>huawei（华为）、h3c（新华三）、cisco（思科）、ruijie（锐捷）、default（通用）</p>

<h3>四、AI 分析说明</h3>
<p>需填入兼容 OpenAI 接口的 API Key（支持 OpenAI、阿里云百炼、DeepSeek 等），
巡检报告将自动发送给 AI，AI 返回问题摘要后整合写入报告末尾。</p>
<div class="tip">提示：API Key 仅保存在本地配置文件中，不会上传至任何第三方服务器。</div>

<h3>五、注意事项</h3>
<ul>
<li>思科/锐捷需进入特权模式时，请在清单中填写特权密码（enable）。</li>
<li>建议线程数不超过设备总数，过多线程可能导致设备负载升高。</li>
<li>SSH 默认端口 22，Telnet 默认端口 23。</li>
</ul>
""")
        layout.addWidget(content, 1)

        # 底部版权
        footer = QLabel("© 2024-2025 四川新数信息技术有限公司  版权所有  未经授权禁止复制或分发")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #999; font-size: 11px; padding: 8px;")
        layout.addWidget(footer)

        btn_ok = QPushButton("我知道了")
        btn_ok.setFixedWidth(100)
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background: {COLOR_HEADER};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #3D5570; }}
        """)
        btn_ok.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 16, 0)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)


class AiConfigDialog(QDialog):
    """AI 分析配置对话框"""

    # 预设的 API 端点
    PRESETS = {
        "OpenAI (官方)":        "https://api.openai.com/v1",
        "DeepSeek":             "https://api.deepseek.com/v1",
        "阿里云百炼 (Qwen)":    "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "自定义端点":           "",
    }

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 分析配置")
        self.setFixedSize(520, 420)
        self.config = config.copy()
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(12)

        # 标题
        title = QLabel("AI 智能分析配置")
        title.setStyleSheet(f"font-size:15px; font-weight:bold; color:{COLOR_HEADER};")
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:#DDD; margin-bottom:4px;")
        layout.addWidget(line)

        # 启用开关
        row_enable = QHBoxLayout()
        self.chk_enable = QCheckBox("启用 AI 分析（巡检完成后自动调用）")
        self.chk_enable.setStyleSheet("font-size:13px; color:#333;")
        self.chk_enable.toggled.connect(self._on_enable_toggle)
        row_enable.addWidget(self.chk_enable)
        row_enable.addStretch()
        layout.addLayout(row_enable)

        # 配置表单
        self.form_group = QGroupBox("接口配置")
        self.form_group.setStyleSheet("""
            QGroupBox { font-size:13px; color:#555; border:1px solid #DDD;
                        border-radius:5px; margin-top:8px; padding-top:10px; }
            QGroupBox::title { subcontrol-origin:margin; left:10px; }
        """)
        form = QFormLayout(self.form_group)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)
        form.setContentsMargins(14, 14, 14, 14)

        # 预设选择
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(list(self.PRESETS.keys()))
        self.combo_preset.currentTextChanged.connect(self._on_preset_change)
        form.addRow("服务商:", self.combo_preset)

        # API 端点
        self.edit_endpoint = QLineEdit()
        self.edit_endpoint.setPlaceholderText("https://api.openai.com/v1")
        form.addRow("API 端点:", self.edit_endpoint)

        # API Key
        self.edit_apikey = QLineEdit()
        self.edit_apikey.setEchoMode(QLineEdit.Password)
        self.edit_apikey.setPlaceholderText("sk-...")
        form.addRow("API Key:", self.edit_apikey)

        # 模型
        self.edit_model = QLineEdit()
        self.edit_model.setPlaceholderText("gpt-4o / deepseek-chat / qwen-plus")
        form.addRow("模型名称:", self.edit_model)

        # Prompt
        self.edit_prompt = QTextEdit()
        self.edit_prompt.setFixedHeight(80)
        self.edit_prompt.setPlaceholderText("自定义分析提示词（留空使用默认）")
        form.addRow("分析提示词:", self.edit_prompt)

        layout.addWidget(self.form_group)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedWidth(80)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_test = QPushButton("测试连接")
        btn_test.setFixedWidth(90)
        btn_test.setStyleSheet(f"""
            QPushButton {{ background: white; color: {COLOR_ACCENT};
                border: 1px solid {COLOR_ACCENT}; border-radius:4px; padding:6px; }}
            QPushButton:hover {{ background: #EBF5FB; }}
        """)
        btn_test.clicked.connect(self._test_connection)
        btn_row.addWidget(btn_test)

        btn_save = QPushButton("保存")
        btn_save.setFixedWidth(80)
        btn_save.setStyleSheet(f"""
            QPushButton {{ background:{COLOR_HEADER}; color:white; border:none;
                border-radius:4px; padding:6px; font-weight:bold; }}
            QPushButton:hover {{ background:#3D5570; }}
        """)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        self._apply_style()
        self.form_group.setEnabled(False)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background:white; font-family:"Microsoft YaHei",Arial; }
            QLabel { font-size:13px; color:#333; }
            QLineEdit, QTextEdit, QComboBox {
                border:1px solid #CCC; border-radius:4px;
                padding:5px 8px; font-size:13px;
                color:#333; background:white;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color:#3498DB; }
        """)

    def _on_enable_toggle(self, checked: bool):
        self.form_group.setEnabled(checked)

    def _on_preset_change(self, text: str):
        url = self.PRESETS.get(text, "")
        if url:
            self.edit_endpoint.setText(url)
            self.edit_endpoint.setReadOnly(True)
        else:
            self.edit_endpoint.setReadOnly(False)
            self.edit_endpoint.clear()

        # 默认模型名
        model_defaults = {
            "OpenAI (官方)":     "gpt-4o",
            "DeepSeek":          "deepseek-chat",
            "阿里云百炼 (Qwen)": "qwen-plus",
        }
        if text in model_defaults:
            self.edit_model.setText(model_defaults[text])

    def _load_config(self):
        self.chk_enable.setChecked(self.config.get('enabled', False))
        self.form_group.setEnabled(self.config.get('enabled', False))
        endpoint = self.config.get('endpoint', '')
        apikey   = self.config.get('apikey', '')
        model    = self.config.get('model', '')
        prompt   = self.config.get('prompt', '')

        self.edit_endpoint.setText(endpoint)
        self.edit_apikey.setText(apikey)
        self.edit_model.setText(model)
        self.edit_prompt.setPlainText(prompt)

        # 匹配预设
        for name, url in self.PRESETS.items():
            if url and url == endpoint:
                self.combo_preset.setCurrentText(name)
                self.edit_endpoint.setReadOnly(True)
                return
        self.combo_preset.setCurrentText("自定义端点")

    def _test_connection(self):
        endpoint = self.edit_endpoint.text().strip()
        apikey   = self.edit_apikey.text().strip()
        model    = self.edit_model.text().strip() or 'gpt-4o-mini'
        if not endpoint or not apikey:
            QMessageBox.warning(self, "提示", "请先填写 API 端点和 API Key")
            return

        try:
            import urllib.request, json
            url = endpoint.rstrip('/') + '/chat/completions'
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": "hello"}],
                "max_tokens": 5
            }).encode()
            req = urllib.request.Request(url, data=payload, method='POST')
            req.add_header('Content-Type', 'application/json')
            req.add_header('Authorization', f'Bearer {apikey}')
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                if 'choices' in data:
                    QMessageBox.information(self, "测试成功", "API 连接正常！")
                    return
            QMessageBox.warning(self, "测试失败", "接口返回异常，请检查配置")
        except Exception as e:
            QMessageBox.critical(self, "连接失败", f"错误信息：\n{e}")

    def _save(self):
        self.config = {
            'enabled':  self.chk_enable.isChecked(),
            'endpoint': self.edit_endpoint.text().strip(),
            'apikey':   self.edit_apikey.text().strip(),
            'model':    self.edit_model.text().strip(),
            'prompt':   self.edit_prompt.toPlainText().strip(),
        }
        self.accept()

    def get_config(self) -> dict:
        return self.config


# ═════════════════════════════════════════════════════════════════════════════
#  报表定制对话框
# ═════════════════════════════════════════════════════════════════════════════
class ReportCustomDialog(QDialog):
    """报表个性化定制对话框"""

    # 预设颜色主题
    COLOR_THEMES = {
        "默认深蓝": ("#2C3E50", "#3498DB"),
        "经典商务": ("#1A2530", "#4A90A4"),
        "科技蓝": ("#0D47A1", "#42A5F5"),
        "清新绿": ("#1B5E20", "#66BB6A"),
        "沉稳灰": ("#37474F", "#90A4AE"),
        "紫罗兰": ("#4A148C", "#CE93D8"),
        "暗夜黑": ("#263238", "#00BCD4"),
        "中国红": ("#B71C1C", "#FF7043"),
    }

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("报表个性化定制")
        self.setMinimumSize(640, 560)
        self.resize(680, 600)
        self.config = config.copy()
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # 标题
        title = QLabel("📊 报表个性化定制")
        title.setStyleSheet("font-size:16px; font-weight:bold; color:#2C3E50; padding:4px 0;")
        layout.addWidget(title)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:#DDD;")
        layout.addWidget(line)

        # 标签页
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # 1. 品牌信息页
        self.tabs.addTab(self._build_brand_tab(), "品牌信息")
        # 2. 颜色主题页
        self.tabs.addTab(self._build_theme_tab(), "颜色主题")
        # 3. LOGO与封面页
        self.tabs.addTab(self._build_logo_tab(), "LOGO & 封面")
        # 4. 显示内容页
        self.tabs.addTab(self._build_content_tab(), "显示内容")
        # 5. 高级设置页
        self.tabs.addTab(self._build_advanced_tab(), "高级设置")

        layout.addWidget(self.tabs, 1)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_reset = QPushButton("恢复默认")
        btn_reset.setFixedWidth(90)
        btn_reset.setStyleSheet("""
            QPushButton { background: white; color: #666; border:1px solid #CCC;
                          border-radius:4px; padding:6px; }
            QPushButton:hover { background: #F5F5F5; }
        """)
        btn_reset.clicked.connect(self._reset_to_default)
        btn_row.addWidget(btn_reset)

        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedWidth(80)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("保存")
        btn_save.setFixedWidth(80)
        btn_save.setStyleSheet("""
            QPushButton { background: #2C3E50; color: white; border: none;
                          border-radius:4px; padding:6px; font-weight:bold; }
            QPushButton:hover { background: #3D5570; }
        """)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)

        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: white; font-family: "Microsoft YaHei", Arial; }
            QLabel { font-size: 13px; color: #333; }
            QLineEdit, QTextEdit {
                border: 1px solid #CCC; border-radius: 4px;
                padding: 6px 8px; font-size: 13px; color: #333; background: white;
            }
            QLineEdit:focus, QTextEdit:focus { border-color: #3498DB; }
            QCheckBox { font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; }
            QGroupBox { font-size: 13px; color: #555; border: 1px solid #DDD;
                        border-radius: 5px; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
            QTabWidget::pane { border: 1px solid #DDD; border-radius: 4px; }
            QTabBar::tab {
                background: #F5F5F5; border: 1px solid #DDD; padding: 8px 16px;
                margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px;
            }
            QTabBar::tab:selected { background: white; border-bottom-color: white; color: #2C3E50; font-weight: bold; }
            QTabBar::tab:hover { background: #EBF5FB; }
            QComboBox {
                border: 1px solid #CCC; border-radius: 4px; padding: 6px 8px; font-size: 13px; color: #333; background: white;
            }
            QComboBox:hover { border-color: #3498DB; }
            QComboBox::drop-down {
                border: none; width: 24px; subcontrol-origin: padding; subcontrol-position: right center;
            }
            QComboBox::down-arrow {
                image: none; border-left: 4px solid transparent; border-right: 4px solid transparent;
                border-top: 6px solid #666; margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #CCC; background: white; selection-background-color: #3498DB; selection-color: white;
            }
            QPushButton#color_btn {
                border-radius: 6px; padding: 4px; font-weight: bold;
                color: white; text-shadow: 0 1px 2px rgba(0,0,0,0.3);
            }
            QPushButton#color_btn:hover {
                border: 2px solid #3498DB;
            }
        """)

    def _build_brand_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(14)

        # 公司名称
        grp = QGroupBox("公司名称")
        form = QFormLayout(grp)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.edit_company = QLineEdit()
        self.edit_company.setPlaceholderText("四川新数信息技术有限公司")
        form.addRow("公司名称:", self.edit_company)

        self.edit_footer = QLineEdit()
        self.edit_footer.setPlaceholderText("© 2024-2025 xxx公司 版权所有")
        form.addRow("版权文字:", self.edit_footer)

        layout.addWidget(grp)

        # 模板预览提示
        hint = QLabel("💡 提示：公司名称将显示在报表顶部品牌栏，版权文字显示在报表底部。")
        hint.setStyleSheet("color:#666; font-size:12px; padding:8px; background:#F9F9F9; border-radius:4px;")
        layout.addWidget(hint)

        layout.addStretch()
        return w

    def _build_theme_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(14)

        grp = QGroupBox("颜色主题")
        layout2 = QVBoxLayout(grp)
        layout2.setSpacing(10)

        # 预设主题选择
        row = QHBoxLayout()
        row.addWidget(QLabel("预设主题:"))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(list(self.COLOR_THEMES.keys()))
        self.combo_theme.currentTextChanged.connect(self._on_theme_changed)
        row.addWidget(self.combo_theme, 1)
        layout2.addLayout(row)

        # 自定义颜色
        row2 = QHBoxLayout()
        row2.setSpacing(12)

        col1 = QVBoxLayout()
        col1.addWidget(QLabel("主色调:"))
        self.btn_main_color = QPushButton()
        self.btn_main_color.setObjectName("color_btn")
        self.btn_main_color.setFixedSize(80, 36)
        self.btn_main_color.clicked.connect(lambda: self._pick_color(self.btn_main_color, "main"))
        col1.addWidget(self.btn_main_color)

        col2 = QVBoxLayout()
        col2.addWidget(QLabel("强调色:"))
        self.btn_accent_color = QPushButton()
        self.btn_accent_color.setObjectName("color_btn")
        self.btn_accent_color.setFixedSize(80, 36)
        self.btn_accent_color.clicked.connect(lambda: self._pick_color(self.btn_accent_color, "accent"))
        col2.addWidget(self.btn_accent_color)

        row2.addLayout(col1)
        row2.addLayout(col2)
        row2.addStretch()
        layout2.addLayout(row2)

        layout.addWidget(grp)

        # 预览效果
        grp2 = QGroupBox("预览效果")
        grp2_layout = QVBoxLayout(grp2)
        grp2_layout.setContentsMargins(10, 10, 10, 10)

        # 品牌栏预览
        preview_brand = QFrame()
        preview_brand.setFixedHeight(36)
        preview_brand.setStyleSheet("""
            QFrame { border: 1px solid #DDD; border-radius: 4px; background: #F5F5F5; }
        """)
        pv_brand_layout = QHBoxLayout(preview_brand)
        pv_brand_layout.setContentsMargins(8, 4, 8, 4)
        self.lbl_preview_brand = QLabel("品牌栏")
        self.lbl_preview_brand.setAlignment(Qt.AlignCenter)
        self.lbl_preview_brand.setStyleSheet("border-radius:4px; color: white; font-weight:bold; font-size:11px;")
        pv_brand_layout.addWidget(self.lbl_preview_brand)

        # 区块标题预览
        preview_section = QFrame()
        preview_section.setFixedHeight(32)
        preview_section.setStyleSheet("""
            QFrame { border: 1px solid #DDD; border-radius: 4px; background: #F5F5F5; }
        """)
        pv_section_layout = QHBoxLayout(preview_section)
        pv_section_layout.setContentsMargins(8, 4, 8, 4)
        self.lbl_preview_section = QLabel("区块标题")
        self.lbl_preview_section.setAlignment(Qt.AlignCenter)
        self.lbl_preview_section.setStyleSheet("border-radius:4px; color: white; font-weight:bold; font-size:11px;")
        pv_section_layout.addWidget(self.lbl_preview_section)

        grp2_layout.addWidget(preview_brand)
        grp2_layout.addWidget(preview_section)
        layout.addWidget(grp2, 0)

        layout.addStretch()
        return w

    def _build_logo_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(14)

        # LOGO设置
        grp = QGroupBox("公司 LOGO")
        form = QFormLayout(grp)
        form.setSpacing(10)

        self.chk_show_logo = QCheckBox("在报表中显示公司 LOGO")
        form.addRow("", self.chk_show_logo)

        row = QHBoxLayout()
        self.edit_logo_path = QLineEdit()
        self.edit_logo_path.setPlaceholderText("选择LOGO图片路径...")
        self.edit_logo_path.setReadOnly(True)
        row.addWidget(self.edit_logo_path, 1)

        btn_browse = QPushButton("浏览")
        btn_browse.setFixedWidth(60)
        btn_browse.clicked.connect(self._browse_logo)
        row.addWidget(btn_browse)
        form.addRow("图片路径:", row)

        layout.addWidget(grp)

        # 封面设置
        grp2 = QGroupBox("封面设置")
        form2 = QFormLayout(grp2)
        form2.setSpacing(10)

        self.edit_cover_title = QLineEdit()
        self.edit_cover_title.setPlaceholderText("自定义封面标题（留空使用项目名称）")
        form2.addRow("封面标题:", self.edit_cover_title)

        self.edit_watermark = QLineEdit()
        self.edit_watermark.setPlaceholderText("页眉水印文字（如：内部资料 严禁外传）")
        form2.addRow("水印文字:", self.edit_watermark)

        layout.addWidget(grp2)

        layout.addStretch()
        return w

    def _build_content_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(14)

        grp = QGroupBox("报表内容显示")
        vbox = QVBoxLayout(grp)
        vbox.setSpacing(8)

        self.chk_device_info = QCheckBox("显示设备信息（名称、IP、类型、端口等）")
        self.chk_device_info.setChecked(True)
        vbox.addWidget(self.chk_device_info)

        self.chk_cmd_output = QCheckBox("显示巡检命令输出")
        self.chk_cmd_output.setChecked(True)
        vbox.addWidget(self.chk_cmd_output)

        self.chk_ai_section = QCheckBox("显示 AI 分析区块")
        self.chk_ai_section.setChecked(True)
        vbox.addWidget(self.chk_ai_section)

        self.chk_edit_hint = QCheckBox("显示可编辑提示")
        self.chk_edit_hint.setChecked(True)
        vbox.addWidget(self.chk_edit_hint)

        layout.addWidget(grp)

        hint = QLabel("💡 提示：取消勾选的内容将不会出现在生成的报告中。")
        hint.setStyleSheet("color:#666; font-size:12px; padding:8px; background:#F9F9F9; border-radius:4px;")
        layout.addWidget(hint)

        layout.addStretch()
        return w

    def _build_advanced_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(14)

        grp = QGroupBox("字体设置")
        form = QFormLayout(grp)
        form.setSpacing(10)

        self.combo_font = QComboBox()
        self.combo_font.addItems(["Microsoft YaHei", "Segoe UI", "Arial", "SimSun", "SimHei"])
        form.addRow("正文字体:", self.combo_font)

        layout.addWidget(grp)

        grp2 = QGroupBox("自定义 CSS")
        vbox = QVBoxLayout(grp2)

        self.edit_custom_css = QTextEdit()
        self.edit_custom_css.setPlaceholderText("/* 在此输入自定义CSS样式 */\n.example { color: red; }")
        self.edit_custom_css.setFont(QFont("Consolas", 11))
        self.edit_custom_css.setFixedHeight(160)
        vbox.addWidget(self.edit_custom_css)

        layout.addWidget(grp2)

        layout.addStretch()
        return w

    def _on_theme_changed(self, theme_name: str):
        if theme_name in self.COLOR_THEMES:
            main, accent = self.COLOR_THEMES[theme_name]
            self._update_color_button(self.btn_main_color, main)
            self._update_color_button(self.btn_accent_color, accent)
            self._update_preview(main, accent)

    def _update_color_button(self, btn: QPushButton, color: str):
        """更新颜色按钮样式，显示颜色值文字"""
        btn.setText(color.upper())
        # 计算文字颜色（根据背景亮度）
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        text_color = "white" if (r*0.299 + g*0.587 + b*0.114) < 150 else "black"
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                border: 2px solid {color};
                border-radius: 6px;
                padding: 4px;
                font-weight: bold;
                font-size: 11px;
                color: {text_color};
            }}
            QPushButton:hover {{
                border: 3px solid #3498DB;
            }}
        """)

    def _update_preview(self, main_color: str, accent_color: str):
        # 品牌栏预览 - 渐变效果
        self.lbl_preview_brand.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {main_color}, stop:1 {accent_color});
            color: white; font-weight:bold; border-radius:4px; padding:4px;
        """)
        # 区块标题预览 - 渐变效果
        self.lbl_preview_section.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {accent_color}, stop:1 {main_color});
            color: white; font-weight:bold; border-radius:4px; padding:4px;
        """)

    def _pick_color(self, btn: QPushButton, color_type: str):
        from PyQt5.QtWidgets import QColorDialog
        from PyQt5.QtGui import QColor

        # 获取当前颜色
        current_text = btn.text()
        current_color = QColor(current_text) if current_text.startswith('#') else QColor("#3498DB")

        # 打开颜色选择对话框
        color = QColorDialog.getColor(current_color, self, "选择颜色")
        if color.isValid():
            hex_color = color.name().upper()
            self._update_color_button(btn, hex_color)
            # 获取当前颜色
            main_color = self.btn_main_color.text()
            accent_color = self.btn_accent_color.text()
            if color_type == "main":
                self._update_preview(hex_color, accent_color)
            else:
                self._update_preview(main_color, hex_color)

    def _browse_logo(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "选择LOGO图片", "", "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp)")
        if path:
            self.edit_logo_path.setText(path)

    def _reset_to_default(self):
        self.edit_company.setText("四川新数信息技术有限公司")
        self.edit_footer.setText("© 2024-2025 四川新数信息技术有限公司  版权所有  未经授权禁止复制或分发")
        self.combo_theme.setCurrentText("默认深蓝")
        self.chk_show_logo.setChecked(False)
        self.edit_logo_path.clear()
        self.edit_cover_title.clear()
        self.edit_watermark.clear()
        self.chk_device_info.setChecked(True)
        self.chk_cmd_output.setChecked(True)
        self.chk_ai_section.setChecked(True)
        self.chk_edit_hint.setChecked(True)
        self.combo_font.setCurrentText("Microsoft YaHei")
        self.edit_custom_css.clear()
        self._on_theme_changed("默认深蓝")

    def _load_config(self):
        self.edit_company.setText(self.config.get('company', ''))
        self.edit_footer.setText(self.config.get('footer_text', ''))

        # 颜色主题
        main = self.config.get('theme_color', '#2C3E50')
        accent = self.config.get('accent_color', '#3498DB')
        self._update_color_button(self.btn_main_color, main)
        self._update_color_button(self.btn_accent_color, accent)
        self._update_preview(main, accent)

        # 匹配预设主题
        for name, (m, a) in self.COLOR_THEMES.items():
            if m == main and a == accent:
                self.combo_theme.setCurrentText(name)
                break

        self.chk_show_logo.setChecked(self.config.get('show_logo', False))
        self.edit_logo_path.setText(self.config.get('logo_path', ''))
        self.edit_cover_title.setText(self.config.get('cover_title', ''))
        self.edit_watermark.setText(self.config.get('watermark', ''))

        self.chk_device_info.setChecked(self.config.get('show_device_info', True))
        self.chk_cmd_output.setChecked(self.config.get('show_cmd_output', True))
        self.chk_ai_section.setChecked(self.config.get('show_ai_section', True))
        self.chk_edit_hint.setChecked(self.config.get('show_edit_hint', True))

        font = self.config.get('report_font', 'Microsoft YaHei')
        self.combo_font.setCurrentText(font)
        self.edit_custom_css.setPlainText(self.config.get('custom_css', ''))

    def _save(self):
        # 从按钮文本获取颜色值
        self.config = {
            'company': self.edit_company.text().strip(),
            'theme_color': self.btn_main_color.text(),
            'accent_color': self.btn_accent_color.text(),
            'show_logo': self.chk_show_logo.isChecked(),
            'logo_path': self.edit_logo_path.text().strip(),
            'cover_title': self.edit_cover_title.text().strip(),
            'footer_text': self.edit_footer.text().strip(),
            'show_device_info': self.chk_device_info.isChecked(),
            'show_cmd_output': self.chk_cmd_output.isChecked(),
            'show_ai_section': self.chk_ai_section.isChecked(),
            'show_edit_hint': self.chk_edit_hint.isChecked(),
            'report_font': self.combo_font.currentText(),
            'watermark': self.edit_watermark.text().strip(),
            'custom_css': self.edit_custom_css.toPlainText().strip(),
        }
        self.accept()

    def get_config(self) -> dict:
        return self.config
