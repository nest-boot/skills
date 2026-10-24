# MikroORM 实体 (Entity) 架构设计规范

使用 MikroORM 声明实体时，让 TypeScript、数据库约束与 GraphQL 契约表达同一领域语义，同时避免为开放集合建立难以演进的 enum。

## 1. 字段类型准则：强制约束有限集合类型

当 `status`、`type`、`role`、`tier` 等字段具有稳定且封闭的有限集合，并需要进入数据库或 GraphQL 契约时，优先使用独立 Enum。供应商动态 code、用户标签等开放集合继续使用字符串和相应验证。

### 不推荐：用字符串表达封闭状态

下面的写法会让封闭状态失去静态类型，并容易与客户端和数据库约束漂移：

```typescript
// source.entity.ts
import { type Opt, t } from '@mikro-orm/core';
import { Property } from '@mikro-orm/decorators/legacy';
import { Field } from '@nest-boot/graphql';

// 错误：使用了硬编码默认值字符串与散列字符类型
@Field(() => String)
@Property({ type: t.string, default: 'processing' })
status: Opt<string> = 'processing';
```

### 推荐：独立枚举

沿用 `nest-boot-module-design` 的枚举约定，并用 `@Enum()` 映射：

```typescript
// <module-root>/source/source.entity.ts
import type { Opt } from '@mikro-orm/core';
import { Enum } from '@mikro-orm/decorators/legacy';
import { Field } from '@nest-boot/graphql';

import { SourceStatus } from './enums/source-status.enum.js';

@Field(() => SourceStatus)
@Enum({ items: () => SourceStatus, default: SourceStatus.PROCESSING })
status: Opt<SourceStatus> = SourceStatus.PROCESSING;
```

## 2. 其它类型准则与索引

1. **标识符序列化**：数据库使用 bigint，而 GraphQL/JSON 客户端不能安全表示 64 位整数时，沿用宿主应用的 string 序列化约定；不要在同一系统混用 number 与 string ID。
2. **按查询设计索引**：只有真实查询会按 `status`/`type` 过滤，且选择性、排序或组合条件能受益时才添加索引。低基数字段的单列索引不一定有效，应结合查询计划选择单列、组合或部分索引。
3. **索引和唯一约束默认自动命名**：通过 `@Index({ properties })` / `@Unique({ properties })` 表达字段，通常省略 name。JSON 路径可使用结构化 columns，部分索引使用 where；确需原生 SQL expression 时接收 `(columns, table, indexName)`，用 `table.qualifiedName` 和传入的 indexName。已有库需要保留外部约定的名称时先设计兼容迁移，不为样式破坏现有依赖。
