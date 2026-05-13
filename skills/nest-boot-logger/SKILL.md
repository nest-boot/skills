---
name: nest-boot-logger
description: 在当前项目中使用 `@nest-boot/logger` 进行结构化日志记录的规范指南。当您需要在 NestJS Service、Controller、Agent 等任何可注入类中添加日志、调试信息、结构化追踪数据时，请触发并使用本技能，确保日志的上下文绑定（assign）、级别调用（log/warn/error）以及模块初始化均符合工程标准。
---

## 概览

`@nest-boot/logger` 是对 [pino](https://github.com/pinojs/pino) 的 NestJS 适配封装，它通过 NestJS 依赖注入系统提供一个请求作用域（request-scoped）的 `Logger` 实例。相比 NestJS 内置的 `Logger`，它额外支持：

- **结构化绑定 (`assign`)**: 可以向日志条目追加上下文键值对，自动附着到同一请求链路的后续日志中。
- **零配置全局注册**: 通过将 `LoggerModule` 注册到全局的 `CommonModule`，所有业务模块无需单独导入即可直接注入 `Logger`。

## 核心原则

1. **永远使用 `@nest-boot/logger` 的 `Logger`，而非 `@nestjs/common` 的 `Logger`。** 两者同名但完全不同，前者支持结构化绑定与 pino 序列化。
2. **通过构造函数依赖注入获取 Logger 实例。** 不要手动 `new Logger()`。
3. **方法入口处使用 `assign` 绑定关键业务参数。** 这样后续所有 `log`/`warn`/`error` 调用都会自动携带这些参数，便于日志检索。

## 参考文档

- [安装与配置指南](references/install.md) — 如何在项目中注册 `LoggerModule` 以及在 `main.ts` 中替换 NestJS 默认日志器。
- [使用方法与最佳实践](references/usage.md) — Logger API 详解、上下文设置、结构化绑定的标准用法与实际示例。
