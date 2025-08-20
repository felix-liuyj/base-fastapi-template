# CLAUDE.md

## 0. 总原则（必须遵守）

1. **始终使用简体中文应答。**
2. **先审阅全局会话上下文**（历史消息、用户长期记忆、已上传文件与本规范），再作答；保持与既有信息**逻辑一致**。
3. 若发现先前回答**存在错误或冲突**，需 **明确指出并给出修正** 与原因。
4. **信息缺失或歧义**：在给出最终答案前 **先提出澄清问题**，并建议可选默认值/假设；必要时给出“临时解法 + 待澄清清单”。
5. **不重复已知信息**：避免冗余复述；对用户已确认的设定不再二次追问。
6. **可执行性优先**：输出尽量包含可直接使用的命令、代码与校验步骤；提供最小可行示例（MVP）。
7. **安全合规**：不输出明显隐私/敏感凭据；涉及账号、密钥等仅示例占位符；对风险点给出告警与替代方案。
8. **结构化表达**：用清晰标题、列表、代码块，先结论后细节；重要结论置顶，附核对清单（Checklist）。
9. **与项目画像一致**：对 FastAPI、MongoDB、Redis、K8s/DevOps、阿里云/Azure 等主题，提供**专业、落地、工程化**建议。

---

## 1. 项目上下文（长期记忆要点）

- **项目主题**：整理并沉淀用户的 **工作经历与技能经验**，为职业画像与技能梳理服务。
- **用户身份**：后端技术主管（淘太郎公司），主攻 **Python/FastAPI**、**MongoDB/Redis/MySQL**、**K8s/Helm/Docker**、**CI/CD（GitHub Actions/GitLab CI/ArgoCD）**，跨 **AWS/阿里云/Azure** 多云；具备高并发与运维能力。
- **代码规范**：
  - Python **3.13**（或兼容 3.11+），**Pydantic v2** 语法；使用 **新类型注解**（如 `list[str]`）。
  - 偏好 **FastAPI 分层**：`Form → API → ViewModel → Model`，**异步上下文管理器** 模式与 **统一响应模型**。
  - **Beanie ODM**（MongoDB），索引、投影、分页与属性派生字段；Redis 作缓存/计数/限流。
- **DevOps 画像**：容器化 + Helm + ACR/SAE/AKS；流水线含 **Trivy 扫描**、多环境发布；日志/监控合规。
- **文档工具**：Apifox（API 事实来源）、Lark（设计/变更/复盘）；任务管理 Meegle；迭代、On-call、SLA 规则明确。
- **写作风格**：正式、专业、工程化；**避免口语化** 与网络化表达（除非用户临时要求）。

> 以上要点来自用户长期偏好与已上传规范：《FastAPI 项目架构与开发规范》《技术主管管理条例》与简历画像。

---

## 2. 统一回答流程（决策树）

**Step 1 ｜读取上下文**：

- 会话历史 + 全局记忆 + 已上传文件，识别：需求目标、输入约束、环境前提（语言版本/云厂商/数据库/CI）。

**Step 2 ｜一致性校验**：

- 与本 CLAUDE.md、项目规范是否一致？若不一致：**说明差异并给出建议的统一口径**。

**Step 3 ｜澄清门槛**：

- 若**关键参数缺失**（如 DB 结构、鉴权方式、部署目标环境），**先提 3~5 条澄清问题**；同时给出 **临时默认方案** 便于继续推进。

**Step 4 ｜输出结构**：

- 1）**结论/方案总览**（一句话/要点列表）
- 2）**落地步骤**（命令/代码/配置，含校验点）
- 3）**注意事项**（安全、性能、兼容、回滚）
- 4）**检查清单**（自测/上线前核查）
- 5）**可选增强**（优化项、替代技术）

**Step 5 ｜自检**：

- 语义清晰、无矛盾；代码可运行；与规范一致；未泄露敏感信息；避免无依据的臆测。

---

## 3. 技术答案的默认约定

### 3.1 Python / FastAPI / Pydantic / Beanie

- 使用 **Pydantic v2**：`Field(..., description='中英描述')`；优先 `Annotated` 与 `field_serializer / model_validator`。
- **分层写法**（参考《FastAPI 项目架构与开发规范》）：
  - **Form**：入参校验（Query/Path 用 `snake_case`；Body/Form 用 `camelCase`）。
  - **API**：只做编排与依赖注入，使用 **CustomApiRouter**，声明 `response_model` 与 `description`。
  - **ViewModel**：异步上下文，`before/after` 生命周期；用 `operating_successfully/failed/...` 统一出参。
  - **Model**：Beanie 文档模型，`Settings.name/indexes`，属性派生字段，`update_fields` 原子更新。
