# GraphQL Schema 命名与关联字段验证

GraphQL 类型共享同一 schema 命名空间。代码可以通过 TypeScript 编译，
但类型名冲突或 relation 暴露不完整仍会让真实查询在运行时失败。

## 避免根操作类型冲突

不要把业务对象命名为 `Query`、`Mutation` 或 `Subscription`。这些名称通常
由 GraphQL 根操作类型占用；code-first schema 中再注册同名 `@ObjectType()`
会发生合并、覆盖或字段缺失。为业务对象补足所有权语义，例如：

```ts
@ObjectType()
export class TenantSubscription {}
```

目录、文件、Resolver、Query/Mutation 和客户端 operation 也应使用同一作用域
名称。不要只给 GraphQL decorator 传别名而保留一套含混的内部命名。

## 明确解析 ORM relation

MikroORM 的 `Ref<T>` 是持久化引用，不等同于已经可序列化的 GraphQL
对象。需要向客户端暴露 relation 时，在拥有该对象类型的 Resolver 中声明
`@ResolveField` 并加载引用：

```ts
@Resolver(() => TenantSubscription)
export class TenantSubscriptionResolver {
  @ResolveField(() => SubscriptionPlan)
  async plan(
    @Parent() tenantSubscription: TenantSubscription,
  ): Promise<SubscriptionPlan> {
    return await tenantSubscription.plan.loadOrFail();
  }
}
```

如果 relation 不应公开，使用 `@HideField()`，不要留下看似可查询但没有
resolver/序列化路径的半公开字段。

## 跨层改名

GraphQL 改名时同步检查：

- `@ObjectType`、Resolver 泛型和返回类型；
- Query、Mutation、Input 字段及 operationName；
- 宿主应用配置的生成 schema 输出；
- 客户端 GraphQL documents、codegen 输出、组件变量和 E2E 响应匹配；
- 错误提示、测试和文档。

## 验收顺序

1. 运行服务端与客户端的 typecheck/codegen。
2. 检查生成 schema：业务对象存在，且没有意外的 `type Subscription` 等
   根类型冲突。
3. 对改动 operation 发出真实 HTTP GraphQL 请求，断言 HTTP 成功且响应中
   没有 `errors`；只渲染静态标题不算数据路径通过。
4. 如果宿主代码库包含浏览器端 E2E，使用其现有测试工具进入真实页面，等待
   目标 GraphQL operation，并检查页面错误、console GraphQL error、加载完成态和空状态。
