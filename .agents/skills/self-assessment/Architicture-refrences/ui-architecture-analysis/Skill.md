---
name: ui-architecture-analysis
description: Multi-dimensional UI/UX architecture analysis framework covering layout systems, component architecture, design systems, rendering strategy, state management, accessibility, responsiveness, animation, and micro-frontends. Given a project, classifies its UI complexity and projects architecture needs across screen sizes, component counts, and interaction complexity.
---

# UI Architecture Analysis Framework

A diagnostic framework that takes any project and produces a **scale-by-scale UI architecture analysis**. It classifies the project's UI complexity across 9 dimensions, then projects what the UI architecture needs at each growth stage.

---

## Step 1: Classify UI Complexity

### Complexity Dimensions

| Dimension | Simple | Medium | Complex |
|-----------|--------|--------|---------|
| **Screens / Routes** | 1–5 screens, linear flow | 5–20 screens, branching navigation | 20+ screens, deep nesting, dynamic routing, multi-workspace |
| **Components** | 10–30 components, low reuse | 30–200 components, moderate composition | 200+ components, compound components, polymorphic primitives, micro-frontends |
| **Layout System** | Single layout, fixed breakpoints | 2–3 layouts (mobile/tablet/desktop), 8px grid | Multi-layout per role, fluid grids, container queries, responsive patterns per component |
| **State Complexity** | Local state only, simple props | Context + server state (TanStack Query) + URL state | Multi-source state (server, client, WebSocket, optimistic), offline sync, CRDTs |
| **Interactions** | Clicks, scrolls, form inputs | Drag-and-drop, sortable lists, modals, async workflows | Real-time collaboration, canvas/graphics, gesture handling, undo/redo, multi-step wizards |
| **Design System Maturity** | No design system, inline styles | Token-based theming, basic component library | Full design system (tokens, primitives, compound components, documentation, Figma sync) |
| **Accessibility** | None | Keyboard nav, semantic HTML, basic ARIA | WCAG 2.2 AA/AAA, screen reader optimization, focus management, reduced motion, high contrast |
| **Rendering** | CSR only | SSR + hydration, basic ISR | RSC, streaming, edge rendering, island architecture, multi-strategy per route |
| **Performance** | No budget, no monitoring | Bundle size budget, code splitting, lazy loading, image optimization | Core Web Vitals SLA, virtual scrolling, concurrent rendering, Web Workers, edge caching |

### Complexity Score

- **Simple** (0–3 complex dimensions) — Basic layout + local state + CSR is fine
- **Medium** (4–6 complex dimensions) — Design system, SSR, server state, responsive grid needed
- **Complex** (7–9 complex dimensions) — Micro-frontends, real-time sync, RSC, full design system, WCAG AA+, canvas/graphics

---

## Step 2: The Dimensions of UI Architecture

### 1. Layout System

The foundation of visual structure.

| Pattern | Description | Best For |
|---------|-------------|----------|
| **8-Pixel Grid** | All spacing, sizing, and layout are multiples of 8px (base unit). Margins, padding, width, height, font sizes follow the 8px scale: 8, 16, 24, 32, 40, 48, 56, 64, etc. | Any app needing visual consistency |
| **Flexbox Layout** | One-dimensional layout for rows or columns. Good for navigation, toolbars, card rows, centering. | Simple to medium layouts |
| **CSS Grid** | Two-dimensional layout for rows and columns simultaneously. Best for dashboards, media galleries, complex page layouts. | Dashboard-heavy, complex page layouts |
| **Fluid / Relative Layout** | Uses %, fr, vw, vh, clamp() for fluid scaling. Text scales with `clamp(16px, 2vw, 24px)`. | Content-heavy, typography-driven apps |
| **Container Queries** | Components respond to their container width, not the viewport. Enables truly reusable responsive components. | Component libraries, embedded widgets, design systems |
| **Masonry / Pinterest Grid** | Column-based layout where items fill the shortest column. Not native CSS (requires JS or CSS columns). | Media galleries, social feeds, discovery pages |
| **Multi-Column** | Content flows into columns (newspaper style). CSS `columns` property. | Article/content-heavy pages |

### 2. Component Architecture

How components are structured, composed, and organized.

