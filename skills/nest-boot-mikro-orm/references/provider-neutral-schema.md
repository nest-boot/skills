# 多供应商持久化建模

支付、推理、存储或消息供应商应被视为可替换适配器。通用表保存本地领域事实，
供应商字段只保存路由和外部身份。

## 标识语义

- `providerCatalogItemId`：供应商目录中的产品、模型、价格或套餐 ID，属于本地目录映射。
- `providerInstanceId`：供应商创建的一笔远端实例、任务或订阅 ID，属于本地业务实例。
- `providerSessionId`：一次临时会话或工作流 ID，只应存放在对应会话记录中。
- 两个字段表达同一外部身份时应统一命名，避免同时保留 `externalXxxId` 与 `providerXxxId`。

供应商使用 Enum，例如 `ProviderKind`，不要在字段和 service 分支中
散落自由字符串。

## 目录与实例

同一个用户可见能力在不同供应商下可以有独立的 provider binding 或目录记录，
因为价格、单位、外部 ID、生效期和能力可能不同。通过 `(provider,
providerCatalogItemId)` 保证供应商目录唯一，并用稳定的本地 code 供配置引用；
不要用当前客户端展示层级代替真实目录身份。

只有领域确实需要独立生命周期时才增加 offer、session 或 binding 表。不要
提前创建没有查询、约束或供应商映射需求的抽象实体。

## 关系与历史

- 由 tenant 或 user 拥有的远端实例应使用明确的本地关系和独立表，而不是把所有外部 ID 塞进目录表。
- 审计、账本或 webhook 记录可以引用业务实例，但删除策略应按审计要求使用 `set null` 或 `restrict`，避免级联丢失历史。
- 在业务实例保存 provider 快照，避免目录配置变化后无法把已有实例路由回原供应商。
- 外部事件处理使用 provider event 或 instance ID 建立幂等与时序保护；不要依赖用户可见名称。
