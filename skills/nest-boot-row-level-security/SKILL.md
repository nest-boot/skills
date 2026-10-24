---
name: nest-boot-row-level-security
description: 在 Nest Boot v8、@nest-boot/database 与 MikroORM 7.2 中设计、迁移、审查和验证 PostgreSQL/PGlite 原生 RLS。适用于 Entity policies、session role/variables、app.member.id、事务边界、受控 fork、后台任务租户隔离。
---

# Nest Boot v8 原生 RLS

使用 MikroORM 的 `@Entity({ policies })` 与 EntityManager session。

## Policy 与数据库角色

- 用 Entity 的 `policies` 作为源定义，按需配置 `command`、`roles`、`using`、`check` 和 `type`；`name` 可省略，由 MikroORM 自动生成。command/type 是小写字面量，例如 `select`、`all`、`restrictive`。
- 一个或多个 policy 会默认启用 RLS；必要时显式设置 `rowLevelSecurity: true` 或 `'force'`。SQL 权限与 RLS 是两层约束，roles 和 GRANT 要由部署/初始化迁移单独配置；policy 不会创建角色或授予表权限。
- 默认 permissive policies 以 OR 合并；restrictive policies 与允许集合以 AND 合并。显式选择命令，避免把只读规则意外扩展到 `all`。
- 表所有者通常绕过 RLS，superuser/BYPASSRLS 也可绕过；业务验证使用真实受限角色。不要以管理员连接的成功查询证明隔离有效。
- RLS 表达稳定的行归属。动作权限、API-key 权限交集与可写字段继续由 Service/Ability 校验，不能只靠一条 workspace policy。

## 身份与 session

Auth 使用 `app.user.id`、`app.workspace.id`、`app.member.id`；空身份值是空字符串。服务账户可以有 member 而没有 user，用户会话也可以登录但未选择 workspace。不要把 `app.member.id` 当成所有已登录请求必有字段，也不要把请求头里的 workspace ID 当作成员资格证明。

`DatabaseModuleOptions.session` 是可选的同步工厂，可为每次 RequestContext 的 EM fork 提供初始 session（例如匿名角色），在 HTTP 认证之前运行；不配置时 DatabaseModule 不会自动添加匿名角色。使用 Auth 时，让认证流程维护最终身份；自定义授权入口应先验证身份和成员关系，再设置范围。业务自定义变量使用一致的完整命名，例如 `app.tenant.id`。

```typescript
em.setSessionContext({
  role: 'authenticated',
  variables: { 'app.tenant.id': authorizedTenantId },
});
await em.transactional(async (tx) => {
  // 所有需要原子性的查询和写入使用 tx。
});
```

`setSessionContext()` 合并变量；需要替换数据库范围时，在独立 fork 上传入完整 `session` 或先 `clearSessionContext()` 再设置，避免普通 session 变量残留。如果启用了 `rls` filter，fork 还会继承 filter 参数并据此重新写入 session 变量；显式 `session` 不保证移除这些变量。先检查 `getSessionContext()` 与对应 filter 参数，在新 fork 上同步设置经过授权的新参数，再开始查询或事务，不能只换 `app.tenant.id` 就认定旧范围已清除。不要在活动事务中切换、清空或绕过 session；先确定范围再开始事务。默认 `transaction` 策略会为带 session 的普通 ORM 查询创建短事务。

`em.getConnection().execute()` 不携带 EntityManager session。受 RLS 保护的查询使用 ORM API 或 SQL EM 的 `em.execute()`；不要为了绕过 session 错误改成底层 connection。

## 空上下文与实体示例

`current_setting(key, true)` 可能返回 NULL 或空字符串；转换 bigint/uuid 前使用 `nullif(..., '')`。不要用可能与真实 ID 相撞的 `0` 作为哨兵值。

```typescript
import { Entity, PrimaryKey, Property } from '@mikro-orm/decorators/legacy';

@Entity({
  policies: [{
    command: 'all',
    roles: ['authenticated'],
    using: "tenant_id = nullif(current_setting('app.tenant.id', true), '')::bigint",
    check: "tenant_id = nullif(current_setting('app.tenant.id', true), '')::bigint",
  }],
})
export class TenantDocument {
  @PrimaryKey()
  id!: number;

  @Property({ type: 'bigint', fieldName: 'tenant_id' })
  tenantId!: string;
}
```

