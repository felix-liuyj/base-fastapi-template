# FastAPI 项目架构与开发规范

## 1. 项目结构

```
base-fastapi-template/
├── app/                        # 应用主目录
│   ├── api/                   # API路由层
│   │   ├── __init__.py        # 根路由定义
│   │   ├── account.py         # 账户相关路由
│   │   └── notification.py    # 通知相关路由
│   ├── config/                # 配置管理
│   │   ├── __init__.py
│   │   └── setting.py         # 应用配置
│   ├── forms/                 # 请求表单验证
│   │   ├── __init__.py
│   │   ├── account.py         # 账户相关表单
│   │   └── settings.py        # 设置相关表单
│   ├── libs/                  # 通用库和工具
│   │   ├── __init__.py
│   │   ├── constants.py       # 常量定义
│   │   ├── custom.py          # 自定义工具函数
│   │   ├── email.py           # 邮件工具
│   │   ├── helpers.py         # 辅助函数
│   │   ├── http_with_retry.py # HTTP请求重试
│   │   ├── ctrl/              # 外部服务控制器
│   │   │   ├── cloud/         # 云服务集成
│   │   │   ├── db/            # 数据库操作
│   │   │   └── kafka/         # 消息队列
│   │   └── sso/               # 单点登录
│   ├── models/                # 数据模型
│   │   ├── __init__.py
│   │   ├── account.py         # 账户模型
│   │   ├── common.py          # 通用模型
│   │   └── events.py          # 事件模型
│   ├── response/              # 响应模型
│   │   ├── __init__.py        # 响应基类
│   │   ├── account.py         # 账户响应模型
│   │   └── root.py            # 根响应模型
│   ├── statics/               # 静态资源
│   ├── templates/             # 模板文件
│   └── view_models/           # 视图模型(业务逻辑层)
│       ├── __init__.py        # 视图模型基类
│       ├── account.py         # 账户视图模型
│       └── notification.py    # 通知视图模型
└── main.py                    # 应用入口
```

## 2. 架构设计

### 2.1 分层架构

项目采用清晰的分层架构模式，各层职责分明：

```
Form(请求验证) => API(路由) => ViewModel(业务逻辑) => Model(数据模型)
```

1. **Forms层**: 请求数据验证
2. **API层**: 路由处理和请求分发
3. **ViewModel层**: 业务逻辑处理
4. **Model层**: 数据模型和数据库操作

### 2.2 请求处理流程

1. 客户端发送HTTP请求
2. FastAPI框架解析请求并验证参数（通过Forms）
3. 路由函数(API)接收验证后的参数
4. 路由函数创建ViewModel实例处理业务逻辑
5. ViewModel与Model交互完成业务操作
6. ViewModel返回统一格式的响应数据
7. API层通过ResponseModel封装响应并返回

### 2.3 异步上下文管理器模式

项目广泛使用异步上下文管理器(`async with`)模式处理业务逻辑和资源管理：

```python
# 在 app/response/__init__.py 中定义
async def create_response(view_model: VMT, *args, response_handler: callable = None, **kwargs) -> ResponseModel:
    async with view_model(*args, **kwargs) as response:
        return response_handler(response) if response_handler else response
```

## 3. 各层详细说明

### 3.1 Forms层 (app/forms/)

负责请求数据验证和参数类型转换，使用Pydantic模型进行参数校验。

```python
# 在 app/forms/account.py 中定义
class LoginForm(BaseModel):
    email: str = Body(..., embed=True)
    password: str = Body(..., embed=True)


class VerifyEmailForm(BaseModel):
    email: str = Body(..., embed=True)
    vCode: str = Body(..., embed=True)
```

**最佳实践**:

- 每个请求参数都应定义类型
- 使用Body、Query、Path等进行详细配置
- 提供参数描述和示例值
- 对敏感字段设置隐藏处理
- 参数嵌入(embed=True)保持一致性

**命名规范**:

- **Query和Path参数**: 使用下划线拼接命名法 (snake_case)
  ```python
  @router.get('/users')
  async def get_users(
      user_id: int = Path(..., description='用户ID'),
      page_size: int = Query(10, description='页面大小'),
      sort_order: str = Query('asc', description='排序方式')
  ):
      pass
  ```

