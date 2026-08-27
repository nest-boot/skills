---
name: nest-boot-logger
description: 使用 `@nest-boot/logger` 在 NestJS 可注入类中记录结构化日志的通用规范。适用于添加日志、调试结构化追踪、配置 LoggerModule 或排查日志上下文，重点覆盖依赖注入、上下文绑定、日志级别与敏感数据保护。
---

## 概览

`@nest-boot/logger` 是对 [pino](https://github.com/pinojs/pino) 的 NestJS 适配封装。`Logger` provider 使用 transient scope；请求级 bindings 存放在 `@nest-boot/request-context` 中。相比 NestJS 内置的 `Logger`，它额外支持：

- **结构化绑定 (`assign`)**: 可以向日志条目追加上下文键值对，自动附着到同一请求链路的后续日志中。
- **集中注册**: 在宿主应用的组合根或公共基础设施模块中注册 `LoggerModule`，避免业务模块重复初始化。

## 核心原则

1. **业务类导入 `@nest-boot/logger` 的 `Logger`。** 它与 `@nestjs/common` 的同名类不同，支持结构化绑定与 pino 序列化。
2. **通过构造函数依赖注入获取 Logger 实例。** 不要手动 `new Logger()`。
3. **默认使用自动上下文。** Logger 会从 NestJS `INQUIRER` 获取注入类名；只有动态 Processor 等无法正确推断时才调用 `setContext()` 覆盖。
4. **只在活动 RequestContext 中使用 `assign`。** HTTP/GraphQL 请求和 `@nest-boot/bullmq` Processor 已建立上下文；其他后台入口应先建立 RequestContext，或把字段附在单条日志调用上。
5. **只记录可审计标识，不记录凭证。** API key、Authorization、Cookie、私钥、完整 webhook body 和供应商签名不得进入日志；使用 requestId、eventId、resourceId、tenantId 等安全标识定位问题。

## 参考文档

- [安装与配置指南](references/install.md) — 如何在宿主应用中注册 `LoggerModule` 以及在引导文件中替换 NestJS 默认日志器。
- [使用方法与最佳实践](references/usage.md) — Logger API 详解、上下文设置、结构化绑定的标准用法与实际示例。
