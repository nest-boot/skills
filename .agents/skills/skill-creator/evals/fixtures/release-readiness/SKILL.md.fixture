---
name: release-readiness
description: Review a service release for rollout readiness, compatibility risks, operational checks, and rollback evidence. Use when preparing or auditing a production deployment plan, canary rollout, worker transition, or database-backed release.
---

# Release Readiness

Build a release decision from evidence rather than a generic checklist.

1. Identify the currently deployed version, candidate version, dependency and schema changes, worker or queue compatibility, and the user-visible risk.
2. Separate pre-deploy checks, rollout stages, live health signals, stop conditions, rollback actions, and post-rollback verification.
3. Require a compatibility plan whenever old and new application or worker versions can coexist.
4. Tie every go/no-go decision to an observable command, metric, query, or test result. Mark missing evidence instead of assuming success.
5. Keep rollback executable: state who initiates it, what is reverted, what cannot be reversed, and how recovery is verified.

Return a concise readiness report with `Risks`, `Required evidence`, `Rollout`, `Stop conditions`, `Rollback`, and `Decision` sections.
