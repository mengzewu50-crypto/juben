FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制依赖列表并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制其余项目文件
COPY . .

# 暴露端口
EXPOSE 8000

# 运行 FastAPI 应用程序
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