- **Body和Form等JSON格式参数**: 使用驼峰命名法 (camelCase)
  ```python
  class CreateUserForm(BaseModel):
      userName: str = Body(..., embed=True, description='用户名')
      userEmail: str = Body(..., embed=True, description='用户邮箱')
      firstName: str = Body(..., embed=True, description='名')
      lastName: str = Body(..., embed=True, description='姓')
  ```

### 3.2 API层 (app/api/)

负责路由定义、权限校验和请求处理编排，使用自定义路由器提供增强功能。

```python
# 在 app/api/__init__.py 中定义自定义路由器
router = CustomApiRouter(
    prefix='', tags=['Root API'], dependencies=[]
)


# 在 app/api/account.py 中使用
@router.get(
    '/user', response_model=ResponseModel[UserProfile], description='Get user info'
)
async def get_user_info(
        request: Request,
        user_profile: Annotated[UserProfile, Depends(get_user_profile)]
):
    return await create_response(UserInfoQueryViewModel, request, user_profile)
```

**最佳实践**:

- 使用CustomApiRouter而非标准APIRouter (定义在 app/libs/constants.py 中)
- 路径遵循RESTful设计规范
- 所有端点必须包含description
- 明确定义response_model
- 使用依赖注入管理共享资源和权限
- 不在API层处理业务逻辑，而是委托给ViewModel

### 3.3 ViewModel层 (app/view_models/)

ViewModel是项目核心，处理所有业务逻辑，实现为异步上下文管理器。

```python
# 在 app/view_models/account.py 中定义
class UserInfoQueryViewModel(BaseViewModel):
    def __init__(self, request: Request, user_profile: UserProfile):
        super().__init__(request=request, user_profile=user_profile)
        self.user_data = user_profile

    async def before(self):
        await super().before()
        self.operating_successfully(self.user_data.model_dump())
```

**核心特性**:

- 通过`__aenter__`和`__aexit__`实现异步上下文管理 (在 app/view_models/__init__.py 的 BaseViewModel 中定义)
- 标准化生命周期：初始化 -> before() -> 操作 -> after()
- 内置状态管理和错误处理机制
- 丰富的响应方法：operating_successfully(), operating_failed()等

**标准化响应方法**:

```python
# 在 app/view_models/__init__.py 中定义
def operating_successfully(self, data: str | dict | list, handled: bool = False):
    self.code = ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY.value
    self.message = get_response_message(ResponseStatusCodeEnum.OPERATING_SUCCESSFULLY)
    self.data = data
    if handled:
        return
    raise ViewModelRequestException(message=data)
```

### 3.4 Model层 (app/models/)

使用Beanie ODM(基于MongoDB)定义数据模型和数据库操作。

```python
# 在 app/models/account.py 中定义
class UserModel(BaseDatabaseModel):
    email: str = Field(..., description='User email')
    password_hash: str = Field(..., description='User password hash')
    status: UserStatusEnum = Field(UserStatusEnum.NEEDS_APPROVAL, description='User status')
    userType: UserTypeEnum = Field(UserTypeEnum.BUYER, description='User type')

    class Settings:
        name = 'users'
        indexes = [
            [('email', 1)],
            [('_id', HASHED)]
        ]

    @property
    def information(self):
        return self.model_dump(exclude=['password_hash'])
```

**最佳实践**:

- 所有字段都应有类型注解和描述
- 使用类属性Settings配置集合名称和索引
- 通过property方法扩展模型功能
- 使用exclude过滤敏感字段
- 字典操作使用安全方法

## 4. 统一响应处理

### 4.1 响应模型

所有API响应使用统一的ResponseModel格式：

```python
# 在 app/response/__init__.py 中定义
class ResponseModel(BaseModel, Generic[T]):
    category: str = Field(..., description='平台标识符', examples=['00'])
    code: ResponseStatusCodeEnum = Field(..., description='响应状态码')
    message: str = Field(..., description='响应消息')
    data: T = Field(..., description='响应数据')
```

### 4.2 响应状态码

```python
# 在 app/libs/constants.py 中定义
class ResponseStatusCodeEnum(Enum):
    OPERATING_SUCCESSFULLY = '0000'  # 操作成功
    EMPTY_CONTENT = '0001'  # 内容为空
    NOTHING_CHANGED = '0002'  # 未发生变化
    OPERATING_FAILED = '2000'  # 操作失败
    ILLEGAL_PARAMETERS = '2001'  # 非法参数
    UNAUTHORIZED = '2002'  # 未授权
    FORBIDDEN = '2003'  # 禁止访问
    NOT_FOUND = '2004'  # 未找到
    METHOD_NOT_ALLOWED = '2005'  # 方法不允许
    REQUEST_TIMEOUT = '2006'  # 请求超时
    SYSTEM_ERROR = '3000'  # 系统错误
```

