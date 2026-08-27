# `nest-boot-best-practices` 原生接口 (Interfaces & Types) 架构规范

在 `@nest-boot` 应用中，纯 TypeScript 类型应与运行时模型保持清晰边界。是否拆文件取决于复用范围与复杂度，并沿用宿主模块的既有约定。

## 1. 独立抽离策略与专属存放位置

跨文件复用、承载公共 payload 或具有一定复杂度的 `interface`/`type`，放入 `types/` 或 `interfaces/`。只服务于单个短函数的简单局部类型可以就近保留，避免产生只含一行定义的文件。

- **避免混合职责**：不要把较大的 `interface XXXPayload` 与 Service 或 Entity 的实现主体堆在同一个文件中。
- **合理的位置范例**: 比如，为 `TeamMember` 准备的相关扩展声明，应放置在 `<module-root>/team-member/interfaces/` 或 `<module-root>/team-member/types/`。`<module-root>` 应沿用宿主应用现有的模块根目录。

## 2. 区分实体与接口边界

TypeScript `interface`/`type` 只存在于编译期。需要 `@Field()`、`@InputType()` 或 class-validator 元数据时，使用 class 并放入相应的 GraphQL Input/Args 模型目录。

当写下 `export interface ...` 时，要确保其纯粹性，用于充当函数入参控制声明或泛型界线控制。
