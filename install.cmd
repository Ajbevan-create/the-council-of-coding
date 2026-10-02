@echo off
where py >nul 2>&1
if errorlevel 1 goto python_fallback
py -3 "%~dp0scripts\install.py" %*
goto done
:python_fallback
where python >nul 2>&1
if errorlevel 1 goto missing_python
python "%~dp0scripts\install.py" %*
goto done
:missing_python
echo Install Python 3.10+ from https://www.python.org/downloads/ with the Python launcher or PATH option enabled.
exit /b 1
:done
exit /b %errorlevel%
