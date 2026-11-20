# Documentation index

Socrat is a learn-anything engine: a learner types what they want to be able to do, plays
Lesson 0, and the engine generates a course for them. Docs from the earlier fixed-course
product (DSA, CP, Zero syllabi, v1 requirements, milestone reports, old audits and redesign
screenshots) were removed on 2026-11-20; they remain in git history.

## Start here

- [Handoff](implementation/HANDOFF.md): owner's rules, environment quirks, what is built, how to commit
- [Universal engine plan](implementation/universal-engine-plan.md): strategy, phases, progress log
- [Engine README](engine/README.md): how a request becomes a course, how to extend it, flags
- [Onboarding → course generation handoff](implementation/onboarding-handoff.md): Lesson 0 and the contract with generation

## Product

- [Universal engine spec](product/universal-engine-spec.md)
- [Metric contract](product/metric-contract.md): outcome, funnel, quality and guardrail definitions

## Engine work in progress

- [Experience plan](implementation/experience-plan.md): calm lessons, page profiles, practice
- [Gap audit](implementation/ule-gap-audit.md) and [audit 3](implementation/universal-engine-audit-3.md)
- [Learning-style engine](implementation/learning-style-engine.md)
- [Harness and workbench](implementation/harness-and-workbench.md): deterministic capabilities
- [Visual playground](implementation/visual-playground.md)
- [Vertex AI handoff](implementation/vertex-ai-handoff.md): the Gemini provider
- [Live run log](implementation/live-run-log.md) and [load test results](implementation/load-test-results.md)

## Research

- [Duolingo teardown](research/duolingo-teardown.md) and [its plan](research/duolingo-teardown-plan.md)

## Architecture

- [ADRs](architecture/adr/): modular monolith, bounded AI, evidence and replay, execution plane, data boundaries, code editor, generated course content
- [Course generation](architecture/course-generation.md)
- [API conventions](architecture/api-conventions.md)
- [OCI staging cost plan](architecture/oci-staging-cost-plan.md)

## Design

- [Design system](redesign/DESIGN-SYSTEM.md): the notebook brand

## Operations and security

- [Oracle deploy](operations/oracle-deploy.md), [API/worker split](operations/api-worker-split.md),
  [staging runbook](operations/m1-staging-runbook.md), [account setup](operations/m1-account-setup.md)
- [Threat model](security/threat-model.md), [execution threat model](security/execution-threat-model.md), [data map](security/m10-data-map.md)
