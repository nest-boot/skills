# 跨层重命名与迁移工作流

## 1. 建立 rename map

在修改前列出精确映射：

| 层 | 旧名称 | 新名称 | 是否兼容保留 |
| --- | --- | --- | --- |
| 领域概念 | `Subscription` | `TenantSubscription` | 否 |
| 数据库表 | `subscription` | `tenant_subscription` | 通过 migration |
| GraphQL 类型 | `Subscription` | `TenantSubscription` | 依 API 兼容策略 |
| 供应商字段 | `subscription_id` | 不变 | 是，边界映射 |

区分有明确所有权的领域实例与通用目录对象。例如 `TenantSubscription` 可以表示租户拥有的一笔订阅，但 `SubscriptionPlan`、`SubscriptionProvider` 和用户文案中的普通 subscription 不应自动替换。

外部 metadata key、webhook event、HTTP 字段、URL、模型名和 external ID 前缀只有在协议允许时才改。协议必须保留旧字面量时，在 adapter/mapper 显式转换，不让旧词继续污染内部模型。

## 2. 影响矩阵

逐层搜索并记录：

1. 模块目录与文件：Entity、Module、Service、Resolver/Controller、scheduler、Input、Interface、Type、Spec；
2. TypeScript：类、构造参数、变量、方法、导入路径、DI token、enum 和注释；
3. GraphQL：对象类型、Query/Mutation、Input 字段、生成 schema、客户端 documents 与生成类型；
4. MikroORM：实体名、表、列、关系、FK、索引、唯一约束、check constraint 和 migration；
5. RLS：`@Policy` metadata、policy 名、上下文字段和生成 SQL；
6. 异步与集成：队列/Job 名、webhook、scheduler、Seeder、缓存 key、事件和配置；
7. 客户端与运维：组件、hooks、路由、监控标签、部署配置和文档。

不要只统计字符串命中数量。大小写、kebab-case、snake_case、复数和缩写都需要独立搜索。

## 3. 修改顺序

1. 使用 `nest-boot-module-design` 确认新目录和文件名称；
2. 修改 Entity、enum、Module 等源定义；
3. 更新 Service、Resolver/Controller、DI 和内部消费者；
4. 使用 `nest-boot-graphql` 更新 schema 源和客户端 operation；
5. 使用 `nest-boot-mikro-orm` 从新 metadata 生成 migration；
6. 使用 `nest-boot-row-level-security` 检查 policy metadata 和 SQL；
7. 更新队列、webhook、scheduler、Seeder、配置、客户端和文档；
8. 重新生成 schema、客户端类型和其他派生工件。

生成文件由源定义驱动。不要先手改生成 schema、客户端类型或 migration，再让源码勉强追随。

## 4. 数据与兼容策略

- 表中已有数据时，优先使用数据库 rename 或明确的 copy/backfill/swap 流程，保留约束、序列、索引和回滚；
- 只有确认旧表无数据且目标语义确实是替换时，才考虑创建新表后删除旧表；
- 公开 GraphQL/API 需要兼容窗口时，明确 deprecated alias、双读/双写或版本边界，不无期限保留两套内部概念；
- 队列中可能仍有旧 Job 时，决定 drain、兼容消费或一次性迁移，不能只改 producer；
- 外部协议保留旧字段时，只在 adapter 边界出现旧名称，并补映射测试。

## 5. 验证闭环

### 静态与单元验证

- TypeScript 类型检查、lint 和相关单元测试通过；
- Entity/enum/policy metadata 测试断言新名称；
- 旧名称搜索的每个残留都被分类为遗漏、合法通用词、外部协议或兼容层。

### GraphQL

- 重新生成 schema，确认类型、字段和根 operation 没有冲突；
- 重新生成客户端类型；
- 执行至少一个使用新名称的真实 query/mutation，而不只依赖编译。

### 数据库与 RLS

- 审查 migration `up()`/`down()` 的表列、FK、索引、约束、数据搬迁和 policy；
- 在 disposable PostgreSQL 运行 `up -> migration:check -> down -> up`；
- 查询 catalog 验证真实表、列、constraint、index、policy 和 RLS enable 状态；
- 用正确、错误和空上下文执行 RLS 读取/写入探针。

### 运行时消费者

- 验证 producer/consumer、webhook、scheduler、Seeder 和缓存 key；
- 客户端真实 operation、路由和用户文案使用预期名称；
- 部署或迁移顺序能处理新旧版本短暂并存。
