# MikroORM Seeder 规范

Seeder 用于可重复部署的内部配置数据，不用于伪装 schema migration 或直接
修改外部供应商目录。

## 设计原则

- 继承 `@mikro-orm/seeder` 的 `Seeder`，并从 `DatabaseSeeder` 调用。
- 使用稳定业务键幂等 upsert；生产重复执行不得制造重复行。
- 将金额、配额等 decimal 值作为字符串解析和写入，避免 JavaScript 与
  YAML 浮点转换。
- 在写入前校验枚举、唯一组合、有效期、货币代码、精度和整数位数。
- 不允许稳定业务键悄悄改绑外部供应商身份；需要新供应商或新目录对象时
  创建新的稳定 code 或新记录。
- `effectiveFrom`/`effectiveTo` 控制业务生效时间。可以今天迁移和运行
  Seeder，让记录在未来日期才被查询为可售。

## 配置与外部系统边界

部署 values、Secret 或环境变量可以提供内部 Seeder 配置。除非任务明确
要求调用供应商 API，不要因为本地需要 `planCode`、积分或映射信息就更新
外部 Product metadata；本地必须能够独立保存所需语义。

## 验证

1. 无配置时安全跳过或按明确约定失败。
2. 同一配置连续运行两次，行数与稳定 ID 不应异常增长。
3. 重复 code、重复 `(provider, providerPlanId)`、非法 decimal 和反向有效期
   必须失败。
4. 宿主应用的数据库部署流程中 migration 与 Seeder 一起通过；如果没有统一脚本，分别执行并验证。
5. 直接查询数据库核对真实值与时区，不只断言 mock 调用参数。
