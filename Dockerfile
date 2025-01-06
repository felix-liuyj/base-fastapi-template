# 使用轻量级的基础镜像
FROM python:3.13-alpine3.20

# 设置环境变量以减少 Python 缓存文件并启用 UTF-8 支持
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ='Asia/Shanghai'
RUN echo $TZ > /etc/timezone
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

# 设置工作目录
WORKDIR /app

# 安装构建依赖
RUN apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev openssl-dev rust cargo build-base && \
    apk add --no-cache libffi openssl curl

# 复制项目所有文件到容器
COPY . .

# 安装项目依赖到全局（不包含开发依赖）
RUN pip install --no-cache-dir poetry
RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-interaction --no-ansi

# 删除构建依赖
RUN apk del .build-deps

# 暴露端口
EXPOSE 8000

# 设置启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]