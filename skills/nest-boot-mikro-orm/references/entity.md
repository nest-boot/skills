# MikroORM 实体 (Entity) 架构设计规范

在 `@nest-boot` 的规范体系中使用 `MikroORM` 声明实体时，为了确保类型强控与数据库扩展的安全性，请严格遵守以下实体属性抽象标准。

## 1. 字段类型准则：强制约束有限集合类型

在遇到存在“有限集范围”的表达性字段时（诸如：`status`, `type`, `role`, `tier` 等），**严禁使用松散的字符串 (`Opt<string>` + `t.string`) 作为属性定义！**

### ❌ 错误示范：松散字符串表达

下面的错误示范将导致服务端与客户端通讯时丢失静态检查能力，同时也无法享受数据库层的常量约束报错：

```typescript
// source.entity.ts
import { Opt, Property, t } from '@mikro-orm/postgresql';
import { Field } from '@nest-boot/graphql';

// 错误：使用了硬编码默认值字符串与散列字符类型
@Field(() => String)
@Property({ type: t.string, default: 'processing' })
status: Opt<string> = 'processing';
```

### ✅ 规范标准示范：独立枚举化

必须依照 `nest-boot-best-practices` 所规定的全大写独立 Enum 书写规则，引入独立的 Enum 并用 `@Enum()` 进行装饰：

```typescript
// src/app/source/source.entity.ts
import { Enum, Opt } from '@mikro-orm/postgresql';
import { Field } from '@nest-boot/graphql';

import { SourceStatus } from './enums/source-status.enum';

// 正确：安全导入完全独立的类型防腐大写枚举
@Field(() => SourceStatus)
@Enum({ items: () => SourceStatus, default: SourceStatus.PROCESSING })
status: Opt<SourceStatus> = SourceStatus.PROCESSING;
```

## 2. 其它类型准则与索引

1. **唯一性标识符**：如果你使用 `t.bigint` 等复杂标识符搭配全局算法（如 `Sonyflake`），确保声明类型时使用统一包装 `Opt<string>` 以向下兼容前端的 53bit Integer 限制。
2. **状态机索引**：像 `status` 或 `type` 这类经常被用于 Where 过滤的数据标尺，请务必在 `@Entity()` 修饰的顶部加上相应的索引支持：`@Index({ properties: ['status'] })`。
