# nest-boot/skills

Nest Boot 相关 AI Agent Skills 仓库，用于沉淀 `@nest-boot` 生态及其依赖的通用 Node.js 工程规范、框架集成和最佳实践。

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
| [nest-boot-bullmq](skills/nest-boot-bullmq/) | 使用 `@nest-boot/bullmq` 构建和管理 NestJS 异步任务队列的通用规范。适用于创建队列、定义 Job payload、注册 Processor、投递任务或排查队列依赖注入，重点保证名称与载荷类型安全、注册关系一致和处理器职责清晰。 |
| [nest-boot-domain-renaming](skills/nest-boot-domain-renaming/) | 在 NestJS 与 `@nest-boot` 应用中执行跨层领域、实体、模块或持久化概念重命名的完整工作流。适用于同步修改目录、文件、TypeScript 符号、依赖注入、GraphQL schema/operation、MikroORM 实体与表列、迁移、RLS policy、队列、客户端、测试和文档，并区分本地概念、通用术语、外部协议与存量数据；普通文件组织使用 `nest-boot-module-design`。 |
| [nest-boot-graphql](skills/nest-boot-graphql/) | 使用 `@nest-boot/graphql` 编写、暴露、重命名、审查或排查 GraphQL Schema、Resolver、ResolveField、Input、Args、Connection 及客户端 operation 的通用规范。适用于 schema 类型冲突、关联字段缺失、代码通过编译但真实 GraphQL 查询失败或跨层名称需要同步的场景。 |
| [nest-boot-logger](skills/nest-boot-logger/) | 使用 `@nest-boot/logger` 在 NestJS 可注入类中记录结构化日志的通用规范。适用于添加日志、调试结构化追踪、配置 LoggerModule 或排查日志上下文，重点覆盖依赖注入、上下文绑定、日志级别与敏感数据保护。 |
| [nest-boot-maintainer](skills/nest-boot-maintainer/) | 诊断使用 `@nest-boot/*` 时发现的可复现框架缺陷或通用改进建议，并为 `nest-boot/nest-boot` 准备或提交 GitHub Issue、修复分支和 PR。适用于运行时异常、类型或公开 API 不一致、错误生成结果、回归、跨包设计改进以及官方文档与实现不符；若问题只属于 `nest-boot/skills` 指引、业务项目约定或上游依赖，应改由相应仓库处理。 |
| [nest-boot-mikro-orm](skills/nest-boot-mikro-orm/) | 使用 `@nest-boot/mikro-orm` 构建 NestJS 持久化层的通用规范，覆盖 Entity、EntityService、关系、迁移、Seeder、外部供应商中立建模、锁与数据库验证。适用于新增或重构持久化功能，修改表、列、枚举、外键或索引，重命名实体，生成或审查迁移，以及排查 schema drift。 |
| [nest-boot-module-design](skills/nest-boot-module-design/) | 使用 NestJS 与 `@nest-boot` 新增、拆分或重构业务模块时的目录、边界、文件和类型组织规范。适用于创建新领域，安排 Entity、Service、Resolver、Controller、DTO/Input、interface/type 或 enum，拆分职责混杂的大文件，判断公共基础设施与业务代码的位置，以及沿用宿主项目的模块根目录和命名约定；领域整体改名应使用 `nest-boot-domain-renaming`。 |
| [nest-boot-row-level-security](skills/nest-boot-row-level-security/) | 使用 `@nest-boot/row-level-security` 新增、重构、审查或排查实体 Policy、RowLevelSecurity 上下文、`RequestContext.child` 局部 RLS 绕过、MikroORM 迁移或 PostgreSQL RLS 行为的通用规范。 |
| [nest-boot-skill-maintainer](skills/nest-boot-skill-maintainer/) | 在 Nest Boot 消费项目或 `nest-boot/skills` 仓库中维护和改进 agent skills。适用于直接修改项目已安装的 `.agents/skills` 副本并自评估、把成熟改进泛化后提交上游 issue 与 PR、新增或重组 skill、调整触发描述与 eval、处理拆分重命名迁移、同步合并后的正式版本以及闭环 CI 和审查；框架 BUG 或公开 API 改进应改用 `nest-boot-maintainer`，项目私有约定或未经验证的猜测不应上游化。 |
| [nest-boot-temporary-directory](skills/nest-boot-temporary-directory/) | 使用 `@nest-boot/temporary-directory` 在 NestJS HTTP、GraphQL、队列或其他 `RequestContext` 工作单元中创建并自动清理临时目录。适用于模块注册、临时文件生命周期、Multer/流式上传、后台任务、命名空间、上下文丢失或清理测试；重点保证目录只在活动上下文中分配、异步消费者不会越过上下文边界、清理所有权保持单一。 |
| [nodejs-streaming](skills/nodejs-streaming/) | 在 Node.js 服务、CLI 与 worker 中设计、实现、重构和测试内存有界的 Node.js Stream 与 Web Streams 数据路径。适用于上传、下载、代理、对象存储、multipart、fetch 请求/响应、媒体处理、压缩解压或子进程集成，以及编写 `Readable`、`Writable`、`Transform`、`pipeline`、`createReadStream`、背压、重试、超时、取消、字节上限、并发预算和 OOM 回归；覆盖 Express、Fastify、NestJS 等框架，也用于排查伪流式整体缓冲、未消费响应、跨重试复用 stream 和并发放大。 |
| [skill-creator](skills/skill-creator/) | Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy. |
<!-- END GENERATED SKILLS -->

## 贡献与安全

提交 skill 改进前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。疑似漏洞、凭证或敏感数据问题请遵循 [SECURITY.md](SECURITY.md)，不要创建公开 Issue。
