---
name: project-reference
description: Central index skill for locating project files, documentation, and routing requests to the right project-specific skills.
---

# Project Reference

Use this skill to locate files, documentation, and relevant skills within this repository. Acts as the project-level router: if a user asks "where is X" or "how is Y implemented", return exact paths and recommended next steps or delegate to a more specific skill.

## Start Here
- When the user asks for code locations, docs, or project-specific references.
- When onboarding new contributors who need a guide to the repository layout.

## Capabilities
- Map conceptual queries to files and skills. Examples:
  - "Where is the JWT validation code?" → `lib/jwt-validate.ts`
  - "How are API routes organized?" → `app/api/*`
  - "Where's the Convex schema?" → `convex/schema.ts` and `.agents/skills/convex/` guidance
  - "Where is authentication configured?" → `lib/auth.ts`, `convex/auth.config.ts`, `.agents/skills/convex-setup-auth/`
  - "Where is the UI design system?" → `documentations/documentations/04-UI_DESIGN_SYSTEM.md`, `app/globals.css`
  - "How are components styled?" → Hybrid CSS Modules (`styles/*.module.css`) + Tailwind v4 via `cn()` utility
  - "Where is the toast system?" → `ui/notifications/`, `ui/primitives/toast.tsx`
  - "How are error pages handled?" → `exceptions/errorPages/`
  - "Where is the FittedImage component?" → `components/shared/FittedImage.tsx`
  - "How is the cards grid implemented?" → `components/adventures/cards/`, `styles/cards/`
- Suggest best next skill to run (e.g., `assessment`, `convex-performance-audit`, `neon-postgres`).

## Local Index (useful paths)
### Documentation
- `documentations/README.md` — Index of all docs
- `documentations/documentations/01-ARCHITECTURE.md` — System architecture
- `documentations/documentations/02-AUTHENTICATION.md` — Auth + JWT
- `documentations/documentations/03-DATA_FLOW.md` — Request/response flows
- `documentations/documentations/04-UI_DESIGN_SYSTEM.md` — UI tokens, styling, components
- `documentations/guides/01-JWT_SETUP.md` — JWT setup guide
- `documentations/guides/02-API_IMPLEMENTATION.md` — API route guide

### UI / Styling
- `app/globals.css` — Design tokens (@theme), utilities, animations
- `styles/*.module.css` — All CSS module files (pages, layout, cards, forms, sidebar, auth)
- `lib/utils.ts` — `cn()` function (clsx + tailwind-merge)
- `ui/primitives/` — Base components (button, card, input, textarea, label, toast, error-page-shell)
- `ui/notifications/` — Toast system (use-toast, toaster)
- `components/shared/FittedImage.tsx` — Image component with fixed container + object-fit

### Components
- `components/background/slidebar.tsx` — Main sidebar (sticky, glass, collapsible)
- `components/background/sidebar/sidebar.tsx` — Sidebar wrapper (passes nav items)
- `components/adventures/cards/cards.tsx` — Individual card component
- `components/adventures/cards/cards-grid.tsx` — Masonry column grid with infinite scroll
- `components/adventures/cards/cards-grid-wrapper.tsx` — Server wrapper
- `components/adventures/form/form.tsx` — Game creation form
- `components/game/GameHeader.tsx` — Game detail hero header
- `components/game/CharacterTabs.tsx` — Character display grid
- `components/game/MapList.tsx` — Map list with details
- `components/game/ItemGrid.tsx` — Item grid display
- `components/authentication/unauthenticated.tsx` — Auth overlay
- `components/authentication/auth-status.tsx` — Auth loading/signin/signup status

### Error / Notification
- `exceptions/errorPages/` — Importable error components (404, 500, 403, 503, 400, general)
- `exceptions/notifications/success.tsx` — Success notification (toast + inline modes)
- `types/errorHandler.ts` — Error handler types (ErrorCategory, ClassifiedError, ExceptionResult, ExceptionOptions, ComponentMapping, etc.)
- `utilities/errorHandler.ts` — Pure utility functions:
  - `tryOrError()` — wraps async functions, auto-classifies errors, returns component + toast
  - `classifyError()` — parses any thrown value into ErrorCategory (network, auth, timeout, HTTP status, etc.)
  - `mapToComponent()` — maps category to the right ErrorPage component with props
  - `showToastFor()` — fires error/warning toast based on severity
  - `handleApiResponse()` — checks response.ok, auto-classifies HTTP errors
  - `tryFetch()` — fetch wrapper with full exception handling
  - `classifyAndFormat()` — classifies + formats Zod errors
  - `createApiErrorHandler()` — factory for scoped error handling
- `exceptions/errors/exceptions.ts` — React hook + barrel re-exports:
  - `useErrorHandler()` — React hook with stateful error tracking
  - Re-exports all utilities from `utilities/errorHandler.ts` and types from `types/errorHandler.ts`

### Backend
- `app/api/` — All API routes
- `lib/auth.ts` — Auth utilities
- `lib/db.ts` — DB query functions
- `lib/GamesInsert.ts` — MongoDB game processor
- `lib/storage.ts` — Supabase storage
- `lib/cache-warmup.ts` — Cache warming
- `db/client.ts` — Neon client
- `models/games/mongodb/client.ts` — MongoDB client
- `hooks/useIdempotentRequest.ts` — Idempotent API requests
- `utilities/idempotency.ts` — Redis idempotency
- `utilities/imagesUtils.ts` — Image upload utilities
- `utilities/insertGameImages.ts` — Batch image upload

## Usage
```yaml
skill: project-reference
action: locate
query: "ui card layout"
repoPath: "."
```

## Outputs
- filePaths: list of relevant file paths
- delegateSkill: recommended skill name (optional)
- short rationale

## When Not to Use
- For external dependency lookups (use `references` skill)
- For deep code changes — delegate to an implementation skill or open a PR

## Implementation Notes
- Prefer exact paths over loose descriptions.
- When in doubt, return multiple candidate paths and recommend the most likely one.
