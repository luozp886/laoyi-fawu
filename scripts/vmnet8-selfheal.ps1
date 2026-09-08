<#
    VMnet8 自愈脚本
    作用：VMware 虚拟网卡 VMnet8(NAT)在宿主机重启后偶发丢失宿主机网关地址 192.168.150.1，
          导致宿主机无法访问 192.168.150.x 网段里的虚拟机。本脚本检测并自动补回该地址。
    用法（需管理员）：
        powershell -ExecutionPolicy Bypass -File vmnet8-selfheal.ps1
    说明：由「计划任务 VMnet8-SelfHeal」在登录时自动运行；也可手动运行。
#>
$ErrorActionPreference = 'Continue'
$log = Join-Path $env:ProgramData 'VMware\vmnet8-selfheal.log'
function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg"
    Write-Host $line
    Add-Content -Path $log -Value $line -ErrorAction SilentlyContinue
}

Write-Log '=== VMnet8 self-heal start ==='

# 1. 等待 VMnet8 网卡出现（最多 ~60 秒）
$adapter = $null
for ($i = 0; $i -lt 30; $i++) {
    $adapter = Get-NetAdapter -ErrorAction SilentlyContinue |
        Where-Object { $_.InterfaceDescription -match 'VMnet8' }
    if ($adapter) { break }
    Start-Sleep -Seconds 2
}
if (-not $adapter) {
    Write-Log 'VMnet8 adapter not found after wait. Giving up.'
    exit 0
}
Write-Log ("VMnet8 found, ifIndex=" + $adapter.ifIndex + ", Status=" + $adapter.Status)

# 2. 确保 VMware NAT / DHCP 服务在跑
foreach ($svc in @('VMware NAT Service', 'VMware DHCP Service')) {
    $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($s -and $s.Status -ne 'Running') {
        try { Start-Service -Name $svc -ErrorAction Stop; Write-Log ("started " + $svc) }
        catch { Write-Log ("start " + $svc + " failed: " + $_.Exception.Message) }
    }
}
Start-Sleep -Seconds 2

# 3. 检查并补回宿主机 NAT 网关地址 192.168.150.1
$idx = $adapter.ifIndex
$hasIp = Get-NetIPAddress -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -eq '192.168.150.1' }
if (-not $hasIp) {
    try {
        New-NetIPAddress -InterfaceIndex $idx -IPAddress 192.168.150.1 -PrefixLength 24 -ErrorAction Stop
        Write-Log 'added 192.168.150.1/24'
    }
    catch { Write-Log ('add IP failed: ' + $_.Exception.Message) }
} else {
    Write-Log '192.168.150.1 already present'
}

# 4. 验证
Start-Sleep -Seconds 1
Get-NetIPAddress -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -like '192.168.150.*' } |
    ForEach-Object { Write-Log ("verify: " + $_.IPAddress + "/" + $_.PrefixLength) }
Write-Log '=== VMnet8 self-heal done ==='
