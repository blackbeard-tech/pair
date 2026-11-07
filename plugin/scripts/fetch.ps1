# Prints the path of this plugin version's verified pair-windows-x64.exe (stdout); errors go to stderr.
# Downloads the release asset on first run and refuses it unless its sha256 is pinned in checksums.txt.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
try {
  if ($env:PAIR_BIN) { $env:PAIR_BIN; exit 0 }  # dev override: a local build
  $root = Split-Path -Parent $PSScriptRoot
  $sums = Get-Content (Join-Path $root 'checksums.txt')
  $version = ($sums | Select-String '^# release v([0-9.]+)').Matches[0].Groups[1].Value  # pinned release (CI keeps it equal to the plugin version)
  $asset = 'pair-windows-x64.exe'  # also runs on Windows on Arm via x64 emulation
  $data = if ($env:PAIR_DATA) { $env:PAIR_DATA } else { Join-Path $env:LOCALAPPDATA 'pair' }
  $bin = Join-Path (Join-Path $data $version) $asset
  if (-not (Test-Path $bin)) {
    $line = $sums | Where-Object { $_ -match "^[0-9a-f]{64}\s+$([regex]::Escape($asset))$" }
    if (-not $line) { throw "no pinned checksum for $asset v$version; update the plugin" }
    $want = ($line -split '\s+')[0]
    New-Item -ItemType Directory -Force (Split-Path $bin) | Out-Null
    $tmp = "$bin.$PID.part"  # per process: the monitor and the MCP server can both be downloading
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/blackbeard-tech/pair/releases/download/v$version/$asset" -OutFile $tmp
    # .NET hashing: no dependence on cmdlet/module loading.
    $sha = [Security.Cryptography.SHA256]::Create()
    $fs = [IO.File]::OpenRead($tmp)
    try { $got = -join ($sha.ComputeHash($fs) | ForEach-Object { $_.ToString('x2') }) } finally { $fs.Dispose() }
    if ($got -ne $want) { Remove-Item $tmp; throw "checksum mismatch for $asset; refusing to run" }
    # If the other launcher got there first (Windows locks the running exe), use its verified copy.
    try { Move-Item -Force $tmp $bin } catch { Remove-Item $tmp -ErrorAction SilentlyContinue; if (-not (Test-Path $bin)) { throw } }
  }
  $bin
} catch { [Console]::Error.WriteLine("pair: $_"); exit 1 }
