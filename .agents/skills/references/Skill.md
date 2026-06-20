---
name: references
description: Centralized reference skill providing links to internal docs and authoritative external documentation (Convex, Neon, Clerk, Supabase, Next.js, MongoDB, Redis, etc.).
---

# References

This skill provides canonical links and short descriptions for technologies and project-specific doc locations. Use it when a user asks "Where is the official docs for X?" or "Give me reference links for Y".

## Local References
- documentations/README.md — project documentation index
- documentations/documentations/01-ARCHITECTURE.md — architecture overview
- documentations/guides/01-JWT_SETUP.md — JWT setup guide
- .agents/skills/* — built-in agent skills and references
- convex/_generated/ai/guidelines.md — Convex project guidelines

## External References
- Convex: https://docs.convex.dev/ai
- Neon (Postgres): https://neon.tech/docs
- Clerk: https://docs.clerk.dev/
- Supabase: https://supabase.com/docs
- Next.js: https://nextjs.org/docs
- MongoDB: https://www.mongodb.com/docs/
- Mongoose: https://mongoosejs.com/docs/
- Redis (ioredis): https://github.com/luin/ioredis
- PostgreSQL docs: https://www.postgresql.org/docs/
- Vercel: https://vercel.com/docs
- Sentry: https://docs.sentry.io/

## Usage
```yaml
skill: references
action: get
topic: "clerk jwt"  # or "convex", "neon", "nextjs" etc.
```

## Outputs
- links: array of { title, url, shortDescription }
- localPaths: array of local files to consult

## When Not to Use
- For local code search — use `project-reference` skill

## Implementation Notes
- Keep lists up-to-date when project dependencies change
- Prefer official docs and trusted community guides
- For slow-changing references, store a short cached copy locally in `.agents/skills/references/` `assets/` if needed
