# MikroORM 迁移 (Migration) 命令指南

在基于 `@nest-boot/mikro-orm` 底层的开发工作流中，每当涉及到实体结构（`Entity`）中字段类型、关联关系或者枚举集的增删改等行为时，我们必须依靠并使用规范的命令生成数据库迁移脚本。

系统依靠底层的 `mikro-orm` CLI 套件提供了强大的实体比对与差分分析能力。

## 1. 核心迁移命令与使用流程

在项目中，主要依赖以下组合流进行迁移生命周期的操作。我们已经在 `package.json` 中配置了代理命令（或者你也可以直接使用 `pnpm mikro-orm migration:*`）。

### 第一步：生成差异文件 (`migration:create`)

当你修改完任何 `.entity.ts` 或者附带的 `enum` 结构并运行了编译（如 `npm run build` 或在 `watch` 态下保存）之后，执行以下命令：

```bash
pnpm mikro-orm migration:create
# 或者是使用被代理的缩写命令:
pnpm run migration:create
```

系统会比对你现有的数据库元表结构和新变动的 TypeScript Entity 结构，自动生成一个包含如 `Migration202604xxxxx.ts` 形式的防篡改快照增量文件，并存放于 `src/database/migrations` 中。

### 第二步：执行上翻变更 (`migration:up`)

快照文件生成以后，需要将变更指令实际落入 PostgreSQL 数据流：

```bash
pnpm run migration:up
```

> **⭐ 核心最佳实践：** 强烈建议使用针对本项目配置过的 `pnpm run migration:up` 代理脚本，而不是直接执行原生的 `pnpm mikro-orm migration:up`。因为本项目的 `package.json` 在 `migration:up` 后方串联追加了 `&& node dist/setup-tenant.js` 这条必须的任务。它能在原生建表之后，无缝帮你补齐诸如 RLS（行级安全）、Tenant 多环境授权架构以及相应的默认角色授权策略等。

### 需要回滚时 (`migration:down`)

若出现脏数据或代码重置需求，退回到上一个快照节点：

```bash
pnpm run migration:down
# 或使用原生命令直接操作:
pnpm mikro-orm migration:down
```

## 2. 其余周边诊断命令

如果遇到版本迷失，或是想用作 CI/CD 检测，`mikro-orm` 内置了以下可用命令应对诊断场景：

```bash
# 罗列所有的当前已经生效和已被记录的迁移文件
pnpm mikro-orm migration:list

# 仅罗列处在 Pending (待执行、即尚未 up) 状态的迁移
pnpm mikro-orm migration:pending

# 用作 bash 脚本断言监测（不生成文件）：快速检阅代码和数据库是否存在结构不同步
pnpm mikro-orm migration:check

# 危险清理：彻头彻尾清空当前数据库的所有表结构数据并一切推倒重来再 up
pnpm mikro-orm migration:fresh
```

## 3. 合并零碎迁移工作流 (Squashing: 基于 Git 的安全回摆法)

在本地开发的日常迭代中，我们往往会随着修改产生了非常多碎片化的迁移文件（比如被 `git status` 抓取到的那些未提交的新 `MigrationXXX.ts` 文件）。只凭肉眼去一行行手工回退通常会漏掉某些历史节点。这里建议使用这套无坚不摧的**稳妥回退与合并法**：

1. **查验需要清理的作用域**：在终端里运行 `git status`。在“Changes to be committed”或者未跟踪列表里，所有新增的 `Migration****.ts` 文件，都是你应该剔除或合并的脏差分。
2. **安全下钻回退表结构**：去查阅 Git 里最后一个没有被改动的，也就是已经平安提交进主线的最干净安全迁移快照的文件名（比如 `Migrationxxxx.ts`），然后执行带 `--to` 旗标的重置命令：
   ```bash
   pnpm mikro-orm migration:down --to Migrationxxxx
   # （注意：回退过程中如果涉及修改过 Base 迁移文件，最后还须跑一次 up: pnpm mikro-orm migration:up --to Migrationxxxx 使得其准确停泊在干净的节点）。
   ```
3. **物理歼灭历史污渍**：
   - 执行 `git rm -f src/database/migrations/旧版那些碎片迁移.ts ...`（如果已被 Git 追踪）。
   - 或者使用终端管理器去 `rm` 掉所有你不需要的脏快照。如果连基础款 `Base` 也遭受了污染，请运用 `git restore --staged` 和 `git restore` 使其还原。
4. **合成并发布终极满汉全席**：当目录变得干净（无变脏文件）且底层 PostgreSQL 也被降级到了安全水位点，重新生成一个统筹全量的合集快照并部署：
   ```bash
   pnpm run build && pnpm run migration:create && pnpm run migration:up
   ```
   至此，一次教科书般无损且没有任何隐患的 Squashing 就杀青了！

## 4. 特殊边界处理：数据库扩展 (Extensions) 的补全

当你的实体设计中引入了依赖 PostgreSQL 原生扩展（Extensions）的高级类型字段（例如使用 `uuid-ossp` 生成主键，或是使用 `vector` 扩展实现 `pgvector` 存储向量数据等结构）时，原生的 `mikro-orm` 自动生成工具能够捕获表字段变化，但是**它不会自动帮你生成加载底层扩展系统的代码**。

如果你发现最新的 Entity 需要依赖这类扩展，请在执行了 `migration:create` 生成快照以后，**务必在执行 `up` 之前手工打开该快照文件**，并在 `up()` 函数的最顶部注入对应的原生拓展 `create extension` 语句：

```typescript
// src/database/migrations/MigrationXXXXXXXXXXX.ts
import { Migration } from '@mikro-orm/migrations';

export class MigrationXXXXXXXXXXX extends Migration {
  override async up(): Promise<void> {
    // 【手工添加的扩展指令】确保当前运行库装载了后续生成所需的拓展
    this.addSql(`create extension if not exists vector;`);
    this.addSql(`create extension if not exists "uuid-ossp";`);

    // ...下面是自动生成的建表语句...
    this.addSql(
      `create table "source_chunk" (..., "embedding" vector(1536) null);`
    );
  }
}
```

只有加入了这样稳妥的护航语句，当这个迁移在新的纯净环境或云端被执行时，才不会因为数据库宿主没来得及安装对应 Extension 引擎而导致后续表列创建直接崩溃。
