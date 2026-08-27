# 领域重命名与迁移检查表

重命名不是一次文本替换。目标是让一个领域在代码、GraphQL、数据库和
用户界面上只保留一套明确语义，同时保留真正属于外部协议或通用领域的
术语。

## 先划定语义边界

- 区分有明确所有权的领域实例与通用目录对象。例如 `TenantSubscription`
  表示租户拥有的一笔订阅，而 `SubscriptionPlan`、`SubscriptionProvider`
  和用户可见的 “subscription” 仍是通用领域词，不应机械改名。
- 区分本地命名与外部协议。供应商要求的 metadata key、webhook event、
  URL 或 external ID 前缀只有在外部契约允许时才改。
- 若目标是替换概念而非保留数据，并已确认旧表无数据，可以让生成迁移
  创建新表后删除旧表；有数据时必须先设计数据搬迁和回滚策略。

## 同步检查范围

1. 模块目录与文件：宿主应用的 `<module-root>/<kebab-name>`、Entity、Module、
   Service、Resolver、scheduler、Input、Interface、Type、Spec。
2. TypeScript 符号：类名、构造参数、局部变量、方法名、导入路径和注释。
3. GraphQL：对象类型、Query/Mutation、Input 字段、生成 schema、客户端
   operation 名及生成类型。
4. MikroORM：默认表名、显式表名、关系属性、FK 列、索引、唯一约束和
   RLS policy 名。
5. 跨领域消费者：webhook、后台任务、scheduler、Seeder 和配置。
6. 客户端：组件文件、hooks、变量、路由文案、GraphQL documents 和测试。
7. 运维与文档：部署配置、环境变量、迁移说明和维护文档。

## 迁移与验证

- 先完成 Entity/装饰器改名，再由 MikroORM 生成迁移；不要手写一份看似
  匹配的迁移来代替 metadata diff。
- 审查生成的 `up()` 与 `down()`，尤其是依赖表的 FK 列、索引和 RLS。
- 在 disposable PostgreSQL 上至少运行 `up -> migration:check -> down -> up`。
- 生成 GraphQL schema，并执行一个真实查询；仅通过 TypeScript 编译不能
  发现 GraphQL 类型名冲突或遗漏的 relation resolver。
- 最后使用 `rg` 搜索旧目录名、文件名、类名、表名、列名和变量名。逐条
  判断剩余命中是合法通用词、外部协议还是遗漏，禁止只看零命中数量。
