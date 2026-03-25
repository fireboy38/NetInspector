#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快照管理器 - 保存和对比设备配置快照
"""

import os
import json
import hashlib
import difflib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Snapshot:
    """快照数据类"""
    id: str
    device_name: str
    device_host: str
    created_at: str
    description: str
    commands_output: Dict[str, str]  # 命令 -> 输出
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Snapshot':
        return cls(**data)


@dataclass
class DiffResult:
    """对比结果"""
    command: str
    old_content: str
    new_content: str
    has_changed: bool
    added_lines: List[str]
    removed_lines: List[str]
    similarity: float  # 相似度 0-1


class SnapshotManager:
    """快照管理器"""
    
    def __init__(self, snapshot_dir: str = None):
        if snapshot_dir is None:
            snapshot_dir = os.path.join(
                os.path.expanduser('~'), 
                'Desktop', 'NetInspector', 'snapshots'
            )
        self.snapshot_dir = snapshot_dir
        self.index_file = os.path.join(snapshot_dir, 'index.json')
        os.makedirs(snapshot_dir, exist_ok=True)
        self._index = self._load_index()
    
    def _load_index(self) -> Dict:
        """加载索引文件"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载快照索引失败: {e}")
        return {'snapshots': []}
    
    def _save_index(self):
        """保存索引文件"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存快照索引失败: {e}")
    
    def _generate_id(self, device_host: str) -> str:
        """生成快照ID"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{device_host.replace('.', '_')}_{timestamp}"
    
    def create_snapshot(self, device_name: str, device_host: str,
                       commands_output: Dict[str, str],
                       description: str = "") -> Snapshot:
        """创建新快照"""
        snapshot = Snapshot(
            id=self._generate_id(device_host),
            device_name=device_name,
            device_host=device_host,
            created_at=datetime.now().isoformat(),
            description=description or f"快照 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            commands_output=commands_output
        )
        
        # 保存快照文件
        snapshot_file = os.path.join(self.snapshot_dir, f"{snapshot.id}.json")
        try:
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
            
            # 更新索引
            self._index['snapshots'].append({
                'id': snapshot.id,
                'device_name': snapshot.device_name,
                'device_host': snapshot.device_host,
                'created_at': snapshot.created_at,
                'description': snapshot.description,
                'file': snapshot_file
            })
            self._save_index()
            
            logger.info(f"创建快照成功: {snapshot.id}")
            return snapshot
            
        except Exception as e:
            logger.error(f"创建快照失败: {e}")
            raise
    
    def get_snapshots(self, device_host: str = None) -> List[Dict]:
        """获取快照列表"""
        snapshots = self._index.get('snapshots', [])
        if device_host:
            snapshots = [s for s in snapshots if s['device_host'] == device_host]
        return sorted(snapshots, key=lambda x: x['created_at'], reverse=True)
    
    def load_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """加载指定快照"""
        snapshot_file = os.path.join(self.snapshot_dir, f"{snapshot_id}.json")
        if not os.path.exists(snapshot_file):
            return None
        
        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Snapshot.from_dict(data)
        except Exception as e:
            logger.error(f"加载快照失败: {e}")
            return None
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """删除快照"""
        try:
            # 删除文件
            snapshot_file = os.path.join(self.snapshot_dir, f"{snapshot_id}.json")
            if os.path.exists(snapshot_file):
                os.remove(snapshot_file)
            
            # 更新索引
            self._index['snapshots'] = [
                s for s in self._index['snapshots'] 
                if s['id'] != snapshot_id
            ]
            self._save_index()
            
            logger.info(f"删除快照成功: {snapshot_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除快照失败: {e}")
            return False
    
    def compare_snapshots(self, old_snapshot_id: str, 
                         new_snapshot_id: str) -> List[DiffResult]:
        """对比两个快照"""
        old_snapshot = self.load_snapshot(old_snapshot_id)
        new_snapshot = self.load_snapshot(new_snapshot_id)
        
        if not old_snapshot or not new_snapshot:
            raise ValueError("无法加载指定的快照")
        
        results = []
        all_commands = set(old_snapshot.commands_output.keys()) | set(new_snapshot.commands_output.keys())
        
        for command in all_commands:
            old_content = old_snapshot.commands_output.get(command, "")
            new_content = new_snapshot.commands_output.get(command, "")
            
            # 计算相似度
            if old_content and new_content:
                similarity = difflib.SequenceMatcher(None, old_content, new_content).ratio()
            elif old_content == new_content:
                similarity = 1.0
            else:
                similarity = 0.0
            
            # 计算差异行
            old_lines = old_content.splitlines() if old_content else []
            new_lines = new_content.splitlines() if new_content else []
            
            diff = list(difflib.unified_diff(
                old_lines, new_lines,
                fromfile='旧版本', tofile='新版本',
                lineterm=''
            ))
            
            added_lines = [line[1:] for line in diff if line.startswith('+') and not line.startswith('+++')]
            removed_lines = [line[1:] for line in diff if line.startswith('-') and not line.startswith('---')]
            
            results.append(DiffResult(
                command=command,
                old_content=old_content,
                new_content=new_content,
                has_changed=old_content != new_content,
                added_lines=added_lines,
                removed_lines=removed_lines,
                similarity=similarity
            ))
        
        return sorted(results, key=lambda x: (not x.has_changed, x.command))
    
    def compare_with_latest(self, device_host: str, 
                           current_output: Dict[str, str]) -> List[DiffResult]:
        """将当前输出与最新快照对比"""
        snapshots = self.get_snapshots(device_host)
        if not snapshots:
            return []
        
        latest = self.load_snapshot(snapshots[0]['id'])
        if not latest:
            return []
        
        # 创建临时快照进行对比
        temp_snapshot = Snapshot(
            id='temp',
            device_name='',
            device_host=device_host,
            created_at=datetime.now().isoformat(),
            description='当前巡检',
            commands_output=current_output
        )
        
        results = []
        all_commands = set(latest.commands_output.keys()) | set(current_output.keys())
        
        for command in all_commands:
            old_content = latest.commands_output.get(command, "")
            new_content = current_output.get(command, "")
            
            if old_content and new_content:
                similarity = difflib.SequenceMatcher(None, old_content, new_content).ratio()
            elif old_content == new_content:
                similarity = 1.0
            else:
                similarity = 0.0
            
            old_lines = old_content.splitlines() if old_content else []
            new_lines = new_content.splitlines() if new_content else []
            
            diff = list(difflib.unified_diff(
                old_lines, new_lines,
                fromfile=f"快照 ({latest.created_at[:10]})",
                tofile='当前巡检',
                lineterm=''
            ))
            
            added_lines = [line[1:] for line in diff if line.startswith('+') and not line.startswith('+++')]
            removed_lines = [line[1:] for line in diff if line.startswith('-') and not line.startswith('---')]
            
            results.append(DiffResult(
                command=command,
                old_content=old_content,
                new_content=new_content,
                has_changed=old_content != new_content,
                added_lines=added_lines,
                removed_lines=removed_lines,
                similarity=similarity
            ))
        
        return sorted(results, key=lambda x: (not x.has_changed, x.command))
    
    def generate_diff_report(self, diff_results: List[DiffResult], 
                            old_desc: str, new_desc: str) -> str:
        """生成对比报告（HTML格式）"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>配置对比报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #2C3E50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .summary {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .command-section {{ background: white; margin-bottom: 15px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .command-header {{ background: #34495E; color: white; padding: 12px 15px; font-weight: bold; }}
        .command-header.changed {{ background: #E74C3C; }}
        .command-header.unchanged {{ background: #27AE60; }}
        .diff-content {{ padding: 15px; }}
        .diff-stats {{ color: #666; font-size: 12px; margin-bottom: 10px; }}
        .added {{ background: #D4EDDA; color: #155724; padding: 2px 5px; border-radius: 3px; }}
        .removed {{ background: #F8D7DA; color: #721C24; padding: 2px 5px; border-radius: 3px; }}
        .line {{ font-family: monospace; font-size: 13px; margin: 2px 0; padding: 2px 5px; }}
        pre {{ background: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 配置对比报告</h1>
        <p>对比: {old_desc} → {new_desc}</p>
    </div>
    
    <div class="summary">
        <h3>📈 变更摘要</h3>
        <p>总命令数: {len(diff_results)}</p>
        <p>变更命令: {sum(1 for r in diff_results if r.has_changed)}</p>
        <p>未变更: {sum(1 for r in diff_results if not r.has_changed)}</p>
    </div>
"""
        
        for result in diff_results:
            status_class = "changed" if result.has_changed else "unchanged"
            status_text = "🔴 已变更" if result.has_changed else "🟢 未变更"
            similarity_text = f"相似度: {result.similarity*100:.1f}%"
            
            html += f"""
    <div class="command-section">
        <div class="command-header {status_class}">
            {result.command} - {status_text} ({similarity_text})
        </div>
        <div class="diff-content">
"""
            
            if result.has_changed:
                html += f'<div class="diff-stats">新增 {len(result.added_lines)} 行, 删除 {len(result.removed_lines)} 行</div>'
                
                if result.removed_lines:
                    html += '<div><strong>删除内容:</strong></div><pre>'
                    for line in result.removed_lines[:50]:  # 最多显示50行
                        html += f'<div class="line removed">- {line}</div>'
                    if len(result.removed_lines) > 50:
                        html += f'<div class="line">... 还有 {len(result.removed_lines) - 50} 行 ...</div>'
                    html += '</pre>'
                
                if result.added_lines:
                    html += '<div><strong>新增内容:</strong></div><pre>'
                    for line in result.added_lines[:50]:
                        html += f'<div class="line added">+ {line}</div>'
                    if len(result.added_lines) > 50:
                        html += f'<div class="line">... 还有 {len(result.added_lines) - 50} 行 ...</div>'
                    html += '</pre>'
            else:
                html += '<div class="diff-stats">内容完全一致</div>'
            
            html += '</div></div>'
        
        html += """
</body>
</html>"""
        
        return html
