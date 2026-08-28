---
name: nest-boot-skill-maintainer
description: 在 Nest Boot 消费项目或 `nest-boot/skills` 仓库中维护和改进 agent skills。适用于直接修改项目已安装的 `.agents/skills` 副本并自评估、把成熟改进泛化后提交上游 issue 与 PR、新增或重组 skill、调整触发描述与 eval、处理拆分重命名迁移、同步合并后的正式版本以及闭环 CI 和审查；框架 BUG 或公开 API 改进应改用 `nest-boot-maintainer`，项目私有约定或未经验证的猜测不应上游化。
---

# Nest Boot Skill Maintainer

## 目标与运行位置

把真实开发问题转化为可复用、可验证的 skill 改进，同时允许改进先在消费项目中孵化，再以脱敏、通用的形式进入 `nest-boot/skills`。

先识别当前宿主和候选版本的位置：

- **消费项目模式**：可以直接修改已安装的 `.agents/skills/<name>/`，把它作为本地候选版本持续自改进和自评估。开始前保存原始版本与完整 `skills-lock.json`；lockfile 不存在时保存明确的 absence marker，便于建立 baseline 和生成上游 diff。不要手工伪造 lockfile 来源。
- **上游仓库模式**：在 `nest-boot/skills` 的专用分支中直接修改 `skills/<name>/`。这里的目录是正式上游源码，不需要先修改 `.agents/skills` 安装副本。

无论候选版本在哪里，每轮先冻结候选与 baseline 快照，再为每个 eval run 把对应快照**复制**到一次性执行根目录的 `.agents/skills/<name>/`，不要使用软链接。记录快照哈希并检查复制后的 skill 树不含软链接，避免并行 run 读取变化中的候选或反向修改候选版本。

## 维护流程

1. **诊断并路由问题**：记录观察结果、期望行为、最小复现、版本、根因和验证命令。按 [Issue 与仓库路由](references/issue-routing.md) 区分 skill 缺口、框架缺陷、依赖问题和项目私有问题；框架 BUG 或公开 API 改进改用 `$nest-boot-maintainer`。
2. **读取实际版本与上游版本**：在消费项目中先读取触发问题的安装副本，并记录它与当前上游版本是否存在差异；在上游仓库中读取目标 `SKILL.md`、相关 reference 和 eval。不要把旧安装版本误当成最新上游行为。
3. **建立本地基线**：改进已有 skill 时，在首次编辑前保存完整原始快照和完整 lockfile 状态。新增 skill 的 baseline 是不安装该 skill；已有 skill 的 baseline 可以是原始版本或上一轮稳定版本，但同一轮 paired runs 必须固定并可由哈希复核。
4. **设计并迭代候选版本**：新增或大幅重组时使用项目安装的 `skill-creator`。将失败案例泛化为触发条件、决策规则、反例和可观察验证，删除项目名、客户数据、内部 URL、凭证和临时 workaround。同步新增或修改真实 eval。
5. **隔离自评估**：触发测试可使用空白 fixture；依赖框架行为时使用消费项目的临时 worktree、最小复现项目或其他可丢弃副本。为 with-skill 与 baseline 复制相同 commit、依赖锁、项目输入和配置，再分别复制本轮不可变的候选与基线快照；保持模型、提示、权限、准备/验证命令和 run 数一致。使用 `skill-creator` 的 grader、benchmark 和 review viewer 汇总结果。
6. **通过质量门槛**：至少确认目标失败已被新版本预防、关键 expectations 有证据、候选优于或不劣于 baseline、相关回归未出现，并处理用户 review 反馈。结构校验通过不能替代语义评估。
7. **决定是否上游化**：项目私有规则留在本地。消费项目中孵化成熟且可泛化的改进，应准备一个记录问题、证据和本地评估结果的上游 issue，并提交关联 PR；直接在上游仓库完成的小型明确修复可以只提交自解释 PR，范围或设计未决时先 issue。
8. **移植到上游源码**：从消费项目上游化时，定位或创建干净的 `nest-boot/skills` checkout，在专用分支把本地候选相对原始快照的通用改动移植到 `skills/<name>/`。不要把业务代码、项目数据、生成 workspace 或整个安装目录未经审查地复制进上游。
9. **验证上游变更**：按 [贡献工作流](references/contribution-workflow.md) 运行目标 skill 的 quick validator、相关测试或行为探针、README 生成器和全仓校验器，并人工审查完整 diff。
10. **执行获授权的外部操作**：创建 issue、推送分支、提交 PR 或合并都需要用户明确授权。提交后返回链接和 commit SHA；安全漏洞、凭证或可利用细节改走私密安全渠道。
11. **闭环审查**：分别保存 issue URL/number、PR URL/number、当前 PR head SHA 和合并 commit，不要混用这些标识。所有 PR 查询与 inline thread 查询使用 PR URL 或 PR number；每次 push 后重新读取 head SHA，再检查 CI、普通评论、reviews 和 inline threads。旧提交的 clean 结果不能覆盖新提交。
12. **合并后回同步消费项目**：确认 merge commit 已进入上游默认分支后，只有得到该消费项目的授权才运行官方 add/update/remove 命令。正式版本会替换本地候选；将安装内容与该默认分支中的已合并 skill 对照，并验证 `skills-lock.json`、旧名称清理和关键场景，确保项目使用已合并版本而非陈旧安装或遗留本地分叉。
13. **交付证据**：报告宿主模式、候选与 baseline、修改的 skill/reference/eval、评估和确定性验证结果、issue/PR 状态，以及有意排除的项目私有内容。

## 自维护边界

- 本 skill 自身出现具体失败时，按同一流程建立 baseline、修改和评估；不要在没有失败证据时递归“自动优化”。
- 本地孵化只修改用户置于范围内的安装副本，不后台扫描其他项目，也不自动创建 issue 或 PR。
- 本地候选允许暂时偏离 lockfile 指向的上游内容，但不得把这种漂移冒充正式发布版本；合并后必须通过官方命令回同步。
- 结构化 `autoreview` 只在用户明确要求时使用，并且不能代替真实代码路径、框架行为和 eval 证据。
- 不把单个失败案例写成无条件规则。优先说明适用条件和原因，让其他 Agent 能根据宿主项目判断。

## 贡献细节

- 本地孵化、上游分支、issue、PR、迁移和审查细节见 [贡献工作流](references/contribution-workflow.md)。
- 判断问题所有权和本地候选是否值得上游化时读 [Issue 与仓库路由](references/issue-routing.md)。
- `scripts/update_readme.py` 根据所有 `SKILL.md` frontmatter 重建 README Skills 表格；使用 `--check` 只检查漂移。
- `scripts/validate_skills.py` 检查目录、frontmatter、references、eval、README 和 Markdown 基础质量。
