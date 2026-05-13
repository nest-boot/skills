---
name: nest-boot-bullmq
description: 在当前项目中使用 `@nest-boot/bullmq` 构建和管理异步任务队列的最佳实践指南。当您需要在 NestJS 系统中创建新队列、定义任务载荷（Payloads）、注册 Processor 处理器或是触发 Job 投递时，请触发并使用本技能。确保作业名称类型安全、队列常量单一职责抽象，并保持依赖注入严格对齐。
---

## 概览

`@nest-boot/bullmq` 封装了基于 Redis 的高可用消息队列库 BullMQ。在本项目中，我们对生产级队列提出了一套极其严格的类型安全（Type-Safe）与结构化定义约束，以彻底杜绝因“魔法字符串”或泛类型的 Job 载荷导致的运行时奔溃。

## 核心设计概念与铁律

1. **绝对禁绝魔法字符串**: 队列名称（Queue Name）必须定义为独立的共用常量（如 `SOURCE_QUEUE_NAME = 'source'`），不得在任何文件里手写字面量字符串。
2. **作业类型枚举化与联合**: 无论是 Job 的投递方还是消耗方（Processor），所有 Job 的载数据结构（Payload Data）与名称都要通过联合强类型（Union Types）绑定。
3. **隔离的处理器层**: Processor（处理逻辑）应当抽离为单独的命名体（比如 `source.processor.ts`），杜绝与 Service 或 Resolver 业务相互缠绕。

## 参考文档

- [配置与局部模块注册](references/install.md) - 当你打算在某个 Module 新增队列服务时的注册样板代码。
- [类型安全的定义与运用全景图](references/usage.md) - 这是本规范最核心的文件。详情解释了如何提取常量、定义 `Job` 联合类型，以及如何在 Service 与 Processor 中实现完美的类型闭环保护。