| Pattern | Description | Best For |
|---------|-------------|----------|
| **Atomic Design** | Atoms → Molecules → Organisms → Templates → Pages. Hierarchical composition from smallest to largest. | Design system-driven apps, large teams |
| **Compound Components** | Related components share implicit state via Context (e.g., `Select.Trigger`, `Select.Content`, `Select.Item`). Prevents prop explosion. | Complex UI widgets (menus, dialogs, tables) |
| **Polymorphic Components** | Component renders as any HTML element via `as` or `asChild` prop. Enables semantic HTML without losing component behavior. | Design system primitives (Button, Text, Box) |
| **Headless / Unstyled UI** | Logic without markup (e.g., Radix UI, React Aria). Consumer provides styling. Maximum flexibility. | Design systems needing custom styling |
| **Feature-Sliced Design** | Layers (app → processes → entities → shared) with strict dependency rules. Each slice is a feature, not a type. | Large apps, multi-team codebases |
| **Render-Boundary Components** | Components designed to stop render propagation. Wrapping heavy subtrees in `React.memo` or isolated state contexts. | Performance-critical, large component trees |

### 3. Design System Maturity Model

| Level | Characteristics | Team Size |
|-------|----------------|-----------|
| **Level 0: Ad-hoc** | No tokens, repeated values, inconsistent spacing/colors. Every developer styles independently. | 1–2 |
| **Level 1: Tokens** | Design tokens for colors, spacing, typography, shadows. CSS custom properties or Style Dictionary. | 2–5 |
| **Level 2: Primitives** | Shared component primitives (Button, Input, Modal, Select). Tokens feed into components. | 3–8 |
| **Level 3: Compound Library** | Compound components, polymorphic props, composition patterns. Documentation site (Storybook). | 5–15 |
| **Level 4: Federated System** | Multi-package design system, versioned releases, Figma sync, dark mode + theming, accessibility baked in, RFC process for contributions. | 10+ |

### 4. Rendering Strategy

| Strategy | How It Works | Best For | Tradeoff |
|----------|-------------|----------|----------|
| **CSR (Client-Side Rendering)** | Browser fetches JS bundle, renders in DOM | Dashboards, authenticated apps | Bad SEO, slow LCP, simple infrastructure |
| **SSR (Server-Side Rendering)** | Server renders HTML per request, hydrates on client | SEO-critical, dynamic content | Higher server cost, TTFB vs FCP tradeoff |
| **SSG (Static Site Generation)** | Build-time HTML generation, served from CDN | Blogs, marketing, docs | Stale content, long builds for large sites |
| **ISR (Incremental Static Regeneration)** | SSG with on-demand revalidation | E-commerce, content sites | Complexity, stale-while-revalidate |
| **RSC (React Server Components)** | Components that never send JS to the client. Zero client bundle for static UI. | 2026 default for new Next.js apps | Mental model shift, client/server boundary management |
| **Streaming SSR** | Server streams HTML chunks as they render. Users see content before the full page is ready. | Long-running queries, heavy pages | Infrastructure complexity |
| **Island Architecture** | Static HTML by default, isolated interactive "islands" of JS. Used by Astro, Qwik. | Content-heavy with pockets of interactivity | Limited interactivity in static regions |
| **Edge Rendering** | Render at CDN edge nodes (CloudFlare Workers, Vercel Edge). Near-zero latency for global users. | Global audience, low-latency needs | Compute limits, no Node APIs |

### 5. State Management

| Category | Best Tool / Pattern | When |
|----------|-------------------|------|
| **Server State** | TanStack Query v5, SWR, RTK Query | Remote data fetching, caching, invalidation |
| **Global UI State** | Zustand, Jotai, Valtio | Theme, modals, toasts, feature flags, user prefs |
| **Form State** | React Hook Form, TanStack Form | Complex forms, validation, multi-step wizards |
| **URL State** | `nuqs`, `useSearchParams` | Filters, pagination, sort, search query |
| **Local State** | `useState`, `useReducer` | Tab selection, open/close, hover, input draft |
| **Derived State** | `useMemo`, selectors, computed signals | Filtered lists, totals, formatted values, permission checks |
| **Sync State** | WebSockets, SSE, Liveblocks, PartyKit | Real-time collaboration, live cursors, multiplayer |

### 6. Responsiveness

