---
name: self-assessment
description: Enhanced entry point for full project + team self-assessment. Orchestrates personality profiling, technical architecture review, UI architecture review, security audit, performance tuning, and outputs a prioritized remediation plan.
---

# Self-Assessment (Enhanced)

This skill runs a comprehensive, multi-phase assessment of a project and its context, combining "who you are" (personality/team context) with "what you build" (architecture, UI, security, performance). Use this as the single entry point for audits, health checks, growth plans, or onboarding reviews.

## When to Use
- Full project audit (security, performance, UI, architecture)
- Team and personality-contextual reviews (leadership, handoffs, strengths)
- Produce a prioritized remediation plan and PR-ready action items
- Onboarding new contributors to map responsibilities and technical debt

## Phases
1. Personality & team context — delegate to `personality-references` (profiles, strengths, risks)
2. Technical architecture review — analyze repo layout, services, data flows, scaling & critical paths
3. UI & frontend review — evaluate component architecture, rendering strategy, accessibility and UX debt
4. Security assessment — checklist-driven audit (auth, secrets, CORS, input validation, rate limiting)
5. Performance audit — DB tuning, cache strategy, worker reliability, query hotspots
6. Cross-reference & prioritize — consolidate findings into a risk matrix and prioritized remediation list with estimated effort
7. Deliverables — produce YAML/Markdown report, suggested PRs, tests and reproduction steps

## Inputs
- repo: local path or git URL (required)
- focus: optional array (e.g., ["security","performance","ui"]) — default: full
- depth: quick | full (default: full)
- env: optional deployment environment (dev|staging|prod)
- contact: optional maintainer or team context

## Outputs
- Structured YAML/Markdown report containing:
  - Executive summary
  - Findings (grouped by phase)
  - Risk matrix (severity, likelihood, impact)
  - Prioritized remediation list with estimated effort and PR suggestions
  - Reproduction commands, tests, and CI checks

## Sub-skills & Delegation
Use the most specific skill available for each phase; this skill orchestrates them:
- personality-references — personality profiling
- Architicture-refrences/technical-architecture-analysis — backend architecture
- Architicture-refrences/UI-architecture-analysis — frontend/UI review
- convex-performance-audit — performance analysis for Convex-backed flows
- neon-postgres — Postgres/Neon analysis and tuning
- convex-migration-helper — safe schema changes and migrations
- convex-setup-auth — auth-specific checks and best practices
- integration-nextjs-app-router — Next.js app-router integration checks
- deploymentChecks — infra, deployment, and environment checks
- references — authoritative docs and local document links

## Usage Example
```yaml
skill: self-assessment
action: run
repo: "."                   # or git url
focus: ["security","performance"]
depth: full
env: staging
```

## Implementation Notes for Skill Authors
- Run read-only analysis by default; ask for explicit permission before making changes.
- Produce small, actionable PRs for each remediation item with tests and a clear diff.
- Include commands and config snippets to reproduce performance findings (explain exact queries / load profile).
- When reporting security issues, include severity, exploitability, and remediation steps.
- Prefer automated checks (linting, zod schemas, tests) when suggesting fixes.

## Deliverable Checklist
- Executive summary (1–3 bullets)
- Top 5 findings (with severity and estimated effort)
- Risk matrix and short-term/long-term roadmap
- PR templates for critical fixes
- Suggested tests and CI checks

## When NOT to Use
- For tiny one-file fixes or simple code questions — use language- or file-specific skills
- For clinical or HR usage of personality outputs

## Backwards Compatibility / Migration
- The old `assessment` skill is kept for compatibility but now delegates to `self-assessment`. Prefer calling `self-assessment` directly.

## References (local)
- documentations/README.md
- documentations/documentations/01-ARCHITECTURE.md
- documentations/problems/01-SECURITY_VULNERABILITIES.md
- .agents/skills/references/Skill.md

## Example Output (YAML snippet)
```yaml
summary: "Critical auth misconfiguration and N+1 queries causing latency"
findings:
  - id: auth-01
    severity: high
    description: "Clerk JWT secret not set in production env"
    remediation: "Add secret to secret manager and rotate"
  - id: perf-02
    severity: medium
    description: "N+1 queries in game list endpoint"
    remediation: "Batch queries; add DB index"
priority: [auth-01, perf-02]
```
