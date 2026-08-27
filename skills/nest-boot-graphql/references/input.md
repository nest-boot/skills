# `nest-boot-graphql` GraphQL Input 网关输入架构规范

在 `@nest-boot` GraphQL API 中，多字段、可复用或需要 class-validator 的输入使用独立 class。简单的 `id`、游标或开关等单一标量可以直接使用 `@Args()`，前提是意图清晰且沿用宿主项目约定。

## 1. 选择 Input 与 Args

根据操作边界组织模型：

- **`inputs/` 目录**：用于承接所有针对执行写入性质操作 (Mutation) 涉及的对象体类型(`@InputType()`)。例如 `create-user.input.ts`。
- **`args/` 目录**：专注于定义获取性质、节点结构控制操作 (Query) 时所需要用到的标尺、连接条件 (`@ArgsType()`)。例如 `user.args.ts`。

## 2. GraphQL 解耦设计验证与对比

### 不推荐：多个相关字段散落在 Resolver 参数中

当多个字段共同构成一个写入契约时，不要把它们拆成一组难以复用和验证的标量参数：

```typescript
// 文件位置混乱：没独立，且直接写在了 resolver 函数内
// user.resolver.ts

@Mutation(() => User)
async createUser(
  @Args('name') name: string,
  @Args('age', { nullable: true }) age: number
) {
  // ...
}
```

### 推荐：独立 Input 聚合验证

将相关字段聚合为 GraphQL Input，并在进入 Service 前使用 class-validator 验证：

```typescript
// 文件存放位置：<module-root>/user/inputs/create-user.input.ts

@InputType()
export class CreateUserInput {
  @Field()
  @IsString()
  @IsNotEmpty()
  name: string;

  @Field(() => Int, { nullable: true })
  @IsOptional()
  @IsInt()
  @Min(0)
  age?: number;
}
```

Resolver 只接收完整输入对象：

```typescript
// user.resolver.ts

@Mutation(() => User)
async createUser(
  @Args('input') input: CreateUserInput
) {
  return this.userService.create(input);
}
```

对于 `user(id: ID!)` 这类单一、明确且无需复用的参数，直接使用 `@Args('id')` 是合理的，不必额外创建只有一个字段的 Args class。
