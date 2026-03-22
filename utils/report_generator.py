#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成器 - 支持 HTML / TXT 格式
四川新数信息技术有限公司  网络设备巡检系统
"""

import os
import html as html_lib
from datetime import datetime

COMPANY     = "四川新数信息技术有限公司"
SYSTEM_NAME = "网络设备巡检系统"
VERSION     = "V1.0.1"
COPYRIGHT   = f"© 2024-2025 {COMPANY}  版权所有"


class ReportGenerator:
    """巡检报告生成器"""

    # 默认配置
    DEFAULT_CONFIG = {
        'company':        '四川新数信息技术有限公司',
        'theme_color':    '#2C3E50',
        'accent_color':   '#3498DB',
        'show_logo':      False,
        'logo_path':      '',
        'cover_title':    '',
        'footer_text':   '© 2024-2025 四川新数信息技术有限公司  版权所有  未经授权禁止复制或分发',
        'show_device_info':   True,
        'show_cmd_output':    True,
        'show_ai_section':    True,
        'show_edit_hint':     True,
        'report_font':        'Microsoft YaHei',
        'watermark':          '',
        'custom_css':         '',
    }

    def __init__(self, device, results: dict, start_time: datetime,
                 error_msg: str = '', project_name: str = '', report_config: dict = None):
        self.device       = device
        self.results      = results
        self.start_time   = start_time
        self.error_msg    = error_msg
        self.project_name = project_name or '未命名项目'
        self.cfg = {**self.DEFAULT_CONFIG, **(report_config or {})}

    def save(self, output_dir: str, fmt: str = 'html') -> str:
        """保存报告到目录，返回文件路径"""
        ts        = self.start_time.strftime('%Y%m%d_%H%M%S')
        safe_name = self.device.name.replace('/', '_').replace('\\', '_')
        filename  = f"{safe_name}_{ts}.{fmt}"
        filepath  = os.path.join(output_dir, filename)

        os.makedirs(output_dir, exist_ok=True)

        content = self._generate_html() if fmt == 'html' else self._generate_txt()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    # ─────────────────────────────────────────────────────
    #  HTML 报告
    # ─────────────────────────────────────────────────────
    def _generate_html(self) -> str:
        # 使用配置中的值
        company = self.cfg.get('company') or COMPANY
        system_name = SYSTEM_NAME
        version = VERSION
        theme_color = self.cfg.get('theme_color', '#2C3E50')
        accent_color = self.cfg.get('accent_color', '#3498DB')
        footer_text = self.cfg.get('footer_text') or COPYRIGHT
        font_family = self.cfg.get('report_font', 'Microsoft YaHei')
        watermark = self.cfg.get('watermark', '')
        custom_css = self.cfg.get('custom_css', '')

        # 根据配置决定显示哪些区块
        show_device = self.cfg.get('show_device_info', True)
        show_cmd = self.cfg.get('show_cmd_output', True)
        show_ai = self.cfg.get('show_ai_section', True)
        show_hint = self.cfg.get('show_edit_hint', True)

        # 生成命令输出区块
        cmd_blocks = ''
        if show_cmd:
            for cmd, output in self.results.items():
                escaped = html_lib.escape(output or '[无输出]')
                cmd_blocks += f"""
        <div class="cmd-block">
            <div class="cmd-header">&#x25B6; {html_lib.escape(cmd)}</div>
            <pre class="cmd-output" contenteditable="true">{escaped}</pre>
        </div>"""

        # 错误区块
        error_section = ''
        if self.error_msg:
            error_section = f"""
        <div class="error-box">
            <strong>&#x26A0; 连接/执行错误：</strong> {html_lib.escape(self.error_msg)}
        </div>"""

        generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        start_str = self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else '-'

        # 设备信息区块
        device_section = ''
        if show_device:
            device_section = f"""
    <!-- 设备信息 -->
    <div class="section">
        <div class="section-title">&#x1F5A5; 设备信息</div>
        <table class="info-table">
            <tr>
                <td>设备名称</td><td>{html_lib.escape(self.device.name)}</td>
                <td>IP 地址</td><td>{html_lib.escape(self.device.host)}</td>
            </tr>
            <tr>
                <td>设备类型</td><td>{html_lib.escape(self.device.platform)}</td>
                <td>巡检时间</td><td>{start_str}</td>
            </tr>
            <tr>
                <td>连接协议</td><td>{html_lib.escape(self.device.protocol).upper()}</td>
                <td>端口号</td><td>{self.device.port}</td>
            </tr>
        </table>
    </div>"""

        # 编辑提示区块
        edit_hint_section = ''
        if show_hint:
            edit_hint_section = '<div class="edit-hint">&#x270F;  以下输出区域支持直接编辑，修改后可通过浏览器【另存为】保存修订版本。</div>'

        # AI区块（隐藏，由AI分析器后续填充）
        ai_section = ''
        if show_ai:
            ai_section = """
    <!-- AI 分析区块（占位，由 AiAnalyzer 填充） -->
    <div class="ai-section" id="ai-analysis-section" style="display:none;">
        <div class="ai-section-title">&#x1F916; AI 智能分析结果</div>
        <div class="ai-content" id="ai-analysis-content"></div>
    </div>"""

        # 封面标题
        cover_title = self.cfg.get('cover_title') or self.project_name

        # 水印
        watermark_html = ''
        if watermark:
            watermark_html = f'.watermark {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-30deg); font-size: 60px; color: rgba(0,0,0,0.08); pointer-events: none; z-index: 9999; white-space: nowrap; }}'

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>巡检报告 · {html_lib.escape(self.device.name)} · {html_lib.escape(cover_title)}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: '{font_family}', 'Segoe UI', Arial, sans-serif;
            background: #f0f2f5;
            color: #2d3436;
        }}
        {watermark_html}
        .watermark-text {{ {watermark_html} }}
        /* ─── 顶部品牌栏 ─── */
        .brand-bar {{
            background: linear-gradient(135deg, {theme_color} 0%, {theme_color} 60%, {accent_color} 100%);
            color: white;
            padding: 14px 36px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            text-shadow: 0 1px 2px rgba(0,0,0,0.2);
        }}
        .brand-bar .company {{ font-size: 1.1em; font-weight: bold; letter-spacing: 1px; }}
        .brand-bar .sys-name {{ font-size: 0.9em; opacity: 0.85; margin-top: 2px; }}
        .brand-bar .version  {{ font-size: 0.82em; opacity: 0.7; }}
        /* ─── 项目标题 ─── */
        .project-header {{
            background: white;
            padding: 18px 36px;
            border-bottom: 2px solid #E8ECF0;
        }}
        .project-header h1 {{
            font-size: 1.4em;
            color: {theme_color};
            font-weight: bold;
        }}
        .project-header .sub {{
            font-size: 0.88em;
            color: #888;
            margin-top: 4px;
        }}
        /* ─── 主内容 ─── */
        .container {{ max-width: 1140px; margin: 24px auto; padding: 0 24px; }}
        .section {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.07);
            margin-bottom: 24px;
            overflow: hidden;
        }}
        .section-title {{
            background: linear-gradient(90deg, {accent_color}, {theme_color});
            color: white;
            padding: 10px 20px;
            font-size: 0.95em;
            font-weight: bold;
            letter-spacing: 1px;
            border-bottom: 2px solid {theme_color};
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .info-table {{ width: 100%; border-collapse: collapse; }}
        .info-table td {{
            padding: 10px 16px;
            border-bottom: 1px solid #ecf0f1;
            font-size: 0.94em;
        }}
        .info-table td:first-child {{
            font-weight: bold;
            background: #f8f9fa;
            width: 140px;
            color: #555;
        }}
        /* ─── 命令输出 ─── */
        .cmd-block {{ margin: 0; }}
        .cmd-header {{
            background: #1a1a2e;
            color: #e0e0e0;
            padding: 8px 16px;
            font-family: 'Courier New', monospace;
            font-size: 0.86em;
            letter-spacing: 0.5px;
        }}
        .cmd-output {{
            background: #1e1e2e;
            color: #a8d8a8;
            padding: 14px 18px;
            font-family: 'Courier New', Consolas, monospace;
            font-size: 0.84em;
            white-space: pre-wrap;
            word-break: break-all;
            line-height: 1.6;
            border-bottom: 1px solid #2a2a3a;
            outline: none;
        }}
        .cmd-output:focus {{
            background: #16213e;
            box-shadow: inset 0 0 0 2px {accent_color};
        }}
        .edit-hint {{
            background: #FFF8E1;
            border-left: 4px solid #F39C12;
            padding: 8px 16px;
            font-size: 0.82em;
            color: #856404;
        }}
        /* ─── 错误框 ─── */
        .error-box {{
            background: #ffeaea;
            border-left: 4px solid #e74c3c;
            padding: 12px 18px;
            margin: 15px;
            border-radius: 4px;
            color: #c0392b;
        }}
        /* ─── AI 分析区块 ─── */
        .ai-section {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.07);
            margin-bottom: 24px;
            overflow: hidden;
        }}
        .ai-section-title {{
            background: linear-gradient(90deg, {accent_color}, {theme_color});
            color: white;
            padding: 10px 20px;
            font-size: 0.95em;
            font-weight: bold;
            letter-spacing: 1px;
        }}
        .ai-content {{
            padding: 16px 20px;
            font-size: 0.93em;
            line-height: 1.8;
            color: #333;
            white-space: pre-wrap;
        }}
        /* ─── 底部版权 ─── */
        .footer {{
            background: {theme_color};
            color: white;
            text-align: center;
            padding: 16px;
            font-size: 0.82em;
            letter-spacing: 0.5px;
        }}
        .footer .copyright {{ opacity: 0.85; margin-top: 4px; }}
        /* 自定义CSS */
        {custom_css}
    </style>
</head>
<body>
{watermark_html and f'<div class="watermark-text">{html_lib.escape(watermark)}</div>' or ''}

<!-- 品牌栏 -->
<div class="brand-bar">
    <div>
        <div class="company">{html_lib.escape(company)}</div>
        <div class="sys-name">{html_lib.escape(system_name)}</div>
    </div>
    <div class="version">{html_lib.escape(version)}</div>
</div>

<!-- 项目标题 -->
<div class="project-header">
    <h1>&#x1F4CB; {html_lib.escape(cover_title)}</h1>
    <div class="sub">巡检报告  ·  生成时间：{generated_at}</div>
</div>

<div class="container">

    {device_section}

    {error_section}

    <!-- 命令输出 -->
    {f'''
    <div class="section">
        <div class="section-title">&#x1F4E1; 巡检命令输出</div>
        {edit_hint_section}
        {cmd_blocks if cmd_blocks else '<p style="padding:16px;color:#999">无执行结果</p>'}
    </div>''' if show_cmd else ''}

    {ai_section}

</div>

<!-- 版权页脚 -->
<div class="footer">
    <div>{html_lib.escape(system_name)}  {html_lib.escape(version)}</div>
    <div class="copyright">{html_lib.escape(footer_text)}</div>
</div>

</body>
</html>"""

    # ─────────────────────────────────────────────────────
    #  TXT 报告
    # ─────────────────────────────────────────────────────
    def _generate_txt(self) -> str:
        sep  = '=' * 72
        sep2 = '-' * 50
        lines = [
            sep,
            f"  {COMPANY}  {SYSTEM_NAME}  {VERSION}",
            sep,
            f"  项目名称: {self.project_name}",
            sep,
            f"  设备名称: {self.device.name}",
            f"  IP 地址 : {self.device.host}",
            f"  设备类型: {self.device.platform}",
            f"  连接协议: {self.device.protocol.upper()}:{self.device.port}",
            f"  巡检时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else '-'}",
            sep,
        ]

        if self.error_msg:
            lines.append(f"  [ERROR] {self.error_msg}")
            lines.append(sep)

        for cmd, output in self.results.items():
            lines.append(f"\n>>> {cmd}")
            lines.append(sep2)
            lines.append(output or '[无输出]')

        lines += [
            '',
            sep,
            f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"  {COPYRIGHT}",
            sep,
        ]
        return '\n'.join(lines)
