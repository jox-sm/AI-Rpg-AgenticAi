---
name: assesment
description: Combined personality + project architecture assessment. Analyzes the user's personality (MBTI, Enneagram, shadow, grip, dark side) — then reviews the project's technical architecture and UI architecture — and cross-references findings for actionable growth recommendations.
---

# Full Self Assessment

A unified assessment that connects **who you are** (personality profile) with **what you build** (project architecture). It uses the personality-references skill for psychological profiling and the architecture-references (technical + UI) for project analysis, then cross-references both to find patterns, blind spots, and growth opportunities.

---

## Step 1: Personality Analysis

Run the personality-references five-lens framework to produce a full profile.

### Input

The user provides their MBTI type, Enneagram (if known), or answers to determine them.

### Output

```yaml
personality:
  core_type: <MBTI>
  cognitive_stack: [dominant, auxiliary, tertiary, inferior]
  enneagram: <type + wing>
  core_fear: <enneagram fear>
  core_desire: <enneagram desire>
  grip_state: <inferior function grip behavior>
  shadow_functions: [opposing, senex, trickster, demonic]
  dark_side_expression: <pathological pattern>

strengths:
  - <strength 1 tied to dominant/auxiliary functions>
  - <strength 2 tied to dominant/auxiliary functions>
  - <strength 3 tied to Enneagram motivation>

weaknesses:
  - <weakness 1 tied to inferior/tertiary functions>
  - <weakness 2 tied to shadow functions>
  - <weakness 3 tied to grip state / dark side>
```

### How Strengths & Weaknesses are Derived

| Source | Strength Example | Weakness Example |
|--------|-----------------|------------------|
| **Dominant Function** | Natural talent, effortless skill | Over-reliance, imbalance |
| **Auxiliary Function** | Supporting strength, good backup | Can be neglected under stress |
| **Tertiary Function** | Fun, hobby-level skill | Immature expression, casual use |
| **Inferior Function** | Growth edge when developed | Grip trigger, blind spot |
| **Shadow Functions** | Hidden potential for integration | Defensive/regressive behavior |
| **Enneagram Core** | Deep motivation, passion | Fixation, core fear reaction |
| **Dark Side** | — | Pathological tipping point |

---

## Step 2: Project Architecture Review

### 2a. Technical Architecture Analysis

Run the technical-architecture-reference skill to audit the project.

**Dimensions assessed:**
- **Routing & Structure** — App Router page hierarchy, API route organization, middleware
- **Data Flow** — Pipeline clarity, caching strategy, queue architecture, database layering
- **Code Organization** — Module boundaries, dependency direction, separation of concerns
- **Error Handling** — Retry patterns, failure isolation, observability
- **Scaling Readiness** — What breaks at 100 / 1,000 / 10,000 concurrent users

### 2b. UI Architecture Analysis

Run the UI-architecture-analysis skill to audit the frontend.

**Dimensions assessed:**
- **Layout System** — 8px grid adherence, responsive breakpoints, container usage
- **Component Architecture** — Composition patterns, coupling, reusability
- **State Management** — State ownership, data flow, prop drilling depth
- **Design System Maturity** — Token usage, primitive consistency, documentation
- **Rendering Strategy** — SSR/CSR/RSC split, component boundaries
- **Accessibility** — Semantic HTML, keyboard nav, ARIA, focus management

### Output

```yaml
project_architecture:
  technical:
    routing:
      structure: <app router organization overview>
      api_routes: <list of routes and their responsibilities>
      middleware: <auth/redirect logic>
    data_flow:
      pipeline: <key data pipelines>
      caching: <strategy and gaps>
      queue: <queue architecture>
      databases: <role of each database>
    code_quality:
      module_boundaries: <clean or crossing>
      error_handling: <strengths and gaps>
      naming: <naming conventions>
    scaling_analysis:
      at_100_users: <verdict>
      at_1000_users: <verdict>
      at_10000_users: <verdict>

  ui:
    layout_system:
      grid: <8px grid usage assessment>
      responsiveness: <breakpoint handling>
    component_architecture:
      pattern: <atomic, compound, etc.>
      coupling: <tight or loose>
      reusability: <component reuse assessment>
    state_management:
      pattern: <local, context, server state, etc.>
      prop_drilling: <depth assessment>
    design_system:
      level: <0–4>
      consistency: <token usage, primitives>
    rendering:
      strategy: <SSR/CSR/RSC split>
      performance: <budgets, code splitting>
    accessibility:
      level: <A/AA/AAA>
      gaps: <missing patterns>
```

