# Type、Interface、DTO 与 Enum

## 编译期类型与运行时模型

TypeScript `interface` 和 `type` 会在编译后消失，适合：

- 内部函数或 service 的参数/返回类型；
- 队列 payload、SDK 适配契约和可辨识联合；
- 不需要装饰器元数据的共享结构；
- 泛型约束和组合类型。

以下边界通常需要 class：

- GraphQL `@InputType()`、`@ArgsType()`、`@ObjectType()`；
- class-validator/class-transformer 输入；
- Swagger/NestJS 需要运行时反射的 DTO；
- MikroORM Entity。

不要给 interface 添加装饰器式期待，也不要用空 class 代替纯内部类型。选择取决于运行时是否需要读取该定义。

## 提取位置

- 跨多个文件复用、属于稳定模块契约或本身较复杂的 interface/type 放入宿主惯用的 `interfaces/` 或 `types/`；
- 局部、短小且只有一个消费者的定义留在使用文件；
- 文件使用 kebab-case 和有意义后缀，例如 `process-source-options.interface.ts`、`audio-result.type.ts`；
- 不在 Entity 或 Service 文件末尾堆放多个跨模块导出的类型。

## Enum 的单一来源

真正有限且稳定的状态集合使用共享 enum，并放入模块 `enums/`：

```typescript
// <module-root>/source/enums/source-status.enum.ts
export enum SourceStatus {
  WAITING = 'WAITING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
}
```

- 默认让字符串 enum 的键和值一致，减少代码、数据库和客户端的大小写漂移；
- 已有数据库值或外部协议字面量不符合该格式时，保留兼容值并显式映射，不为样式破坏契约；
- Entity、GraphQL 和客户端生成类型应追溯到同一语义来源，不在多层手写不同列表；
- 开放且经常新增的供应商、模型或目录数据通常不适合 enum，应按持久化建模规则处理。

将 enum 暴露到 GraphQL 时使用 `nest-boot-graphql` 的注册规则；映射到 MikroORM 列、约束或迁移时使用 `nest-boot-mikro-orm`。本技能只负责源定义的位置、命名和复用边界。
