@echo off
rem Runs the Newton Windows installation test; arguments are passed on (for example -Gui).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows-install-test.ps1" %*
exit /b %errorlevel%
