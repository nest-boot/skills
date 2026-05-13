# GraphQL 枚举 (Enum) 安全注册与映射规范

当我们的系统使用独立提取的枚举值（如：`SourceStatus` 或 `SourceType` 等）作为与客户端通讯及数据库的底层值源时，必须严格遵守 GraphQL Schema 层与底层数据实体的桥接规范。

## 1. 独立使用与变量名映射统一（最重点）

当你在 `enums/` 目录下创建一个强类型的 `TS Enum` 抛出时，如果该值需要成为能够被 GraphQL 客户端感知和操作的安全常量范围：

- 必须通过引入 `@nest-boot/graphql` （或原生的 `@nestjs/graphql`）带来的 `registerEnumType` 方法，在同一份定义文件内将其自动注册为底层支持的类型集。
- 🚨 **强约束：**你填入用来注册的参数 `name` 的选项字符串，**必须与定义的 TS 变量名称分毫不差**。绝不允许瞎编或缩写映射名称！

### ✅ 最佳规范定义示范（保持严格同名）

```typescript
// src/app/source/enums/source-status.enum.ts
import { registerEnumType } from '@nest-boot/graphql';

export enum SourceStatus {
  WAITING = 'WAITING',
  PROCESSING = 'PROCESSING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
}

// 注意这里：name 属性必须死死地绑定回 'SourceStatus'，也就是变量名本身
registerEnumType(SourceStatus, {
  name: 'SourceStatus',
});
```

## 2. 结合底层实体的闭环

当我们回到带有数据库属性和通信网关双重身份的 `Entity` 实体层时，应当双重利用这层已经成功注册为 Graph 类型集的枚举。

- **对 GraphQL 的暴露**：由于我们成功将其 `registerEnumType`，现在可以直接向 `@Field(() => SourceStatus)` 抛掷，客户端生成的 TS 和 Schema 会天然支持并校验这些纯大写常量集。
- **对底层的映射**：使用 `MikroORM` 带来的 `@Enum` 去映射限制数据库列的行为上限。

### ✅ 实体内的安全双层嵌套绑定

```typescript
// source.entity.ts

import { Enum, Opt } from '@mikro-orm/postgresql';
import { Field } from '@nest-boot/graphql';

// 被上一步完美构造并在内部实施了 registerEnumType 注册后的安全容器
import { SourceStatus } from './enums/source-status.enum';

// ...
export class Source {

  // 第一层: GraphQL 的 Schema 类型保证了 HTTP 通讯层面对传入传出参数做出了拦截。
  @Field(() => SourceStatus)

  // 第二层: MikroORM 则确保了落库前的值一定锁死为这几个。
  @Enum({ items: () => SourceStatus, default: SourceStatus.WAITING })

  status: Opt<SourceStatus> = SourceStatus.WAITING;

}
```

如此这般，才算真正的用一套枚举模型，完美打通了通讯防腐层与存储抗污层。
