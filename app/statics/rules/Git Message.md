## 一、推荐格式（Conventional Commits）

```
<type>(<scope>)!: <subject>           # 最多50字符，祈使句，首字母小写，勿结尾句号
                                      # 如有破坏性变更，加 "!"
<BLANK LINE>
<body>                                # 每行≤72字符，说明动机与变更细节、方案取舍
<BLANK LINE>
<footer>                              # 关联 issue、破坏性变更、共同作者等
```

**常用 type（团队可白名单化）**

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

**scope 建议**

- 选填，指明影响模块，例如：`auth`、`api/user`、`db`、`deps`、`infra`、`ui`
- 单一 scope，必要时使用多条提交代替“大杂烩”

**footer 约定**

- 关联：`Refs #123`，`Closes #123` / `Fixes #123`
- 破坏性：`BREAKING CHANGE: user.profile 字段重命名为 user.bio`
- 共同作者：`Co-authored-by: Name <email>`
- DCO：`Signed-off-by: Name <email>`

## 二、示例

**1）功能新增（含中文说明）**

```
feat(auth): 支持 OAuth2 PKCE 登录

为 web 客户端增加基于 PKCE 的授权码流程，避免在浏览器环境中暴露 client_secret。
包含 token 刷新与错误码统一处理。

验证：本地与 dev 环境通过登录、刷新、登出用例；新增 e2e 用例。
Refs #482
```

**2）修复缺陷并关闭 Issue**

```
fix(api/user): 修正分页参数越界导致 500

问题：page < 1 或 pageSize > 1000 时触发未捕获异常。
方案：参数归一化 + 上限限制 + 统一错误响应。

测试：新增单元测试覆盖边界；灰度验证通过。
Closes #519
```

**3）破坏性变更**

```
refactor(db)!: 统一主键为 uuid v7

BREAKING CHANGE: 所有表 id 改为 uuid v7，旧的自增 id 下线。
迁移脚本见 migrations/2025-08-20-uuid.sql。
```

**4）回滚**

```
revert: feat(search): 引入向量召回

原因：线上 QPS 异常与召回不稳定，回滚至 d4d2c1e。
Reverts commit a1b2c3d.
```
