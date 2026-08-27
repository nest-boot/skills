# @nest-boot/graphql 模块安装与配置指南

在 NestJS 应用中接入 GraphQL 时，按需安装并注册 `@nest-boot` 的 GraphQL 包及底层驱动。

## 1. 核心包与关联依赖安装

接入 GraphQL 与 Connection（游标分页）前，先确认宿主应用采用的 Apollo 驱动和现有依赖版本，再安装缺少的包。

常用的依赖命令如下（建议使用 pnpm）：

```bash
pnpm add @nestjs/graphql @nestjs/apollo graphql @apollo/server
pnpm add @nest-boot/graphql @nest-boot/graphql-connection
```

## 2. 模块级引入与全局配置装载

在应用组合根或公共基础设施模块中集中初始化 GraphQL，避免在业务模块中重复装载。承载模块可以是 `AppModule`、`CommonModule` 或其他宿主应用已有的基础模块。

`@nest-boot/graphql` 提供默认 Apollo 配置，也支持通过 `forRoot`/`forRootAsync` 覆盖。沿用宿主应用现有配置；没有额外选项时可以直接导入模块：

```typescript
// 示例：<infrastructure-root>/graphql-infrastructure.module.ts

// ... 其他引用
import { GraphQLModule } from '@nest-boot/graphql';
import { GraphQLConnectionModule } from '@nest-boot/graphql-connection';
import { Global, Module } from '@nestjs/common';

@Global()
@Module({
  imports: [
    // 将装载工作交给基础模块
    GraphQLModule,
    GraphQLConnectionModule,
    // ... 可能包含 MikroOrmModule 和其它基础组件等
  ],
  providers: [
    // 提供器或者管道守卫等
  ],
})
export class GraphQLInfrastructureModule {}
```

## 3. 注意点分析

- **配置来源**: 导入模块前核对宿主应用的环境配置、driver、schema 输出与 endpoint；不要假定固定路径或默认端点。
- **`@nest-boot/graphql`**：封装 Apollo driver、schema 生成与异常过滤，并允许宿主应用覆盖路径、插件等选项。
- **`@nest-boot/graphql-connection`**：提供 `ConnectionBuilder`、`ConnectionManager` 与 Relay-style connection 类型。