### 4.3 响应创建工具函数

```python
# 在 app/response/__init__.py 中定义
async def create_response(view_model: VMT, *args, response_handler: callable = None, **kwargs) -> ResponseModel:
    async with view_model(*args, **kwargs) as response:
        return response_handler(response) if response_handler else response
```

对于SSE（服务器发送事件）响应：

```python
# 在 app/response/__init__.py 中定义
async def create_event_stream_response(view_model: VMT, *args, **kwargs) -> StreamingResponse:
    async def event_stream():
        while True:
            async with view_model(*args, **kwargs) as response:
                yield f'data: {response.model_dump_json()}\n\n'
            await sleep(5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

## 5. 错误处理机制

### 5.1 自定义异常类

```python
# 在 app/view_models/__init__.py 中定义
class ViewModelException(Exception):
    pass


class ViewModelRequestException(ViewModelException):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
```

### 5.2 全局异常处理器

```python
# 在 main.py 中注册
def register_http_exception_handlers(app: FastAPI):
    app.add_exception_handler(HTTP_401_UNAUTHORIZED, custom_un_auth_exception_handler)
    app.add_exception_handler(HTTP_403_FORBIDDEN, custom_auth_forbidden_exception_handler)
    app.add_exception_handler(RequestValidationError, custom_validation_exception_handler)
    app.add_exception_handler(HTTP_500_INTERNAL_SERVER_ERROR, custom_internal_server_exception_handler)
```

### 5.3 具体异常处理器实现

```python
# 在 app/libs/constants.py 中定义
async def custom_validation_exception_handler(exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            'category': '00',
            'code': ResponseStatusCodeEnum.ILLEGAL_PARAMETERS.value,
            'message': get_response_message(ResponseStatusCodeEnum.ILLEGAL_PARAMETERS),
            'data': [f'{" → ".join(map(str, error.get("loc")))}: {error.get("msg")}' for error in exc.errors()]
        }
    )
```

### 5.4 自定义路由器异常处理增强

```python
# 在 app/libs/constants.py 中定义
class CustomApiRouter(APIRouter):
    def api_route(self, *args, **kwargs):
        responses = {
            422: {'description': 'Illegal Parameters', 'model': IllegalParametersResponseModel},
            500: {'description': 'Internal Server Error', 'model': InternalServerErrorResponseModel}
        }
        kwargs.update(responses=responses)
        return super().api_route(*args, **kwargs)
