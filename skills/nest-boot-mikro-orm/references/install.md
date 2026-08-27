# MikroOrm 模块安装与配置指南

在 `@nest-boot` 体系下接入 MikroORM 时，使用 `@nest-boot/mikro-orm` 提供的 NestJS 集成、配置加载与 `EntityService` 能力。

## 1. 安装核心依赖

在需要装载数据实体的服务包下安装核心引擎包和所需扩展：

```bash
pnpm add @nest-boot/mikro-orm @mikro-orm/postgresql
# 仅在采用请求级事务时安装
pnpm add @nest-boot/mikro-orm-request-transaction
```

`@nest-boot/mikro-orm-request-transaction` 可把 HTTP/GraphQL 请求包裹在事务中。它不是所有应用的默认要求；启用前确认长请求、流式响应、后台任务和外部调用的事务边界符合需求。

## 2. 全局容器与挂载方式

在应用组合根或已有的全局基础设施模块中一次性挂载数据库模块，避免业务模块重复初始化。承载模块可以是 `AppModule`、`CommonModule` 或其他宿主应用已有的模块；不要把名称当作框架要求。

### 示例：挂载于 Global 基础设施模块

若宿主应用采用全局基础设施模块，可将 `MikroOrmModule` 放入 `imports`；只有启用请求级事务时才同时导入 `RequestTransactionModule`。连接配置应沿用该应用现有的环境或配置文件来源：

```typescript
// <infrastructure-root>/persistence.module.ts

import { Module, Global } from '@nestjs/common';
import { MikroOrmModule } from '@nest-boot/mikro-orm';
import { RequestTransactionModule } from '@nest-boot/mikro-orm-request-transaction';

@Global()
@Module({
  imports: [
    // ... 其他系统底层件 (如 ConfigModule)

    // 注入事务环境上下文
    RequestTransactionModule,

    // 注入数据库实体加载引擎
    MikroOrmModule,

    // ...
  ],
})
export class PersistenceModule {}
```

## 3. 配置来源

`@nest-boot/mikro-orm` 可以从环境与 MikroORM 配置文件加载连接信息：
- 先检查宿主应用现有的启动配置、环境变量和 `mikro-orm.config.ts`，不要另建并行配置源。
- 后续业务模块通常无需重复执行 `MikroOrmModule.forFeature([Entity])`。是否可直接继承 `EntityService<Entity>` 取决于宿主应用已完成的全局注册与实体发现配置；修改前先检查现有模块和测试。

## 4. 驱动与 CLI 配置 (mikro-orm.config.ts 与 package.json)

尽管 `@nest-boot/mikro-orm` 做到了业务级的零配置，但为了让底层的 CLI 命令行工具（如生成和执行快照依赖的 `mikro-orm migration:create`）能够准确定位到宿主的全局账密配置源：你需要显式地在对应的服务包根目录下建立 `src/mikro-orm.config.ts` 暴露这些被框架包裹的安全配置，并在 `package.json` 中映射它。

### 第一步：创建暴露器文件

在应用的 `src/` 根目录新建 `mikro-orm.config.ts`。在这个文件里，主要是利用 `@nest-boot/mikro-orm` 底层自带的 `loadConfigFromEnv` 把环境源无缝托盘而出，并过滤掉无需参与主应用 ORM 全局实体差分比对的外部隔离 Schema（诸如 `auth` 等独立子域系统表空间）：

```typescript
// src/mikro-orm.config.ts
import 'dotenv/config';

import { defineConfig } from '@mikro-orm/postgresql';
import { loadConfigFromEnv } from '@nest-boot/mikro-orm';

export default async () => {
  return defineConfig({
    ...((await loadConfigFromEnv()) as any),
    schemaGenerator: {
      ignoreSchema: ['auth'], // 隔绝非应用底层接管的第三方/鉴权系统空间域
    },
  });
};
```

### 第二步：底层探针注入

在同一应用目录的 `package.json` 中添加下面的底层 CLI 映射指向配置：

```json
{
  "mikro-orm": {
    "useTsNode": true,
    "configPaths": [
      "./src/mikro-orm.config.ts",
      "./dist/mikro-orm.config.js"
    ]
  }
}
```

完成映射后，应从包含该 `package.json` 的应用包目录运行 MikroORM CLI，或使用宿主 workspace 已定义的包过滤脚本。
