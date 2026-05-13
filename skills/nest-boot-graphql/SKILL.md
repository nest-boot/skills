---
name: nest-boot-graphql
description: 在为 `@nest-boot` 服务端项目编写、暴露或重构 GraphQL 端点（Resolver, Input, Args, Connection 等）时，或者在使用 `@nest-boot/graphql` 和 `@nestjs/graphql` 依赖库时，必须使用且严格参考本项接口网关架构解耦与防腐规范。
---

# nest-boot GraphQL 开发规范指南

本项目采用了先进的 NestJS GraphQL 编排架构。在对外暴露查询和变更方法时，为了保证类型安全、方便后续复用以及防御脏数据流入系统体系内部，必须坚决遵循以下原则。

## 核心理念与使用说明

1. **防腐层拦截**：禁止将未经高度强化的原生对象直接混入 `Resolver` 函数体内。必须将输入和请求负载分离存放。
2. **连接器范式**：面对多记录场景必须要规范化抽象。

## 参考规范资源

- [GraphQL 模块安装与配置指南](references/install.md) - 详解工程初始化或者介入时应如何安装 `@nest-boot/graphql`，以及怎样借助公共的 `CommonModule` 优雅导入全局装载。
- [GraphQL 枚举 (Enum) 安全注册规范](references/enum.md) - 详解在独立切分的枚举上如何搭配 `registerEnumType` 进行绑定映射，以及它的变量名强约束条件。
- [GraphQL 网关输入 (Inputs/Args) 架构规范](references/input.md) - 详解如何拆分处理 `@InputType()` 以及 `@ArgsType()` 所使用的入参与过滤标尺对象。
- [GraphQL 连接器 (Connection Edge) 架构规范](references/connection.md) - 详解具备有记录翻页行为能力接口的带有衍生 Edge/Node 定义的解耦和存放规则。
