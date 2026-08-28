## Summary

- What reusable guidance changed?
- Which skill, reference, or eval is affected?

## Problem and evidence

Describe the real development failure this prevents. Link sanitized reproduction evidence, framework source/tests, or official documentation.

## Validation

- [ ] Updated or added a realistic eval
- [ ] Ran `python3 skills/nest-boot-skill-maintainer/scripts/update_readme.py --repo .`
- [ ] Ran `python3 skills/nest-boot-skill-maintainer/scripts/validate_skills.py --repo .`
- [ ] Ran project-installed `quick_validate.py` for every changed skill
- [ ] Ran `git diff --check`

List command results and explain any check that was not run.

## Scope

State project-specific behavior, framework changes, or follow-up work intentionally excluded from this PR.

## Safety

- [ ] The diff contains no credentials, customer data, private URLs, production logs, or generated caches
- [ ] This is a skill change; framework bugs are routed to `nest-boot/nest-boot`
