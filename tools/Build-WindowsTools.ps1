param([string]$Compiler = (Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'))

$ErrorActionPreference = 'Stop'
$output = Join-Path $PSScriptRoot 'dist'
New-Item -Path $output -ItemType Directory -Force | Out-Null
$references = @('System.dll', 'System.Core.dll', 'System.Drawing.dll', 'System.Windows.Forms.dll',
    'System.Management.dll', 'System.Web.Extensions.dll', 'System.IO.Compression.dll',
    'System.IO.Compression.FileSystem.dll') | ForEach-Object { '/reference:' + $_ }
$shared = Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'shared') -Filter '*.cs' -File

foreach ($tool in @(
    @{ Folder = 'hytale-server-panel'; Main = 'HytaleServerPanel'; File = 'Hytale Server Panel.exe' },
    @{ Folder = 'hytale-quiet-mode'; Main = 'HytaleQuietMode'; File = 'Hytale Quiet Mode.exe' }
)) {
    $own = Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot $tool.Folder) -Filter '*.cs' -File
    $sources = @($shared) + @($own) | Select-Object -ExpandProperty FullName
    $destination = Join-Path $output $tool.File
    & $Compiler /nologo /target:winexe /optimize+ ('/main:' + $tool.Main) ('/out:' + $destination) @references @sources
    if ($LASTEXITCODE -ne 0) { throw "Compilation failed for $($tool.File)." }
    Write-Output $destination
}
