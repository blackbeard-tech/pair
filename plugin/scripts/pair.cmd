@echo off
rem Windows launcher for the pair channel server. fetch.ps1 ensures this plugin version's
rem pair.exe is present and checksum-verified, then cmd runs it with stdio passed straight through.
setlocal
rem Monitors pass the data dir as an argument: `pair watch <data>`.
if /i "%~1"=="watch" if not "%~2"=="" set "PAIR_DATA=%~2"
for /f "usebackq delims=" %%B in (`powershell -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0fetch.ps1"`) do set "PAIR_EXE=%%B"
if not defined PAIR_EXE exit /b 1
"%PAIR_EXE%" %*
