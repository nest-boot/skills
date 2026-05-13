# `nest-boot-best-practices` 原生接口 (Interfaces & Types) 架构规范

在日常的 `@nest-boot` 的应用编写中，我们经常遇到需要声明与数据库无关的局部纯净类型，或者是特定的通信层契约载荷（Payload Interfaces）。此时必须严格控制 `interface` 或者 `type` 块的位置。

## 1. 独立抽离策略与专属存放位置

所有与泛型组合或者是通用对象类型（不具有 GraphQL 等复杂层级装饰器的纯基础 TS `interface` 或 `type`）必须被转移出逻辑主线，专门在 `types/` 或 `interfaces/` 文件夹中做二次封装。

- **禁用混合排布**: 绝不要把一段长达几十行的 `interface XXXPayload` 直接跟 `Service` 或 `Entity` 的功能主体混在同一个源文件中。
- **合理的位置范例**: 比如，为 `WorkspaceMember` 准备的相关扩展声明，应放置在类似于 `./src/app/workspace-member/interfaces/` 或是 `./src/app/workspace-member/types/` 的级联关系目录下。

## 2. 区分实体与接口边界

真正的 TypeScript 极简 `interface` 代表着纯粹的类型定义：如果你发现自己在往里面挂 `@Field()` , `@InputType()` ，甚至是加入 `ClassValidator` 类的规则方法，那说明它并不能算是一个常规的原生接口，它应当是一个专用的 GraphQL 入参模型或是实体容器对象。

当写下 `export interface ...` 时，要确保其纯粹性，用于充当函数入参控制声明或泛型界线控制。
