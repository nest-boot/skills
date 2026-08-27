---
name: nest-boot-row-level-security
description: 使用 `@nest-boot/row-level-security` 新增、重构、审查或排查实体 Policy、RowLevelSecurity 上下文、`RequestContext.child` 局部 RLS 绕过、MikroORM 迁移或 PostgreSQL RLS 行为的通用规范。
---

# nest-boot Row Level Security

## 概览

用简单实体策略表达稳定的归属规则，把例外查询流程放在范围很小的业务代码中。RLS 应描述长期成立的表访问边界，不要承载一次性 token、hash、邀请链接等临时流程。

## Policy 设计

- 优先为直接归属字段或关联使用 `@Policy({ property, context, roles })`。
- 能加直接关联时优先加关联，例如 `tenant!: Ref<Tenant>`，避免在 RLS 里写复杂子查询。
- 记住 `command` 默认是 `PolicyCommand.ALL`。如果表不应授予 insert、update 或 delete 权限，不要省略 `command`。
- 多条 permissive policy 在 PostgreSQL 中按 OR 合并。restrictive policy 会与 permissive 结果按 AND 合并。
- 只有真正需要约束所有匹配命令的护栏才使用 `PolicyMode.RESTRICTIVE`，例如软删除可见性。
- 当命令意图重要，或稳定的迁移策略名有助于 review 时，优先使用具名 policy。
- Entity 装饰器是 policy 的源定义。先修改 `@Policy`，再让 MikroORM 生成继承 `RowLevelSecurityMigration` 的迁移；不要只手改迁移 SQL。

## 可选上下文与类型转换

`current_setting('app.tenant_id', true)` 在上下文未设置时可能得到 `NULL`
或空字符串。空字符串直接 `::bigint` 会让本来应返回空结果的匿名/无租户
请求报 `invalid input syntax for bigint: ""`。

当 `property/context` 简写不能安全表达可选上下文时，使用具名自定义 policy：

```ts
@Policy({
  name: 'tenant_resource_tenant_all_authenticated_policy',
  using:
    "(nullif(current_setting('app.tenant_id', true), '')::bigint = tenant_id)",
  withCheck:
    "(nullif(current_setting('app.tenant_id', true), '')::bigint = tenant_id)",
  roles: ['authenticated'],
})
```

不要用 `coalesce(..., '0')` 制造一个可能与真实 ID 相撞的哨兵值。

## 常见模式

租户归属表：

```ts
@Policy({
  property: 'tenant',
  context: 'tenant_id',
  roles: ['authenticated'],
})
```

登录用户可以读取所有用户，但只能更新自己：

```ts
@Policy({
  name: 'user_select_policy',
  command: PolicyCommand.SELECT,
  using: '(true)',
  roles: ['authenticated'],
})
@Policy({
  name: 'user_update_policy',
  command: PolicyCommand.UPDATE,
  property: 'id',
  context: 'user_id',
  roles: ['authenticated'],
})
```

用户或租户访问：

```ts
@Policy({
  property: 'user',
  context: 'user_id',
  roles: ['authenticated'],
})
@Policy({
  property: 'tenant',
  context: 'tenant_id',
  roles: ['authenticated'],
})
```

这个模式成立是因为 permissive policies 会按 OR 合并。注意这两条 policy 都默认作用于 `ALL`，如果写入行为需要更严格控制，应显式设置 `command`。

## 业务例外

不要把邀请 token、API key hash、一次性 token 或其他查找密钥写进实体 RLS 策略。使用 `RequestContext.child()`，只在确实需要的那一次查询周围临时禁用 RLS。

```ts
return await RequestContext.child(() => {
  RowLevelSecurity.setMode(RowLevelSecurityMode.DISABLED);

  return this.findOne({
    inviteToken,
    user: null,
  });
});
```

当子作用域需要在正常 RLS 下使用另一组上下文写入时，先清理继承的 RLS 状态，再设置子作用域内的值：

```ts
return await RequestContext.child(() => {
  RowLevelSecurity.clear();
  RowLevelSecurity.setRole('authenticated');
  RowLevelSecurity.setContext('user_id', currentUser.id);
  RowLevelSecurity.setContext('tenant_id', tenant.id);

  return this.update(entity, input);
});
```

如果当前可能没有活动的 request context，用 `RequestContext.isActive()` 包装 helper，并在需要时回退到 `RequestContext.run(new RequestContext({ type: '...' }), run)`。

后台 scheduler、webhook 和 reconciliation worker 没有用户租户上下文时，
把 RLS bypass 限制在一个 `RequestContext.child()` 内；不要改变进程级默认值，
也不要让禁用状态泄漏到下一次作业。

## 迁移与数据库验证

1. 对 Entity policy 写 metadata 单元测试，断言名称、命令、`using` 和
   `withCheck`。
2. 用 MikroORM 生成迁移，检查 `up()` 创建新 policy，`down()` 恢复旧
   policy；如果删除了最后一条 policy，检查表的 RLS enable/disable 状态。
3. 在 disposable PostgreSQL 运行 `up -> check -> down -> up`。
4. 查询 `pg_policies` 和 `pg_class.relrowsecurity` 验证真实数据库状态。
5. 至少运行一次空上下文 SQL 探针：设置 authenticated role、清空
   `app.tenant_id`，对受保护表执行 `select`，确认返回空/允许的行而不是
   bigint cast 错误。
6. 再用正确与错误 tenant context 验证读取和写入边界。
