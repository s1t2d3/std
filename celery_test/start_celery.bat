@echo off
chcp 65001 > nul

:: 设置工作目录
set WORK_DIR=D:\develop\PycharmProjects\AGENT项目\celery_test
set VENV_DIR=D:\develop\PycharmProjects\PyrhonLearn\.venv

cd /d %WORK_DIR%

:: 使用完整路径激活虚拟环境
call %VENV_DIR%\Scripts\activate.bat

:: 检查是否激活成功
if errorlevel 1 (
    echo [ERROR] 虚拟环境激活失败！
    echo 请检查路径: %VENV_DIR%
    pause
    exit /b 1
)

echo ========================================
echo [%date% %time%] 启动 Celery Worker...
echo ========================================

:: 启动 Celery Worker（使用 start 命令，指定完整路径）
start "Celery Worker" cmd /k "%VENV_DIR%\Scripts\celery.exe -A celery_task worker -l info -P threads --concurrency=10"

timeout /t 3 /nobreak > nul

echo ========================================
echo [%date% %time%] 启动 Celery Beat...
echo ========================================

:: 启动 Celery Beat
start "Celery Beat" cmd /k "%VENV_DIR%\Scripts\celery.exe -A celery_task beat -l info"

timeout /t 2 /nobreak > nul

echo ========================================
echo [%date% %time%] ✅ 所有服务已启动！
echo ========================================

exit /b 0