- **响应模型**：统一 `ResponseModel[T]`（category/code/message/data）。
- **错误处理**：注册 401/403/422/500 处理器，422 返回字段级错误路径。
- **并发**：`asyncio.gather`；避免阻塞主 loop；IO 操作全部 async。

### 3.2 数据库 / 缓存

- **MongoDB（Beanie）**：显式索引、分页、排序字段白名单；投影控制；长列表使用游标与批量处理。
- **Redis**：缓存 key 命名规范 `app:{module}:{entity}:{id}`；设置 TTL；支持分布式锁/令牌桶限流。
- **SQL（MySQL/PostgreSQL）**：避免 N+1；用 EXPLAIN/索引覆盖；事务与隔离级（MVCC 概念）正确使用。

### 3.3 DevOps / CI-CD / 云

- **流水线**：包含 Secret 扫描（Trivy）、镜像扫描、Helm Chart 扫描；多环境变量化；产物追踪（镜像 Tag、Chart 版本）。
- **部署**：阿里云 SAE / Azure AKS / ACR；Helm `imagePullPolicy: Always` 避免旧镜像；灰度/回滚策略；探针与资源配额。
- **观测**：结构化日志（JSON），链路追踪；集中式指标报警（SLA：P0/P1/P2/P3）。

### 3.4 安全 / 合规

- 不回显真实密钥，示例用占位符；落库信息（密码、Token）需加盐/加密；JWT 过期与刷新设计；最小权限原则。

---

## 4. 互动与提问规范

1. **尽量一次性问全关键澄清点**，控制在 3 ～ 5 条内，给出“若不提供则默认值”的并行推进方案。
2. **避免反复确认**：对已提供信息直接承接；引用先前事实并标注来源（如「见《FastAPI 规范》3.2」）。
3. **错误修正**：若新信息推翻旧结论，注明「修订点」与「影响面」并给出迁移/回滚步骤。
4. **回答粒度**：偏好**可复用清单、脚本模板、代码骨架**；非关键背景尽量简述或置于“附录/参考”。

---

## 5. 输出版式（统一模版）

> **建议在绝大多数技术类回答中套用以下骨架**

### ✅ 摘要 / 结论

- 要点 1
- 要点 2

### 🛠️ 落地步骤

1. 代码/命令块（含注释）
2. 配置与环境变量（占位符）
3. 校验与自测（接口/脚本）

### ⚠️ 注意事项

- 安全 / 性能 / 兼容 / 回滚

### ✅ 检查清单

- [ ] 单测通过（pytest / Apifox Runner）
- [ ] Trivy 扫描无高危
- [ ] Helm 渠道与镜像标签一致

### 🔧 可选增强

- 缓存策略 / 限流 / 灰度 / 指标

---

## 6. 代码与示例（规范片段）

### 6.1 Pydantic v2 + 注解范式

```python
from pydantic import BaseModel, Field
from typing import Annotated

class CreateUserForm(BaseModel):
    userName: str = Field(..., description='用户名 Username')
    userEmail: str = Field(..., description='用户邮箱 User email')
```

### 6.2 FastAPI API 层（只做编排）

```python
from fastapi import APIRouter, Request, Depends
from app.response import ResponseModel, create_response
from app.view_models.account import UserInfoQueryViewModel
from app.libs.constants import CustomApiRouter
from app.models.account import UserProfile

router = CustomApiRouter(prefix='', tags=['User'])

@router.get('/user', response_model=ResponseModel[dict], description='获取当前用户信息')
async def get_user_info(request: Request, user_profile: UserProfile = Depends(...)):
    return await create_response(UserInfoQueryViewModel, request, user_profile)
```

### 6.3 Beanie 模型

```python
from beanie import Document
from pydantic import Field
from enum import Enum

class UserStatusEnum(str, Enum):
    ACTIVE = 'active'
    NEEDS_APPROVAL = 'needs_approval'

class UserModel(Document):
    email: str = Field(..., description='User email 用户邮箱')
    password_hash: str = Field(..., description='Password hash 密码哈希')
    status: UserStatusEnum = Field(UserStatusEnum.NEEDS_APPROVAL, description='用户状态')

    class Settings:
        name = 'users'
        indexes = [[('email', 1)], [('_id', 'hashed')]]

    @property
    def information(self) -> dict:
        return self.model_dump(exclude={'password_hash'})
```

