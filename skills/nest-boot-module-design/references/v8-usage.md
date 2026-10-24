# Nest Boot v8 使用基线

先检查宿主 `package.json`、锁文件和安装版本的公开声明。以下以 v8 正式版为基线。

## 运行时与 ESM

- Node.js >=24.21.0、NestJS 12，`@nest-boot/*` 使用兼容的 8.x。
- GraphQL 集成使用 `@nestjs/graphql` / `@nestjs/apollo` 14、Apollo Server 5；当前 queue 8.2 使用 BullMQ `^6.3.12` 和 Zod 4；数据库使用 MikroORM 7.2。
- `package.json` 设置 `"type": "module"`；TypeScript 使用 `module` / `moduleResolution: "NodeNext"`、`target: "ES2023"` 或更新目标。Nest legacy decorators 配置继续开启 `experimentalDecorators` / `emitDecoratorMetadata`。
- TypeScript 相对路径包含输出 `.js` 扩展名；不依赖 CommonJS require 入口。Nest Boot v8 只提供 import exports。
- 类型专用导入用 `import type`；需要 Nest 构造注入或装饰器运行时值的 class 保持 value import。不能把 `EntityManager` 等 DI token 机械改为 type-only。
- MikroORM legacy 装饰器从 `@mikro-orm/decorators/legacy` 导入；普通类型从 `@mikro-orm/core` 导入。配置、迁移和生成文件也要验证在 ESM 下可加载。

## 包与模块

| 包 | 模块 |
| --- | --- |
| `@nest-boot/database` | `DatabaseModule` |
| `@nest-boot/queue` | `QueueModule` |
| `@nest-boot/queue-api` | `QueueApiModule` |
| `@nest-boot/auth` | `AuthModule` |
| `@nest-boot/staged-upload` | `StagedUploadModule` |
| `@nest-boot/staged-upload-graphql` | `StagedUploadGraphQLModule` |

`DatabaseModule` 需要 `forRoot()` / `forRootAsync()` 初始化，环境配置由 `getDatabaseConfig()` 加载，Auth 提供 `withAuthDatabaseConfig()` 合并实体发现；具体 CLI 注册见 `nest-boot-database`。Auth 通过 `forRoot(options)` / `forRootAsync(...)` 注册；上传核心通过 `register(options)` / `registerAsync(...)` 配置并依赖 Storage，GraphQL 适配模块直接静态导入，详见 `nest-boot-graphql`。

当前队列 API 需 `@nest-boot/queue` 8.2+，可选历史/API 需 queue-api 8.1+。静态 QueueModule 配合 `@Queue()` + BaseQueue provider、Zod jobSchemas、`@Processor(QueueClass)` + BaseProcessor 具名 handlers；构造函数配置连接与 Worker，使用 `queue:start` 显式消费。QueueApiModule 复用已配置的全局 Database/GraphQL/Auth；JobEntity 进应用迁移，队列需 `@QueueVisible()` 才能从 API 读取。详细契约见 `nest-boot-queue`。

GraphQL 开发工具使用 `graphiql`。Mailer 使用 Nodemailer 10（v8 peer 范围为 `^10.0.16`）；Mailer 提供直接 transport，不会自动把邮件投递到队列。需要异步发送时由应用显式接入 Queue。

## Auth、Member 与 API key

- Auth 持有具体 `User`、`Account`、`Session`、`Verification`、`Workspace`、`Member`、`Invitation`、`UserApiKey`、`MemberApiKey`。使用内置类作为关系目标，业务扩展放在独立关联实体。
- `entities` 数组从 `@nest-boot/auth` 导出，同时加入运行时与迁移 CLI 的 `entities` / `entitiesTs`。CLI 不会执行 Nest 模块初始化。
- `Member.type` 区分 `USER` 与 `SERVICE_ACCOUNT`；服务账户不对应登录 User。工作区 key 归属于 Member，创建接口使用 `memberId`，不是 workspace owner 字段。
- 用户只能为自己对应的 member 或服务账户创建 key；查看、删除其他人的 key 仍要通过对应权限。服务账户读写权限独立，内置 owner/admin 默认拥有；改其角色、直接权限还要检查相应的成员授权权限。
- API-key 默认权限和 allowlist 分为 `apiKey.user` 与 `apiKey.member`。key 自身的 `permissions: []` 表示不额外限制，运行时仍使用 user/member 的有效权限；非空数组与所属主体权限取交集。member key 创建/更新还受目标 member 与签发者的授权上限约束。
- 区分 `permissions: []` 与配置 `allowedPermissions: []`：后者是不允许授予任何权限，省略 allowlist 才允许作用域目录内的权限。两类 key 配置不互相继承。
- 内置权限是区分大小写的字符串，role/permission 名使用小写约定；目录和角色配置扩展内置默认项，空配置不会删除默认 grants。业务 Ability callback 使用 `can(permission, action, subject, conditions?)`，不重建 Auth 内置规则。
- 数据库仅携带 `app.user.id` / `app.workspace.id` / `app.member.id` 身份边界，不携带应用权限。服务账户可以没有 user，用户可在没有所选 workspace/member 时登录；不要把 workspace 或 member 是否存在当成所有作用域通用的登录判断。
- Session 存放在主数据库。通过 Service 授权读取实体，不把数据库 RLS 当作字段或动作权限的替代。

创建服务账户与创建 MemberApiKey 是两个独立调用；应用可先创建账户，再把返回的 member ID 传入 key API。表单默认角色和权限如何选择属于宿主交互，不要求框架接口隐式创建账户。

## GraphQL 与数据库

`signUp` 返回 `{ id, token }`；管理用户的写操作返回各自 `{ id }` payload，成功后另行查询。`acceptInvitation` 返回 `{ id, memberId, workspaceId }`，后续请求切换 workspace 再查关系。

Workspace 使用永久删除。Member/API-key 表、FK cascade、service-account 约束和 RLS metadata 需要针对宿主既有数据写升级迁移；框架示例的 init + schema baseline 仅供新库，不可覆盖已执行迁移或代替数据迁移。

实现：[DatabaseModule](https://github.com/nest-boot/nest-boot/blob/main/packages/database/src/database.module.ts)、[AuthModule](https://github.com/nest-boot/nest-boot/blob/main/packages/auth/src/auth.module.ts)。