| Approach | Description | Best For |
|----------|-------------|----------|
| **Mobile-First** | Base styles for mobile, min-width breakpoints for larger screens. Default: narrow. | 2026 standard for all web apps |
| **Desktop-First** | Base styles for desktop, max-width breakpoints for smaller. Default: wide. | Complex desktop tools later adapted |
| **Adaptive** | Separate layouts per breakpoint, served by device detection. | Legacy apps, TV/game console |
| **Fluid / Intrinsic** | No breakpoints. Use clamp(), min/max, container queries, percentage-based widths. | Component libraries, pattern libraries |
| **Container-Query-First** | Components respond to their own container, not viewport. Combined with mobile-first for page-level. | Design system components, embedded widgets |

### 7. Performance Architecture

| Concern | Technique | Impact |
|---------|-----------|--------|
| **Bundle Size** | Code splitting by route, dynamic imports, tree shaking, package analysis | LCP, TTI, JS parse time |
| **Image Optimization** | Next/Image, srcset, WebP/AVIF, lazy loading, blur placeholder | LCP, CLS |
| **Font Loading** | `font-display: swap`, subset fonts, preload critical fonts, variable fonts | CLS, FCP |
| **Render Optimization** | `React.memo`, `useMemo`, virtualization (react-window, tanstack-virtual), list recycling | FPS, scroll performance |
| **CSS Performance** | CSS modules / scoped styles, purge unused CSS (Tailwind JIT), avoid expensive selectors | TTI, FCP |
| **Network** | CDN, HTTP/3, prefetch, preconnect, service worker caching, stale-while-revalidate | TTFB, repeat visit speed |
| **JavaScript Execution** | Web Workers for heavy computation, idle-until-urgent for non-critical work, `requestIdleCallback` | TTI, INP |

### 8. Accessibility Architecture

| Level | Requirements | Tools |
|-------|-------------|-------|
| **A** | Semantic HTML, form labels, alt text, video captions | axe-core, Lighthouse |
| **AA** | Color contrast (4.5:1), keyboard navigation, focus indicators, ARIA landmarks, error announcements | axe DevTools, WAVE, NVDA |
| **AAA** | Contrast (7:1), sign language, extended audio descriptions, reduced motion support, simpler language | Manual expert audit, user testing |
| **Design System Level** | Focus-visible ring, reduced motion media query, prefers-contrast, forced colors, announce on toast | Storybook a11y addon, cypress-axe |

### 9. Animation & Motion

| Pattern | Use Case | Implementation |
|---------|----------|----------------|
| **Micro-interactions** | Button hover, toggle switch, loading spinner | CSS transitions, Framer Motion |
| **Page Transitions** | Route-level enter/exit animations | Framer Motion AnimatePresence, view transitions API |
| **Layout Animation** | List reorder, accordion expand, sidebar collapse | Framer Motion `layout` prop, FLIP technique |
| **Scroll-Driven** | Parallax, reveal on scroll, sticky headers | Intersection Observer, GSAP ScrollTrigger |
| **Gesture-Based** | Swipe to dismiss, pull to refresh, pinch zoom | Framer Motion, use-gesture |
| **Reduced Motion** | Respect `prefers-reduced-motion`, replace animations with fade | CSS media query, system-level respect |

### 10. Micro-Frontends

| Pattern | Description | Best For |
|---------|-------------|----------|
| **iframe** | Each micro-frontend in an iframe. Maximal isolation. | Legacy integration, third-party widgets |
| **Web Components** | Framework-agnostic custom elements. Standardized. | Multi-framework teams, slow migration |
| **Module Federation** | Webpack 5 Module Federation. Share components at runtime. | Large apps, independent deploy cycles |
| **Single-SPA** | Meta-framework that orchestrates multiple frameworks on one page. | Migrating from old to new framework |
| **Islands (Astro)** | Static HTML with interactive islands. Multiple frameworks coexist. | Content sites with interactive widgets |

---

## Step 3: UI Scale Projection

### Screen Size Scale

| Threshold | Mobile | Tablet | Desktop | Ultra-Wide |
|-----------|--------|--------|---------|------------|
| Width | < 640px | 640–1024px | 1024–1440px | > 1440px |
| **What Breaks** | Touch targets too small, content too wide, nav overflow | Side-by-side layout breaks, cards too wide | White space wasted, line length too long | Text lines too long, content not centered |
| **Fix** | Min 48px touch targets, single column, collapsible nav | Multi-column grid, responsive sidebar, adaptive cards | Max-width container, multi-column text, expanded sidebar | Max-width: 1200px content area, multi-column layouts, centered content |

### Component Count Scale

