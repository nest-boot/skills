---
name: nest-boot-skill-maintainer
description: 将 Nest Boot 项目开发中发现的可复用指引缺口转化为 `nest-boot/skills` 中的 skill 新增、修订、拆分、重命名、迁移、eval、GitHub issue 或 PR，并闭环语义验证、CI 与审查。适用于总结开发经验、调整 skill 边界或触发描述、处理已发布 skill 的升级路径、响应 PR 建议以及维护 skills 仓库；框架 BUG 或公开 API 改进应改用 `nest-boot-maintainer`，项目私有约定或未经验证的猜测不应进入上游 skill。
---

# Nest Boot Skill Maintainer

## 目标

把业务项目中的真实问题沉淀为可复用、可验证的上游改进，同时避免把项目私有命名、临时 workaround、凭证或未经证实的偏好扩散到所有使用者。

修改上游 `nest-boot/skills` 仓库，而不是业务项目中的 `.agents/skills/` 安装副本。同名内容更新通过官方安装工具分发；拆分、重命名或删除已发布 skill 时，必须先验证当前工具的更新行为并提供显式迁移路径。直接编辑安装副本会造成来源漂移并可能在下次更新时丢失。

## 维护流程

1. **先解决并验证原问题**：记录观察结果、期望行为、最小复现、根因和验证命令。只有能解释“现有 skill 为什么没有预防该问题”时，才进入上游维护。
2. **读取受影响的领域 skill**：检查其 `SKILL.md`、相关 reference 和 eval；必要时对照 `nest-boot/nest-boot` 的源码、测试或正式文档，不从单个项目实现推导框架通用规则。
3. **判断归属**：按 [Issue 与仓库路由](references/issue-routing.md) 区分 skill 缺口、框架缺陷、依赖问题和项目私有问题。框架 BUG 或公开 API 改进改用 `$nest-boot-maintainer`；归属不清时继续诊断，不要猜测性修改多个仓库。
4. **设计 skill 边界**：新增或大幅重组时使用项目安装的 `skill-creator`。让一个 skill 对应一个主要开发任务；工作流、产物或完成条件明显不同则拆分并交叉路由。框架中立能力只有在本仓库是合理所有者时才保留中立名称。
5. **提炼通用规则**：删除项目名、客户数据、内部 URL、凭证和无关上下文。保留触发条件、决策标准、反例、正确做法与可观察验证。
6. **选择 issue 或 PR**：对 `nest-boot/skills` 的明确修复直接提交带 eval 的 PR；需要维护者确认规则、范围或触发策略时先提交 issue。一个自解释 PR 不需要为了流程额外创建空洞 issue。
7. **在上游分支修改**：检查工作区和远程状态，保留用户已有改动，从最新默认分支创建专用分支。不要直接推送 `main`，也不要覆盖不属于本任务的文件。
8. **保持最小改动**：更新最相关的 `SKILL.md` 或 reference；新增规则、触发变化或迁移行为时同步新增或修改至少一个真实 eval。若修改 frontmatter description，重新生成 README。
9. **验证语义与结构**：版本敏感或工具相关的规则要用官方源码/文档和最小行为探针验证；结构校验器、CI 或自动 reviewer 不能证明指引本身正确。随后在仓库根目录执行：

   ```bash
   python3 skills/nest-boot-skill-maintainer/scripts/update_readme.py --repo .
   python3 skills/nest-boot-skill-maintainer/scripts/validate_skills.py --repo .
   ```

10. **设计发布迁移**：已发布 skill 被拆分、重命名或删除时，检查锁文件与当前安装工具行为，提供 remove/add 或兼容窗口，并确保旧、新 skill 不会长期重叠触发。上游合并后，只有得到消费项目授权才执行安装迁移。
11. **提交外部变更**：只有用户明确要求创建 issue、推送分支或提交 PR 时才执行相应外部写操作。用户在当前请求中明确说“提交 issue/PR”即构成授权；目标仓库、公开范围或敏感性不清时先停下确认。
12. **闭环 PR 审查**：用户要求在线审查或合并时，等待 CI 与 reviewer 回执，检查普通评论、review 和 inline thread，并确认审查覆盖当前 head SHA。修复后重新验证、推送和审查最新提交；只有用户授权且不存在未解决项时才合并。
13. **交付证据**：报告根因、修改的 skill/eval、语义与确定性验证结果，以及 issue/PR 链接和最终状态。说明哪些项目细节被有意排除，方便维护者判断泛化是否合理。

## 自维护边界

- 本 skill 自身出现缺口时，像维护其他 skill 一样更新它并增加 eval；不要在没有具体失败证据时进行递归“自动优化”。
- 不在后台自动扫描项目、创建 issue 或发起 PR。维护由具体开发发现或用户请求触发。
- 结构化 `autoreview` 只在用户明确要求时使用；无论是否使用，都要人工验证关键规则与真实工具行为。
- 不把一个失败案例写成无条件规则。优先解释适用条件和原因，让其他 Agent 能根据宿主项目作出判断。
- 安全漏洞、凭证泄漏或可利用细节不得提交公开 issue；停止公开发布流程并使用仓库维护者提供的私密安全渠道。

## 贡献细节

- 准备分支、issue 和 PR 内容时阅读 [贡献工作流](references/contribution-workflow.md)。
- 判断应修改哪个仓库、是否值得上游化时阅读 [Issue 与仓库路由](references/issue-routing.md)。
- `scripts/update_readme.py` 根据所有 `SKILL.md` frontmatter 重建 README Skills 表格；使用 `--check` 仅检查漂移。
- `scripts/validate_skills.py` 检查目录、frontmatter、references、eval、README 和 Markdown 基础质量。
