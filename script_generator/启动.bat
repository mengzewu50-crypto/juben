@echo off
:: 自动进入你的代码文件夹
cd /d "D:\juben\script_generator"

:: 启动后端服务
echo 正在启动剧本神器，请稍候...
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

pause