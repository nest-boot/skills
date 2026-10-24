# GraphQL 分页连接器 (Connection Definition) 架构规范

向外界提供需要游标分页、搜索、过滤或排序的数据集时，使用 Relay-style GraphQL Connection。

## 1. 使用与拆分强约束

当端点返回分页集合时，不要在 Entity 或 Resolver 中重复实现分页包装体。

为领域定义独立的类型安全文件：
1. 文件名要求：以实体名为前缀，采用脊柱命名法加特殊后缀 `.connection-definition.ts`。例如针对 `User` 的就是 `user.connection-definition.ts`。
2. 存放位置：放在宿主应用已有业务模块根目录下的对应领域目录，例如 `<module-root>/<module-name>/`。

## 2. 规范定义示范 (使用 ConnectionBuilder)

### 使用 ConnectionBuilder 生成类型

`ConnectionBuilder` 根据 `addField` 中允许搜索、过滤或排序的字段，生成标准的 `Connection` 返回类型与 `ConnectionArgs`：

```typescript
// 文件存放位置示例：<module-root>/conversation/conversation.connection-definition.ts

import { ArgsType, ObjectType } from '@nest-boot/graphql';
import { ConnectionBuilder } from '@nest-boot/graphql-connection';

import { Conversation } from './conversation.entity.js';

// 1. 初始化构建器并声明对应可以用来 search / filter / sort 的合法安全字段
export const { Connection, ConnectionArgs } = new ConnectionBuilder(
  Conversation,
)
  .addField({
    field: 'title',        // 数据库字段或者 GraphQL 列名
    searchable: true,      // 允许使用 query 进行全文模糊搜索
    filterable: true,      // 允许精确等值过滤
    type: 'string',
  })
  .addField({
    field: 'created_at',
    replacement: 'createdAt',
    filterable: true,
    sortable: true,
    type: 'date',
  })
  .build();

// 2. 将产出结果分别挂载成被 GraphQL 系统所识别的 @ArgsType 和 @ObjectType
@ArgsType()
export class ConversationConnectionArgs extends ConnectionArgs {}

@ObjectType()
export class ConversationConnection extends Connection {}
```

## 3. 在 Resolver 中消费连接器

在 Resolver 中注入 `ConnectionManager`，并把生成的 Connection class 与 Args 传给 `find()`：

```typescript
// <module-root>/conversation/conversation.resolver.ts

import { ConnectionManager } from '@nest-boot/graphql-connection';

@Resolver(() => Conversation)
export class ConversationResolver {
  constructor(private readonly cm: ConnectionManager) {}

  @Query(() => ConversationConnection)
  async conversations(
    @Args() args: ConversationConnectionArgs,
  ): Promise<ConversationConnection> {
    return await this.cm.find(ConversationConnection, args);
  }
}
```

需要租户范围、软删除或关联过滤时，通过 `find()` 的第三个参数传入 `where`，不要接受客户端直接控制这些服务端边界。

## 4. 限制排序与按选择计算 count

默认生成 ID 排序。只允许创建时间等业务排序键时，显式声明 `.addField({ field: 'id', type: 'string', sortable: false })`，再为允许的字段启用 sortable；id 仍作为游标内部 tie-breaker，不等于把它从实体删除。GraphQL 的 CREATED_AT 等枚举经 coercion 后是实体属性路径 `createdAt`，不要在 Service 中再次按枚举字面量比较。

当 Resolver 能取得 `@Info()` 的 GraphQLResolveInfo 时，将其放进第三个 options 参数，可以在客户端未选择 totalCount/totalCountRelation 时跳过 count 查询：

```typescript
import type { GraphQLResolveInfo } from 'graphql';
import { Args, Info, Query, Resolver } from '@nest-boot/graphql';
import { ConnectionManager, type ConnectionResult } from '@nest-boot/graphql-connection';

// ConversationConnection/Args 来自上面的 connection definition。
@Resolver(() => Conversation)
export class ConversationResolver {
  constructor(private readonly cm: ConnectionManager) {}

  @Query(() => ConversationConnection)
  async conversations(
    @Args() args: ConversationConnectionArgs,
    @Info() info: GraphQLResolveInfo,
  ): Promise<ConnectionResult<Conversation>> {
    return await this.cm.find(ConversationConnection, args, { info });
  }
}
```

有授权范围时在同一个 options 中传 `{ info, where: trustedScope }`，不要把 where 本身作为第三参数，也不要用客户端 OR 条件替换固定范围。ConnectionResult 反映未选择时省略的 count 字段；未传 info 的调用维持原来的计数行为。测试分页边界、允许/禁止的排序键，并断言单条、节点分页与 count 使用同一授权范围。

可选队列历史/API 还有 `@QueueVisible()` 和 user/workspace/system 查询边界，见 `nest-boot-queue`；不要通过自建无范围 Job Resolver 绕过 JobService。
