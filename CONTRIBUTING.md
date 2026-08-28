# Contributing to nest-boot/skills

Thank you for improving the guidance used by Nest Boot agents. Contributions should be based on a real, reproducible development problem and remain useful across projects.

## Choose the correct repository

- Change this repository when a skill is missing an important decision, contains outdated or incorrect guidance, triggers incorrectly, or needs a reusable example/reference.
- Report framework runtime, type, public API, generation, or official documentation defects to [nest-boot/nest-boot](https://github.com/nest-boot/nest-boot).
- Keep organization-specific naming, directory layout, deployment, and private wrapper conventions in the consuming project.
- Follow [SECURITY.md](SECURITY.md) instead of opening a public Issue for suspected vulnerabilities or sensitive data exposure.

## Prepare a contribution

1. Search open and closed Issues and PRs for the skill name and symptom.
2. Capture a sanitized example showing what the agent did, what it should have done, and the evidence supporting the correction.
3. Work from an up-to-date `main` on a dedicated branch. Preserve unrelated changes and never push directly to `main`.
4. Use the project-installed `skill-creator` from `xudongcc/skills` when creating or substantially restructuring a skill.

Python validation requires [PyYAML](https://pyyaml.org/). Install it in your preferred virtual environment if it is not already available.

## Skill requirements

- Store each skill in `skills/<skill-name>/` with a matching `name` in `SKILL.md` frontmatter.
- Put all trigger conditions in the frontmatter `description`; keep the body focused on non-obvious execution guidance.
- Keep `SKILL.md` concise and link every reference directly from it.
- Add or update `evals/evals.json` for every behavioral rule, bug fix, or trigger change. Use realistic prompts and observable expectations.
- Do not add project names, customer data, credentials, private URLs, production logs, or speculative rules.
- Do not edit the generated Skills table in `README.md` by hand.

## Validate locally

Run from the repository root:

```bash
python3 skills/nest-boot-skill-maintainer/scripts/update_readme.py --repo .
python3 skills/nest-boot-skill-maintainer/scripts/validate_skills.py --repo .
```

Validate the changed skill with the project-installed validator:

```bash
python3 .agents/skills/skill-creator/scripts/quick_validate.py skills/<skill-name>
```

This repository exposes `nest-boot-skill-maintainer` to agents through a tracked relative symbolic link. When changing it, verify that the link still points to the source directory:

```bash
test -L .agents/skills/nest-boot-skill-maintainer
test "$(readlink .agents/skills/nest-boot-skill-maintainer)" = "../../skills/nest-boot-skill-maintainer"
test -f .agents/skills/nest-boot-skill-maintainer/SKILL.md
```

Before submitting, also run:

```bash
git diff --check
git status --short
```

Review the diff for unrelated formatting, generated caches, secrets, and README drift.

## Issues and pull requests

Use the GitHub Issue forms and include the affected skill, a sanitized reproduction, expected behavior, evidence, and why the change generalizes beyond one project.

A pull request should contain:

- a concise summary and the real failure it prevents;
- the changed skill/reference and corresponding eval;
- every validation command actually run and its result;
- scope intentionally excluded from the contribution.

Use a focused title such as `fix(graphql): correct connection lookup guidance` or `feat: add nest boot maintainer skill`. A candidate incubated and evaluated in a consuming project should open an Issue containing that evidence and link the implementation PR with `Fixes #...` or `Refs #...`. A small, self-contained fix made directly in this upstream repository does not require a duplicate Issue.

Agents may prepare diagnostics, branches, and draft content, but must not create an Issue, push a branch, or open a PR without explicit user authorization. They must return the resulting URL and commit SHA after an authorized submission.
