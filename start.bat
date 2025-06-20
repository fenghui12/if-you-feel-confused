@echo off
rem 设置控制台窗口的标题
TITLE AI Assistant Launcher

echo -------------------------------------------------------------------
echo  Welcome to the AI Assistant Launcher!
echo  This script will set up and run the application for you.
echo -------------------------------------------------------------------
echo.

rem --- 1. 尝试激活 Conda 环境 ---
echo [1/5] Activating Conda environment...
rem 普遍的 Conda 安装会把 conda.bat 的路径添加到用户的 PATH 中
rem 我们先尝试直接调用它。如果失败，再给出指引。
call conda activate base 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Could not automatically activate the 'base' Conda environment.
    echo If the script fails, please open an Anaconda Prompt, navigate to this directory, and run 'start.bat' manually.
    echo.
) else (
    echo Conda 'base' environment activated.
)
echo.


rem --- 2. 检查 Python 环境 ---
echo [2/5] Checking for Python installation...
rem 在激活了Conda环境后，这个检查的成功率会大大提高
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found even in the Conda environment.
    echo Please ensure Python is installed correctly in your 'base' Conda environment.
    pause
    exit /b
)
echo Python found.
echo.

rem --- 3. 安装依赖 ---
echo [3/5] Checking and installing required packages...
pip freeze | findstr "fastapi" >nul
if %errorlevel% neq 0 (
    echo Installing packages from requirements.txt... this may take a moment.
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install required packages.
        echo Please check your internet connection and try running this script again from an Anaconda Prompt.
        pause
        exit /b
    )
    echo Packages installed successfully.
) else (
    echo All required packages are already installed.
)
echo.


rem --- 4. 处理 .env 文件和 API 密钥 ---
echo [4/5] Setting up API Key...
IF NOT EXIST .env (
    echo.
    echo To use this AI Assistant, you need a DeepSeek API Key.
    echo You can get one from the DeepSeek official website.
    echo.
    set /p DEEPSEEK_API_KEY="Please enter your DeepSeek API Key and press Enter: "
    echo DEEPSEEK_API_KEY=%DEEPSEEK_API_KEY% > .env
    echo API Key has been saved to the .env file for future use.
) else (
    echo Found an existing .env file. Using the saved API Key.
)
echo.

rem --- 5. 启动服务器并打开浏览器 ---
echo [5/5] Starting the application server...
start "AI Assistant Server" cmd /k "conda activate base && uvicorn main:app --host 127.0.0.1 --port 8000"

echo.
echo Waiting for the server to initialize...
timeout /t 5 /nobreak >nul

echo Opening the application in your default browser...
start http://127.0.0.1:8000

echo.
echo -------------------------------------------------------------------
echo  Your AI Assistant is now running!
echo. 
echo  - A new window has opened to run the server.
echo  - Your browser should have opened the application automatically.
echo  - If not, please manually open this URL: http://127.0.0.1:8000
echo  - DO NOT CLOSE the new server window. Closing it will stop the server.
echo -------------------------------------------------------------------
echo.

pause 