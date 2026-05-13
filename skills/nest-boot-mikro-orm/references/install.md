# MikroOrm 模块安装与配置指南

在 `@nest-boot` 体系下接入数据库底层能力时，我们使用高度定制并适配企业规约的 `@nest-boot/mikro-orm`。与纯正原生的 MikroORM 相比，它在 NestJS 中做到了真正的零配置约定与最佳解耦。

## 1. 安装核心依赖

在需要装载数据实体的服务包下（如：`apps/server`），安装核心引擎包和环境扩展底座：

```bash
pnpm install @nest-boot/mikro-orm @nest-boot/mikro-orm-request-transaction @mikro-orm/postgresql
```

*附注*：`@nest-boot/mikro-orm-request-transaction` 提供了一种自动把每个 HTTP/GraphQL 请求包裹在单一事务里的能力，保证一旦发生拦截或宕机即时回滚，是企业级标配。

## 2. 全局容器与挂载方式

为了保持 `AppModule` 干净纯净并且杜绝循环加载，我们强制将数据库模块归拢在一个被声明了 `@Global()` 的 `CommonModule` 中一次性挂载，其余业务域模块随后直接注入所需 `Repository` 或继承 `EntityService` 即可。

### ✅ 最佳架构：挂载于 Global 模块

请直接在被 `@Global()` 装饰的公共模块中，将 `MikroOrmModule` 和 `RequestTransactionModule` 同步放到 `imports` 里，**不需要通过参数去注入链接地址**：

```typescript
// src/common/common.module.ts

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
export class CommonModule {}
```

## 3. 为什么是“零配置”？

可以看到 `imports` 内部仅仅列出 `MikroOrmModule`，没有任何类似 `.forRoot(...)` 或 `.register(...)` 的数据库 URI 指定动作。

在 `@nest-boot` 的规范下，它天然就与内建环境体系关联：
- 它会自动截取并读取系统抛出的数据库账密（通常挂靠于启动脚本、`.env` 变量或根目录的专属 `mikro-orm.config.ts` 文件内）。
- 后续如果开发出了具体的业务 `Module` 库（如 `WorkspaceModule`），它也不需要在该模块里执行类似 `MikroOrmModule.forFeature([XXXEntity])` 这样的注入大杂烩动作。依托 `@nest-boot/mikro-orm`，你在 Service 层或者其它任意地带只要需要数据库，只需让服务类 `extends EntityService<Entity>` 即可自动全盘接收容器中的一切。

## 4. 驱动与 CLI 配置 (mikro-orm.config.ts 与 package.json)

尽管 `@nest-boot/mikro-orm` 做到了业务级的零配置，但为了让底层的 CLI 命令行工具（如生成和执行快照依赖的 `mikro-orm migration:create`）能够准确定位到宿主的全局账密配置源：你需要显式地在对应的服务包根目录下建立 `src/mikro-orm.config.ts` 暴露这些被框架包裹的安全配置，并在 `package.json` 中映射它。

### 第一步：创建暴露器文件

在应用的 `src/` 根目录新建 `mikro-orm.config.ts`。在这个文件里，主要是利用 `@nest-boot/mikro-orm` 底层自带的 `loadConfigFromEnv` 把环境源无缝托盘而出，并过滤掉无需参与主应用 ORM 全局实体差分比对的外部隔离 Schema（诸如 `auth` 与 `mastra` 等独立子域系统表空间）：

```typescript
// src/mikro-orm.config.ts
import 'dotenv/config';

import { defineConfig } from '@mikro-orm/postgresql';
import { loadConfigFromEnv } from '@nest-boot/mikro-orm';

export default async () => {
  return defineConfig({
    ...((await loadConfigFromEnv()) as any),
    schemaGenerator: {
      ignoreSchema: ['auth', 'mastra'], // 隔绝非应用底层接管的第三方/鉴权系统空间域
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

如此这般，当我们直接在根目录执行带有 `mikro-orm` 标签的原生指令系统时，它便能借此识别上下文并自动引导编译器完成数据库探测。
