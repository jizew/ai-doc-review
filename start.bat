@echo off
chcp 65001 >nul
title AI 文档智能审校系统

echo.
echo ============================================================
echo   AI 文档智能审校系统 - 启动程序
echo ============================================================
echo.

:: 检查 Python 是否已安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.9 或更高版本。
    echo 下载地址: https://www.python.org/downloads/
    echo 安装时请勾选 "Add Python to PATH" 选项！
    pause
    exit /b 1
)

:: 检查虚拟环境是否存在，不存在则创建
if not exist "venv\Scripts\activate.bat" (
    echo [1/3] 首次运行：正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 虚拟环境创建失败，请检查 Python 是否正确安装。
        pause
        exit /b 1
    )
    echo       虚拟环境创建成功。
) else (
    echo [1/3] 虚拟环境已存在，跳过创建。
)

:: 激活虚拟环境
echo [2/3] 正在激活虚拟环境...
call venv\Scripts\activate.bat

:: 安装/更新依赖
echo [3/3] 正在检查并安装依赖（首次运行可能需要几分钟）...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络连接后重试。
    pause
    exit /b 1
)

:: 检查配置文件
if not exist "config.yaml" (
    echo.
    echo [提示] 未找到 config.yaml，正在从模板创建...
    copy config.yaml.example config.yaml >nul
    echo       已创建 config.yaml，请用文本编辑器打开并填写您的 API Key。
    echo       填写完成后，再次双击本脚本启动应用。
    echo.
    pause
    exit /b 0
)

:: 启动应用
echo.
echo ============================================================
echo   正在启动应用，浏览器将自动打开...
echo   如未自动打开，请手动访问: http://localhost:8501
echo   关闭此窗口即可停止应用。
echo ============================================================
echo.
streamlit run app.py --server.headless false
pause
