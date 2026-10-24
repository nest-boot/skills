# nest-boot/skills

Nest Boot 相关 AI Agent Skills 仓库，用于沉淀 `@nest-boot` 生态及其依赖的通用 Node.js 工程规范、框架集成和最佳实践。

当前指引对齐 **Nest Boot v8 正式版**：Node.js >=24.21.0、NestJS 12、原生 ESM，数据库使用 MikroORM 7.2。升级入口见 [v8 使用与迁移](skills/nest-boot-module-design/references/v8-usage.md)。

`nest-boot-database` 和 `nest-boot-queue` 分别对应 `@nest-boot/database` 和 `@nest-boot/queue`；`nest-boot-row-level-security` 指导 MikroORM 原生 RLS，不再依赖旧 Nest Boot RLS 包。

队列指引对齐 `@nest-boot/queue` 8.2+ 的 Redis/Zod API；可选 Job 历史与 GraphQL 查询使用 `@nest-boot/queue-api` 8.1+。较早 8.x 的 queue-database、字符串队列注册、通用 process 和事件装饰器已移除；不能只凭相同 major 假定 API 一致。

## 使用

建议在项目根目录中以项目级别安装本仓库中的所有 skills，并安装到通用 `.agents/skills/` 目录：

```sh
npx skills add https://github.com/nest-boot/skills \
  --agent universal \
  --copy \
  -y
```

如只需安装单个 skill，可以使用 `--skill <skill-name>` 指定名称：

```sh
npx skills add https://github.com/nest-boot/skills \
  --skill nest-boot-module-design \
  --agent universal \
  --copy \
  -y
```

### 从 v7 / 旧 beta skills 升级

`nest-boot-mikro-orm` 已更名为 `nest-boot-database`，`nest-boot-bullmq` 已更名为 `nest-boot-queue`。`skills update` 不会自动删除旧名称或安装新名称；先保存项目内尚未上游化的修改，再显式迁移：

```sh
npx skills remove nest-boot-mikro-orm nest-boot-bullmq -y
npx skills add https://github.com/nest-boot/skills \
  --skill nest-boot-database nest-boot-queue \
  --agent universal \
  --copy \
  -y
npx skills update -y
```

迁移后核对 `.agents/skills/` 和 `skills-lock.json`，确认旧名称已移除、新名称来自正式上游。其余 skill 原位更新；不要把本地候选内容或手工修改的 lockfile 当作正式安装。

### 从 `nest-boot-best-practices` 升级

`nest-boot-best-practices` 已拆分为 `nest-boot-module-design` 和 `nest-boot-domain-renaming`。`skills update -y` 不会自动删除上游已移除的 skill，也不会自动安装新名称；已有项目需要显式迁移，并可同时安装新增的 `nodejs-streaming`：

```sh
npx skills remove nest-boot-best-practices -y
npx skills add https://github.com/nest-boot/skills \
  --skill nest-boot-module-design nest-boot-domain-renaming nodejs-streaming \
  --agent universal \
  --copy \
  -y
```

## Skills 列表

