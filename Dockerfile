# 1. 基础镜像：Python 3.11（兼容性较好）
FROM python:3.11-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 先装系统依赖（编译型 Python 包常需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 4. 先拷依赖清单，再装依赖（利用 Docker 缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 拷贝项目其余代码
COPY . .

# 6. 声明 Flask 默认端口（你 app.py 用的 5000）
EXPOSE 5000

# 7. 容器启动时跑 Flask
CMD ["python", "app.py"]