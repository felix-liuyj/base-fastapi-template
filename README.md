# Base FastAPI Template

<!-- PROJECT SHIELDS -->

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]

<p align="center">
<!-- PROJECT LOGO -->
<br />

<p align="center">
  <a href="https://github.com/felix-liuyj/base-fastapi-template">
    <img src="https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png" alt="Logo" width="250" height="90">
  </a>

<h3 align="center">Base FastAPI Template</h3>
<p align="center">
    高性能FastAPI后端模板，支持云原生部署
    <br />
    <a href="https://github.com/felix-liuyj/base-fastapi-template"><strong>查看详细文档 »</strong></a>
    <br />
    <br />
    <a href="https://github.com/felix-liuyj/base-fastapi-template">演示</a>
    ·
    <a href="https://github.com/felix-liuyj/base-fastapi-template/issues">报告Bug</a>
    ·
    <a href="https://github.com/felix-liuyj/base-fastapi-template/issues">功能请求</a>
</p>

## 目录

- [Base FastAPI Template](#base-fastapi-template)
    - [目录](#目录)
        - [快速开始](#快速开始)
            - [环境要求](#环境要求)
            - [安装步骤](#安装步骤)
        - [项目结构](#项目结构)
        - [核心功能](#核心功能)
        - [部署选项](#部署选项)
            - [Docker部署](#docker部署)
            - [使用GitHub Actions](#使用github-actions)
            - [使用GitLab CI](#使用gitlab-ci)
        - [技术栈](#技术栈)
        - [环境变量配置](#环境变量配置)
            - [应用基本配置](#应用基本配置)
            - [安全与加密](#安全与加密)
            - [Redis配置](#redis配置)
            - [MongoDB配置](#mongodb配置)
            - [Kafka配置](#kafka配置)
            - [SMTP邮件服务配置](#smtp邮件服务配置)
            - [阿里云OSS配置](#阿里云oss配置)
            - [Azure Blob存储配置](#azure-blob存储配置)
            - [Azure SSO单点登录配置](#azure-sso单点登录配置)

### 快速开始

#### 环境要求

1. Python 3.13+
2. Poetry（包管理工具）
3. Docker（用于容器化部署）
4. MongoDB（数据库）
5. Redis（缓存和会话管理）
6. Kafka（可选，用于消息队列）

#### 安装步骤

1. 克隆仓库

    ```sh
    git clone https://github.com/felix-liuyj/base-fastapi-template.git
    cd base-fastapi-template
    ```

2. 安装依赖

    ```sh
    # 安装Poetry（如果尚未安装）
    curl -sSL https://install.python-poetry.org | python3 -
    
    # 安装项目依赖
    poetry install
    
    # 激活虚拟环境
    poetry shell
    ```

3. 配置环境变量

    ```sh
    # 复制示例环境变量文件
    cp .env.example .env
    
    # 编辑.env文件，填入必要的环境变量
    ```

4. 运行开发服务器

    ```sh
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```

5. 访问API文档：http://localhost:8000/docs

### 项目结构

```
├── /app/                  # 应用主目录
│  ├── /api/               # API路由定义
│  ├── /config/            # 配置模块
│  ├── /forms/             # 请求表单模型
│  ├── /libs/              # 工具库和辅助函数
│  │  ├── /ctrl/           # 控制器（云服务、数据库、消息队列）
│  │  ├── /sso/            # 单点登录实现
│  ├── /models/            # 数据模型定义
│  ├── /response/          # 响应模型
│  ├── /statics/           # 静态资源
│  ├── /templates/         # Jinja2模板
│  └── /view_models/       # 视图模型层
├── /ci-cd/                # CI/CD配置
│  ├── /github-actions/    # GitHub Actions工作流
│  ├── /gitlab-actions/    # GitLab CI配置
│  └── Jenkinsfile         # Jenkins流水线
├── .env.example           # 环境变量示例
├── Dockerfile             # Docker构建文件
├── pyproject.toml         # Poetry依赖管理
├── main.py                # 应用入口点
└── README.md              # 项目文档
```

### 核心功能

- **高性能API框架**：基于FastAPI，支持异步I/O和自动文档
- **数据持久化**：MongoDB与Beanie ODM集成
- **缓存系统**：Redis集成
- **消息队列**：Kafka支持
- **认证与安全**：
    - Azure SSO集成
    - JWT认证
    - 密码加密
- **云服务集成**：
    - Azure Blob存储
    - 阿里云OSS对象存储
    - 其他阿里云服务API
- **部署支持**：
    - Docker容器化
    - 多种CI/CD流水线配置
    - 云原生部署支持

### 部署选项

#### Docker部署

```sh
# 构建Docker镜像
docker build -t base-fastapi-app .

# 运行容器
docker run -d -p 8000:8000 --name fastapi-app base-fastapi-app
```

#### 使用GitHub Actions

GitHub Actions 是一个持续集成和持续部署（CI/CD）工具，支持自动化构建、测试和部署流程。本项目的 GitHub Actions 工作流配置文件位于
`.github/workflows` 目录，主要实现以下功能：

1. **代码检查与测试**：

    - 在每次提交代码或创建 Pull Request 时，自动运行代码质量检查（如 linting）和单元测试，确保代码符合质量标准。

2. **Docker 镜像构建**：

    - 自动构建项目的 Docker 镜像，并将其推送到指定的容器镜像仓库（如 Docker Hub 或 GitHub Container Registry）。

3. **部署到阿里云 SAE**：

    - 使用阿里云 Serverless 应用引擎（SAE）进行部署。工作流会通过阿里云 CLI 或 API 将最新的镜像部署到 SAE 环境中，实现无缝更新。

4. **通知与报告**：

    - 在工作流执行完成后，发送通知（如通过 Slack 或邮件）以报告构建和部署状态。

#### 使用GitLab CI

GitLab CI 是 GitLab 提供的内置 CI/CD 工具，支持从代码提交到生产部署的全流程自动化。本项目的 GitLab CI 配置文件位于
`ci-cd/gitlab-actions/.gitlab-ci.yml`，主要实现以下功能：

1. **代码质量检查**：

    - 在代码提交后，自动运行静态代码分析工具（如 pylint 或 mypy），确保代码符合规范。

2. **镜像扫描**：

    - 在构建 Docker 镜像后，使用安全扫描工具（如 Trivy）对镜像进行漏洞扫描，确保镜像安全性。

3. **部署到 Azure 容器服务**：

    - 自动将构建的 Docker 镜像推送到 Azure 容器注册表（ACR），并通过 Azure Kubernetes Service（AKS）进行部署。工作流会使用
      Azure
      CLI 或 Helm 完成部署和更新。

4. **版本管理与回滚**：

    - 支持版本化部署，记录每次部署的版本信息，并在需要时快速回滚到之前的版本。

通过以上 CI/CD 流程，项目能够实现高效的开发、测试和部署，提升团队协作效率并降低生产环境的风险。

### 技术栈

- **Web框架**：[FastAPI](https://fastapi.tiangolo.com/)
- **ASGI服务器**：[Uvicorn](https://www.uvicorn.org/)
- **数据验证**：[Pydantic](https://pydantic-docs.helpmanual.io/)
- **ORM**：[Beanie](https://beanie-odm.dev/)（MongoDB ODM）
- **数据库**：[MongoDB](https://www.mongodb.com/)
- **缓存**：[Redis](https://redis.io/)
- **消息队列**：[Kafka](https://kafka.apache.org/)
- **云服务**：
    - [Azure Blob Storage](https://azure.microsoft.com/zh-cn/services/storage/blobs/)
    - [阿里云OSS](https://www.aliyun.com/product/oss)
- **认证**：
    - [Azure SSO](https://azure.microsoft.com/zh-cn/services/active-directory/)
    - [JWT](https://jwt.io/)
- **开发工具**：
    - [Poetry](https://python-poetry.org/)
    - [Docker](https://www.docker.com/)

### 环境变量配置

项目使用`.env`文件进行环境变量配置，以下是主要配置项的说明：

#### 应用基本配置

| 变量名      | 描述            | 示例值             |
|----------|---------------|-----------------|
| APP_NAME | 应用名称          | FastAPI Backend |
| APP_NO   | 应用编号，用于标识不同实例 | app001          |
| APP_ENV  | 运行环境          | dev/test/prod   |

#### 安全与加密

| 变量名             | 描述            | 示例值                 |
|-----------------|---------------|---------------------|
| ENCRYPT_KEY     | 用于加密敏感数据的密钥   | your-secure-key     |
| FRONTEND_DOMAIN | 前端域名，用于CORS配置 | https://example.com |

#### Redis配置

| 变量名                | 描述          | 示例值                   |
|--------------------|-------------|-----------------------|
| REDIS_HOST         | Redis服务器地址  | localhost             |
| REDIS_PORT         | Redis服务器端口  | 6379                  |
| REDIS_CLUSTER_NODE | Redis集群节点地址 | host1:6379,host2:6379 |
| REDIS_USERNAME     | Redis用户名    | default               |
| REDIS_PASSWORD     | Redis密码     | your-redis-password   |

#### MongoDB配置

| 变量名                           | 描述           | 示例值                       |
|-------------------------------|--------------|---------------------------|
| MONGODB_USERNAME              | MongoDB用户名   | mongodb_user              |
| MONGODB_PASSWORD              | MongoDB密码    | your-mongodb-password     |
| MONGODB_URI                   | MongoDB连接字符串 | mongodb://localhost:27017 |
| MONGODB_DB                    | MongoDB数据库名  | fastapi_db                |
| MONGODB_PORT                  | MongoDB端口    | 27017                     |
| MONGODB_AUTHENTICATION_SOURCE | MongoDB认证数据库 | admin                     |

#### Kafka配置

| 变量名                          | 描述              | 示例值                     |
|------------------------------|-----------------|-------------------------|
| KAFKA_CLUSTER_BROKERS        | Kafka集群地址       | kafka1:9092,kafka2:9092 |
| KAFKA_CLUSTER_TOPICS         | Kafka主题列表       | topic1,topic2           |
| KAFKA_CLUSTER_CONSUMER_GROUP | 消费者组标识          | fastapi-consumer-group  |
| KAFKA_CLUSTER_SASL_USERNAME  | Kafka SASL认证用户名 | kafka_user              |
| KAFKA_CLUSTER_SASL_PASSWORD  | Kafka SASL认证密码  | your-kafka-password     |

#### SMTP邮件服务配置

| 变量名           | 描述          | 示例值                |
|---------------|-------------|--------------------|
| SMTP_HOST     | SMTP服务器地址   | smtp.example.com   |
| SMTP_USERNAME | SMTP用户名     | mail@example.com   |
| SMTP_API_USER | SMTP API用户名 | api_user           |
| SMTP_PASSWORD | SMTP密码      | your-smtp-password |
| SMTP_PORT     | SMTP端口      | 465                |

#### 阿里云OSS配置

| 变量名                   | 描述           | 示例值                    |
|-----------------------|--------------|------------------------|
| ALI_OSS_ACCESS_KEY    | 阿里云OSS访问密钥ID | your-ali-access-key    |
| ALI_OSS_ACCESS_SECRET | 阿里云OSS访问密钥密码 | your-ali-access-secret |
| ALI_OSS_REGION        | 阿里云OSS区域     | oss-cn-hangzhou        |
| ALI_OSS_BUCKET_NAME   | 阿里云OSS存储桶名称  | your-bucket-name       |

#### Azure Blob存储配置

| 变量名                       | 描述               | 示例值                  |
|---------------------------|------------------|----------------------|
| AZURE_BLOB_ACCOUNT_NAME   | Azure Blob存储账户名  | your-storage-account |
| AZURE_BLOB_ACCESS_TOKEN   | Azure Blob存储访问密钥 | your-access-token    |
| AZURE_BLOB_CONTAINER_NAME | Azure Blob存储容器名  | your-container-name  |

#### Azure SSO单点登录配置

| 变量名                     | 描述             | 示例值                                   |
|-------------------------|----------------|---------------------------------------|
| SSO_AZURE_CLIENT_ID     | Azure应用程序客户端ID | your-client-id                        |
| SSO_AZURE_CLIENT_SECRET | Azure客户端密钥     | your-client-secret                    |
| SSO_AZURE_CALLBACK_PATH | Azure回调路径      | /api/auth/callback                    |
| SSO_AZURE_REDIRECT_URI  | Azure重定向URI    | https://api.example.com/auth/callback |
| SSO_AZURE_BASE_URL      | Azure基础URL     | https://login.microsoftonline.com/    |

<!-- links -->

[contributors-shield]: https://img.shields.io/github/contributors/felix-liuyj/base-fastapi-template.svg?style=flat-square

[contributors-url]: https://github.com/felix-liuyj/base-fastapi-template/graphs/contributors

[forks-shield]: https://img.shields.io/github/forks/felix-liuyj/base-fastapi-template.svg?style=flat-square

[forks-url]: https://github.com/felix-liuyj/base-fastapi-template/network/members

[stars-shield]: https://img.shields.io/github/stars/felix-liuyj/base-fastapi-template.svg?style=flat-square

[stars-url]: https://github.com/felix-liuyj/base-fastapi-template/stargazers

[issues-shield]: https://img.shields.io/github/issues/felix-liuyj/base-fastapi-template.svg?style=flat-square

[issues-url]: https://img.shields.io/github/issues/felix-liuyj/base-fastapi-template.svg

[license-shield]: https://img.shields.io/github/license/felix-liuyj/base-fastapi-template.svg?style=flat-square

[license-url]: https://github.com/felix-liuyj/base-fastapi-template/blob/master/LICENSE.txt