```

## 6. 开发规范与最佳实践

### 6.1 通用编码规范

#### 6.1.1 命名规范

- **类名**: 使用大驼峰命名法 (PascalCase)
  ```python
  class UserProfile:
      pass
  ```

- **方法名和变量名**: 使用下划线命名法 (snake_case)
  ```python
  def get_user_info():
      user_profile = fetch_profile()
  ```

- **常量**: 全大写加下划线
  ```python
  MAX_RETRY_COUNT = 3
  ```

- **枚举成员**: 全大写加下划线
  ```python
  class ResponseStatusCodeEnum(Enum):
      OPERATING_SUCCESSFULLY = '0000'
  ```

#### 6.1.2 导入规范

- 使用`__all__`控制模块导出
  ```python
  # 在项目各模块文件开头常见的写法
  __all__ = (
      'UserLogoutViewModel',
      'AccountAuthCallbackViewModel',
  )
  ```

- 导入排序: 标准库 > 第三方库 > 本地库
  ```python
  import json
  from datetime import datetime
  
  from fastapi import Request
  from pydantic import BaseModel
  
  from app.models import UserModel
  from app.libs.custom import serialize
  ```

#### 6.1.3 代码注释

- 使用清晰的docstring
  ```python
  def serialize(obj: dict | list) -> str:
      """
      将对象序列化为JSON字符串
      
      Args:
          obj: 待序列化的字典或列表
          
      Returns:
          序列化后的JSON字符串
      """
  ```

#### 6.1.4 函数设计规范

- **函数代码行数限制**: 每个函数代码量尽量不超过20行
  ```python
  # 推荐: 简洁的函数实现
  async def create_user(user_data: dict) -> UserModel:
      """创建用户"""
      # 验证数据
      validated_data = validate_user_data(user_data)
      
      # 创建用户实例
      user = UserModel(**validated_data)
      
      # 保存到数据库
      await user.save()
      
      # 发送通知
      await send_welcome_notification(user.email)
      
      return user
  ```

- **数据初始化分离**: 大量参数的数据类型初始化应提取为独立方法
  ```python
  # 推荐: 将复杂的数据初始化提取为独立方法
  def get_default_user_config() -> dict:
      """获取默认用户配置"""
      return {
          'notification_settings': {
              'email_enabled': True,
              'sms_enabled': False,
              'push_enabled': True,
          },
          'privacy_settings': {
              'profile_visible': True,
              'email_visible': False,
              'phone_visible': False,
          },
          'feature_flags': {
              'beta_features': False,
              'advanced_mode': False,
              'analytics_enabled': True,
          }
      }
  
  async def initialize_user_profile(email: str) -> UserProfile:
      """初始化用户配置文件"""
      default_config = get_default_user_config()
      profile = UserProfile(
          email=email,
          config=default_config
      )
      return profile
  ```

- **功能封装**: 多余的功能代码封装成通用方法
  ```python
  # 推荐: 将通用功能提取为独立方法
  async def validate_and_hash_password(password: str) -> str:
      """验证密码强度并生成哈希"""
      if not is_strong_password(password):
          raise ValueError("密码强度不够")
      return hash_password(password)
  
  async def send_verification_email(email: str, code: str) -> bool:
      """发送验证邮件"""
      template = get_email_template('verification')
      content = render_template(template, {'code': code})
      return await send_email(email, '邮箱验证', content)
  
  async def create_user_account(user_form: CreateUserForm) -> UserModel:
      """创建用户账户"""
      # 验证密码并生成哈希
      password_hash = await validate_and_hash_password(user_form.password)
      
      # 创建用户
      user = UserModel(
          email=user_form.email,
          password_hash=password_hash,
          status=UserStatusEnum.PENDING_VERIFICATION
      )
      await user.save()
      
      # 发送验证邮件
      verification_code = generate_verification_code()
      await send_verification_email(user.email, verification_code)
      
      return user
  ```

### 6.2 安全编码规范

#### 6.2.1 字典操作

**必须使用安全的字典操作方法**:

- 使用`.get()`而非直接索引:
  ```python
  # 推荐
  value = data.get('key', default_value)
  
  # 不推荐
  value = data['key']  # 可能抛出KeyError
  ```

- 使用`.setdefault()`设置默认值:
  ```python
  # 推荐
  data.setdefault('key', default_value)
  
  # 不推荐
  if 'key' not in data:
      data['key'] = default_value
  ```

- 使用`.update()`批量更新:
  ```python
  # 推荐
  data.update({'key1': value1, 'key2': value2})
  
  # 不推荐
  data['key1'] = value1
  data['key2'] = value2
  ```

#### 6.2.2 错误处理

- 使用带有重试的HTTP请求:
  ```python
  # 在 app/libs/http_with_retry.py 中定义
  async def request_get_with_retry(url, headers=None, params=None, retries=3):
      await request_with_retry(url, RequestMethodEnum.GET, headers, params, retries)
  ```

- 使用上下文管理器:
  ```python
  # 在 app/libs/ctrl/__init__.py 中定义
  @staticmethod
  @contextmanager
  def req_status_monitor():
      try:
          yield
      except SSLError as e:
          # 处理SSL异常
          print(f"SSL Error: {e}")
  ```

### 6.3 数据库操作规范

#### 6.3.1 Beanie ODM最佳实践

- 定义明确的集合名称:
  ```python
  class Settings:
      name = 'users'
  ```

- 定义索引:
  ```python
  class Settings:
      indexes = [
          [('email', 1)],  # 单字段索引 
          [('_id', HASHED)]  # 哈希索引
      ]
  ```

- 使用异步查询:
  ```python
  # 在 app/view_models/account.py 等文件中常见的查询模式
  user = await UserModel.find_one(UserModel.email == email)
  
  users = await UserModel.find().sort(-UserModel.created_at).to_list()
  ```

- 模型直接更新:
  ```python
  # 在 app/view_models/account.py 的 ChangeUserStatusViewModel 中使用
  await user.update_fields(status=UserStatusEnum.ACTIVE)
  ```

- 属性方法添加派生字段:
  ```python
  # 在 app/models/events.py 的 EventModel 中使用
  @property
  def information(self):
      return self.model_dump(exclude=['password_hash'])
  ```

### 6.4 异步编程规范

#### 6.4.1 异步函数定义

- 所有涉及I/O的操作应该是异步的:
  ```python
  async def fetch_user_data(user_id: str):
      user = await UserModel.find_one(UserModel.id == user_id)
      return user
  ```

- 使用asyncio并发:
  ```python
  tasks = [fetch_user_data(uid) for uid in user_ids]
  users = await asyncio.gather(*tasks)
  ```

- 使用异步上下文管理器:
  ```python
  # 在 app/view_models/__init__.py 中使用
  async with RedisCacheController() as redis:
      await redis.set(key, value)
  ```

#### 6.4.2 异步生命周期管理

ViewModel的标准异步生命周期 (在 app/view_models/__init__.py 的 BaseViewModel 中定义):

1. `__init__`: 初始化实例变量
2. `__aenter__`: 设置上下文，调用before()
3. `before()`: 执行业务逻辑前的准备
4. 执行业务逻辑
5. `__aexit__`: 清理资源，调用after()
6. `after()`: 执行业务逻辑后的清理

### 6.5 API设计规范

- 使用CustomApiRouter而非标准APIRouter
- 所有端点都要有详细描述(description)
- 显式定义response_model
- 使用依赖注入管理权限和共享资源
- 路径遵循RESTful规范

```python
# 在 app/api/account.py 中使用
@router.get(
    '/users/{user_id}',
    response_model=ResponseModel[UserProfile],
    description='根据ID获取用户信息'
)
```

### 6.6 视图模型设计规范

#### 6.6.1 标准响应方法

视图模型应该使用标准化响应方法 (在 app/view_models/__init__.py 的 BaseViewModel 中定义):

```python
# 成功响应
self.operating_successfully(data)

