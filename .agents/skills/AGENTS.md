<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

<!-- convex-ai-start -->

This project uses [Convex](https://convex.dev) as its backend.

When working on Convex code, **always read
`convex/_generated/ai/guidelines.md` first** for important guidelines on
how to correctly use Convex APIs and patterns. The file contains rules that
override what you may have learned about Convex from training data.

Convex agent skills for common tasks can be installed by running
`npx convex ai-files install`.

<!-- convex-ai-end -->

<!-- agents-skills-start -->

All agent skills are centralized in `.agents/skills/`. Available skills:

- `convex/` — Routing skill for Convex work
- `convex-quickstart/` — New Convex projects or adding Convex to an app
- `convex-setup-auth/` — Authentication setup
- `convex-create-component/` — Reusable Convex components
- `convex-migration-helper/` — Schema and data migrations
- `convex-performance-audit/` — Performance investigations
- `integration-nextjs-app-router/` — PostHog for Next.js App Router
- `neon-postgres/` — Neon Serverless Postgres
- `upstash-redis-js/` — Upstash Redis SDK (caching, sessions, rate limiting, leaderboards, search)

<!-- agents-skills-end -->