---

## Step 3: Cross-Reference — Personality × Architecture

Map personality traits to architectural findings. This reveals:

| Pattern | What It Means |
|---------|---------------|
| **Dominant function matches architecture strength** | You built what comes naturally — it is solid. |
| **Inferior function appears in architecture gap** | The area you avoid is visible in the code. |
| **Shadow function in project weakness** | A blind spot you have as a person shows up as a project risk. |
| **Grip state stresses = architecture fragility** | Under pressure, you make architectural decisions that create debt. |
| **Enneagram core desire = project ambition** | Your deep motivation drives what the project does well. |
| **Enneagram core fear = project omission** | What you avoid personally is often missing from the project. |

### Output

```yaml
cross_reference:
  strengths_aligned:
    - <personality strength → architectural strength>
    - <personality strength → UI strength>
  blind_spots:
    - <personality weakness → architectural gap>
    - <personality weakness → UI gap>
  stress_indicators:
    - <grip state trigger → code debt pattern>
  growth_path:
    - <shadow integration → project improvement>
    - <inferior development → project improvement>
```

---

## Complete Example

### Given: User is ENTP 7w8, Project is Deepslate Dungeons

```yaml
personality:
  core_type: ENTP
  cognitive_stack: [Ne (dominant), Ti (auxiliary), Fe (tertiary), Si (inferior)]
  enneagram: "7w8 — The Visionary Enthusiast"
  core_fear: Being trapped in pain or boredom
  core_desire: Satisfaction, freedom, new possibilities
  grip_state: Si grip — rumination, catastrophizing, rigid routines, dwelling on past mistakes
  shadow_functions: [Ni (opposing), Te (senex), Fi (trickster), Se (demonic)]
  dark_side_expression: Gaslighting through debate,逃避 responsibility, avoiding emotional depth, over-promising

strengths:
  - Visionary system design (Ne dom): Sees the whole pipeline before writing code — designed a multi-database ingestion pipeline from client → Redis → PostgreSQL → MongoDB without hesitation
  - Logical architecture rigor (Ti aux): Caching strategy with warmup, TTL, cache-aside pattern, sorted sets for pagination — well-reasoned
  - High-iteration prototyping (Ne + 7): Built a full wizard form, three databases, image pipeline, and infinite scroll in one project — moves fast

weaknesses:
  - Neglected backend fundamentals (inferior Si): Authentication is incomplete, middleware not registered, no tests, no rate limiting, no input sanitization beyond basic pattern check
  - Potential consistency challenges: Eventual consistency across systems requires careful handling
  - Operational complexity overhead: More services to monitor, debug, and maintain
   
  Note: This architecture represents an intentional cost-optimization strategy rather than unconscious over-engineering. The user has selected services based on their specific strengths within free tiers:
  - Redis: Efficient queue buffering and caching (low latency for high-frequency operations)
  - Neon PostgreSQL: Optimized for relational game catalog data (efficient querying, indexing)
  - MongoDB: Flexible document storage for variable game assets (handles JSON objects efficiently)
  - Supabase: Specialized media storage (optimized for blobs, CDN integration)
  - Convex: Real-time capabilities (though currently unused by frontend)
  - Clerk: Robust authentication management
  
  Alternative approaches like Redis+PostgreSQL alone would:
  1. Increase latency for complex JSON objects (MongoDB handles document storage more efficiently)
  2. Require more sophisticated schema migrations for evolving game asset structures
  3. Potentially increase costs if pushing PostgreSQL beyond its optimal use cases
  4. Limit flexibility in handling varying data structures across different game types

project_architecture:
  technical:
    routing:
      structure: >
        Clean App Router layout — root layout with Clerk+Convex+AuthGate+Sidebar.
        Home (/) uses client component for infinite scroll. Inventory (/inventory)
        uses client component for wizard form. Profile and Settings are placeholders.
        API routes organized by domain: games/, push/, convertUrl/. Sensible.
      clean_code_notes:
        positives:
          - Consistent file naming (kebab-case for files, PascalCase for components)
          - CSS Modules alongside components — good co-location
          - Architecture doc is thorough and up-to-date
        issues:
          - Layout imports sidebar from components/background/sidebar/sidebar.tsx but the file likely re-exports — check for unnecessary nesting
          - Auth-gate and convex-client-provider are in app/ — they belong in components/ or lib/
          - page.tsx is 'use client' but does not need to be — it just renders CardsGrid which is already client. Unnecessary client boundary on the page wrapper.
    data_flow:
      pipeline: >
        Game creation: User form → convertUrl (main image) → fileToBase64 (component images)
        → push to Redis queue → pull.ts batch inserts to PostgreSQL
        → convertGameImages (base64 → Supabase URLs)
        → push to MongoDB queue → processGamesQueue → MongoDB insertMany.
        This is 7 steps for "user fills form and saves." Every step is a potential failure point.
      caching: >
        Redis cache-aside with 24h TTL, sorted set for ID range, warmup on first request.
        Well-designed caching for reads. But no cache invalidation on write — after a game is
        created, the cache stays stale until 24h TTL expires.
      queue: >
        Two Redis queues with polling-based consumers (850ms sleep in pull.ts).
        Polling is fine at low scale but wastes Redis connections. No dead-letter queue —
        failed jobs are silently dropped (try/catch with console.error).
    code_quality:
      module_boundaries: >
        Clean separation: types/ for types, db/ for PG, models/ for MongoDB,
        lib/ for services, utilities/ for helpers, components/ for React.
        However, utilities/ and lib/ overlap in responsibility — utilities/db.ts
        handles Redis queue operations while lib/queue.ts holds the Redis client.
        Queue logic is split across both directories.
      error_handling: >
        retry() utility with 3 attempts + 500ms delay. API routes have try/catch
        with console.error. MongoDB insert uses { ordered: false }. But no structured
        logging, no error aggregation, no Sentry/Axiom, no user-facing error notifications.
        Silent failures in queue consumers.
      tech_debt:
        - Auth middleware functions exist but are not registered in next.config or middleware.ts
        - Two database clients for two databases but connection management is manual
        - Pull.ts uses legacy polling pattern while GamesInsert.ts uses a working-flag pattern
          — two queue processing approaches in one codebase
        - No tests at any level (unit, integration, e2e)
    scaling_analysis:
      at_100_users: >
        No issues. Single Next.js instance, PostgreSQL handles reads, Redis handles cache.
        7-step pipeline is slow but functional. Response time 200–500ms.
      at_1000_users: >
        Queue processing becomes the bottleneck. Polling-based consumers (850ms sleep)
        cannot keep up. DB connections from multiple serverless function instances
        exceed PostgreSQL connection limit. Missing connection pooler becomes critical.
        Response time 1–5s. Caching helps reads, but writes queue up fast.
      at_10000_users: >
        System collapses. Serverless functions exhaust Neon PostgreSQL connections.
        Redis queue grows unbounded — no backpressure, no rate limiting.
        MongoDB write-heavy insertMany under parallel requests causes contention.
        No auth means every request is unauthenticated — no abuse prevention.
        Response time 5s+ or timeout.

  ui:
    layout_system:
      grid: >
        Tailwind utility classes used but no consistent 8px grid system documented
        or enforced. Spacing values appear arbitrary (p-4, gap-6, mt-8 mixed with
        custom CSS Module values). No design tokens for spacing.
      responsiveness: >
        Sidebar has collapse behavior. CSS Modules for breakpoints on cards grid.
        However, no container queries, no fluid typography, no explicit breakpoint
        strategy documented. Mobile layout is not verified.
    component_architecture:
      pattern: >
        Mix of patterns. CardsGrid/CardsLoad uses composition well. Wizard form
        uses step-based rendering with conditional display. No compound components,
        no polymorphic primitives. Components are mostly presentational with
        logic mixed in.
      coupling: >
        Moderate coupling. CardsGrid imports fetch function from utilities/utils
        directly — the data source is hardcoded. Wizard components import form
        state hooks directly. Props drilled through 3–4 levels in the form.
      reusability: >
        ProfileCard is reused in CardsLoad. FormUI components (TextAreaField, etc.)
        are reusable. But many components are page-specific and tightly coupled
        to their parent.
    state_management:
      pattern: "100% local state (useState, useReducer) + prop drilling"
      prop_drilling: >
        Wizard form drills state through CreateForm → GamesFormWizard → individual
        step components. 3–4 levels of prop passing. No Context, no Zustand, no
        server state library. Adding a new field requires threading it through
        every intermediate component.
      concerns: >
        With server state (TanStack Query), the form could be simplified significantly.
        Currently manual loading/error states, manual cache management.
    design_system:
      level: 1 (tokens exist via Tailwind config but no custom semantic tokens, no component library documentation)
      consistency: >
        schadcn/ui provides primitives but custom components (FormUI, GamesFormUi)
        use inline Tailwind classes with no token abstraction. Some spacing uses
        Tailwind defaults, some uses CSS Modules with custom values.
    rendering:
      strategy: >
        Mix of SSR (layout, home page shell) and CSR (infinite scroll, wizard form).
        No RSC, no streaming, no ISR. The home page is 'use client' at page level
        when it could be a server component that renders a client island for the grid.
      performance: >
        No bundle analysis, no lazy loading beyond Next.js automatic code splitting
        by route. Image optimization via Next/Image on main cards. No virtual
        scrolling for the game catalog — would break at 1000+ games.
    accessibility:
      level: A
      gaps: >
        Semantic HTML used (nav, main, etc.) but keyboard navigation not verified,
        no ARIA live regions for dynamic content (infinite scroll loading), no skip
        links, no focus management in modals/wizard. Touch targets not measured.

cross_reference:
  strengths_aligned:
    - "ENTP visionary design → Multi-database pipeline was architected before a single line of UI was written. The data flow is well-thought-out despite being over-engineered."
    - "ENTP logical rigor (Ti) → Caching strategy (warmup + sorted set + TTL + cache-aside) is textbook correct."
    - "Enneagram 7 desire for variety → Project uses 5 different services (Neon, MongoDB, Redis, Supabase, PostHog) — keeps it interesting but adds complexity."

  blind_spots:
    - "Inferior Si (detail work) → Auth is not implemented. Middleware exists but is not registered. The boring but critical parts are incomplete."
    - "Enneagram 7 fear of boredom → No tests. Testing is repetitive and uninteresting for a 7, so it got skipped entirely."
    - "Te shadow (senex function) → No project management, no task tracking, no deadlines. The 'just build it' approach leaves operations undone."
    - "Se demonic (shadow) → No rate limiting, no input size validation, no abuse prevention. The dark side of Ne-Ti is 'it works on my machine' syndrome."

  stress_indicators:
    - "Si grip trigger → Under deadline pressure, expect more over-engineering (adding more systems) rather than simplifying and finishing."

  growth_path:
    - "Integrate Te shadow → Add a basic project board. Write a migration plan for auth. Ship before adding another service."
    - "Develop inferior Si → Write one test for the most critical path (game creation pipeline). Fix auth middleware registration."
    - "Face Enneagram 7 fear → Delete the MongoDB queue if it is not handling real traffic. Simplify to PostgreSQL + Redis until 10k users."

verdict: >
  You are a classic ENTP 7w8 builder — you see the whole system, design bold
  architectures, and move fast. The project's strengths (multi-database pipeline,
  caching strategy, clean module structure) reflect your dominant Ne-Ti. The
  weaknesses (incomplete auth, no tests, over-engineering, operational gaps) are
  textbook inferior Si and Enneagram 7 blind spots.

  The single highest-leverage change is: **finish auth, add one test, and remove
  the MongoDB dependency until you have paying users.** This directly addresses
  your Si blind spot while simplifying the architecture to match what a 0-user
  project actually needs. The architecture doc is excellent — keep it updated.

  Important Edge Cases:
  
  1. **Cost-Efficiency Optimization**: If the multi-service architecture represents an
     intentional cost-optimization strategy (where each service is selected for
     its specific strengths within free tiers to minimize latency and maximize
     flexibility), then the core assessment shifts. Instead of assuming
     simplification is needed, evaluate whether the architecture represents
     optimal cost-efficiency for the specific use case:
     
     **Cost Efficiency Validation**: 
     - Confirm each service is being used for its optimal workload type
     - Verify free tier limits provide adequate headroom for current/near-term scale
     - Measure actual latency and cost compared to simplified alternatives
     
     **If validated as cost-optimal**:
     - Focus improvements on operational excellence (connection pooling, queue reliability, monitoring)
     - Evolve services independently based on actual usage patterns
     - Maintain the architectural flexibility that enables handling diverse workloads efficiently
     
     **If not validated as cost-optimal**:
     - Then consider simplification toward a more streamlined architecture
  
  2. **Multi-Framework Synergy**: If using multiple frameworks/libraries together
     (e.g., Convex + Clerk for authentication layer, or Convex for real-time
     backend while using REST APIs for current data fetching), evaluate whether
     the combination provides strategic value even if one component appears
     underutilized:
     
     - **Future-Proofing**: Convex may provide real-time capabilities ready for
       future features without frontend changes
     - **Schema Management**: Convex provides schema validation and relationships
       that simplify backend development
     - **Authentication Layer**: Combining Clerk (frontend auth) with Convex
       (backend auth/validation) can create a more robust security model
     - **Gradual Migration**: Allows incremental adoption of real-time features
       while maintaining current REST API stability
     
     In such cases, assess whether the underutilized component provides
     strategic value that justifies keeping it in the stack, rather than
     assuming it's dead weight.
```

