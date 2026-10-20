FROM python:3.11-slim

WORKDIR /app

# 设置时区和 HuggingFace 镜像
ENV LANG=C.UTF-8
ENV TZ=Asia/Shanghai
ENV HF_ENDPOINT=https://hf-mirror.com
ENV HF_HUB_DISABLE_SYMLINKS_WARNING=1

COPY requirements.txt .

RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
# 用阿里云安装依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --default-timeout=1000

COPY . .

EXPOSE 8001

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1", "--loop", "asyncio"]
#  重新启动容器
#docker run -d -p 8001:8001 -v C:/Users/XH/.cache/huggingface:/root/.cache/huggingface -v D:/faiss_store:/app/faiss_store -v D:/faiss_memory_store:/app/faiss_memory_store -v D:/agent_memory.sqlite:/app/agent_memory.sqlite --name agent-service agent-project:v1























































































