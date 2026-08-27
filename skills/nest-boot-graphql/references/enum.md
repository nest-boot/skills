# GraphQL 枚举 (Enum) 安全注册与映射规范

当独立枚举（如 `SourceStatus`）需要进入 GraphQL schema 时，显式注册它，并让 GraphQL 名称、TypeScript 名称与持久化值保持可追踪的对应关系。

## 1. 独立使用与变量名映射统一（最重点）

当你在 `enums/` 目录下创建一个强类型的 `TS Enum` 抛出时，如果该值需要成为能够被 GraphQL 客户端感知和操作的安全常量范围：

- 使用 `@nest-boot/graphql`（或宿主应用统一采用的 `@nestjs/graphql`）导出的 `registerEnumType` 注册枚举。
- 默认让 `name` 与 TypeScript 枚举名一致，减少 schema 与代码之间的映射成本。只有兼容既有公开 schema 时才保留不同名称，并补充测试与迁移说明。

### 推荐定义（保持同名）

```typescript
// <module-root>/source/enums/source-status.enum.ts
import { registerEnumType } from '@nest-boot/graphql';

export enum SourceStatus {
  WAITING = 'WAITING',
  PROCESSING = 'PROCESSING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
}

registerEnumType(SourceStatus, {
  name: 'SourceStatus',
});
```

## 2. 结合底层实体的闭环

当我们回到带有数据库属性和通信网关双重身份的 `Entity` 实体层时，应当双重利用这层已经成功注册为 Graph 类型集的枚举。

- **对 GraphQL 的暴露**：由于我们成功将其 `registerEnumType`，现在可以直接向 `@Field(() => SourceStatus)` 抛掷，客户端生成的 TS 和 Schema 会天然支持并校验这些纯大写常量集。
- **对底层的映射**：使用 `MikroORM` 带来的 `@Enum` 去映射限制数据库列的行为上限。

### 在 Entity 中复用同一枚举

```typescript
// source.entity.ts

import { Enum, Opt } from '@mikro-orm/postgresql';
import { Field } from '@nest-boot/graphql';

import { SourceStatus } from './enums/source-status.enum';

// ...
export class Source {

  // GraphQL schema 暴露允许的枚举值。
  @Field(() => SourceStatus)

  // MikroORM 将同一枚举映射到数据库列。
  @Enum({ items: () => SourceStatus, default: SourceStatus.WAITING })

  status: Opt<SourceStatus> = SourceStatus.WAITING;

}
```

生成 schema 并运行一个包含该字段的真实 operation，确认服务端、客户端 codegen 与数据库值使用同一组字面量。
