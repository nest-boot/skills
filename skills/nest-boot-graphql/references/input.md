# `nest-boot-graphql` GraphQL Input 网关输入架构规范

在使用 `@nest-boot` 应用构建外部的 GraphQL 客户端 API 接口时，对于入参模型必须强制进行独立目录切割防腐：严禁使用随意的参数对象内联或把 `@Args` 类型定义成堆塞入 Resolver 之中。

## 1. 必须单独创建专门的专属输入与参数层

根据它对应的业务操作类型，强制转移至具备高鲜明性的子级模型架构夹层：

- **`inputs/` 目录**：用于承接所有针对执行写入性质操作 (Mutation) 涉及的对象体类型(`@InputType()`)。例如 `create-user.input.ts`。
- **`args/` 目录**：专注于定义获取性质、节点结构控制操作 (Query) 时所需要用到的标尺、连接条件 (`@ArgsType()`)。例如 `user.args.ts`。

## 2. GraphQL 解耦设计验证与对比

### ❌ 坏代码示范（在 Resolver 内直接散乱铺设参数）

严禁直接往 `Resolver` 的实体内部注入未加防腐阻击、无法复用的原子散列传参：

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

### ✅ 优秀规范示范（独立 Input 模型进行聚合和验证层化）

一定要抽离所有的属性至专属独立的 Graph 模型，并在进入 Service 的主业流水前运用 `class-validator` 开展属性强筛：

```typescript
// 文件存放位置：src/app/user/inputs/create-user.input.ts

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

然后再去 Resolver 处直接引入此一整条高度纯净统一的安全对象管道：

```typescript
// user.resolver.ts

@Mutation(() => User)
async createUser(
  @Args('input') input: CreateUserInput
) {
  return this.userService.create(input);
}
```