# 失败响应
self.operating_failed(message)

# 内容为空
self.empty_content(message)

# 参数错误
self.illegal_parameters(message)

# 未授权
self.unauthorized(message)

# 禁止访问
self.forbidden(message)

# 资源未找到
self.not_found(message)

# 系统错误
self.system_error(message)
```

#### 6.6.2 初始化模式

```python
# 在 app/view_models/__init__.py 的 BaseViewModel 中定义
def __init__(
        self, request: Request = None, user_profile: UserProfile = None,
        access_title: list[UserTypeEnum] = None, bg_tasks: BackgroundTasks = None
):
    super().__init__()
    self.request = request
    self.user_profile = user_profile
    # ...其他初始化
```

### 6.7 共享资源操作规范

#### 6.7.1 Redis操作

```python
# 在 app/libs/ctrl/db/redis.py 中定义的方法使用方式
# 设置键值
await self.redis.set(key, value, expire=3600)

# 获取键值
value = await self.redis.get(key)

# 使用上下文管理器
async with RedisCacheController() as redis:
    await redis.set(key, value)
```

#### 6.7.2 云存储操作

```python
# 在 app/view_models/__init__.py 的 BaseOssViewModel 中定义
# 上传文件
async with AzureBlobController() as ab_c:
    result = await ab_c.upload_file(file_path, data, overwrite=True)

# 生成访问URL
access_url = await self.generate_access_url(file_path)
```

## 7. 应用实例化与生命周期

### 7.1 应用创建

```python
# 在 main.py 中定义
def create_app():
    app = FastAPI(lifespan=lifespan)

    # 静态文件挂载
    app.mount("/statics", StaticFiles(directory=statis_path), name="statics")

    # 中间件注册
    app.add_middleware(CORSMiddleware, allow_origins=['*'], ...)

    # 注册自定义中间件
    register_middlewares(app)

    # 注册异常处理器
    register_http_exception_handlers(app)

    return app
```

### 7.2 应用生命周期

```python
# 在 main.py 中定义
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时操作
    print('Check Env Config:', dict(get_settings()))

    # 注册路由
    await register_routers(app)

    # 初始化数据库
    mongo_client = await initialize_mongodb_client()
    await init_db(mongo_client)

    print("Startup complete")
    yield

    # 关闭时操作
    mongo_client.close()
    print("Shutdown complete")
