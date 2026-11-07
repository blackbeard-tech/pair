@echo off
rem Windows launcher for the pair binary (MCP server, monitor or hook). fetch.ps1 ensures this plugin version's
rem pair-windows-x64.exe is present and checksum-verified, then cmd runs it with stdio passed straight through.
setlocal
rem Started from PowerShell 7, we'd inherit its PSModulePath and Windows PowerShell 5.1 then can't load
rem its own cmdlets (Get-FileHash not recognised). Empty makes 5.1 use its default.
set "PSModulePath="
rem Monitors pass the data dir as an argument: `pair watch <data>`.
if /i "%~1"=="watch" if not "%~2"=="" set "PAIR_DATA=%~2"
rem Hooks get the plugin data dir in their environment.
if not defined PAIR_DATA if defined CLAUDE_PLUGIN_DATA set "PAIR_DATA=%CLAUDE_PLUGIN_DATA%"
for /f "usebackq delims=" %%B in (`powershell -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0fetch.ps1"`) do set "PAIR_EXE=%%B"
if not defined PAIR_EXE exit /b 1
"%PAIR_EXE%" %*