---

## How to Use This Skill

### Workflow

1. **Determine personality** — ask the user for their MBTI type and Enneagram (or use a questionnaire to determine them)
2. **Produce personality profile** — use the personality-references 5-lens framework, extract strengths and weaknesses
3. **Analyze technical architecture** — use the technical-architecture-reference dimensions: routing, data flow, code quality, scaling projection
4. **Analyze UI architecture** — use the UI-architecture-analysis dimensions: layout, components, state, design system, rendering, accessibility
5. **Cross-reference** — map personality strengths to architecture strengths, personality weaknesses to architecture gaps, stress triggers to code debt patterns
6. **Output the full report** — use the YAML format above

### Reference Skills Used

| Skill | Location | Purpose |
|-------|----------|---------|
| personality-references | `Self assesments/personality-refrences/Skill.md` | 5-lens psychological profiling |
| technical-architecture-reference | `Architicture-refrences/technical-architecture-reference/Skill.md` | Backend architecture analysis |
| UI-architecture-analysis | `Architicture-refrences/UI-architecture-analysis/Skill.md` | Frontend/UI architecture analysis |

### When Not to Use

- Do not use without a clear personality type — the cross-reference requires a personality profile
- Do not use for projects you have not read — the analysis must be grounded in actual code
- Do not use the personality analysis as a clinical assessment — it is a framework, not a diagnosis
- Do not skip the cross-reference — that is where the most actionable insights live
