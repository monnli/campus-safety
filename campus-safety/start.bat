@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"

set "CONDA_ENV=campus_env"

rem ---- 定位 conda.bat（用于 activate）----
set "CONDA_BAT="
for /f "delims=" %%i in ('where conda 2^>nul') do (
    set "CAND=%%i"
    goto :_got_conda
)
:_got_conda
if defined CAND (
    rem 可能命中 conda.exe 或 conda.bat，统一尝试推导 conda.bat
    for %%p in ("%CAND%") do set "CAND_DIR=%%~dpp"
    rem 如果是 condabin\conda.bat，直接用
    if /i "%CAND%"=="%CAND_DIR%conda.bat" (
        set "CONDA_BAT=%CAND%"
    ) else (
        rem 如果命中 conda.exe，尝试在同级/上级寻找 condabin\conda.bat
        if exist "%CAND_DIR%..\\condabin\\conda.bat" set "CONDA_BAT=%CAND_DIR%..\\condabin\\conda.bat"
        if not defined CONDA_BAT if exist "%CAND_DIR%condabin\\conda.bat" set "CONDA_BAT=%CAND_DIR%condabin\\conda.bat"
        if not defined CONDA_BAT if exist "%CAND_DIR%Scripts\\activate.bat" (
            rem 退一步：用 activate.bat（在部分安装中存在）
            set "CONDA_BAT=%CAND_DIR%Scripts\\activate.bat"
        )
    )
)

rem ---- 若 PATH 中找不到 conda，尝试常见安装路径 ----
if not defined CONDA_BAT (
    if exist "%ProgramData%\Anaconda3\condabin\conda.bat" set "CONDA_BAT=%ProgramData%\Anaconda3\condabin\conda.bat"
)
if not defined CONDA_BAT (
    if exist "%ProgramData%\Miniconda3\condabin\conda.bat" set "CONDA_BAT=%ProgramData%\Miniconda3\condabin\conda.bat"
)
if not defined CONDA_BAT (
    if exist "%UserProfile%\Anaconda3\condabin\conda.bat" set "CONDA_BAT=%UserProfile%\Anaconda3\condabin\conda.bat"
)
if not defined CONDA_BAT (
    if exist "%UserProfile%\Miniconda3\condabin\conda.bat" set "CONDA_BAT=%UserProfile%\Miniconda3\condabin\conda.bat"
)
if not defined CONDA_BAT (
    if exist "%LocalAppData%\miniconda3\condabin\conda.bat" set "CONDA_BAT=%LocalAppData%\miniconda3\condabin\conda.bat"
)
if not defined CONDA_BAT (
    if exist "%LocalAppData%\Continuum\anaconda3\condabin\conda.bat" set "CONDA_BAT=%LocalAppData%\Continuum\anaconda3\condabin\conda.bat"
)

if not defined CONDA_BAT (
    echo [错误] 未找到 conda。请先安装 Anaconda/Miniconda，并确保在终端中能运行 conda。
    echo 你也可以在“Anaconda Prompt”里运行本脚本，或把 conda 加入系统 PATH。
    pause
    exit /b 1
)

if not exist "%ROOT%frontend\node_modules\" (
    echo [错误] 未找到 frontend\node_modules，请先在 frontend 目录执行 npm install。
    pause
    exit /b 1
)

echo 正在启动后端（新窗口）...
start "黔视护苗-后端" /D "%ROOT%backend" cmd /k "call \"%CONDA_BAT%\" activate %CONDA_ENV% && python app.py"

echo 等待后端就绪...
timeout /t 4 /nobreak >nul

echo 正在启动前端（新窗口）...
start "黔视护苗-前端" /D "%ROOT%frontend" cmd /k "npm run dev"

echo 等待前端开发服务器启动...
timeout /t 6 /nobreak >nul

start "" "http://localhost:3000"

echo.
echo 已打开两个服务窗口，并已尝试在浏览器打开 http://localhost:3000
echo 停止运行时请关闭「黔视护苗-后端」「黔视护苗-前端」窗口。
echo 本窗口 5 秒后自动关闭...
timeout /t 5 /nobreak >nul
