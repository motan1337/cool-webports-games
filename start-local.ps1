param([int]$Port = 8081, [string]$BindAddress = '127.0.0.1')
$archiveDirectory = $PSScriptRoot
Write-Host "Open http://localhost:$Port/play.html"
Write-Host 'Press Ctrl+C to stop the server.'
python -m http.server $Port --bind $BindAddress --directory $archiveDirectory
