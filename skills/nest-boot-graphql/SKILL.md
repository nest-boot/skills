---
name: nest-boot-graphql
description: 使用 `@nest-boot/graphql` 编写、暴露、重命名、审查或排查 GraphQL Schema、Resolver、ResolveField、Input、Args、Connection 及客户端 operation 的通用规范。适用于 schema 类型冲突、关联字段缺失、代码通过编译但真实 GraphQL 查询失败或跨层名称需要同步的场景。
---

# nest-boot GraphQL 开发规范指南

在使用 `@nest-boot/graphql` 的 NestJS 应用中，对外暴露查询和变更时应保持输入边界、分页抽象和 schema 契约清晰。文件位置与生成命令应沿用宿主应用现有约定，不要假定固定的源码根目录或客户端包名。

## 核心理念与使用说明

1. **明确输入边界**：多字段、可复用或需要验证的输入使用 `@InputType()`/`@ArgsType()`；简单标量参数可以直接使用 `@Args()`，避免为形式制造空壳类型。
2. **分页集合使用 Connection**：需要游标分页、过滤或排序的集合使用 `ConnectionBuilder`；固定且很小的非分页列表可沿用宿主 API 约定。
3. **Schema 是独立契约**：TypeScript 类型正确不代表 GraphQL schema 正确；必须检查生成 schema 并执行真实 operation。

## 参考规范资源

- [GraphQL 模块安装与配置指南](references/install.md) - 说明如何安装 `@nest-boot/graphql`，并在宿主应用的组合根或公共基础设施模块中集中装载。
- [GraphQL 枚举 (Enum) 安全注册规范](references/enum.md) - 详解在独立切分的枚举上如何搭配 `registerEnumType` 进行绑定映射，以及它的变量名强约束条件。
- [GraphQL 网关输入 (Inputs/Args) 架构规范](references/input.md) - 详解如何拆分处理 `@InputType()` 以及 `@ArgsType()` 所使用的入参与过滤标尺对象。
- [GraphQL 连接器 (Connection Edge) 架构规范](references/connection.md) - 详解具备有记录翻页行为能力接口的带有衍生 Edge/Node 定义的解耦和存放规则。
- [Schema 命名与关联字段验证](references/schema-safety.md) - 避免根操作类型命名冲突，正确暴露 MikroORM relation，并通过生成 schema 与真实请求验收。
