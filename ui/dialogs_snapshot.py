#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快照管理和对比对话框
"""

import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QMessageBox, QTableWidget, QTableWidgetItem, 
    QHeaderView, QListWidget, QTreeWidget, QTreeWidgetItem,
    QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor


class SnapshotManagerDialog(QDialog):
    """快照管理对话框"""

    def __init__(self, snapshot_manager, parent=None):
        super().__init__(parent)
        self.snapshot_manager = snapshot_manager
        self.selected_snapshot = None
        self.setWindowTitle("快照管理")
        self.setMinimumSize(700, 500)
        self._init_ui()
        self._load_snapshots()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 标题
        title = QLabel("配置快照管理")
        title.setStyleSheet("font-size:15px; font-weight:600; color:#1A365D;")
        layout.addWidget(title)

        # 说明
        hint = QLabel("保存设备配置快照，用于后续对比变更。")
        hint.setStyleSheet("color:#6B7280; font-size:12px;")
        layout.addWidget(hint)

        # 筛选
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("设备筛选:"))
        self.combo_device = QComboBox()
        self.combo_device.addItem("全部设备")
        self.combo_device.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.combo_device, 1)
        layout.addLayout(filter_layout)

        # 快照列表
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["时间", "设备", "IP地址", "描述", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setStyleSheet("""
            QTableWidget { border:1px solid #E5E7EB; border-radius:6px; background:white; }
            QHeaderView::section { background:#1A365D; color:white; padding:8px; font-weight:600; border:none; border-right:1px solid rgba(255,255,255,0.1); }
            QTableWidget::item { padding:6px 8px; border-bottom:1px solid #E5E7EB; color:#1F2937; }
            QTableWidget::item:selected { background:#2563EB; color:white; }
            QTableWidget::item:selected:alternate { background:#1D4ED8; color:white; }
        """)
        layout.addWidget(self.table)

        # 按钮
        btn_layout = QHBoxLayout()
        
        self.btn_view = QPushButton("查看详情")
        self.btn_view.clicked.connect(self._view_snapshot)
        self.btn_view.setEnabled(False)
        btn_layout.addWidget(self.btn_view)

        self.btn_compare = QPushButton("对比选中")
        self.btn_compare.clicked.connect(self._compare_snapshots)
        self.btn_compare.setEnabled(False)
        btn_layout.addWidget(self.btn_compare)

        btn_layout.addStretch()

        self.btn_delete = QPushButton("删除")
        self.btn_delete.setStyleSheet("background:#DC2626; color:white; border:none; border-radius:4px; padding:6px 14px;")
        self.btn_delete.clicked.connect(self._delete_snapshot)
        self.btn_delete.setEnabled(False)
        btn_layout.addWidget(self.btn_delete)

        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

        # 连接选择信号
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    def _load_snapshots(self):
        """加载快照列表"""
        try:
            snapshots = self.snapshot_manager.get_snapshots()
            
            # 更新设备筛选列表（断开信号避免递归）
            self.combo_device.currentTextChanged.disconnect(self._on_filter_changed)
            devices = set(s.get('device_host', '') for s in snapshots if s.get('device_host'))
            current_text = self.combo_device.currentText()
            self.combo_device.clear()
            self.combo_device.addItem("全部设备")
            for device in sorted(devices):
                self.combo_device.addItem(device)
            if current_text in [self.combo_device.itemText(i) for i in range(self.combo_device.count())]:
                self.combo_device.setCurrentText(current_text)
            self.combo_device.currentTextChanged.connect(self._on_filter_changed)

            # 填充表格
            self.table.setRowCount(len(snapshots))
            for i, snap in enumerate(snapshots):
                # 时间
                created_at = snap.get('created_at', '')
                dt = created_at[:19].replace('T', ' ') if created_at else ''
                self.table.setItem(i, 0, QTableWidgetItem(dt))
                # 设备名
                self.table.setItem(i, 1, QTableWidgetItem(snap.get('device_name', '')))
                # IP
                self.table.setItem(i, 2, QTableWidgetItem(snap.get('device_host', '')))
                # 描述
                self.table.setItem(i, 3, QTableWidgetItem(snap.get('description', '')))
                # ID (隐藏)
                snap_id = snap.get('id', '')
                item = QTableWidgetItem(snap_id)
                item.setData(Qt.UserRole, snap_id)
                self.table.setItem(i, 4, item)
        except Exception as e:
            import traceback
            print(f"加载快照列表出错: {e}")
            print(traceback.format_exc())
            QMessageBox.warning(self, "错误", f"加载快照列表失败: {e}")

    def _on_filter_changed(self, text):
        """筛选设备"""
        try:
            if text == "全部设备":
                self._load_snapshots()
            else:
                snapshots = self.snapshot_manager.get_snapshots(text)
                self.table.setRowCount(len(snapshots))
                for i, snap in enumerate(snapshots):
                    created_at = snap.get('created_at', '')
                    dt = created_at[:19].replace('T', ' ') if created_at else ''
                    self.table.setItem(i, 0, QTableWidgetItem(dt))
                    self.table.setItem(i, 1, QTableWidgetItem(snap.get('device_name', '')))
                    self.table.setItem(i, 2, QTableWidgetItem(snap.get('device_host', '')))
                    self.table.setItem(i, 3, QTableWidgetItem(snap.get('description', '')))
                    snap_id = snap.get('id', '')
                    item = QTableWidgetItem(snap_id)
                    item.setData(Qt.UserRole, snap_id)
                    self.table.setItem(i, 4, item)
        except Exception as e:
            import traceback
            print(f"筛选快照出错: {e}")
            print(traceback.format_exc())
            QMessageBox.warning(self, "错误", f"筛选快照失败: {e}")

    def _on_selection_changed(self):
        """选择变化"""
        selected = self.table.selectedItems()
        has_selection = len(selected) > 0
        self.btn_view.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)
        self.btn_compare.setEnabled(has_selection)

    def _view_snapshot(self):
        """查看快照详情"""
        row = self.table.currentRow()
        if row < 0:
            return
        snapshot_id = self.table.item(row, 4).data(Qt.UserRole)
        snapshot = self.snapshot_manager.load_snapshot(snapshot_id)
        if not snapshot:
            QMessageBox.warning(self, "错误", "无法加载快照")
            return

        # 显示详情对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"快照详情 - {snapshot.device_name}")
        dialog.setMinimumSize(600, 400)
        layout = QVBoxLayout(dialog)

        info = QLabel(f"设备: {snapshot.device_name} ({snapshot.device_host})<br>"
                     f"时间: {snapshot.created_at[:19].replace('T', ' ')}<br>"
                     f"描述: {snapshot.description}")
        info.setStyleSheet("background:#F0F2F5; padding:10px; border-radius:4px;")
        layout.addWidget(info)

        # 命令输出列表
        list_widget = QListWidget()
        for cmd in snapshot.commands_output.keys():
            list_widget.addItem(cmd)
        layout.addWidget(QLabel("包含命令:"))
        layout.addWidget(list_widget)

        btn = QPushButton("关闭")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)

        dialog.exec_()

    def _compare_snapshots(self):
        """对比快照"""
        row = self.table.currentRow()
        if row < 0:
            return
        
        snapshot_id = self.table.item(row, 4).data(Qt.UserRole)
        snapshot = self.snapshot_manager.load_snapshot(snapshot_id)
        if not snapshot:
            return

        # 获取该设备的其他快照
        snapshots = self.snapshot_manager.get_snapshots(snapshot.device_host)
        if len(snapshots) < 2:
            QMessageBox.information(self, "提示", "该设备只有一个快照，无法对比")
            return

        # 使用第一个其他快照进行对比
        other_id = [s['id'] for s in snapshots if s['id'] != snapshot_id][0]
        
        # 打开对比对话框
        dialog = SnapshotCompareDialog(self.snapshot_manager, other_id, snapshot_id, self)
        dialog.exec_()

    def _delete_snapshot(self):
        """删除快照"""
        row = self.table.currentRow()
        if row < 0:
            return
        
        snapshot_id = self.table.item(row, 4).data(Qt.UserRole)
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个快照吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.snapshot_manager.delete_snapshot(snapshot_id):
                self._load_snapshots()
                QMessageBox.information(self, "成功", "快照已删除")
            else:
                QMessageBox.warning(self, "错误", "删除失败")


class SnapshotCompareDialog(QDialog):
    """快照对比对话框"""

    def __init__(self, snapshot_manager, old_id, new_id, parent=None):
        super().__init__(parent)
        self.snapshot_manager = snapshot_manager
        self.old_id = old_id
        self.new_id = new_id
        self.setWindowTitle("配置对比")
        self.setMinimumSize(900, 600)
        self._init_ui()
        self._load_comparison()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 标题
        self.title_label = QLabel("配置对比")
        self.title_label.setStyleSheet("font-size:15px; font-weight:600; color:#1A365D;")
        layout.addWidget(self.title_label)

        # 对比结果表格
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["命令", "状态", "相似度", "变更详情"])
        self.tree.setColumnWidth(0, 250)
        self.tree.setColumnWidth(1, 80)
        self.tree.setColumnWidth(2, 80)
        self.tree.setColumnWidth(3, 400)
        self.tree.setStyleSheet("""
            QTreeWidget { border:1px solid #E5E7EB; border-radius:6px; background:white; }
            QHeaderView::section { background:#1A365D; color:white; padding:8px; font-weight:600; border:none; }
            QTreeWidget::item { padding:5px 8px; border-bottom:1px solid #F3F4F6; color:#1F2937; }
            QTreeWidget::item:selected { background:#2563EB; color:white; }
        """)
        layout.addWidget(self.tree)

        # 按钮
        btn_layout = QHBoxLayout()
        
        self.btn_export = QPushButton("导出HTML报告")
        self.btn_export.clicked.connect(self._export_report)
        btn_layout.addWidget(self.btn_export)

        btn_layout.addStretch()

        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def _load_comparison(self):
        """加载对比结果"""
        try:
            results = self.snapshot_manager.compare_snapshots(self.old_id, self.new_id)
            
            old_snap = self.snapshot_manager.load_snapshot(self.old_id)
            new_snap = self.snapshot_manager.load_snapshot(self.new_id)
            
            self.title_label.setText(f"配置对比: {old_snap.device_name} - "
                                    f"{old_snap.created_at[:10]} vs {new_snap.created_at[:10]}")

            self.tree.clear()
            for result in results:
                item = QTreeWidgetItem()
                item.setText(0, result.command)
                
                if result.has_changed:
                    item.setText(1, "变更")
                    item.setBackground(1, QColor("#FEE2E2"))
                else:
                    item.setText(1, "一致")
                    item.setBackground(1, QColor("#D1FAE5"))
                
                item.setText(2, f"{result.similarity*100:.1f}%")
                
                if result.has_changed:
                    detail = f"+{len(result.added_lines)} / -{len(result.removed_lines)}"
                    item.setText(3, detail)
                    
                    # 添加子项显示详细变更
                    if result.removed_lines:
                        child = QTreeWidgetItem(item)
                        child.setText(0, "删除:")
                        child.setText(3, f"{len(result.removed_lines)} 行")
                        child.setForeground(3, QColor("#DC2626"))
                    
                    if result.added_lines:
                        child = QTreeWidgetItem(item)
                        child.setText(0, "新增:")
                        child.setText(3, f"{len(result.added_lines)} 行")
                        child.setForeground(3, QColor("#059669"))
                else:
                    item.setText(3, "无变更")
                
                self.tree.addTopLevelItem(item)
                
            # 展开所有项
            self.tree.expandAll()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"对比失败: {e}")

    def _export_report(self):
        """导出对比报告"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存对比报告", 
            f"对比报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            "HTML文件 (*.html)"
        )
        
        if not file_path:
            return

        try:
            results = self.snapshot_manager.compare_snapshots(self.old_id, self.new_id)
            old_snap = self.snapshot_manager.load_snapshot(self.old_id)
            new_snap = self.snapshot_manager.load_snapshot(self.new_id)
            
            html = self.snapshot_manager.generate_diff_report(
                results,
                f"{old_snap.created_at[:10]} {old_snap.description}",
                f"{new_snap.created_at[:10]} {new_snap.description}"
            )
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            QMessageBox.information(self, "成功", f"报告已保存到:\n{file_path}")
            
            # 自动打开
            os.startfile(file_path)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {e}")
