# 招待费智能审核系统 - 防火墙放行脚本
# 以管理员身份运行: Right-click -> Run as Administrator
# 或 PowerShell (Admin) 中执行: .\allow_firewall.ps1

$Port = 8099
$RuleName = "招待费智能审核系统"

# 检查规则是否已存在
$existing = Get-NetFirewallRule -Name $RuleName -ErrorAction SilentlyContinue

if ($existing) {
    Write-Host "防火墙规则 '$RuleName' 已存在，跳过。" -ForegroundColor Yellow
} else {
    New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow
    Write-Host "已添加防火墙入站规则: TCP 端口 $Port 允许访问" -ForegroundColor Green
}

# 获取本机局域网 IP
try {
    $ip = (Test-Connection 8.8.8.8 -Count 1 -ErrorAction Stop | Select-Object -ExpandProperty Ipv4Address)
} catch {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -ne "127.0.0.1" } | Select-Object -First 1 -ExpandProperty IPAddress)
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  局域网访问地址: http://$ip`:$Port" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "启动服务: cd 到项目目录后运行 python start_server.py" -ForegroundColor Yellow
