@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"

if not exist "%ROOT%backend\venv\Scripts\activate.bat" (
    echo [错误] 未找到 backend\venv，请先在后端目录执行部署说明中的 venv 与 pip 安装步骤。
    pause
    exit /b 1
)

if not exist "%ROOT%frontend\node_modules\" (
    echo [错误] 未找到 frontend\node_modules，请先在 frontend 目录执行 npm install。
    pause
    exit /b 1
)

echo 正在启动后端（新窗口）...
start "黔视护苗-后端" /D "%ROOT%backend" cmd /k "call venv\Scripts\activate.bat && python app.py"

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
