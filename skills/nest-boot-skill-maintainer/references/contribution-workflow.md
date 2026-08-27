# 贡献工作流

先阅读仓库根目录的 `CONTRIBUTING.md`、`SECURITY.md` 和 `.github` 模板；它们是人类与 Agent 共用的提交入口。以下内容补充 skill 维护的诊断细节。

## 目录

- [1. 准备证据包](#1-准备证据包)
- [2. 检查重复项](#2-检查重复项)
- [3. 设计 skill 边界](#3-设计-skill-边界)
- [4. 本地孵化与自评估](#4-本地孵化与自评估)
- [5. 准备上游分支](#5-准备上游分支)
- [6. 移植与上游验证](#6-移植与上游验证)
- [7. 拆分、重命名与删除](#7-拆分重命名与删除)
- [8. Issue 内容](#8-issue-内容)
- [9. PR 内容](#9-pr-内容)
- [10. PR 审查闭环](#10-pr-审查闭环)

## 1. 准备证据包

在修改上游前整理：

- 当前宿主是 `nest-boot/skills` 上游 checkout，还是安装了本 skill 的 Nest Boot 消费项目；
- 受影响的包、版本和 skill；
- 消费项目已安装 skill 与上游版本是否一致；
- 最小复现或失败调用路径；
- 观察行为与期望行为；
- 根因证据：源码、测试、生成结果或数据库/API 探针；
- 为什么这是通用问题，而不是当前项目约定；
- 修复后执行的验证命令。

先脱敏。用 `Tenant`、`Resource` 等通用名称替换业务实体；删除 token、内部域名、客户数据、完整生产日志和无法公开的堆栈上下文。

## 2. 检查重复项

具备 GitHub CLI 和登录状态时，先做只读查重：

```bash
gh auth status
gh issue list --repo nest-boot/skills --state all --search '<关键词>'
gh pr list --repo nest-boot/skills --state all --search '<关键词>'
```

框架问题改用 `$nest-boot-maintainer`。没有 GitHub CLI 时使用可用的浏览器或连接器查重；不要因为工具缺失就重复提交。

## 3. 设计 skill 边界

创建或大幅重组 skill 时使用项目安装的 `skill-creator`，并先回答：

- 这个 skill 的主要任务是开发、迁移、诊断还是维护？名称应表达主要任务，review 只是适用场景时不要把它命名成 review skill；
- 不同用例是否共享同一输入、执行顺序、产物和完成条件？若明显不同，拆成独立 skill 并在 description 中互相路由；
- 规则是否已有明确所有者？GraphQL、ORM、RLS 等细节留在专项 skill，协调 skill 只维护顺序和闭环；
- 框架中立能力是否会在多个 Nest Boot 项目重复出现，且没有更合适的成熟上游 skill？满足时可留在本仓库，但使用中立名称和触发描述；
- 正文是否只保留核心决策，具体实现与变体放到直接链接的 reference？

一个 skill 同时支持开发和审查并不等于职责混杂；关键是两者是否检查同一个工程契约。不要只因文件变长而拆分，也不要用一个“best-practices”总入口承载完成条件完全不同的工作流。

## 4. 本地孵化与自评估

消费项目中的 `.agents/skills/<name>/` 可以作为可写的本地候选版本。它在孵化期间有意偏离上游，但仍须保留来源和基线：

1. 在首次编辑前复制完整安装目录作为原始 baseline，并复制完整 `skills-lock.json`；若 lockfile 不存在，保存明确的 absence marker。另行记录目标条目的 source、skillPath、hash 以及 skill 快照校验和；不要为了匹配本地内容而手工伪造 hash。
2. 直接修改安装副本，保留目录名和 frontmatter `name`。只把当前任务涉及的 skill 置于修改范围，不顺带改写其他已安装 skill。
3. 把失败案例加入候选版本的 eval，或在项目外的 workspace 保存本轮 eval metadata；不要把 trace、输出、反馈和 benchmark 写进待发布 skill 目录。
4. 每轮先冻结候选与 baseline 并记录内容哈希；每个 run 再使用新的可丢弃执行根目录。复制同一 commit、依赖锁、消费项目 fixture 和输入后，把本轮快照复制到该根目录的 `.agents/skills/<name>/`。使用 `find ... -type l` 等确定性检查确认复制后的 skill 树没有软链接；paired runs 保持模型、提示、配置、权限、准备/验证命令与 run 数一致。
5. 用确定性检查和 rubric grader 评估 expectations，生成 benchmark 与 review viewer。只有目标失败被预防、相关回归未出现、候选相对 baseline 有证据支持且用户反馈已处理，才认为候选达到上游化门槛。
6. 保存候选相对原始 baseline 的 diff、版本证据、eval 结果摘要和有意排除的项目私有内容，作为上游 issue 与 PR 的证据包。

当前宿主就是 `nest-boot/skills` 时，不需要先建立消费项目安装副本；直接在上游分支修改，并使用相同的隔离复制规则评估 `skills/<name>/` 候选。

## 5. 准备上游分支

- 当前宿主就是 `nest-boot/skills` 时，优先使用该干净 checkout；存在无关改动时使用独立 worktree 或 clone。
- 当前宿主是消费项目时，等本地候选通过质量门槛后再定位或创建干净的 `nest-boot/skills` checkout；消费项目保留为复现和回归场景。
- 同步远程并确认默认分支没有领先提交，再创建 `fix/<skill>-<topic>` 或 `docs/<skill>-<topic>` 分支。
- 上游正式改动只进入 `skills/<name>/`；不要把整个消费项目安装目录、lockfile 或评估 workspace 复制进仓库，也不要强制覆盖用户分支或直接推送 `main`。

## 6. 移植与上游验证

1. 在消费项目孵化时，根据候选相对原始 baseline 的 diff，把通用规则、reference 和 eval 移植到上游 `skills/<name>/`；不要直接覆盖上游目录，因为安装版本可能落后且包含项目私有实验。
2. 在上游仓库直接维护时，更新最接近问题的正文或 reference，避免在多个文件复制同一规则。
3. 将失败案例泛化为真实 eval，包含期望输出和可观察 expectations；触发范围、拆分和迁移变化同样需要 eval。
4. 若新增 skill 或修改 description，运行 README 生成器。
5. 对版本敏感的框架、运行时、SDK 或 CLI 规则，记录锁定版本并读取官方源码、类型或文档；能运行时执行最小行为探针，不把单个项目现象直接写成通用结论。
6. 对移植后的上游候选重新运行关键 paired eval，确认清理项目细节时没有损失本地验证过的行为。
7. 运行全仓校验器、quick validator 和与改动相关的框架测试。
8. 人工审查完整 diff，确认示例可执行、失败路径闭环，并且没有项目私有信息、生成缓存或无关格式化。结构校验和自动 reviewer 通过不能替代这一步。

若用户明确要求结构化本地审查，可使用项目的 `autoreview` skill；不要把它变成每次提交前的隐式动作。无论审查工具是否报告问题，都要验证每条建议所依赖的真实代码路径或外部行为。

## 7. 拆分、重命名与删除

skill 名称是安装和触发契约。修改已进入默认分支的名称或目录前：

1. 检查 README、默认分支、消费项目 `skills-lock.json` 和安装目录，确认旧 skill 是否已发布；
2. 核对消费项目锁定的 `skills` CLI 版本、帮助或实现，并在可丢弃目录中验证 update/add/remove 行为；不要假设 update 会删除旧名称或安装新名称；
3. 为显式迁移准备官方 `skills remove <old>` 与 `skills add ... --skill <new...>` 命令，迁移说明放在 README 生成区之外；
4. 默认使用明确迁移。只有消费者无法原子更新且兼容 skill 不会与新 skill 竞争触发时，才保留带移除期限的临时兼容入口；
5. 本地孵化阶段可以直接编辑安装副本验证拆分方案；上游合并前不要把临时目录结构当成已发布迁移结果；
6. 上游合并后，通过官方安装命令更新已授权的消费项目及其 lockfile，让正式版本替换本地候选；
7. 验证旧 skill 已移除、新 skill 已安装、锁文件指向正确路径，并检查不会同时加载新旧重叠规则。

## 8. Issue 内容

Issue 应包含：

```markdown
## 问题
现有行为或指引造成了什么可观察失败。

## 最小复现
最少的版本、配置、代码或命令。

## 期望行为
基于公开 API 或设计意图应该发生什么。

## 根因证据
相关源码、测试、schema、SQL 或日志探针；不包含敏感信息。

## 本地评估
候选版本、baseline、关键 expectations、benchmark 或人工反馈摘要。

## 建议范围
应修改 skill、framework、docs 还是 tests；仍待维护者决定的事项。
```

不要只写“文档不对”或粘贴未经整理的聊天记录。

## 9. PR 内容

PR 应包含：

```markdown
## Summary
- 修复的通用问题
- 更新的 skill/reference/eval

## Evidence
- 原问题如何复现
- 为什么修改适用于其他项目
- 本地候选相对 baseline 的评估证据

## Validation
- 执行的命令与结果

## Scope
- 明确未包含的项目私有行为或后续框架工作
```

消费项目中孵化成熟的改进应创建承载问题与评估证据的 issue，并让 PR 使用 `Fixes #...` 或 `Refs #...` 关联；直接在上游仓库完成的小型明确修复仍可只提交自解释 PR。推送分支和调用 `gh issue create`/`gh pr create` 都会修改外部状态，仅在用户明确授权后执行；完成后返回可点击链接和提交 SHA。

远端流程中把以下标识当作不同类型，不要因数字恰好相同而复用：

- `ISSUE_URL` / `ISSUE_NUMBER` 只标识证据 issue 和 PR body 中的关联；
- `PR_URL` / `PR_NUMBER` 用于 `gh pr`、pull request GraphQL 查询和 review threads；
- `HEAD_SHA` 是当前 PR head，每次 push 后都会变化，必须重新读取；
- `MERGE_SHA` 只在合并后读取，用于确认提交已进入默认分支。

优先把 `PR_URL` 直接传给支持 URL 的 `gh pr` 命令。必须传数字时，先从对应 URL 提取并验证，再执行查询；交付命令清单前检查所有变量均在首次使用前定义，issue/PR/head/merge 标识没有跨类型混用。

## 10. PR 审查闭环

用户要求在线审查、处理建议或合并时，以当前 PR head 为审查单位：

1. 从 `PR_URL` 读取并校验 `PR_NUMBER`，再读取 `headRefOid`、merge state、CI checks、普通评论、reviews 和 inline `reviewThreads`；GraphQL 的 `pullRequest(number:)` 必须使用 `PR_NUMBER`，不要使用 `ISSUE_NUMBER`，也不要只看 PR 顶部评论。
2. 等待 reviewer 明确完成，并比较 review/评论中的 reviewed commit 与当前 `headRefOid`。没有评论不代表仍在排队的审查已经通过。
3. 对每条建议回读真实文件、依赖源码和测试；只修复成立且在本 PR 范围内的问题，并回复或解决对应 thread。
4. 推送修复后重新运行确定性与语义验证，重新读取 `HEAD_SHA`，再触发或等待 reviewer 审查该 SHA；旧提交的 clean 回执不能覆盖新提交。
5. 合并前确认 CI 成功、PR 可合并、当前 head 没有未解决 thread，并再次确认用户已经授权合并。合并后读取 `MERGE_SHA`，验证它是远端默认分支祖先；沿用仓库现有 merge 策略，不自行改写历史约定。

若只被授权创建 PR，不要把授权扩大为自动合并。若用户要求持续处理到解决，保持 PR 打开并循环上述步骤，直到当前 head 的检查与审查闭环或出现需要用户决策的真实阻塞。
