# nest-boot/skills

Nest Boot 相关 AI Agent Skills 仓库，用于沉淀 `@nest-boot` 生态下的工程规范、框架集成和最佳实践。

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
  --skill nest-boot-best-practices \
  --agent universal \
  --copy \
  -y
```

## Skills 列表

<!-- BEGIN GENERATED SKILLS -->
| Skill | 描述 |
| --- | --- |
| [nest-boot-best-practices](skills/nest-boot-best-practices/) | 使用 `@nest-boot` 构建或重构 NestJS 业务模块时的通用组织与命名规范。适用于新增领域，调整 Entity、Service、Resolver、DTO 或 Enum，重命名实体、表或模块，以及检查服务端、客户端与数据库之间的跨层一致性。 |
| [nest-boot-bullmq](skills/nest-boot-bullmq/) | 使用 `@nest-boot/bullmq` 构建和管理 NestJS 异步任务队列的通用规范。适用于创建队列、定义 Job payload、注册 Processor、投递任务或排查队列依赖注入，重点保证名称与载荷类型安全、注册关系一致和处理器职责清晰。 |
| [nest-boot-graphql](skills/nest-boot-graphql/) | 使用 `@nest-boot/graphql` 编写、暴露、重命名、审查或排查 GraphQL Schema、Resolver、ResolveField、Input、Args、Connection 及客户端 operation 的通用规范。适用于 schema 类型冲突、关联字段缺失、代码通过编译但真实 GraphQL 查询失败或跨层名称需要同步的场景。 |
| [nest-boot-logger](skills/nest-boot-logger/) | 使用 `@nest-boot/logger` 在 NestJS 可注入类中记录结构化日志的通用规范。适用于添加日志、调试结构化追踪、配置 LoggerModule 或排查日志上下文，重点覆盖依赖注入、上下文绑定、日志级别与敏感数据保护。 |
| [nest-boot-maintainer](skills/nest-boot-maintainer/) | 诊断使用 `@nest-boot/*` 时发现的可复现框架缺陷或通用改进建议，并为 `nest-boot/nest-boot` 准备或提交 GitHub Issue、修复分支和 PR。适用于运行时异常、类型或公开 API 不一致、错误生成结果、回归、跨包设计改进以及官方文档与实现不符；若问题只属于 `nest-boot/skills` 指引、业务项目约定或上游依赖，应改由相应仓库处理。 |
| [nest-boot-mikro-orm](skills/nest-boot-mikro-orm/) | 使用 `@nest-boot/mikro-orm` 构建 NestJS 持久化层的通用规范，覆盖 Entity、EntityService、关系、迁移、Seeder、外部供应商中立建模、锁与数据库验证。适用于新增或重构持久化功能，修改表、列、枚举、外键或索引，重命名实体，生成或审查迁移，以及排查 schema drift。 |
| [nest-boot-row-level-security](skills/nest-boot-row-level-security/) | 使用 `@nest-boot/row-level-security` 新增、重构、审查或排查实体 Policy、RowLevelSecurity 上下文、`RequestContext.child` 局部 RLS 绕过、MikroORM 迁移或 PostgreSQL RLS 行为的通用规范。 |
| [nest-boot-skill-maintainer](skills/nest-boot-skill-maintainer/) | 将 Nest Boot 项目开发中发现的可复用指引缺口转化为 `nest-boot/skills` 的 skill 改进、eval、GitHub issue 或 PR。适用于用户要求总结开发经验、修订 nest-boot skill、报告过时或错误指引以及维护 skills 仓库；框架 BUG 或公开 API 改进应改用 `nest-boot-maintainer`，项目私有约定或尚未验证的猜测不应进入上游 skill。 |
| [nest-boot-temporary-directory](skills/nest-boot-temporary-directory/) | 使用 `@nest-boot/temporary-directory` 在 NestJS HTTP、GraphQL、队列或其他 `RequestContext` 工作单元中创建并自动清理临时目录。适用于模块注册、临时文件生命周期、Multer/流式上传、后台任务、命名空间、上下文丢失或清理测试；重点保证目录只在活动上下文中分配、异步消费者不会越过上下文边界、清理所有权保持单一。 |
<!-- END GENERATED SKILLS -->

## 贡献与安全

提交 skill 改进前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。疑似漏洞、凭证或敏感数据问题请遵循 [SECURITY.md](SECURITY.md)，不要创建公开 Issue。