```

## 8. 工程化与项目管理

### 8.1 依赖管理

项目使用Poetry管理依赖，在pyproject.toml中定义:

```toml
[tool.poetry.dependencies]
python = ">=3.13,<3.14"
fastapi = "*"
beanie = "*"
pydantic = "*"
httpx = "*"
redis = "*"
aiokafka = "*"
motor = "*"
python-dotenv = "*"
python-dateutil = "*"
azure-storage-blob = "*"
```

### 8.2 环境配置

使用.env文件和Settings类管理配置:

```python
# 在 app/config/setting.py 中定义
class Settings(BaseSettings):
    # 应用基本配置
    APP_NAME: str
    APP_NO: str
    APP_ENV: str

    # 数据库配置
    MONGODB_URI: str
    MONGODB_USERNAME: str
    MONGODB_PASSWORD: str

    # 缓存配置
    REDIS_HOST: str
    REDIS_PORT: int
```

### 8.3 CI/CD配置

项目支持多种CI/CD工具，配置文件位于ci-cd目录:

- GitHub Actions: ci-cd/github-actions/workflows/
- GitLab CI: ci-cd/gitlab-actions/
- Jenkins: ci-cd/Jenkinsfile

```yaml
# 示例GitHub Actions工作流配置位于 ci-cd/github-actions/workflows/build-image-to-acr-and-deploy-to-sae.yaml
name: Build and Deploy
on:
  push:
    branches: [ main ]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.13"
```

## 9. Git 提交规范

### 9.1 推荐格式（Conventional Commits）

```
<type>(<scope>)!: <subject>           # 最多50字符，祈使句，首字母小写，勿结尾句号
                                      # 如有破坏性变更，加 "!"
<BLANK LINE>
<body>                                # 每行≤72字符，说明动机与变更细节、方案取舍
<BLANK LINE>
<footer>                              # 关联 issue、破坏性变更、共同作者等
```

### 9.2 常用 type（团队可白名单化）

- **feat**：新增功能（触发 *minor*）
- **fix**：缺陷修复（触发 *patch*）
- **docs**：仅文档
- **style**：格式（不影响逻辑，如空格、分号、格式化）
- **refactor**：重构（无功能变更、无修复）
- **perf**：性能优化
- **test**：测试相关
- **build**：构建系统或外部依赖（npm、poetry、docker 等）
- **ci**：CI 配置
- **chore**：杂项（不影响 src 或测试）
- **revert**：回滚

### 9.3 scope 建议

- 选填，指明影响模块，例如：`auth`、`api/user`、`db`、`deps`、`infra`、`ui`
- 单一 scope，必要时使用多条提交代替"大杂烩"

### 9.4 footer 约定

- 关联：`Refs #123`，`Closes #123` / `Fixes #123`
- 破坏性：`BREAKING CHANGE: user.profile 字段重命名为 user.bio`
- 共同作者：`Co-authored-by: Name <email>`
- DCO：`Signed-off-by: Name <email>`

### 9.5 提交示例

#### 9.5.1 功能新增（含中文说明）

```
feat(auth): 支持 OAuth2 PKCE 登录

为 web 客户端增加基于 PKCE 的授权码流程，避免在浏览器环境中暴露 client_secret。
包含 token 刷新与错误码统一处理。

验证：本地与 dev 环境通过登录、刷新、登出用例；新增 e2e 用例。
Refs #482
```

#### 9.5.2 修复缺陷并关闭 Issue

```
fix(api/user): 修正分页参数越界导致 500

问题：page < 1 或 pageSize > 1000 时触发未捕获异常。
方案：参数归一化 + 上限限制 + 统一错误响应。

测试：新增单元测试覆盖边界；灰度验证通过。
Closes #519
```

#### 9.5.3 破坏性变更

```
refactor(db)!: 统一主键为 uuid v7

BREAKING CHANGE: 所有表 id 改为 uuid v7，旧的自增 id 下线。
迁移脚本见 migrations/2025-08-20-uuid.sql。
```

#### 9.5.4 回滚

```
revert: feat(search): 引入向量召回

原因：线上 QPS 异常与召回不稳定，回滚至 d4d2c1e。
Reverts commit a1b2c3d.
```

### 9.6 Git Message 模板

项目提供了标准化的 Git 提交消息模板，帮助团队成员编写规范的提交信息。

#### 9.6.1 模板文件位置

- **全局模板**: `app/statics/rules/.gitmessage.txt`
- **项目级配置**: 在项目根目录执行以下命令应用模板

#### 9.6.2 配置使用方法

**方法一：项目级配置（推荐）**

