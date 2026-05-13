# @nest-boot/graphql 模块安装与配置指南

当你要在一个基于 NestJS 且期望继承本公司基础网关规范的项目中新装 GraphQL 系统时，请参照本指南引入并注册核心依赖和相关的全家桶 `@nest-boot` 的包装抽象库。

## 1. 核心包与关联依赖安装

为了保证 GraphQL 网关以及支持本文档中提到的 Connection (游标分页体系) 架构，你在开始实施前至少要保证相关的底层通信包（如 apollo 驱动）和 `nest-boot` 两侧都已经安装完毕。

常用的依赖命令如下（建议使用 pnpm）：

```bash
pnpm add @nestjs/graphql @nestjs/apollo graphql @apollo/server
pnpm add @nest-boot/graphql @nest-boot/graphql-connection
```

## 2. 模块级引入与全局配置装载 (基于 CommonModule)

在规范体系中，我们极其不推荐直接在 `AppModule` 中长篇大论地写大量环境加载、网关初始化的逻辑。最好的架构实践是将所有第三方底层驱动放入 `CommonModule`（或同等级别的基础支撑公共模块）中进行声明和 `imports` 初始化。

由于 `@nest-boot/graphql` 具有“无侵入/零繁冗配置”或者通过内置 `ConfigModule` （如果有涉及）进行自动化提取的好处。所以在引入时，无需传入一大堆的 `forRoot`：

```typescript
// src/common/common.module.ts

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
export class CommonModule {}
```

## 3. 注意点分析

- **零配置启动**: 在 `CommonModule` 导入上述两个模块之后，网关层就已经激活（默认监听 `/api/graphql` 等配置端点）。
- **`@nest-boot/graphql` 层的好处**: 它能为你接管非常底层的 Apollo 上下文与异常处理包装，自动让你的 GraphQL 与 HTTP 请求的 `Request` 及拦截器形成连通管道，让你在编写规范的 Input 与 Resolver 时无需分心处理驱动层网络配置。
- **`@nest-boot/graphql-connection` 层的作用**: 它作为单独拓展包导入后，提供底层 `ConnectionBuilder`, `Edge` 等类的原生集成支持，是完成 `connection-definition.ts` 不可或缺的基石。
