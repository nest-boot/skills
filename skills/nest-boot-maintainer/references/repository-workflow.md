# 仓库贡献工作流

目标仓库：[nest-boot/nest-boot](https://github.com/nest-boot/nest-boot)。开始工作时读取根 `package.json`、`turbo.json`、`.changeset/config.json`、目标 package manifest 与 `.github/workflows/verify.yml` / `release.yml`；本文是 v8 基线，不替代当前配置。

## 当前仓库约束

- 默认分支 `main`；Node.js >=24.21.0、pnpm 10.30.3、原生 ESM。
- Turborepo 编排构建任务，Changesets 管理独立包版本，GitHub Actions 执行验证与发布。
- 使用 Vitest + SWC，注释通过 ESLint 的 JSDoc TypeScript preset 检查；不再运行 Nx、Jest 或 TypeDoc 命令。
- `@nest-boot/<name>` 通常对应 `packages/<name>`，以 manifest 为准；旧数据库/队列包已更名为 database/queue。
- PR 标题仍使用 Conventional Commits；版本升级幅度由 changeset 声明，不再依赖提交标题推断。
- 完整 CI 包含包/示例构建、类型/格式/Lint、coverage、E2E、示例服务器、浏览器和独立 tarball 消费者。服务依赖包括 PostgreSQL、Redis、S3 兼容存储（当前 CI 使用 RustFS）和 Mailpit。

## 准备 checkout 与分支

1. 确认 origin 与 `git status`，保留无关改动，必要时创建独立 worktree。
2. 同步默认分支，从最新 `main` 创建专用分支；beta 用于明确的预发布周期。
3. 读取当前 CONTRIBUTING、SECURITY 和 GitHub 模板；查询相同问题的 open/closed Issue 和 PR。
4. 创建 Issue、推送、提交 PR 与合并按用户已授权范围执行，不直接推送 main。

## 按改动选择验证

可复现的行为修复先添加能失败的回归测试。确认目标包确实声明对应脚本；构建所需依赖后再运行测试，例如：

```bash
pnpm exec turbo run build --filter=@nest-boot/<package> --force
pnpm --filter @nest-boot/<package> test
pnpm exec turbo run lint --filter=@nest-boot/<package>
```

需要缩小 Vitest 范围时用该包的 `exec vitest run <file>`，不套用 Jest 的 `--runInBand`。测试或 lint 脚本缺失时先检查 manifest，不执行不存在的命令。

根据风险追加相关命令，不要求每次文案修订跑全部集成测试：

```bash
pnpm build:packages --force
pnpm build:examples --force
pnpm format:check
pnpm lint
pnpm test:cov
pnpm test:e2e
pnpm test:consumer
pnpm test:release
```

`test:consumer` 验证发布 tarball 的独立安装、公开导出、strict peers 与启动；公开依赖或入口变更应运行。`test:release` 用于版本/发布流程变更。需要完整 CI 时复用当前 workflow 的服务和示例测试命令。缺少依赖服务时明确未运行项，不把类型检查冒充运行时通过。

文档改动按范围运行 `pnpm build:docs`；JSDoc 对齐 `jsdoc.configs['flat/recommended-typescript-error']`，由仓库 ESLint 检查，不恢复 TypeDoc/TSDoc 工具链。

## Changesets 与发布

- 对用户可见的包变更运行 `pnpm changeset`，选择受影响包和 patch/minor/major，提交生成的 `.changeset/*.md`。
- 只改工具或文档且不需要发布时使用 `pnpm changeset --empty`；用 `pnpm release:status` 检查影响。不要因 Conventional Commit 标题是 feat/fix 就省略 changeset。
- 合入 main 后，Action 创建/更新 version PR；`pnpm release:version` 更新版本、changelog 和 lockfile。version PR 合并后完整验证、打包，再由独立 OIDC job 发布 npm。
- 不手改包版本或在普通功能 PR 本地发布；本地预演使用可丢弃副本，以免消耗待提交的 changeset。
- beta 使用 `changeset pre enter beta`，`.changeset/config.json` 的 baseBranch 对齐 beta；首次周期先同步 main 的稳定版本与工具。退出时执行 `changeset pre exit`、恢复 main 基线，并按贡献文档走稳定版 version PR，不能直接把 beta 包作为 latest 发布。
- npm 部分成功后，重跑原失败 workflow 的 publish job，保留原打包 artifact/plan。新开 workflow 的 plan 会排除已发布版本，不能代替原计划的 GitHub tag/release 修复。

提交前运行 `git diff --check` 并检查 `git status --short`，排除测试缓存、环境文件、生产数据与无关 lockfile 改动。

## Issue 模板

```markdown
## Package and version

- Package: `@nest-boot/...`
- Version:
- Node / pnpm / relevant peers:

## Problem

说明影响和出现条件。

## Minimal reproduction

提供脱敏代码、仓库或确定性步骤。

## Actual behavior

粘贴最短必要输出。

## Expected behavior

说明依据的公开契约。

## Investigation

列出已排除项、源码位置和可能根因；不确定处明确标记。
```

改进建议把 `Minimal reproduction` 替换为 `Use cases and constraints`，补充备选方案和兼容影响。得到授权后可使用 `gh issue create --repo nest-boot/nest-boot`，但先让正文落到临时文件或通过安全参数传入，避免 shell 插值执行内容。

## PR 模板

PR 标题使用 Conventional Commit，例如 `fix(logger): preserve context outside requests`。

```markdown
## Summary

- 修复或改进了什么
- 影响哪些 packages、公开 API 或文档

## Problem and root cause

说明复现、被破坏的契约和根因证据。

## Verification

- `实际执行的命令` — 结果
- 未运行项及原因

## Compatibility and release impact

说明默认行为、类型、依赖、迁移和预期 release 类型。
```

已有 Issue 时使用 `Fixes #...` 或 `Refs #...`。审查 diff 后再推送并创建 PR；没有写权限时从 fork 分支向 `nest-boot/nest-boot:main` 发起。返回 PR URL 和 head commit SHA，不自动合并或发布。
