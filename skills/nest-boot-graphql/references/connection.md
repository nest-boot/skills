# GraphQL 分页连接器 (Connection Definition) 架构规范

在向外界提供具有一对多查询或多对多查询等支持数据集翻页和搜索过滤能力的端点结构时，本框架要求使用 Relay-style GraphQL Connection 进行编排。

## 1. 使用与拆分强约束

当一个端点查询返回不再是单纯的单条 Entity 对象，而是基于分页、游标等数组类操作结果时：
**绝不允许在 Entity 或 Resolver 中顺手拼凑泛型或是手搓翻页包装体。**

必须独立生成专属的类型安全文件：
1. 文件名要求：以实体名为前缀，采用脊柱命名法加特殊后缀 `.connection-definition.ts`。例如针对 `User` 的就是 `user.connection-definition.ts`。
2. 存放位置：必须存在于此业务模块的根目录下（即 `./src/app/[module-name]/` 根深目录）。

## 2. 规范定义示范 (使用 ConnectionBuilder)

### ✅ 最佳代码示范：使用框架底层的动态生成包装体

我们推荐借助 `@nest-boot/graphql-connection` 带来的核心工具类 `ConnectionBuilder`。它会自动将你配置好的列（如通过 `addField` 限定了某些字段能够作为搜索、过滤条件或排序），动态解构成标准的 `Connection` 返回容器结构及 `ConnectionArgs` 输入参数结构：

```typescript
// 文件存放位置示例：src/app/conversation/conversation.connection-definition.ts

import { ArgsType, ObjectType } from '@nest-boot/graphql';
import { ConnectionBuilder } from '@nest-boot/graphql-connection';

import { Conversation } from './conversation.entity';

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

做好了高可用高防腐的定义之后，这层带有翻页属性与搜索过滤安全的 `Args` 载体和 `Connection` 返回体，就能极大减少我们在 Resolver 与 Service 层写的繁文缛节代码。

在对应的 Resolver 中，你能极为清爽地将它用作端点：

```typescript
// src/app/conversation/conversation.resolver.ts

import { ConnectionManager } from '@nest-boot/graphql-connection';

@Resolver(() => Conversation)
export class ConversationResolver {
  constructor(
    // 注入对应的连接管理器
    private readonly conversationService: ConversationService,
    private readonly cm: ConnectionManager,
  ) {}

  @Query(() => ConversationConnection)
  async conversations(
    @CurrentWorkspace() workspace: Workspace,
    // 消费被构建好的专属入参体
    @Args() args: ConversationConnectionArgs,
  ): Promise<ConversationConnection> {

    // 把带有搜索过滤及翻页特性的 args 移交给特定业务底层接口处理即可获得标准响应
    return await this.conversationService.getConnection({
        ...args,
        workspace
    });
  }
}
```