| Threshold | 10–30 Components | 30–200 Components | 200–1000+ Components |
|-----------|-----------------|------------------|---------------------|
| **Architecture** | Single folder, inline styles or utility classes | Design system primitives, feature folders, tokens | Micro-frontends, federated design system, strict boundaries |
| **What Breaks** | Duplicate styles, inconsistent spacing, no reuse | Import spaghetti, circular deps, slow builds, style conflicts | Team coordination, design system drift, CI build times, bundle size |
| **Fix** | Extract shared utilities, 8px grid convention | Feature-Sliced Design, dependency lint rules, Storybook | Module federation, monorepo tools (Turborepo/Nx), RFC process |

### Interaction Complexity Scale

| Threshold | Simple (Clicks + Forms) | Medium (Drag + Async) | Complex (Canvas + Real-Time) |
|-----------|------------------------|----------------------|------------------------------|
| **State Architecture** | Local state + form submit | Server state (TanStack Query) + Context + URL state | Multi-source state, WebSocket sync, CRDTs, undo/redo |
| **What Breaks** | None — state lives in components | Prop drilling, stale server state, modal-on-modal hell | Cross-workspace state sync, optimistic rollback, memory leaks |
| **Fix** | — | TanStack Query for server state, Zustand for global UI | Event sourcing, state machines (XState), time-travel debugging |

---

## Step 4: Generate the Analysis Report

When given a project, produce this output:

```yaml
project:
  name: <project name>
  ui_complexity_score: <simple | medium | complex>
  complexity_breakdown:
    screens_routes: <simple | medium | complex>
    components: <simple | medium | complex>
    layout_system: <simple | medium | complex>
    state_complexity: <simple | medium | complex>
    interactions: <simple | medium | complex>
    design_system_maturity: <simple | medium | complex>
    accessibility: <simple | medium | complex>
    rendering: <simple | medium | complex>
    performance: <simple | medium | complex>

ui_patterns:
  layout_system:
    recommended: <pattern>
    explanation: <why>
  component_architecture:
    recommended: <pattern>
    explanation: <why>
  rendering_strategy:
    recommended: <strategy>
    explanation: <why>
  state_management:
    server_state: <tool>
    global_state: <tool>
    form_state: <tool>
    url_state: <tool>
  responsiveness:
    approach: <mobile-first | fluid | etc>
    breakpoints: <values>
  design_system_level: <0–4>
  accessibility_target: <A | AA | AAA>

scale_projections:
  screen_scale:
    mobile: <what breaks and recommendation>
    tablet: <what breaks and recommendation>
    desktop: <what breaks and recommendation>
    ultrawide: <what breaks and recommendation>
  component_scale:
    at_10_30: <architecture>
    at_30_200: <architecture>
    at_200_plus: <architecture>

verdict: <one-paragraph summary of the optimal UI architecture path>
```

---

## Example Analysis

### Input: E-Commerce Dashboard

```
- Screens: Dashboard, Orders, Products, Customers, Analytics, Settings, Login (7 screens)
- Components: ~80 (data tables, charts, forms, modals, navigation, cards, filters)
- Layout: Sidebar nav, top header, main content area. Responsive: sidebar collapses on mobile.
- State: Product list (server), orders with real-time updates (WebSocket), theme + sidebar state (global UI), filters/search (URL), forms (form state)
- Interactions: Sortable tables, drag-and-drop reorder, inline edit, multi-select bulk actions, chart zoom
- Design System: Tailwind-based custom primitives (Button, Input, Modal, Table, Badge), CSS custom properties for tokens, no dedicated design system team
- Accessibility: Semantic HTML, keyboard navigation for tables, focus rings, no screen reader testing
- Rendering: Next.js SSR with some client components for interactivity
- Performance: Bundle size ~400KB JS, images optimized, code splitting by route, no virtual scrolling
```

### Complexity Classification

| Dimension | Rating | Reason |
|-----------|--------|--------|
| Screens / Routes | Medium | 7 screens, branching navigation with params |
| Components | Medium | ~80 components, moderate composition |
| Layout System | Medium | Sidebar + header + content, responsive collapse |
| State Complexity | Medium | Server state + global UI + URL + WebSocket sync |
| Interactions | Medium | Sortable tables, drag-and-drop, bulk actions |
| Design System | Medium | Custom primitives with tokens, no dedicated team |
| Accessibility | Simple | Semantic HTML + basic keyboard, no screen reader testing |
| Rendering | Medium | SSR + client components, no RSC/island architecture |
| Performance | Simple | Code splitting + image opt, no virtual scrolling or bundle analysis |

