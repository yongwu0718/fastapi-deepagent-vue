@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Index RAG 智能检索系统

rem ====== 检查 .env ======
if exist ".env" (
    echo [OK] .env 配置文件已存在
) else (
    echo [INFO] .env 不存在，正在从 .env.example 复制.
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        if exist ".env" (
            echo [OK] 已复制 .env.example -^> .env
        ) else (
            echo [ERROR] 复制失败，请手动处理
        )
    echo [INFO] .env_key 不存在，正在从 .env_key.example 复制.
        if exist ".env_key.example" (
            copy ".env_key.example" ".env_key" >nul
            if exist ".env_key" (
                echo [OK] 已复制 .env_key.example -^> .env_key
            ) else (
                echo [ERROR] 复制失败，请手动处理
            )
        ) else (
            echo [ERROR] .env_key.example 模板文件不存在
        )
           ) else (
        echo [ERROR] .env.example 模板文件不存在
    )
)

rem ====== 激活虚拟环境 ======
call .venv\Scripts\activate.bat >nul 2>&1
if errorlevel 1 (
    echo [WARN] 虚拟环境激活失败，尝试安装依赖.
    uv sync
    call .venv\Scripts\activate.bat >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] 无法激活虚拟环境，请检查 uv 和 Python 环境
        pause
        exit /b 1
    )
)

:menu
cls
echo ============================================
echo   Index RAG 智能检索系统
echo ============================================
echo.
echo   [1] 启动 DeepAgents 后端 (FastAPI)
echo   [2] 启动 Web 前端 (Vite)
echo   [3] 启动 Chroma 本地服务
echo   [4] Chroma 可视化面板 (Streamlit)
echo   [0] 退出程序
echo.
set /p choice=请输入选项 (0-4): 

if "%choice%"=="0" goto :quit
if "%choice%"=="1" goto :service_deepagents
if "%choice%"=="2" goto :service_web
if "%choice%"=="3" goto :service_chroma
if "%choice%"=="4" goto :service_chroma_view
echo 无效选项，请重新选择
timeout /t 2 >nul
goto :menu

:service_deepagents
cls
echo ============================================
echo   启动 DeepAgents 后端 (FastAPI)
echo ============================================
echo.
start "DeepAgents Backend" cmd /c "cd /d "%~dp0" && call .venv\Scripts\activate.bat && cd backend && fastapi dev"
echo [OK] DeepAgents 后端已在新窗口启动
echo.
pause
goto :menu

:service_web
cls
echo ============================================
echo   启动 Web 前端 (Vite)
echo ============================================
echo.
start "Web Frontend" cmd /c "cd /d "%~dp0frontend" && npm run dev"
echo [OK] Web 前端已在新窗口启动
echo.
pause
goto :menu

:service_chroma
cls
echo ============================================
echo   启动 Chroma 本地服务
echo ============================================
echo.
start "Chroma Server" cmd /c "cd /d "%~dp0" && call .venv\Scripts\activate.bat && python view_db\start_chroma_server.py"
echo [OK] Chroma 本地服务已在新窗口启动
echo.
pause
goto :menu

:service_chroma_view
cls
echo ============================================
echo   Chroma 可视化面板 (Streamlit)
echo ============================================
echo.
start "Chroma Viewer" cmd /c "cd /d "%~dp0" && call .venv\Scripts\activate.bat && python -m streamlit run view_db\view_chroma.py"
echo [OK] Chroma 可视化面板已在新窗口启动
echo.
pause
goto :menu


:quit
echo.
echo 再见！
timeout /t 1 >nul
exit /b 0