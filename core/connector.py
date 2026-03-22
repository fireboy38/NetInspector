#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH/Telnet 连接核心模块
支持华为(Huawei)、H3C、Cisco、锐捷(Ruijie)等主流厂商

Telnet 实现说明：
  Python 3.13 移除了内置 telnetlib，改用 asyncio.open_connection 原生实现。
  为避免 asyncio 与 PyQt5 主线程冲突，每个 Telnet 连接在独立后台线程中
  运行自己的 event loop，所有异步操作通过 run_coroutine_threadsafe 提交。
"""

import time
import socket
import re
import logging
import asyncio
import threading
import concurrent.futures
from typing import List, Tuple

logger = logging.getLogger(__name__)


class DeviceConnector:
    """网络设备连接器，支持 SSH 和 Telnet"""

    PLATFORM_PROMPTS = {
        'huawei': [r'<[\w\-\.]+>', r'\[[\w\-\.]+\]'],
        'h3c':    [r'<[\w\-\.]+>', r'\[[\w\-\.]+\]'],
        'cisco':  [r'[\w\-]+[>#]', r'[\w\-]+\(config[^\)]*\)#'],
        'ruijie': [r'[\w\-]+[>#]', r'[\w\-]+\(config[^\)]*\)#'],
        'default': [r'[\w\-\.]+[>#\$]', r'<[\w\-\.]+>', r'\[[\w\-\.]+\]'],
    }

    def __init__(self, host: str, port: int, username: str, password: str,
                 enable_password: str = '', platform: str = 'default',
                 protocol: str = 'ssh', timeout: int = 30):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.enable_password = enable_password
        self.platform = platform.lower()
        self.protocol = protocol.lower()
        self.timeout = timeout

        # SSH 相关
        self._connection = None
        self._channel = None

        # Telnet 相关：后台线程 + 持久 loop
        self._telnet_loop: asyncio.AbstractEventLoop = None
        self._telnet_thread: threading.Thread = None
        self._telnet_reader: asyncio.StreamReader = None
        self._telnet_writer: asyncio.StreamWriter = None

    # ──────────────────────────────────────────────────
    #  公共接口
    # ──────────────────────────────────────────────────

    def connect(self) -> Tuple[bool, str]:
        if self.protocol == 'ssh':
            return self._connect_ssh()
        elif self.protocol == 'telnet':
            return self._connect_telnet()
        return False, f"不支持的协议: {self.protocol}"

    def execute_command(self, command: str, timeout: int = 30) -> str:
        """执行单条命令并返回输出"""
        try:
            self._send_raw(command)
            return self._collect_output(timeout)
        except Exception as e:
            logger.error(f"命令执行失败: {command}, 错误: {e}")
            raise

    def execute_commands(self, commands: List[str],
                         progress_callback=None) -> dict:
        """批量执行命令列表，返回 {命令: 输出} 字典"""
        results = {}
        total = len(commands)
        for idx, cmd in enumerate(commands):
            cmd = cmd.strip()
            try:
                output = self.execute_command(cmd)
                results[cmd] = output
            except Exception as e:
                results[cmd] = f"[ERROR] {e}"
            if progress_callback:
                progress_callback(idx + 1, total)
        return results

    def disconnect(self):
        try:
            if self.protocol == 'ssh':
                if self._channel:
                    self._channel.close()
                if self._connection:
                    self._connection.close()
            elif self.protocol == 'telnet':
                self._telnet_disconnect()
        except Exception as e:
            logger.warning(f"断开连接时出错: {e}")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    # ──────────────────────────────────────────────────
    #  SSH
    # ──────────────────────────────────────────────────

    def _connect_ssh(self) -> Tuple[bool, str]:
        try:
            import paramiko
            self._connection = paramiko.SSHClient()
            self._connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._connection.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False,
            )
            self._channel = self._connection.invoke_shell(width=512, height=64)
            self._channel.settimeout(self.timeout)
            time.sleep(1.5)
            self._ssh_recv()          # 清空 banner
            if self.platform in ('cisco', 'ruijie') and self.enable_password:
                self._ssh_enable()
            # 禁用分页（解决 -- More -- 问题）
            self._disable_paging()
            return True, ""
        except Exception as e:
            return False, str(e)

    def _ssh_enable(self):
        self._channel.send(b"enable\n")
        time.sleep(0.5)
        out = self._ssh_recv()
        if re.search(r'[Pp]assword', out):
            self._channel.send(self.enable_password.encode() + b"\n")
            time.sleep(0.5)
            self._ssh_recv()

    def _disable_paging(self):
        """禁用设备输出分页，解决 -- More -- 问题"""
        if self.platform == 'huawei':
            # 华为设备：临时禁用屏幕分页
            self._send_raw('screen-length 0 temporary')
            time.sleep(0.3)
            self._recv_all()
        elif self.platform == 'h3c':
            # H3C 设备
            self._send_raw('screen-length disable')
            time.sleep(0.3)
            self._recv_all()
        elif self.platform == 'cisco':
            # 思科设备
            self._send_raw('terminal length 0')
            time.sleep(0.3)
            self._recv_all()
        elif self.platform == 'ruijie':
            # 锐捷设备
            self._send_raw('terminal length 0')
            time.sleep(0.3)
            self._recv_all()

    def _ssh_recv(self, wait: float = 0.5) -> str:
        time.sleep(wait)
        buf = b""
        while self._channel.recv_ready():
            buf += self._channel.recv(65535)
            time.sleep(0.05)
        return buf.decode('utf-8', errors='replace')

    # ──────────────────────────────────────────────────
    #  Telnet  — 后台持久 event loop
    # ──────────────────────────────────────────────────

    def _start_telnet_loop(self):
        """在后台线程启动并保持 event loop 运行"""
        self._telnet_loop = asyncio.new_event_loop()
        self._telnet_loop.run_forever()

    def _run_async(self, coro, timeout=None):
        """把协程提交到后台 loop，同步等待结果"""
        future = asyncio.run_coroutine_threadsafe(coro, self._telnet_loop)
        return future.result(timeout=timeout or self.timeout + 5)

    def _connect_telnet(self) -> Tuple[bool, str]:
        try:
            # 启动后台 loop 线程
            self._telnet_thread = threading.Thread(
                target=self._start_telnet_loop, daemon=True)
            self._telnet_thread.start()
            time.sleep(0.1)           # 等待 loop 就绪

            return self._run_async(self._telnet_login_async(), timeout=self.timeout + 10)
        except Exception as e:
            return False, f"Telnet连接失败: {e}"

    async def _telnet_login_async(self) -> Tuple[bool, str]:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout
            )
            self._telnet_reader = reader
            self._telnet_writer = writer

            # 读欢迎信息
            await asyncio.sleep(0.8)
            welcome = await self._async_read(timeout=5)
            logger.debug(f"[Telnet] 欢迎信息: {welcome[:200]!r}")

            # 若没有登录提示，先发回车
            login_kws = ["login:", "username:", "user name:"]
            if not any(k in welcome.lower() for k in login_kws):
                writer.write(b"\r\n")
                await writer.drain()
                await asyncio.sleep(1.0)
                extra = await self._async_read(timeout=5)
                welcome += extra
                logger.debug(f"[Telnet] 回车后: {extra[:200]!r}")

            if any(k in welcome.lower() for k in login_kws):
                # 发用户名
                writer.write(self.username.encode() + b"\r\n")
                await writer.drain()
                await asyncio.sleep(0.5)
                after_user = await self._async_read(timeout=10)
                logger.debug(f"[Telnet] 用户名后: {after_user[:200]!r}")

                # 发密码
                writer.write(self.password.encode() + b"\r\n")
                await writer.drain()
                await asyncio.sleep(2.0)
                after_pass = await self._async_read(timeout=10)
                logger.debug(f"[Telnet] 密码后: {after_pass[:200]!r}")

                if any(k in after_pass.lower() for k in
                       ["login failed", "login incorrect", "authentication failed",
                        "bad password", "access denied", "error"]):
                    writer.close()
                    return False, "用户名或密码错误"
            else:
                logger.warning("[Telnet] 未检测到登录提示，直接尝试继续")

            # Cisco/锐捷 enable
            if self.platform in ('cisco', 'ruijie') and self.enable_password:
                writer.write(b"enable\r\n")
                await writer.drain()
                await asyncio.sleep(0.5)
                en_out = await self._async_read(timeout=5)
                if re.search(r'[Pp]assword', en_out):
                    writer.write(self.enable_password.encode() + b"\r\n")
                    await writer.drain()
                    await asyncio.sleep(0.5)
                    await self._async_read(timeout=3)

            # 禁用分页（解决 -- More -- 问题）
            await self._async_disable_paging()

            logger.info(f"[Telnet] 连接成功: {self.host}")
            return True, ""

        except asyncio.TimeoutError:
            return False, "连接超时"
        except Exception as e:
            return False, f"连接失败: {e}"

    async def _async_read(self, timeout: float = 3) -> str:
        """非阻塞读取所有可用数据，返回字符串"""
        buf = b""
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break
            try:
                chunk = await asyncio.wait_for(
                    self._telnet_reader.read(4096),
                    timeout=min(remaining, 0.5)
                )
                if not chunk:
                    break
                buf += chunk
                # 短暂等待看是否还有更多数据
                await asyncio.sleep(0.05)
            except asyncio.TimeoutError:
                break
        return buf.decode('utf-8', errors='replace')

    async def _async_send(self, data: bytes):
        self._telnet_writer.write(data)
        await self._telnet_writer.drain()

    async def _async_disable_paging(self):
        """异步禁用设备输出分页（Telnet用）"""
        if self.platform == 'huawei':
            self._telnet_send(b"screen-length 0 temporary\r\n")
            await asyncio.sleep(0.3)
            await self._async_read()
        elif self.platform == 'h3c':
            self._telnet_send(b"screen-length disable\r\n")
            await asyncio.sleep(0.3)
            await self._async_read()
        elif self.platform == 'cisco':
            self._telnet_send(b"terminal length 0\r\n")
            await asyncio.sleep(0.3)
            await self._async_read()
        elif self.platform == 'ruijie':
            self._telnet_send(b"terminal length 0\r\n")
            await asyncio.sleep(0.3)
            await self._async_read()

    def _telnet_send(self, data: bytes):
        self._run_async(self._async_send(data), timeout=10)

    def _telnet_recv(self, wait: float = 0.5, read_timeout: float = 2) -> str:
        time.sleep(wait)
        return self._run_async(self._async_read(timeout=read_timeout), timeout=read_timeout + 5)

    def _telnet_disconnect(self):
        if self._telnet_writer:
            try:
                self._run_async(self._async_close(), timeout=5)
            except Exception:
                pass
        if self._telnet_loop and self._telnet_loop.is_running():
            self._telnet_loop.call_soon_threadsafe(self._telnet_loop.stop)

    async def _async_close(self):
        self._telnet_writer.close()
        try:
            await self._telnet_writer.wait_closed()
        except Exception:
            pass

    # ──────────────────────────────────────────────────
    #  通用发送 / 接收
    # ──────────────────────────────────────────────────

    def _send_raw(self, cmd: str):
        if self.protocol == 'ssh':
            self._channel.send(cmd.encode() + b"\n")
        elif self.protocol == 'telnet':
            self._telnet_send(cmd.encode() + b"\r\n")

    def _recv_all(self, wait: float = 0.3) -> str:
        if self.protocol == 'ssh':
            return self._ssh_recv(wait=wait)
        elif self.protocol == 'telnet':
            return self._telnet_recv(wait=wait, read_timeout=1.5)
        return ""

    # ──────────────────────────────────────────────────
    #  输出收集（处理分页）
    # ──────────────────────────────────────────────────

    def _collect_output(self, timeout: int) -> str:
        prompts = self.PLATFORM_PROMPTS.get(self.platform, self.PLATFORM_PROMPTS['default'])
        prompt_re = re.compile('|'.join(prompts))
        more_re   = re.compile(r'--\s*[Mm]ore\s*--|<-+\s*[Mm]ore\s*-+>|\[Q to quit\]')

        full = []
        buffer = ""
        deadline = time.time() + timeout

        while time.time() < deadline:
            chunk = self._recv_all(wait=0.3)
            if not chunk:
                # 没有新数据，检查是否已在提示符
                last = buffer.rsplit('\n', 1)[-1].strip() if buffer else ''
                if last and prompt_re.search(last):
                    break
                # 再等一轮
                chunk = self._recv_all(wait=0.5)
                if not chunk:
                    break

            buffer += chunk
            full.append(chunk)

            # 处理 --More--
            if more_re.search(buffer):
                self._send_raw(' ')
                # 去掉 More 行
                buffer = re.sub(r'--\s*[Mm]ore\s*--[^\r\n]*', '', buffer)
                continue

            # 检测提示符
            last = buffer.rsplit('\n', 1)[-1].strip() if buffer else ''
            if last and prompt_re.search(last):
                break

        raw = ''.join(full)
        # 清理 ANSI 转义码
        raw = re.sub(r'\x1b\[[0-9;]*[mABCDHJKf]', '', raw)
        # 去掉第一行（命令回显）和最后一行（提示符）
        lines = raw.split('\n')
        if len(lines) > 2:
            lines = lines[1:-1]
        elif len(lines) == 2:
            lines = []
        return '\n'.join(lines).strip()
