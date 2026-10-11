# MikroORM 迁移规范

数据库迁移必须来自当前 Entity 与装饰器 metadata 的 MikroORM diff。迁移
文件是生成结果和审查对象，不是先手写 SQL 再让实体追赶的设计源。

## 生成流程

1. 完成 Entity、Enum、关系、Index、Check、Unique 与原生 RLS
   `@Entity({ policies })` metadata 修改。
2. 准备一个结构与当前主线迁移一致的 disposable PostgreSQL。不要对生产库
   运行 `migration:create`，也不要用含有个人开发漂移的长期数据库生成。
3. 检查目标应用的 `package.json`、workspace 配置和现有 CI 命令，使用宿主代码库定义的迁移生成脚本。若没有包装脚本，再使用 MikroORM CLI。例如：

```bash
pnpm run migration:create
# 或
pnpm mikro-orm migration:create
```

4. 保留 MikroORM 生成的当前时间戳文件名。业务的未来生效时间属于 Seeder
   数据或配置字段，例如 `effectiveFrom`；不要把业务日期伪装成迁移生成时间。
5. 审查完整 `up()` 与 `down()`：表、列、默认值、枚举约束、FK、索引、
   unique/check、RLS policy 和依赖表改名都必须闭环。

表结构与 policy 不要手写一份迁移来代替生成器。角色、GRANT、扩展与数据搬迁
等 metadata 不能完整表达的基础设施行为，可以使用单独审查的手写迁移。
只有在通过 metadata、生成 SQL 和实测证明
生成器遗漏了不可表达或回滚所需的行为后，才允许在生成文件上做最小、带
说明的修正；例如生成的 `down()` 未恢复旧表原有 RLS。修正后仍要保留可
识别的生成主体，并重新跑双向验证。

## 重命名、替换与数据

- 有需要保留的数据：设计显式数据迁移、兼容窗口和回滚路径，不能假设表
  为空。
- 已经核实旧表无数据，且新名称代表新的明确所有权边界：允许生成迁移
  创建新表、修复依赖 FK 后删除旧表，不必制造无意义的数据复制。
- 表存在不等于有业务数据；在决定 drop 前，用只读查询确认行数、依赖 FK、
  外部事件或审计记录引用和当前生产版本。
- 同步检查关系属性及 FK 列。例如 `subscription` 改为
  `tenantSubscription` 时，依赖列与索引也应变成
  `tenant_subscription_id`。

## RLS 与迁移

RLS 的源定义位于 `@Entity({ policies })`，原生配置使用 `check`、小写
`command` / `type`。先更新 metadata，再用官方 `@mikro-orm/migrations`
的 `Migration` / `Migrator` 生成和执行迁移，不使用旧自定义 RLS migration。

升级已有数据库时，先把已有 policy 纳入 metadata，避免原生 introspection
把缺失定义当成待删除策略。角色、GRANT 与 RLS 是独立层次，必须分别验证。

对可选 request context 使用自定义表达式时，注意 PostgreSQL
`current_setting(..., true)` 可能返回空字符串。向 bigint 转换前应保护：

```sql
nullif(current_setting('app.tenant.id', true), '')::bigint
```

同时审查 `down()` 是否恢复旧 policy，以及生成器在删除最后一条 policy 时
是否正确处理 `disable row level security`。

## Seeder 与部署

检查宿主应用是否提供统一的数据库部署脚本，以及该脚本是否依次执行
`migration:up` 和幂等 Seeder。不要假定脚本名、包过滤器或部署平台。若部署
流程包含 Seeder，Seeder 失败必须使数据库部署失败，而不能被静默忽略。

## 必做验证

在 disposable PostgreSQL 上使用宿主应用已有脚本执行完整循环；以下是未提供包装脚本时的 CLI 示例：

```bash
pnpm mikro-orm migration:up
pnpm mikro-orm migration:check
pnpm mikro-orm migration:down
pnpm mikro-orm migration:up
pnpm mikro-orm seeder:run
```

然后用只读 SQL 验证目标表/旧表、列、FK、索引、`pg_policies`、最新迁移
记录和 Seeder 行。最后运行相关 Entity/Service/Seeder 测试、PostgreSQL
集成测试、typecheck 和 build。

禁止使用 `migration:fresh`、递归删除迁移目录或 Git 强制恢复来“清理”用户
工作区。若确实要重做未提交迁移，先确认这些文件只属于当前任务，并通过
迁移 down 回到已知基线后重新生成。

Nest Boot v8 示例的 init + schema baseline 仅供新数据库，不是 v7/旧 beta
业务库的数据升级路径。保留现有迁移历史，单独设计重命名、数据转换和回滚。
