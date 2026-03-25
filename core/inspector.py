#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
巡检任务执行器 - 多线程并发执行
"""

import os
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Callable, Optional

from core.connector import DeviceConnector
from utils.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class DeviceInfo:
    """设备信息数据类"""
    def __init__(self, name: str, platform: str, host: str, port: int,
                 protocol: str, username: str, password: str,
                 enable_password: str = ''):
        self.name = name
        self.platform = platform.lower().strip()
        self.host = host.strip()
        self.port = int(port) if port else (22 if protocol.lower() == 'ssh' else 23)
        self.protocol = protocol.lower().strip()
        self.username = username.strip()
        self.password = password
        self.enable_password = enable_password

    def to_dict(self):
        return {
            'name': self.name,
            'platform': self.platform,
            'host': self.host,
            'port': self.port,
            'protocol': self.protocol,
            'username': self.username,
        }


class InspectionTask:
    """单设备巡检任务"""

    def __init__(self, device: DeviceInfo, commands: List[str],
                 output_dir: str, output_format: str = 'html',
                 project_name: str = '', report_config: dict = None):
        self.device        = device
        self.commands      = commands
        self.output_dir    = output_dir
        self.output_format = output_format
        self.project_name  = project_name
        self.report_config = report_config or {}
        self.status        = 'pending'
        self.results       = {}
        self.error_msg     = ''
        self.start_time    = None
        self.end_time      = None
        self.output_file   = ''

    def run(self, log_callback: Optional[Callable] = None,
            cmd_progress_callback: Optional[Callable] = None) -> bool:
        """执行巡检任务"""
        self.status = 'running'
        self.start_time = datetime.now()

        def _log(level, msg):
            logger.log(getattr(logging, level), msg)
            if log_callback:
                log_callback(level, msg)

        connector = DeviceConnector(
            host=self.device.host,
            port=self.device.port,
            username=self.device.username,
            password=self.device.password,
            enable_password=self.device.enable_password,
            platform=self.device.platform,
            protocol=self.device.protocol,
            timeout=30
        )

        try:
            _log('INFO', f"{self.device.name} ({self.device.host}) - 正在连接...")
            ok, err = connector.connect()
            if not ok:
                raise Exception(f"连接失败: {err}")

            _log('INFO', f"{self.device.name} ({self.device.host}) - 连接成功，开始执行命令...")

            total_cmds = len(self.commands)
            for idx, cmd in enumerate(self.commands):
                cmd = cmd.strip()
                if not cmd:
                    continue
                _log('DEBUG', f"{self.device.name} ({self.device.host}) - 执行命令 {idx+1}/{total_cmds}: {cmd}")
                try:
                    output = connector.execute_command(cmd)
                    self.results[cmd] = output
                    _log('DEBUG', f"{self.device.name} ({self.device.host}) - 命令 '{cmd}' 执行完成，输出行数: {len(output.splitlines())}")
                except Exception as e:
                    self.results[cmd] = f"[ERROR] {str(e)}"
                    _log('ERROR', f"{self.device.name} ({self.device.host}) - 命令 '{cmd}' 执行失败: {e}")
                if cmd_progress_callback:
                    cmd_progress_callback(self.device.host, idx + 1, total_cmds)

            self.status = 'success'
            _log('INFO', f"{self.device.name} ({self.device.host}) - 巡检完成，所有命令执行成功")

        except Exception as e:
            self.status = 'failed'
            self.error_msg = str(e)
            _log('ERROR', f"{self.device.name} ({self.device.host}) - 巡检失败: {e}")
        finally:
            connector.disconnect()
            self.end_time = datetime.now()

        # 生成报告
        if self.results or self.status == 'failed':
            try:
                report_gen = ReportGenerator(
                    self.device, self.results,
                    self.start_time, self.error_msg,
                    project_name=self.project_name,
                    report_config=self.report_config
                )
                self.output_file = report_gen.save(self.output_dir, self.output_format)
                _log('INFO', f"{self.device.name} ({self.device.host}) - 报告已生成: {self.output_file}")
            except Exception as e:
                _log('ERROR', f"{self.device.name} ({self.device.host}) - 生成报告失败: {e}")

        return self.status == 'success'


class InspectionEngine:
    """巡检引擎 - 管理多线程并发执行"""

    def __init__(self):
        self.tasks: List[InspectionTask] = []
        self.completed_tasks: List[InspectionTask] = []  # 存储完成的任务
        self._stop_event = threading.Event()
        self._executor: Optional[ThreadPoolExecutor] = None
        self._futures = []

        # 回调函数
        self.on_task_start: Optional[Callable] = None    # (task)
        self.on_task_done: Optional[Callable] = None     # (task)
        self.on_all_done: Optional[Callable] = None      # (success, failed)
        self.on_log: Optional[Callable] = None           # (level, message)
        self.on_progress: Optional[Callable] = None      # (completed, total)

    def _log(self, level: str, msg: str):
        if self.on_log:
            self.on_log(level, msg)

    def start(self, devices: List[DeviceInfo], commands_map: Dict[str, List[str]],
              output_dir: str, output_format: str = 'html',
              max_workers: int = 10, project_name: str = '',
              report_config: dict = None):
        """开始巡检"""
        self._stop_event.clear()
        os.makedirs(output_dir, exist_ok=True)

        # 构建任务列表
        self.tasks = []
        self.completed_tasks = []  # 清空上次结果
        for dev in devices:
            cmds = commands_map.get(dev.platform) or commands_map.get('default', [])
            task = InspectionTask(dev, cmds, output_dir, output_format,
                                  project_name=project_name,
                                  report_config=report_config)
            self.tasks.append(task)

        total = len(self.tasks)
        self._log('INFO', f"开始巡检，共 {total} 台设备，最大并发: {max_workers}")

        completed_count = [0]
        success_count = [0]
        failed_count = [0]
        count_lock = threading.Lock()

        def run_task(task: InspectionTask):
            if self._stop_event.is_set():
                task.status = 'cancelled'
                return

            if self.on_task_start:
                self.on_task_start(task)

            def log_cb(level, msg):
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self._log(level, f"[{ts}] [{level}] {msg}")

            task.run(log_callback=log_cb)

            with count_lock:
                completed_count[0] += 1
                if task.status == 'success':
                    success_count[0] += 1
                else:
                    failed_count[0] += 1

            # 保存完成的任务
            self.completed_tasks.append(task)
            
            if self.on_task_done:
                self.on_task_done(task)
            if self.on_progress:
                self.on_progress(completed_count[0], total)

        self._executor = ThreadPoolExecutor(max_workers=max_workers,
                                            thread_name_prefix='NetInspector')
        self._futures = [self._executor.submit(run_task, t) for t in self.tasks]

        def wait_all():
            for f in as_completed(self._futures):
                try:
                    f.result()
                except Exception as e:
                    self._log('ERROR', f"任务异常: {e}")
            self._executor.shutdown(wait=False)

            # 汇总
            failed_names = [t.device.name for t in self.tasks if t.status == 'failed']
            self._log('INFO', f"巡检完成: 成功 {success_count[0]} 个，失败 {failed_count[0]} 个")
            if failed_names:
                self._log('INFO', f"失败的设备: {', '.join(failed_names)}")
            self._log('INFO', f"结果已保存到: {output_dir}")

            if self.on_all_done:
                self.on_all_done(success_count[0], failed_count[0])

        t = threading.Thread(target=wait_all, daemon=True, name="InspectionWatcher")
        t.start()

    def stop(self):
        """停止巡检"""
        self._stop_event.set()
        if self._executor:
            self._executor.shutdown(wait=False)
        self._log('INFO', "用户已请求停止巡检...")
