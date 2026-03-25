# NetInspector 自动提交脚本
# 运行此脚本自动提交所有更改到 GitHub

$ErrorActionPreference = "Stop"

# 切换到脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 刷新环境变量
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# 检查是否有未提交的更改
$status = git status --porcelain
if ($status.Count -eq 0) {
    Write-Host "没有需要提交的更改" -ForegroundColor Yellow
    exit 0
}

# 显示更改列表
Write-Host "检测到以下更改:" -ForegroundColor Cyan
git status --short

# 获取提交信息
if ($args.Count -gt 0) {
    $commitMsg = $args -join " "
} else {
    $commitMsg = Read-Host "请输入提交信息 (直接回车使用默认信息)"
    if ([string]::IsNullOrWhiteSpace($commitMsg)) {
        $commitMsg = "更新: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    }
}

# 添加所有更改
git add -A

# 提交
git commit -m $commitMsg

# 推送到 GitHub
Write-Host "正在推送到 GitHub..." -ForegroundColor Cyan
git push origin master

Write-Host "提交完成!" -ForegroundColor Green
