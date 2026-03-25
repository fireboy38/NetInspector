# NetInspector 文件监控自动提交脚本
# 检测到文件变化时自动提交并推送到 GitHub

$ErrorActionPreference = "Stop"

# 刷新环境变量
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# 切换到项目目录
$ProjectDir = "c:/Users/diao/WorkBuddy/20260320140032/NetInspector"
Set-Location $ProjectDir

# 忽略的文件模式
$IgnorePatterns = @("*.pyc", "__pycache__", ".git", "*.log", ".exe", "dist", "build", "*.spec")

# 上次提交时间
$LastCommitTime = [DateTime]::MinValue
$CooldownSeconds = 5

# 创建文件系统监控器
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $ProjectDir
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $false
$watcher.NotifyFilter = [System.IO.NotifyFilters]::LastWrite -bor [System.IO.NotifyFilters]::FileName -bor [System.IO.NotifyFilters]::DirectoryName

# 写入日志
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message" -ForegroundColor Cyan
}

# 检查是否忽略文件
function Should-Ignore {
    param([string]$Path)
    foreach ($pattern in $IgnorePatterns) {
        if ($Path -like "*$pattern*") {
            return $true
        }
    }
    return $false
}

# 执行提交
function Commit-And-Push {
    $currentTime = Get-Date
    
    if (($currentTime - $LastCommitTime).TotalSeconds -lt $CooldownSeconds) {
        return
    }
    
    $status = git status --porcelain
    if ($status.Count -eq 0) {
        return
    }
    
    $script:LastCommitTime = $currentTime
    
    Write-Log "检测到文件变化，准备提交..."
    git status --short
    
    git add -A
    $commitMsg = "更新: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    git commit -m $commitMsg
    
    Write-Log "正在推送到 GitHub..."
    git push origin master
    
    Write-Log "提交完成!"
}

# 事件处理
$onChanged = Register-ObjectEvent $watcher "Changed" -Action {
    $path = $Event.SourceEventArgs.FullPath
    if (-not (Should-Ignore $path)) {
        Commit-And-Push
    }
}

$onCreated = Register-ObjectEvent $watcher "Created" -Action {
    $path = $Event.SourceEventArgs.FullPath
    if (-not (Should-Ignore $path)) {
        Commit-And-Push
    }
}

$onRenamed = Register-ObjectEvent $watcher "Renamed" -Action {
    $path = $Event.SourceEventArgs.FullPath
    if (-not (Should-Ignore $path)) {
        Commit-And-Push
    }
}

# 启用监控
$watcher.EnableRaisingEvents = $true

Write-Host "========================================" -ForegroundColor Green
Write-Host "  文件监控自动提交已启动" -ForegroundColor Green
Write-Host "  监控目录: $ProjectDir" -ForegroundColor Green
Write-Host "  按 Ctrl+C 停止监控" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Green

try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    $watcher.EnableRaisingEvents = $false
    $watcher.Dispose()
    Write-Log "文件监控已停止"
}
