# NetInspector 网络设备自动化巡检工具

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/PyQt5-GUI-green.svg" alt="PyQt5">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

> 支持华为、H3C、Cisco、锐捷等主流厂商交换机的自动化巡检工具

## 功能特性

### 核心功能

- **多厂商支持**: 支持华为(Huawei)、H3C、Cisco、锐捷(Ruijie)等主流网络设备
- **多种连接方式**: 支持 SSH 和 Telnet 协议连接网络设备
- **批量巡检**: 支持从 Excel 导入设备列表，批量执行巡检任务
- **定时巡检**: 支持每日定时、每周定时、自定义时间间隔等多种定时任务模式
- **AI 智能分析**: 集成 AI 大模型分析巡检结果，自动识别潜在问题（需配置）
- **报告生成**: 支持生成 HTML 和 TXT 格式的巡检报告

### 设备管理

- 添加/编辑/删除设备信息
- 支持设备分组管理
- 设备连接测试功能
- 支持自定义巡检命令

### 定时任务

- 每日定时执行巡检
- 每周指定日期定时执行
- 自定义间隔执行
- 支持星期选择

### 报告系统

- 自动生成巡检报告
- 支持自定义公司名称、主题颜色
- 支持添加水印
- 报告包含设备信息、命令输出、AI 分析结果

## 系统要求

- Windows 10/11
- Python 3.8+
- PyQt5
- 网络可达待巡检设备

## 安装依赖

```bash
pip install -r requirements.txt
```

依赖包括：
- PyQt5 >= 5.15
- paramiko (SSH 连接)
- openpyxl (Excel 解析)
- requests (HTTP 请求)

## 使用方法

### 1. 启动程序

```bash
python main.py
```

### 2. 添加设备

点击"添加设备"按钮，填写设备信息：
- 设备名称
- IP 地址
- 协议类型（SSH/Telnet）
- 端口号
- 用户名/密码

### 3. 导入设备列表

支持从 Excel 文件导入设备：
- 设备名称、IP、协议、端口、用户名、密码等字段

### 4. 执行巡检

1. 选择要巡检的设备（可多选）
2. 选择巡检命令
3. 点击"开始巡检"按钮

### 5. 定时巡检配置

1. 点击"定时巡检"按钮
2. 选择巡检模式（每日/每周/间隔）
3. 设置执行时间
4. 启动定时任务

### 6. AI 分析配置（可选）

1. 点击"AI 配置"按钮
2. 填写 AI 接口地址、API Key、模型名称
3. 启用 AI 分析功能

## 项目结构

```
NetInspector/
├── main.py                 # 程序入口
├── core/
│   ├── connector.py        # SSH/Telnet 连接模块
│   └── inspector.py        # 巡检引擎
├── ui/
│   ├── main_window.py      # 主窗口
│   └── dialogs.py          # 对话框组件
├── utils/
│   ├── ai_analyzer.py      # AI 分析模块
│   ├── excel_parser.py     # Excel 解析
│   └── report_generator.py # 报告生成器
├── auto-commit.ps1         # 自动提交脚本
├── watch-and-commit.ps1   # 文件监控自动提交
└── README.md               # 本文件
```

## 技术实现

### 连接模块 (connector.py)

- 使用 `paramiko` 库实现 SSH 连接
- 使用 Python socket 实现 Telnet 连接
- 自动识别设备厂商类型
- 支持华为、H3C、Cisco、锐捷等厂商特定命令

### 巡检引擎 (inspector.py)

- 多线程并发执行巡检任务
- 实时显示巡检进度和日志
- 支持任务中断和重试

### 报告生成器 (report_generator.py)

- HTML 报告：支持自定义主题颜色、水印、CSS 样式
- TXT 报告：纯文本格式，便于打印
- 自动包含 AI 分析结果

### AI 分析模块 (ai_analyzer.py)

- 支持对接各类 AI 大模型 API
- 自动分析巡检命令输出
- 识别潜在网络问题

## 界面预览

主界面包含：
- 顶部工具栏（添加设备、导入、巡检、定时等）
- 左侧设备列表（支持分组显示）
- 中间命令选择区
- 底部日志显示区

## 版本历史

- **V1.0.1**: 优化SSH连接体验，修复设备分页问题
- **V1.0.0**: 初始版本发布

## 许可证

MIT License

## 作者

四川新数信息技术有限公司

## 联系方式

技术支持：diao@vip.qq.com
