---
name: nest-boot-bullmq
description: 使用 `@nest-boot/bullmq` 构建和管理 NestJS 异步任务队列的通用规范。适用于创建队列、定义 Job payload、注册 Processor、投递任务或排查队列依赖注入，重点保证名称与载荷类型安全、注册关系一致和处理器职责清晰。
---

## 概览

`@nest-boot/bullmq` 封装了基于 Redis 的 BullMQ。使用时应让队列名称、Job 名称和 payload 在投递方与消费方之间形成类型闭环，减少“魔法字符串”和宽泛载荷导致的运行时错误。

## 核心设计原则

1. **共享队列名称**：队列名称在注册、注入和 Processor 之间复用同一常量，避免字符串漂移。
2. **绑定名称与载荷**：单一任务可使用 `Job<Data, Result, Name>`；同一队列存在多个任务名时，使用可辨识联合让投递方和消费方共享约束。
3. **隔离 Processor**：Processor 放在独立文件中负责队列入口、日志和任务路由；较长的领域逻辑委托给 Service 或私有处理方法。

## 参考文档

- [配置与局部模块注册](references/install.md) - 当你打算在某个 Module 新增队列服务时的注册样板代码。
- [类型安全的定义与使用](references/usage.md) - 说明如何提取常量、定义 `Job` 联合类型，以及在 Service 与 Processor 间保持名称和载荷一致。