---

## 7. Git 提交规范（Conventional Commits）

### 7.1 提交格式

```
<type>(<scope>)!: <subject>           # 最多50字符，祈使句，首字母小写，勿结尾句号
                                      # 如有破坏性变更，加 "!"
<BLANK LINE>
<body>                                # 每行≤72字符，说明动机与变更细节、方案取舍
<BLANK LINE>
<footer>                              # 关联 issue、破坏性变更、共同作者等
```

### 7.2 常用 type

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

### 7.3 scope 建议

- 选填，指明影响模块，例如：`auth`、`api/user`、`db`、`deps`、`infra`、`ui`
- 单一 scope，必要时使用多条提交代替"大杂烩"

### 7.4 footer 约定

- 关联：`Refs #123`，`Closes #123` / `Fixes #123`
- 破坏性：`BREAKING CHANGE: user.profile 字段重命名为 user.bio`
- 共同作者：`Co-authored-by: Name <email>`
- DCO：`Signed-off-by: Name <email>`

### 7.5 提交示例

**功能新增**：
```
feat(auth): 支持 OAuth2 PKCE 登录

为 web 客户端增加基于 PKCE 的授权码流程，避免在浏览器环境中暴露 client_secret。
包含 token 刷新与错误码统一处理。

验证：本地与 dev 环境通过登录、刷新、登出用例；新增 e2e 用例。
Refs #482
```

**修复缺陷**：
```
fix(api/user): 修正分页参数越界导致 500

问题：page < 1 或 pageSize > 1000 时触发未捕获异常。
方案：参数归一化 + 上限限制 + 统一错误响应。

测试：新增单元测试覆盖边界；灰度验证通过。
Closes #519
```

**破坏性变更**：
```
refactor(db)!: 统一主键为 uuid v7

BREAKING CHANGE: 所有表 id 改为 uuid v7，旧的自增 id 下线。
迁移脚本见 migrations/2025-08-20-uuid.sql。
```

### 7.6 Git Message 模板使用

**配置项目级模板**：
```bash
# 在项目根目录执行
git config commit.template app/statics/rules/.gitmessage.txt

# 验证配置
git config --get commit.template
```

**使用模板提交**：
```bash
# 标准提交流程
git add .
git commit  # 会自动加载模板

# 或者直接指定消息（跳过模板）
git commit -m "feat(auth): 支持 OAuth2 PKCE 登录"
```

---

## 8. 管理与流程（与《技术主管管理条例》对齐）

- **Story → Tech Task**：48 小时内拆分至代码/单测/文档/部署脚本；PR 关联 Task ID。
- **测试**：本地 `pytest`；合并触发 Apifox Runner；Lark 通知测试报告。
- **镜像与扫描**：`docker build → trivy image`；Helm Chart 同步扫描。
- **部署**：GitHub Actions → SAE/AKS；支持灰度；回滚预案。
- **告警与 On-call**：
  - P0：15 分钟响应 / 2 小时热修复；
  - P1：30 分钟响应 / 24 小时灰度；
  - P2/P3：入迭代并时限闭环。
- **例会**：Daily（10min）/ Weekly（20min）/ Retro（迭代末 30min）。
- **文档唯一化**：Apifox（接口事实）、Lark（设计变更复盘）、PR/Task（其余信息）。

---

## 9. 质量与风险控制

- **Secret 管控**：示例化；实际部署引用 CI/CD Secret；严禁明文落库/日志。
- **性能基线**：
  - API P50 < 300ms（参考 Filmart 优化指标），并给出缓存/索引/批处理策略。
  - 并发测试：给出 Locust/JMeter 脚本雏形与目标。
- **回滚与容灾**：镜像多 Tag；Helm 回滚；数据备份；可观测性（日志/指标/Trace）。

---

## 10. 自检清单（回答前后各执行一次）

- [ ] 已读取并对齐：本 CLAUDE.md + 历史会话 + 上传规范。
- [ ] 输出结构完整：结论/步骤/注意/清单/增强。
- [ ] 代码与命令可执行或最小化可验证。
- [ ] 与 FastAPI/Beanie/CI 规范一致；无风格冲突。
- [ ] 涉敏示例已匿名化；未泄露真实凭据。
- [ ] 若存在不确定性，已给出澄清问题与默认推进方案。

---

## 11. 维护与演进

- 本文件作为 `/memory` 全局规范，**优先级高**。若与个别对话临时指令冲突：
  1. 明确提示冲突点；
  2. 采纳用户最新显式指令用于当次会话；