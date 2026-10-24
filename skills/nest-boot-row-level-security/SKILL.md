---
name: nest-boot-row-level-security
description: 在 Nest Boot v8、@nest-boot/database 与 MikroORM 7.2 中设计、迁移、审查和验证 PostgreSQL/PGlite 原生 RLS。适用于 Entity policies、session role/variables、app.member.id、事务边界、受控 fork、后台任务租户隔离，以及从已移除的 @nest-boot/row-level-security 迁移。
---

# Nest Boot v8 原生 RLS

v8 使用 MikroORM 的 `@Entity({ policies })` 与 EntityManager session。旧 `@nest-boot/row-level-security`、`@Policy`、`RowLevelSecurity`、自定义 driver 和 `RowLevelSecurityMigration` 已移除；保留本 skill 名称仅为了安装兼容。

## Policy 与数据库角色

- 用 Entity 的 `policies` 作为源定义，配置 `name`、`command`、`roles`、`using`、`check` 和 `type`。原生属性是 `check`，不是旧 `withCheck`；command/type 是小写字面量，例如 `select`、`all`、`restrictive`。
- 一个或多个 policy 会默认启用 RLS；必要时显式设置 `rowLevelSecurity: true` 或 `'force'`。SQL 权限与 RLS 是两层约束，roles 和 GRANT 要由部署/初始化迁移单独配置；policy 不会创建角色或授予表权限。
- 默认 permissive policies 以 OR 合并；restrictive policies 与允许集合以 AND 合并。显式选择命令，避免把只读规则意外扩展到 `all`。
- 表所有者通常绕过 RLS，superuser/BYPASSRLS 也可绕过；业务验证使用真实受限角色。不要以管理员连接的成功查询证明隔离有效。
- RLS 表达稳定的行归属。动作权限、API-key 权限交集与可写字段继续由 Service/Ability 校验，不能只靠一条 workspace policy。

## 身份与 session

Auth 使用 `app.user.id`、`app.workspace.id`、`app.member.id`；空身份值是空字符串。服务账户可以有 member 而没有 user，用户会话也可以登录但未选择 workspace。不要把 `app.member.id` 当成所有已登录请求必有字段，也不要把请求头里的 workspace ID 当作成员资格证明。

通过 `DatabaseModuleOptions.session` 给每次 request fork 设置初始匿名 session；它在认证之前运行。使用 Auth 时，让认证流程维护最终身份；自定义授权入口应先验证身份和成员关系，再设置范围。业务自定义变量使用一致的完整命名，例如 `app.tenant.id`。

```typescript
em.setSessionContext({
  role: 'authenticated',
  variables: { 'app.tenant.id': authorizedTenantId },
});
await em.transactional(async (tx) => {
  // 所有需要原子性的查询和写入使用 tx。
});
```

`setSessionContext()` 合并变量；需要替换身份时，在独立 fork 上传入完整 `session` 或先 `clearSessionContext()` 再设置，避免残留上一组变量。不要在活动事务中切换、清空或绕过 session；先确定范围再开始事务。默认 `transaction` 策略会为带 session 的普通 ORM 查询创建短事务，不需要旧的全请求事务模块。

`em.getConnection().execute()` 不携带 EntityManager session。受 RLS 保护的查询使用 ORM API 或 SQL EM 的 `em.execute()`；不要为了绕过 session 错误改成底层 connection。

## 空上下文与实体示例

`current_setting(key, true)` 可能返回 NULL 或空字符串；转换 bigint/uuid 前使用 `nullif(..., '')`。不要用可能与真实 ID 相撞的 `0` 作为哨兵值。

```typescript
import { Entity, PrimaryKey, Property } from '@mikro-orm/decorators/legacy';

@Entity({
  policies: [{
    name: 'tenant_document_tenant_all',
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

只有经过明确授权的内部操作才考虑清空独立 fork 的 session 或使用维护角色。清空 session 恢复的是连接基础角色，并不保证或自动授予 BYPASSRLS；必须核对真实数据库权限。不要修改父 EM、改变全局设置，或为方便查询在数据库 session 中传递 token/hash。

Auth 的认证和邀请等流程已有 Service 边界；不要复制其私有 `runAuthQuery`。调用 Auth Service 后再开始业务事务，避免在带 RLS 的活动事务内调用需要独立认证持久化上下文的操作。

## 迁移与验证

1. 升级前把已有 policy 纳入 `@Entity({ policies })`，再生成 diff。MikroORM 会 introspect 原生 policy，缺少 metadata 可能使 diff 删除旧 policy 并关闭 RLS；暂不接管时评估 `schemaGenerator.ignorePolicies`，不要只靠 safe 模式。
2. 使用官方 `@mikro-orm/migrations` 的 `Migration` / `Migrator`。单独审查角色、GRANT、policy 与 RLS enable/force 状态；不要复制框架示例的重建 baseline 到已有数据的库。
3. 在 disposable PostgreSQL 执行 `up -> migration:check -> down -> up`，检查 `pg_policies`、`pg_class.relrowsecurity` / `relforcerowsecurity`。
4. 用受限角色验证空、正确、错误租户的读取和写入；验证两个并发请求/连续 job 的 session 不串用、事务内切换被拒绝、异常结束后父 session 不变。
5. 只有替身或 metadata 校验时，明确尚未完成真实 PostgreSQL 验证。RLS 不限制 TRUNCATE/序列操作，初始化权限按业务实际收敛。

依据：[MikroORM 原生 RLS](https://mikro-orm.io/docs/row-level-security)、[v8 迁移指南](https://github.com/nest-boot/nest-boot/blob/main/apps/docs/content/docs/migration-v8.mdx)。
