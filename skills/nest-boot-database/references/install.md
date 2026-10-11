# v8 数据库模块安装与配置

使用 `@nest-boot/database` 的 `DatabaseModule`、`DatabaseModuleOptions` 和 `EntityService`。MikroORM 仍是底层实现；保留 `@mikro-orm/*` 依赖、`mikro-orm.config.ts` 和 CLI 名称。

## 依赖与运行时

使用 Node.js >=24.21.0、NestJS 12、原生 ESM 和 MikroORM 7.2。把 MikroORM 的 core、driver、decorators、reflection、migrations、seeder 和 CLI 解析到同一兼容版本；`@mikro-orm/nestjs` 使用其独立的 7.x 版本线。按实际功能安装 peer dependencies，例如 PostgreSQL 服务：

```bash
pnpm add @nest-boot/database@^8 @nest-boot/request-context@^8 \
  @mikro-orm/core@~7.2.0 @mikro-orm/postgresql@~7.2.0 \
  @mikro-orm/decorators@~7.2.0 @mikro-orm/reflection@~7.2.0 \
  @mikro-orm/nestjs@^7
pnpm add @mikro-orm/migrations@~7.2.0 @mikro-orm/seeder@~7.2.0
pnpm add -D @mikro-orm/cli@~7.2.0
```

v8 不使用 `@nest-boot/mikro-orm-request-transaction`。跨操作原子性使用 `em.transactional()`；数据库 session 使用 MikroORM 原生能力，不要安装旧请求事务包来恢复被移除的全请求事务。

Nest 常用的 legacy decorator 配置下，装饰器从 `@mikro-orm/decorators/legacy` 导入；`Opt`、`Ref`、`t` 等从 `@mikro-orm/core` 导入。不要继续从驱动包导入 legacy 装饰器。相对 TypeScript 导入使用 `.js`。

## 运行时注册

在应用组合根初始化一次，使用 `DatabaseModule.forRoot()` 或 `forRootAsync()`。直接把静态 `DatabaseModule` 放入 `imports` 不会创建 ORM root。

```typescript
import { PostgreSqlDriver } from '@mikro-orm/postgresql';
import { DatabaseModule } from '@nest-boot/database';
import { Module } from '@nestjs/common';

@Module({
  imports: [
    DatabaseModule.forRoot({
      driver: PostgreSqlDriver,
      entities: ['dist/**/*.entity.js'],
      entitiesTs: ['src/**/*.entity.ts'],
    }),
  ],
})
export class PersistenceModule {}
```

未显式指定连接目标时，模块从 `DATABASE_URL` 加载连接。显式传入 `clientUrl`、host、dbName 等目标时不会混入环境中的另一条连接；`forRootAsync()` 的 driver 选择可用 `driverHint` 提前告知 Nest。沿用宿主配置和发现路径，不假定固定目录。

继承 `EntityService<T>` 的 Service 通过 EntityManager 工作。只有使用 repository token / `@InjectRepository()` 等 feature provider 时，才按需要调用 `DatabaseModule.forFeature([Entity])`。

## CLI 配置与 Auth 实体

CLI 不启动 Nest；运行时的 `autoLoadEntities` 或 AuthModule 注册不能代替 CLI entity discovery。v8 Auth 导出具体实体的 `entities` 数组；使用 Auth 时将其加入运行时和迁移 CLI 的 `entities` **及** `entitiesTs`。没有 Auth 的应用不需要安装它。

下面是采用 Auth、PostgreSQL 和 `DATABASE_URL` 的 CLI 示例：

```typescript
import { defineConfig } from '@mikro-orm/core';
import { entities as authEntities } from '@nest-boot/auth';
import { loadConfigFromEnv } from '@nest-boot/database';

export default async () => {
  const config = await loadConfigFromEnv();
  return defineConfig({
    ...config,
    entities: [...authEntities, ...(config.entities ?? [])],
    entitiesTs: [...authEntities, ...(config.entitiesTs ?? [])],
  });
};
```

这里由 `loadConfigFromEnv()` 选择 driver，使用 core 的泛型 `defineConfig` 保留其类型；不要用 `as any` 掩盖 driver 不匹配。运行时的 `DatabaseModule.forRoot({ ... })` 也合并同一实体数组。不要照抄旧 `ignoreSchema: ['auth']` 配置隐藏 Auth 表，也不要继承旧 `BaseUser` 或用 `AuthModuleOptions.entities` 替换框架实体。业务字段放在关联实体中。

按宿主的构建与 TypeScript 执行器配置 CLI；已构建应用可直接使用 `pnpm exec mikro-orm --config ./dist/mikro-orm.config.js migration:check`。从应用包执行命令，确认 production JS 路径与开发 TS 路径分别能加载，不把旧 `ts-node` 配置当作 ESM 的通用解决方案。

## 请求 session、事务与健康检查

- `DatabaseModuleOptions.session` 是同步 factory，在 request-scoped EM fork 创建时、认证之前执行。给匿名请求设置最小初始 role/variables；完成认证和成员验证后才更新授权身份。
- `em.setSessionContext({ role, variables })` 更新原生 session；事务开始后不能切换它。先确定身份与范围，再进入 `em.transactional()`。
- 自定义 `RequestContext.registerMiddleware()` 的依赖名称是 `database`。不要保留旧的 `mikro-orm` 依赖字符串。
- 引入 `HealthCheckModule` 后，模块使用现有连接注册 `DatabaseHealthIndicator`；不要为健康检查再建一条数据库连接。
- RLS 的原生 policy、角色授权和局部 fork 用法见 `nest-boot-row-level-security`。框架示例的全新数据库 baseline 不适合作为现有业务库的升级迁移。

依据：[v8 迁移指南](https://github.com/nest-boot/nest-boot/blob/main/apps/docs/content/docs/migration-v8.mdx)、[DatabaseModule](https://github.com/nest-boot/nest-boot/blob/main/packages/database/src/database.module.ts)。