```bash
# 在项目根目录执行
git config commit.template app/statics/rules/.gitmessage.txt

# 验证配置
git config --get commit.template
```

**方法二：全局配置**

```bash
# 复制模板到全局位置
cp app/statics/rules/.gitmessage.txt ~/.gitmessage

# 设置全局模板
git config --global commit.template ~/.gitmessage

# 验证配置
git config --global --get commit.template
```

#### 9.6.3 使用模板提交

配置完成后，执行 `git commit` 命令会自动打开编辑器并加载模板：

```bash
# 标准提交流程
git add .
git commit  # 会自动加载模板

# 或者直接指定消息（跳过模板）
git commit -m "feat(auth): 支持 OAuth2 PKCE 登录"
```

#### 9.6.4 模板内容

```
# <type>(<scope>): <subject>
#  - type: feat | fix | docs | style | refactor | perf | test | build | ci | chore | revert
#  - scope: 可选，表示影响范围，如 auth、db、api/user
#  - subject: 不超过50字符，祈使句（如：add、fix、refactor），不以句号结尾

# Body: 描述为什么改、改了什么、如何验证
# 每行不超过72字符，详细说明动机、变更点与取舍

# Footer:
# - 关联 Issue: Refs #123 / Closes #123
# - 破坏性变更: BREAKING CHANGE: xxx
# - 共同作者: Co-authored-by: Name <email>
# - DCO: Signed-off-by: Name <email>

# -------------------- 提交示例 --------------------
# feat(auth): 支持 OAuth2 PKCE 登录
#
# 为 web 客户端增加基于 PKCE 的授权码流程，避免在浏览器环境中暴露 client_secret。
# 包含 token 刷新与错误码统一处理。
#
# 验证：本地与 dev 环境通过登录、刷新、登出用例；新增 e2e 用例。
# Refs #482
#
# -------------------------------------------------
```

#### 9.6.5 IDE 集成配置

**VS Code 配置**

在 `.vscode/settings.json` 中添加：

```json
{
  "git.inputValidationLength": 50,
  "git.inputValidationSubjectLength": 50,
  "git.useCommitInputAsStashMessage": true
}
```

**JetBrains IDEs (PyCharm/WebStorm)**

1. 打开 `Settings/Preferences > Version Control > Git`
2. 勾选 `Use commit message template`
3. 设置路径为 `app/statics/rules/.gitmessage.txt`

#### 9.6.6 团队协作建议

1. **强制使用模板**：在 `.pre-commit-hooks.yaml` 中添加提交消息检查
2. **PR 合并规范**：确保 PR 标题遵循 Conventional Commits 格式
3. **自动化检查**：使用 `commitizen` 或 `conventional-changelog` 工具
4. **培训新成员**：确保团队成员了解模板使用方法

#### 9.6.7 常见问题解决

**问题 1：模板不生效**

```bash
# 检查配置
git config --get commit.template

# 重新设置
git config commit.template app/statics/rules/.gitmessage.txt
```

**问题 2：编辑器不自动打开**

```bash
# 设置默认编辑器
git config --global core.editor "code --wait"  # VS Code
git config --global core.editor "vim"          # Vim
```

**问题 3：模板路径错误**

```bash
# 使用绝对路径
git config commit.template "$(pwd)/app/statics/rules/.gitmessage.txt"
```

## 10. 安全性考虑

### 10.1 身份验证与授权

- 使用Azure SSO进行身份验证 (在 app/libs/sso/azure.py 中实现)
- 使用JWT令牌保持会话
- 基于角色的访问控制

### 10.2 数据安全

- 密码哈希存储
- 敏感数据加密
- HTTPS传输

### 10.3 安全最佳实践

- 所有输入都进行验证
- 防止SQL注入
- 定期安全审计
- 最小权限原则

## 11. 性能优化

### 11.1 数据库优化

- 合理使用索引
- 异步数据库操作
- 结果分页

### 11.2 缓存策略

- Redis缓存频繁访问数据 (使用 app/libs/ctrl/db/redis.py 中的RedisCacheController)
- 合理设置缓存过期时间

### 11.3 异步并发

- 使用asyncio.gather并发执行任务
- 避免阻塞主事件循环

## 12. 测试策略

### 12.1 单元测试

- 测试各层独立功能
- 使用Mock隔离依赖

### 12.2 集成测试

- 测试各层交互
- API端到端测试

### 12.3 负载测试

- 性能基准测试
- 并发用户模拟
