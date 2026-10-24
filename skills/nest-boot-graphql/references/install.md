# @nest-boot/graphql 模块安装与配置指南

在 NestJS 应用中接入 GraphQL 时，按需安装并注册 `@nest-boot` 的 GraphQL 包及底层驱动。

## 1. 核心包与关联依赖安装

接入 GraphQL 与 Connection（游标分页）前，先确认宿主应用采用的 Apollo 驱动和现有依赖版本，再安装缺少的包。

常用的依赖命令如下（建议使用 pnpm）：

```bash
pnpm add @nestjs/graphql@^14.0.3 @nestjs/apollo@^14 graphql@^16 @apollo/server@^5.5.1
pnpm add @nest-boot/graphql@^8 @nest-boot/graphql-connection@^8
```

## 2. 模块级引入与全局配置装载

v8 要求 Node.js >=24.21.0、NestJS 12 与 ESM。按包的 peerDependencies 配齐 Express 5、`@as-integrations/express5` 及所用数据库依赖；不要把上面的短命令当成完整 peer 清单。开发 IDE 使用 `graphiql`。

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
    // ... 可能包含 DatabaseModule.forRoot(...) 和其它基础组件
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

## 4. v8 Auth 与上传边界

Auth 的 GraphQL API 由 `@nest-boot/auth` 提供，使用内置具体实体。`signUp` 返回 `{ id, token }`；管理用户的写操作返回各自的 `{ id }` payload，成功后另行查询实体。`acceptInvitation` 返回 `{ id, memberId, workspaceId }`，后续请求选定 workspace 才查询其成员关系。

Auth 通过 `AuthModule.forRoot(options)` / `forRootAsync(...)` 注册，保留宿主的数据库、Hash 和 Mailer 配置；不要把静态 `AuthModule` 放进 imports 代替初始化。

上传核心使用 `@nest-boot/staged-upload` 的 `StagedUploadModule` 与 transport-independent request/result 类型；需要 `createStagedUploads` mutation 时额外注册 `@nest-boot/staged-upload-graphql` 的 `StagedUploadGraphQLModule`。`StagedUploadInput`、`StagedUpload`、`StagedUploadField` 从适配包导入，不从核心包导入。

核心模块使用 `StagedUploadModule.register(options)` / `registerAsync(...)`，并依赖已配置的 `Storage`；适配模块才是直接导入的静态 `StagedUploadGraphQLModule`。不能把这两个模块都写成无配置的静态 imports，也不能给上传模块虚构 `forRoot()`。