Auth 的标准 user/workspace 归属可复用 `@nest-boot/auth` 的 `userScopePolicy()` / `workspaceScopePolicy()`，组合进原生 `policies`；默认字段分别为 user/workspace，默认 SQL 类型为 bigint。字段或 ID 类型不同时显式传 property/type，仍需 Service 授权。自定义 tenant 示例不自动对应 Auth workspace。

以上 SQL 针对已显式映射的 `tenant_id`。需要复用或重命名安全时，使用 policy callback 的 columns 映射并正确引用标识符；不要混淆 TS 属性名与数据库列名。

## 后台任务与业务例外

先验证 job 的租户来源和业务权限，优先创建带精确租户 session 的 fork。v8 Queue Processor 已建立 RequestContext；自定义 CLI/worker 在应用初始化后使用 `RequestContext.run()` 包住完整 awaited 工作。

区分受 RLS 保护的业务实体与 queue-api 的内置 JobEntity：JobEntity 本身没有 RLS，公开查询由 JobService 统一执行 QueueVisible、用户/工作区范围与管理员 system-job 权限检查。不要给它套用 user OR workspace policy，或把 job.data 的身份标识当作已经认证的 session；详见 `nest-boot-queue`。

需要局部上下文时，`RequestContext.child()` 本身不会 fork EM 或切换数据库角色。创建 fork，并在 child 内绑定它；当前调用已有事务时不要用新 fork 把操作悄悄拆出原事务：

```typescript
import { EntityManager } from '@mikro-orm/core';
import { RequestContext } from '@nest-boot/request-context';

const current = em.getContext(false);
if (current.isInTransaction()) {
  throw new Error('Choose the database scope before starting the transaction');
}
const scoped = current.fork({
  session: {
    role: 'authenticated',
    variables: { 'app.tenant.id': authorizedTenantId },
  },
});
await RequestContext.child(async () => {
  RequestContext.set(EntityManager, scoped);
  await scoped.find(TenantDocument, {});
});
```

上例只切换数据库 EM/session。child 仍会继承父上下文的 User、Workspace、Member 和 Ability 等值；数据库 role/variables 不会认证用户或同步 Auth 身份。依赖 Auth 身份的操作必须走可信的认证/授权流程，不能把仅更换 EM 的 child 当作另一个用户或工作区。

只有经过明确授权的内部操作才考虑清空独立 fork 的 session 或使用维护角色。清空 session 恢复的是连接基础角色，并不保证或自动授予 BYPASSRLS；必须核对真实数据库权限。不要修改父 EM、改变全局设置，或为方便查询在数据库 session 中传递 token/hash。

Auth 的认证和邀请等流程已有 Service 边界；不要复制其私有 `runAuthQuery`。调用 Auth Service 后再开始业务事务，避免在带 RLS 的活动事务内调用需要独立认证持久化上下文的操作。

## 迁移与验证

1. 升级前把已有 policy 纳入 `@Entity({ policies })`，再生成 diff。MikroORM 会 introspect 原生 policy，缺少 metadata 可能使 diff 删除旧 policy 并关闭 RLS；暂不接管时评估 `schemaGenerator.ignorePolicies`，不要只靠 safe 模式。
2. 使用官方 `@mikro-orm/migrations` 的 `Migration` / `Migrator`。单独审查角色、GRANT、policy 与 RLS enable/force 状态；不要复制框架示例的重建 baseline 到已有数据的库。
3. 在 disposable PostgreSQL 执行 `up -> migration:check -> down -> up`，检查 `pg_policies`、`pg_class.relrowsecurity` / `relforcerowsecurity`。
4. 用受限角色验证空、正确、错误租户的读取和写入；验证两个并发请求/连续 job 的 session 不串用、事务内切换被拒绝、异常结束后父 session 不变。
5. 只有替身或 metadata 校验时，明确尚未完成真实 PostgreSQL 验证。RLS 不限制 TRUNCATE/序列操作，初始化权限按业务实际收敛。

实现依据：[DatabaseModule fork 与 context](https://github.com/nest-boot/nest-boot/blob/main/packages/database/src/database.module.ts)、[Auth 身份与数据库 scope](https://github.com/nest-boot/nest-boot/blob/main/packages/auth/src/infrastructure/request-identity.ts)、[RequestContext.child](https://github.com/nest-boot/nest-boot/blob/main/packages/request-context/src/request-context.ts)。MikroORM 的 session 合并、fork 与 RLS filter 行为核对宿主实际安装的 EntityManager 实现；教程只作辅助。