**Overall: Medium (6 of 9 complex dimensions)**

### Analysis Report

```yaml
project:
  name: E-Commerce Dashboard
  ui_complexity_score: medium
  complexity_breakdown:
    screens_routes: medium
    components: medium
    layout_system: medium
    state_complexity: medium
    interactions: medium
    design_system_maturity: medium
    accessibility: simple
    rendering: medium
    performance: simple

ui_patterns:
  layout_system:
    recommended: 8px grid + CSS Grid (dashboard) + Flexbox (components)
    explanation: >
      8px base for all spacing. CSS Grid for the main dashboard layout
      (sidebar + header + content grid). Flexbox inside components
      (toolbars, card rows, form fields).
  component_architecture:
    recommended: Atomic Design (feature-aligned) + Compound components for complex widgets
    explanation: >
      Organize by feature folders, not type folders.
      Table, FilterBar, and ChartPanel benefit from compound component pattern
      to avoid prop explosion.
  rendering_strategy:
    recommended: SSR (page shell) + client components (interactive islands) + ISR for analytics data
    explanation: >
      Dashboard shell is SSR for fast first paint. Interactive parts
      (tables, charts) are client islands. Analytics page uses ISR
      with 60s revalidation since it is OK with slightly stale data.
  state_management:
    server_state: TanStack Query v5
    global_state: Zustand (sidebar, theme, toast)
    form_state: React Hook Form
    url_state: nuqs (filters, pagination, search)
    websocket: useWebSocket with TanStack Query invalidation
  responsiveness:
    approach: mobile-first with container queries for data table
    breakpoints: 640px, 768px, 1024px, 1280px
  design_system_level: 2 (primitives + tokens, needs compound components + documentation)
  accessibility_target: AA

scale_projections:
  screen_scale:
    mobile: >
      Sidebar becomes bottom nav or hamburger. Data tables horizontal-scroll.
      Fix: stack cards instead of table rows on <640px, collapsible sidebar,
      min 48px touch targets.
    tablet: >
      Sidebar collapsible, 2-column card layout works. Data table shows fewer columns.
      Fix: responsive table with column toggle, sidebar icons only.
    desktop: >
      Full sidebar + multi-column charts. Data with full columns.
      Watch for: white space on wide screens, line length > 80ch.
    ultrawide: >
      Content stretches too wide. Fix: max-width 1440px container,
      multi-column data sections, expanded detail panels on the right.
  component_scale:
    at_10_30: >
      Single components/ folder, inline Tailwind. No design system needed.
      Just shared utilities (cn(), formatDate(), etc.).
    at_30_200: >
      Feature folder structure. Extract primitives (Button, Input, Modal)
      into shared/ui/. CSS custom properties for tokens. Storybook for
      component documentation. ESLint boundaries between features.
    at_200_plus: >
      Federated design system as separate package. Compound components
      for all complex widgets. Micro-frontends if different teams own
      dashboard vs analytics vs settings. Module Federation for
      independent deploys.

verdict: >
  Start with a feature-folder structure and 8px Tailwind-based primitives.
  The biggest gap is state management — integrate TanStack Query for
  server data and Zustand for UI state before the component count hits 50.
  Push to AA accessibility (focus management, screen reader announcements
  for table updates). SSR is fine; do not add RSC until the interactive
  islands pattern is well-understood by the team. The data table will
  be the hardest component to get right — invest in compound component
  pattern and container queries there first.
```

---

## How to Use This Skill

### Workflow

1. **Get the project description** — ask the user or audit the codebase to fill in the 9 complexity dimensions
2. **Classify UI complexity** — rate each dimension as simple / medium / complex; count complex dimensions
3. **Select patterns** — choose layout system, component architecture, rendering strategy, state tools, responsiveness approach based on complexity
4. **Project across scales** — run the scale projections for screen sizes (mobile → ultrawide) and component counts (10 → 200+)
5. **Output the full report** — use the YAML format above

### Key Rules

