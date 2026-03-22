#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 智能分析模块
将巡检报告发送给 AI，获取分析结果并写回 HTML/TXT 报告
兼容 OpenAI 格式接口（OpenAI / DeepSeek / 阿里云百炼 / 自定义）
"""

import os
import re
import json
import logging
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = """你是一位资深网络工程师，请仔细分析以下网络设备巡检报告，完成以下任务：

1. **问题识别**：列出发现的故障、告警、异常配置或潜在风险（如有）。
2. **风险评级**：对每个问题标注风险级别（高 / 中 / 低）。
3. **处置建议**：针对每个问题给出简明的处置建议。
4. **总体评价**：用2-3句话对设备整体状态作出评价。

请用清晰的中文列表格式输出，如无明显问题请说明"设备运行状态良好"。

---
巡检报告内容如下：
"""


class AiAnalyzer:
    """AI 分析器"""

    MAX_REPORT_CHARS = 12000   # 发送给 AI 的最大字符数（避免超出 token 限制）

    def __init__(self, config: dict):
        self.enabled  = config.get('enabled', False)
        self.endpoint = config.get('endpoint', '').rstrip('/')
        self.apikey   = config.get('apikey', '')
        self.model    = config.get('model', 'gpt-4o') or 'gpt-4o'
        self.prompt   = config.get('prompt', '').strip() or DEFAULT_PROMPT

    def analyze_report(self, report_path: str, project_name: str = '') -> Optional[str]:
        """
        读取报告文件，调用 AI 接口，返回分析结果字符串。
        失败返回 None。
        """
        if not self.enabled or not self.apikey or not self.endpoint:
            return None

        try:
            report_text = self._read_report_text(report_path)
            if not report_text:
                logger.warning(f"AI 分析：读取报告失败 {report_path}")
                return None

            # 截断超长内容
            if len(report_text) > self.MAX_REPORT_CHARS:
                report_text = report_text[:self.MAX_REPORT_CHARS] + "\n...[内容过长已截断]"

            messages = [
                {
                    "role": "system",
                    "content": (
                        f"你是{project_name or ''}网络设备巡检的专业分析助手，"
                        "擅长识别华为、H3C、思科、锐捷等设备的配置问题和运行异常。"
                    )
                },
                {
                    "role": "user",
                    "content": self.prompt + "\n\n" + report_text
                }
            ]

            result = self._call_api(messages)
            return result

        except Exception as e:
            logger.error(f"AI 分析失败: {e}")
            return None

    def _read_report_text(self, path: str) -> str:
        """从 HTML/TXT 报告中提取纯文本内容"""
        try:
            with open(path, encoding='utf-8', errors='replace') as f:
                content = f.read()

            if path.lower().endswith('.html'):
                # 去掉 HTML 标签，保留文本内容
                text = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
                text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
                # 清理多余空白
                text = re.sub(r'[ \t]+', ' ', text)
                text = re.sub(r'\n{3,}', '\n\n', text)
                return text.strip()
            else:
                return content.strip()
        except Exception as e:
            logger.error(f"读取报告文件失败: {e}")
            return ''

    def _call_api(self, messages: list) -> Optional[str]:
        """调用 OpenAI 兼容接口"""
        url = self.endpoint + '/chat/completions'
        payload = json.dumps({
            "model":    self.model,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.3,
        }).encode('utf-8')

        req = urllib.request.Request(url, data=payload, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {self.apikey}')

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data['choices'][0]['message']['content'].strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            logger.error(f"AI API HTTP 错误 {e.code}: {body[:300]}")
            return None

    def append_ai_section(self, report_path: str, ai_result: str):
        """将 AI 分析结果写回报告文件"""
        if not ai_result:
            return
        try:
            with open(report_path, encoding='utf-8') as f:
                content = f.read()

            if report_path.lower().endswith('.html'):
                import html as html_lib
                escaped = html_lib.escape(ai_result).replace('\n', '<br>')
                # 激活隐藏的 AI 区块
                content = content.replace(
                    'id="ai-analysis-section" style="display:none;"',
                    'id="ai-analysis-section"'
                )
                content = content.replace(
                    'id="ai-analysis-content"></div>',
                    f'id="ai-analysis-content">{escaped}</div>'
                )
            else:
                sep = '=' * 72
                ai_block = (
                    f"\n{sep}\n"
                    f"  AI 智能分析结果\n"
                    f"{sep}\n"
                    f"{ai_result}\n"
                    f"{sep}\n"
                )
                # 插入到版权行之前
                content = content.rstrip() + '\n' + ai_block

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"AI 分析结果已写入: {os.path.basename(report_path)}")
        except Exception as e:
            logger.error(f"写入 AI 分析结果失败: {e}")

    def merge_reports(self, report_files: list, output_path: str, project_name: str = '') -> str:
        """
        将多个设备报告整合成一个汇总报告。
        返回整合后的文件路径。
        """
        import html as html_lib
        from datetime import datetime

        if not report_files:
            return ''

        # 收集所有报告的纯文本内容
        device_sections = []
        for fp in report_files:
            if not os.path.isfile(fp):
                continue
            text = self._read_report_text(fp)
            # 提取设备名称作为标题
            fname = os.path.basename(fp)
            # 从文件名提取设备名（去掉时间戳后缀）
            dev_name = fname.rsplit('_', 1)[0] if '_' in fname else fname
            device_sections.append((dev_name, text))

        if not device_sections:
            return ''

        # 生成整合报告
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        project_title = project_name or '网络设备巡检汇总报告'

        # 构建 HTML 内容
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html_lib.escape(project_title)} - AI 分析报告</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
            background: #f0f2f5; color: #2d3436;
        }}
        .header {{
            background: linear-gradient(135deg, #2C3E50 0%, #3498DB 100%);
            color: white; padding: 24px 36px;
        }}
        .header h1 {{ font-size: 1.6em; margin-bottom: 6px; }}
        .header .meta {{ opacity: 0.85; font-size: 0.9em; }}
        .container {{ max-width: 1000px; margin: 24px auto; padding: 0 24px; }}
        .section {{
            background: white; border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.07);
            margin-bottom: 20px; overflow: hidden;
        }}
        .section-title {{
            background: #2C3E50; color: white;
            padding: 10px 20px; font-size: 0.95em;
            font-weight: bold; letter-spacing: 1px;
            border-left: 5px solid #3498DB;
        }}
        .device-block {{
            padding: 16px 20px; border-bottom: 1px solid #ecf0f1;
        }}
        .device-block:last-child {{ border-bottom: none; }}
        .device-name {{
            font-weight: bold; color: #2C3E50; font-size: 1.05em;
            margin-bottom: 10px;
        }}
        .device-content {{
            font-family: 'Courier New', Consolas, monospace;
            font-size: 0.85em; line-height: 1.6;
            white-space: pre-wrap; word-break: break-all;
            background: #1e1e2e; color: #a8d8a8;
            padding: 12px 16px; border-radius: 4px;
            max-height: 300px; overflow-y: auto;
        }}
        .ai-section {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px; margin-bottom: 24px; overflow: hidden;
        }}
        .ai-title {{
            background: rgba(0,0,0,0.2); color: white;
            padding: 12px 20px; font-size: 1.1em; font-weight: bold;
        }}
        .ai-content {{
            padding: 20px; font-size: 0.95em; line-height: 1.8;
            color: white; white-space: pre-wrap;
        }}
        .footer {{
            background: #2C3E50; color: #A8C7E8;
            text-align: center; padding: 16px; font-size: 0.82em;
        }}
    </style>
</head>
<body>

<div class="header">
    <h1>&#x1F4CB; {html_lib.escape(project_title)}</h1>
    <div class="meta">整合巡检报告 · 共 {len(device_sections)} 台设备 · 生成时间：{timestamp}</div>
</div>

<div class="container">
    <!-- 设备报告摘要 -->
    <div class="section">
        <div class="section-title">&#x1F5A5; 设备报告摘要（共 {len(device_sections)} 台）</div>
"""

        for dev_name, content in device_sections:
            html_content += f"""
        <div class="device-block">
            <div class="device-name">&#x25CF; {html_lib.escape(dev_name)}</div>
            <div class="device-content">{html_lib.escape(content[:3000])}</div>
        </div>"""

        # AI 分析结果区块（占位）
        html_content += """
    </div>

    <!-- AI 智能分析结果 -->
    <div class="ai-section" id="ai-analysis-section">
        <div class="ai-title">&#x1F916; AI 智能分析结果</div>
        <div class="ai-content" id="ai-analysis-content">正在分析中...</div>
    </div>

</div>

<div class="footer">
    <div>本报告由四川新数网络设备巡检系统自动生成</div>
    <div>&#169; 2024-2025 四川新数信息技术有限公司  版权所有</div>
</div>

</body>
</html>"""

        # 保存整合报告
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"整合报告已生成: {output_path}")
        return output_path