<!-- BEGIN GENERATED SKILLS -->
| Skill | 描述 |
| --- | --- |
| [nest-boot-database](skills/nest-boot-database/) | 使用 Nest Boot v8 的 `@nest-boot/database` 与 MikroORM 7 构建 NestJS 持久化层，覆盖 Entity、EntityService、关系、原生 RLS、迁移、Seeder、外部供应商中立建模、锁与数据库验证。适用于升级旧数据库包、新增或重构持久化功能、修改表列与约束、注册 Auth 实体、生成或审查迁移，以及排查 schema drift。 |
| [nest-boot-domain-renaming](skills/nest-boot-domain-renaming/) | 在 NestJS 与 `@nest-boot` 应用中执行跨层领域、实体、模块或持久化概念重命名的完整工作流。适用于同步修改目录、文件、TypeScript 符号、依赖注入、GraphQL schema/operation、MikroORM 实体与表列、迁移、RLS policy、队列、客户端、测试和文档，并区分本地概念、通用术语、外部协议与存量数据；普通文件组织使用 `nest-boot-module-design`。 |
| [nest-boot-graphql](skills/nest-boot-graphql/) | 使用 `@nest-boot/graphql` 编写、暴露、重命名、审查或排查 GraphQL Schema、Resolver、ResolveField、Input、Args、Connection 及客户端 operation 的通用规范。适用于 schema 类型冲突、关联字段缺失、代码通过编译但真实 GraphQL 查询失败或跨层名称需要同步的场景。 |
| [nest-boot-logger](skills/nest-boot-logger/) | 使用 `@nest-boot/logger` 在 NestJS 可注入类中记录结构化日志的通用规范。适用于添加日志、调试结构化追踪、配置 LoggerModule 或排查日志上下文，重点覆盖依赖注入、上下文绑定、日志级别与敏感数据保护。 |
| [nest-boot-maintainer](skills/nest-boot-maintainer/) | 诊断使用 `@nest-boot/*` 时发现的可复现框架缺陷或通用改进建议，并为 `nest-boot/nest-boot` 准备或提交 GitHub Issue、修复分支和 PR。适用于运行时异常、类型或公开 API 不一致、错误生成结果、回归、跨包设计改进以及官方文档与实现不符；若问题只属于 `nest-boot/skills` 指引、业务项目约定或上游依赖，应改由相应仓库处理。 |
| [nest-boot-module-design](skills/nest-boot-module-design/) | 使用 Nest Boot v8 与 NestJS 12 新增、升级、拆分或重构业务模块的目录、边界、文件和类型组织规范。适用于 v8 ESM 与包迁移、创建新领域、安排 Entity/Service/Resolver/Controller/DTO/Input、拆分大文件和共享类型，以及确定公共基础设施与业务代码的位置；领域整体改名使用 `nest-boot-domain-renaming`。 |
| [nest-boot-queue](skills/nest-boot-queue/) | 使用 Nest Boot v8 的 Redis 队列 API（queue 8.2+、可选 queue-api 8.1+）声明 Zod jobSchemas、BaseQueue 和具名 BaseProcessor handlers。适用于任务投递与消费、job 名称/data/result 推导、Worker 启停、QueueEvents、Job 历史与 GraphQL 可见性，以及从旧 BullMQ/queue-database API 迁移；重点区分 Redis 执行、可选持久化、验证与请求身份边界。 |
| [nest-boot-row-level-security](skills/nest-boot-row-level-security/) | 在 Nest Boot v8、@nest-boot/database 与 MikroORM 7.2 中设计、迁移、审查和验证 PostgreSQL/PGlite 原生 RLS。适用于 Entity policies、session role/variables、app.member.id、事务边界、受控 fork、后台任务租户隔离，以及从已移除的 @nest-boot/row-level-security 迁移。 |
| [nest-boot-skill-maintainer](skills/nest-boot-skill-maintainer/) | 在 Nest Boot 消费项目或 `nest-boot/skills` 仓库中维护和改进 agent skills。适用于直接修改项目已安装的 `.agents/skills` 副本并自评估、把成熟改进泛化后提交上游 issue 与 PR、新增或重组 skill、调整触发描述与 eval、处理拆分重命名迁移、同步合并后的正式版本以及闭环 CI 和审查；框架 BUG 或公开 API 改进应改用 `nest-boot-maintainer`，项目私有约定或未经验证的猜测不应上游化。 |
| [nest-boot-temporary-directory](skills/nest-boot-temporary-directory/) | 使用 `@nest-boot/temporary-directory` 在 NestJS HTTP、GraphQL、队列或其他 `RequestContext` 工作单元中创建并自动清理临时目录。适用于模块注册、临时文件生命周期、Multer/流式上传、后台任务、命名空间、上下文丢失或清理测试；重点保证目录只在活动上下文中分配、异步消费者不会越过上下文边界、清理所有权保持单一。 |
| [nodejs-streaming](skills/nodejs-streaming/) | 在 Node.js 服务、CLI 与 worker 中设计、实现、重构和测试内存有界的 Node.js Stream 与 Web Streams 数据路径。适用于上传、下载、代理、对象存储、multipart、fetch 请求/响应、媒体处理、压缩解压或子进程集成，以及编写 `Readable`、`Writable`、`Transform`、`pipeline`、`createReadStream`、背压、重试、超时、取消、字节上限、并发预算和 OOM 回归；覆盖 Express、Fastify、NestJS 等框架，也用于排查伪流式整体缓冲、未消费响应、跨重试复用 stream 和并发放大。 |
<!-- END GENERATED SKILLS -->

## 贡献与安全

提交 skill 改进前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。疑似漏洞、凭证或敏感数据问题请遵循 [SECURITY.md](SECURITY.md)，不要创建公开 Issue。
