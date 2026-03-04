# 必须用 Debian 基础镜像：Alpine 无 apt-get，且 onnxruntime 的 pip 包不支持 musl
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.13.5


WORKDIR /app
ENV PYTHONPATH=/app/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制 backend/app 目录的内容到 /app 下
COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini ./alembic.ini

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

