---
name: nest-boot-queue
description: 使用 Nest Boot v8 的 Redis 队列 API（queue 8.2+、可选 queue-api 8.1+）声明 Zod jobSchemas、BaseQueue 和具名 BaseProcessor handlers。适用于任务投递与消费、job 名称/data/result 推导、Worker 启停、QueueEvents、Job 历史与 GraphQL 可见性，以及从旧 BullMQ/queue-database API 迁移；重点区分 Redis 执行、可选持久化、验证与请求身份边界。
---

## 先确认版本与职责

读取宿主 manifest、锁文件和实际公开类型。本文针对 `@nest-boot/queue` 8.2+、`@nest-boot/queue-api` 8.1+，不能把较早的 8.x 当成相同 API。运行时是 Node.js >=24.21.0、NestJS 12、原生 ESM；当前 BullMQ peer 是 `^6.3.12`。

- `@nest-boot/queue` 只负责 Redis 执行，不依赖数据库、GraphQL 或数据库迁移。
- `@nest-boot/queue-api` 可选，负责数据库 Job 历史、认证和 GraphQL 查询；不承担 Redis 状态存储。
- 先确定生产者、消费者及历史/API 各在哪个进程运行，再配置模块与启动入口。

## 核心规则

1. **声明队列 provider。** 用 `@Queue(name?)` 装饰继承 `BaseQueue` 的 class；静态名称在装饰器中，Redis/defaultJobOptions 在 `super(options)` 中。`@Queue()` 会去掉类名末尾的 Queue 后转 kebab-case。
2. **以 schema 为任务契约源。** 声明具体的 `readonly jobSchemas`，每个任务的 `data` 必须是 `z.object()`；`result` 可省略，省略意味着 handler 返回 `Promise<void>`。保留对象字面量推导，不把属性显式拓宽为 `JobSchemas`。
3. **每个任务一个 handler。** 使用 `@Processor(QueueClass)`、`BaseProcessor` 和 `Job<QueueClass, 'job-name'>`；`send-email` 对应 `processSendEmail`。参数与返回类型都要匹配，转换后重名的任务会被拒绝；不实现通用 `process(job)` 路由。
4. **直接注入队列 class。** Queue 与 Processor 都是 singleton providers，放入所属模块的 `providers`。不使用 `InjectQueue`、字符串注册、WorkerHost 或旧事件装饰器；Processor 类名前缀与 Queue 一致由共享 ESLint 规则检查，不是 TypeScript 自动比较类名。
5. **显式启动消费。** 注册队列会启动 QueueEvents，注册 Processor 不自动启动 Worker。通过 `QueueManager.start(names?)` 或 `queue:start` 消费；不传过滤器启动全部，传入名称仅启动所选队列。
6. **验证保留原值。** add/addBulk、调度模板、消费和完成结果使用异步 Zod 校验，但丢弃解析结果，类型采用 `z.input`。不承诺默认值、strip、coerce、transform 会改写 Redis payload 或 handler result；优先声明稳定、可 JSON 序列化的契约。解释校验边界时同时说明：原生 `job.updateData()` 不经过封装校验，消费时仍会复验；addBulk 在写入前先验证整个批次。
7. **分开上下文与身份。** 每个 job 有自己的 RequestContext，singleton Processor 不保存当前 job 或临时路径。原 HTTP 的 user/workspace/member 不自动传播，业务授权仍要从可信标识重新建立。

## 参考文档

- [依赖、注册与启停](references/install.md) — 静态 QueueModule、Redis 连接、provider 与 server/worker 入口。
- [类型、校验和事件](references/usage.md) — 可执行的 Queue/Processor/Service 示例、具名 handler、输入语义与 QueueEvents 边界。
- [可选 Job 历史与 API](references/job-history.md) — QueueApiModule、JobEntity、QueueVisible、作用域查询和内置 job 队列。
