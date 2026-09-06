# BookPlay Backend —— FastAPI + LangChain Agent 服务
FROM python:3.11-slim

WORKDIR /app

# 安装依赖（利用层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝源码（.dockerignore 排除 .venv / __pycache__）
COPY . .

EXPOSE 8000

# 生产启动：seed 语料在 lifespan 启动时自动导入向量库
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