- **Layout scales first** — without a consistent layout system (8px grid, responsive breakpoints), every other layer becomes harder to maintain
- **Design system maturity follows team size** — do not build a federated design system for 2 developers. Do not stay at Level 0 with 15+ developers
- **State management is the most common failure point** — not because it is hard, but because teams mix server state and UI state into one global store
- **Accessibility is not optional at scale** — retrofitting accessibility across 200+ components costs 10x what it costs to build it in from the start
- **Performance budgets must be set before the 100th component** — bundle size doubles silently without budgets
- **SSR is the 2026 default** — but RSC is only worth it when most of your UI is static and you have a small amount of interactivity

### When Not to Use

- Do not use for graphic design / visual arts decisions (color theory, typography pairing, brand identity)
- Do not use for backend architecture decisions (use the Technical Architecture Analysis skill)
- Do not use when the project is purely native mobile (iOS / Android) — this framework targets web UI
- Do not use for deciding between specific UI libraries (e.g., shadcn vs MUI vs Chakra) — use it for architectural decisions, not library choices

---

## References

### Articles
- [The UI Architecture That Won't Break Your App (Feature-Sliced Design)](https://feature-sliced.design/blog/ui-architecture-patterns)
- [Component Architecture Blueprint for Scalable UI — Sujeet Jaiswal](https://sujeet.pro/articles/component-architecture-blueprint)
- [Frontend System Design Guide (System Design Handbook)](https://www.systemdesignhandbook.com/guides/frontend-system-design/)
- [Modern Frontend Architecture 2026: What Actually Works](https://dailydevpost.com/blog/frontend-architecture-guide)
- [Frontend Design Patterns That Actually Work in 2026](https://www.netguru.com/blog/frontend-design-patterns)
- [React System Design & Architecture: The Complete 2026 Guide](https://qcode.in/react-system-design-architecture-the-complete-2026-guide/)
- [Building Scalable UI Architectures — Part 4: Design Systems That Scale](https://medium.com/the-thinking-interface/building-scalable-ui-architectures-part-4-design-systems-that-scale-inside-product-teams-ca513656b046)
- [Design Systems as Living Architecture — Chris West](https://www.chriswest.tech/article/design-systems-living-architecture)
- [Design System Documentation: A Practical Guide for 2026](https://docsio.co/blog/design-system-documentation)
- [The Complete Guide to Design Systems in 2026](https://productrocket.ro/articles/design-systems-guide/)
- [React State Management: A Scalable Architecture (FSD)](https://feature-sliced.design/blog/scalable-react-state-patterns)
- [State Management Patterns: Boundaries, Ownership, and Consistency](https://sujeet.pro/articles/state-management-patterns)
- [Component Library Architecture and Governance](https://sujeet.pro/articles/component-library-architecture-and-governance)
- [Building a Production Component Library (shadcn → Your Design System)](https://ui.spectrumhq.in/blog/building-production-component-library)
- [Rethinking Frontend Architecture for Large React Applications](https://dev.to/humayun_jawad/rethinking-frontend-architecture-for-large-react-applications-state-isolation-render-boundaries-4idf)

### GitHub Repositories
- [awesome-front-end-architecture (tiagovilasboas)](https://github.com/tiagovilasboas/awesome-front-end-architecture) — Principles, patterns, real-world examples for scalable front-end architecture
- [awesome-front-end-system-design (greatfrontend)](https://github.com/greatfrontend/awesome-front-end-system-design) — Curated front-end system design resources
- [awesome-design-systems (alexpate)](https://github.com/alexpate/awesome-design-systems) — Collection of design systems from major companies
- [frontend-system-design (devkodeio)](https://github.com/devkodeio/frontend-system-design) — Frontend system design guide with HLD and LLD breakdowns
- [frontend-architecture-playbook (khasky)](https://github.com/khasky/frontend-architecture-playbook) — Opinionated guide to scalable React architecture, folder strategy, state boundaries
- [awesome-software-design (QDenka)](https://github.com/QDenka/awesome-software-design) — Implementation patterns, decision records, verification rules
- [ux-patterns-for-developers (thedaviddias)](https://github.com/thedaviddias/ux-patterns-for-developers) — Comprehensive UX patterns with best practices and accessibility guidelines
- [front-end-system-design (ZeeshanAli-0704)](https://github.com/ZeeshanAli-0704/front-end-system-design) — Case studies: Facebook feed, Pinterest grid, Excalidraw, Uber, etc.
- [awesome-design-patterns (DovAmir)](https://github.com/DovAmir/awesome-design-patterns) — Software and architecture design patterns catalog
