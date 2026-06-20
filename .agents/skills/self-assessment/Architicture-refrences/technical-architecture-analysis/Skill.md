---
name: technical-architecture-analysis
description: Project architecture analysis framework. Given a project description, assess its complexity, then project behavior at 100 / 1,000 / 10,000 concurrent users — identifying breaking points, bottlenecks, and architecture evolution per scale.
---

# Technical Architecture Analysis Framework

A diagnostic framework that takes any project and produces a **scale-by-scale architecture analysis**. It first classifies the project's complexity, then simulates what happens at 100, 1,000, and 10,000 concurrent users — what breaks, what the bottleneck is, and what architecture shift is needed.

---

## Step 1: Classify Project Complexity

Before analyzing scale, assess the project's inherent complexity across these dimensions:

### Complexity Dimensions

| Dimension | Simple | Medium | Complex |
|-----------|--------|--------|---------|
| **Domain Logic** | CRUD, basic validation, simple workflows | Multi-step business rules, state machines, conditional workflows | Distributed transactions, sagas, real-time constraints, complex domain models |
| **Data Model** | 1–5 tables, no relationships | 10–20 tables, foreign keys, moderate joins | 50+ tables, polymorphic relationships, graph/temporal data, polyglot persistence |
| **Integrations** | 0–1 external API | 2–5 APIs, webhooks, file ingestion | 10+ services, event streams, third-party orchestration, compliance logging |
| **Real-Time Needs** | None | Soft real-time (notifications, polls) | Hard real-time (collaboration, gaming, live trading, streaming) |
| **Team Size** | 1–3 developers | 3–10 developers | 10+ developers across multiple teams |
| **Deploy Cadence** | Weekly / monthly | Daily | Multiple deploys per day per service |
| **Data Consistency** | Strong ACID required | Mix of strong + eventual | Mostly eventual, conflict resolution, CRDTs |
| **Compliance** | None | SOC2, GDPR | PCI-DSS, HIPAA, FedRAMP, multi-region |
| **State** | Stateless | Session state, in-memory cache | Distributed state, event sourcing, multi-region replication |

### Complexity Score

- **Simple** (0–3 complex dimensions): Monolithic architecture is the right starting point
- **Medium** (4–6 complex dimensions): Modular monolith or targeted microservice extraction
- **Complex** (7–9 complex dimensions): Full distributed architecture from day one

---

## Step 2: Run the Scale Projection

For each user threshold, the framework simulates the system under load and reports:

| Output | Description |
|--------|-------------|
| **Architecture** | What architecture the project should use at this scale |
| **Infra** | What infrastructure is needed |
| **What Breaks** | The first component to fail under load |
| **Bottleneck** | The root cause of the failure |
| **Response Time** | Expected end-to-end latency range |
| **Cost Profile** | Infrastructure cost estimate |
| **Next Shift** | What forces the move to the next scale |

---

### At 100 Concurrent Users

**Assumption**: Single application instance, single database.

| Project Type | Architecture | What Breaks | Bottleneck | Response Time | Cost | Next Shift |
|--------------|-------------|-------------|------------|---------------|------|------------|
| **Simple** | Monolith (single process + single DB) | Nothing | None | <50ms | ~$50/mo | — |
| **Medium** | Monolith + background job queue | DB connection pool under peak | DB connections (default 100–200) | 50–200ms | ~$100–200/mo | Connection pooler |
| **Complex** | Modular monolith + message broker | Eventual consistency latencies, integration timeouts | External API rate limits, message broker throughput | 200–500ms | ~$300–500/mo | Async processing |

**Profile at 100 users**:
- Single web server (2–4 vCPU, 8 GB RAM) handles everything
- Single database instance (no replicas needed)
- No caching layer needed yet (DB can handle the read load)
- No CDN needed (static assets from app server)
- **If you need anything more than this at 100 users, you are over-engineering**

---

### At 1,000 Concurrent Users

**Assumption**: 2–3 application instances behind load balancer. Single database.

| Project Type | Architecture | What Breaks | Bottleneck | Response Time | Cost | Next Shift |
|--------------|-------------|-------------|------------|---------------|------|------------|
| **Simple** | Monolith + load balancer + Redis cache | Repeated reads hammer the DB | DB I/O from uncached reads | 100–300ms | ~$200–500/mo | Caching layer |
| **Medium** | Modular monolith + Redis + job workers | Transaction contention, slow queries | Missing indexes, N+1 queries, lock contention | 300–800ms | ~$500–1,500/mo | Read replicas, query optimization |
| **Complex** | Microservices (partially extracted) + Kafka + per-service DBs | Inter-service latency, data consistency failures | Network hops between services, saga failures, tracing gaps | 500ms–2s | ~$2,000–5,000/mo | Service mesh, distributed tracing |

**Profile at 1,000 users**:
- 2–4 app instances behind ALB / reverse proxy
- **Redis / Memcached is mandatory** — 60–80% of reads should hit cache
- Connection pooler (PgBouncer) required — default 100 connections will exhaust
- Background jobs must run on dedicated workers (separate process)
- Read replicas start making sense (offload primary DB)
- CDN recommended for static assets
- **Most projects fail here because they skip caching and hit DB on every request**

---

### At 10,000 Concurrent Users

**Assumption**: Horizontal app cluster, read replicas, caching tier, message broker.

| Project Type | Architecture | What Breaks | Bottleneck | Response Time | Cost | Next Shift |
|--------------|-------------|-------------|------------|---------------|------|------------|
| **Simple** | Monolith + read replicas + Redis + CDN + connection pooling | Lock contention on writes, thundering herd on cache expiry | Database write path, cache stampede | 500ms–2s | ~$2,000–5,000/mo | Extract hot services, consider serverless for spiky paths |
| **Medium** | Modular monolith + read replicas + CQRS + Redis + workers | Coordination overhead, background job backlog | DB write contention, queue depth, slow projections | 1–3s | ~$5,000–15,000/mo | Targeted microservice extraction, event-driven refactor |
| **Complex** | Microservices + CQRS/ES + Kafka + service mesh + multi-region | Distributed tracing debt, saga failures, partition rebalancing | Cross-service coordination, eventual consistency lag, cost explosion | 500ms–5s | ~$15,000–50,000+/mo | Sharding, space-based architecture, custom infrastructure |

**Profile at 10,000 users**:
- Multi-instance cluster (10–20+ app instances)
- **Read replicas are non-negotiable** (primary DB cannot serve all reads)
- Caching (Redis cluster, not single instance)
- CDN for all static + semi-static content
- Database sharding may be needed for write-heavy workloads
- **DevOps team is mandatory** — this scale cannot run without dedicated ops
- Observability stack (metrics, tracing, logging) is mandatory
- **If you are still on a single DB instance, it will fall over**

---

## Step 3: Generate the Analysis Report

When given a project, produce this output:

```yaml
project:
  name: <project name>
  complexity_score: <simple | medium | complex>
  complexity_breakdown:
    domain_logic: <simple | medium | complex>
    data_model: <simple | medium | complex>
    integrations: <simple | medium | complex>
    real_time: <simple | medium | complex>
    team_size: <simple | medium | complex>
    deploy_cadence: <simple | medium | complex>
    consistency: <simple | medium | complex>
    compliance: <simple | medium | complex>
    statefulness: <simple | medium | complex>

analysis:
  at_100_users:
    architecture: <recommended architecture>
    infra: <what to run>
    what_breaks: <first failure mode>
    bottleneck: <root cause>
    response_time: <range>
    cost_estimate: <monthly>
    next_shift: <what forces the jump>

  at_1000_users:
    architecture: <recommended architecture>
    infra: <what to add>
    what_breaks: <first failure mode>
    bottleneck: <root cause>
    response_time: <range>
    cost_estimate: <monthly>
    next_shift: <what forces the jump>

  at_10000_users:
    architecture: <recommended architecture>
    infra: <what to add>
    what_breaks: <first failure mode>
    bottleneck: <root cause>
    response_time: <range>
    cost_estimate: <monthly>
    next_shift: <what forces the jump>

evolution_path:
  - from: <arch at 100>
    to: <arch at 1000>
    trigger: <what broke to force the move>
  - from: <arch at 1000>
    to: <arch at 10000>
    trigger: <what broke to force the move>

verdict: <one-paragraph summary of the optimal architecture path>
```

---

## Example Analysis

### Input: E-Commerce Checkout System

```
- Domain: Multi-vendor e-commerce with payments, inventory, shipping
- Data: 30+ tables (orders, products, vendors, payments, shipments, reviews)
- Integrations: Stripe, ShipEngine, 3PL API, email provider, SMS
- Real-time: Inventory updates across vendors, live shipping quotes
- Team: 5 developers
- Deploy: Twice weekly
- Consistency: Strong for payments/inventory, eventual for reviews
- Compliance: PCI-DSS (payment data scope), GDPR
- State: Cart sessions, inventory cache, order state machines
```

### Complexity Classification

| Dimension | Rating | Reason |
|-----------|--------|--------|
| Domain Logic | Complex | Multi-step order workflows, payment + inventory state machines, refund/reversal flows |
| Data Model | Medium | 30+ tables with foreign keys, but no graph/temporal complexity |
| Integrations | Medium | 4 external services, well-defined APIs, no event streams |
| Real-Time | Medium | Inventory notifications, not hard real-time |
| Team Size | Medium | 5 developers — single team, but approaching split point |
| Deploy Cadence | Simple | Twice weekly — no need for per-service deploy |
| Consistency | Complex | Mixed: strong for money/inventory, eventual for everything else |
| Compliance | Complex | PCI-DCC scope requires payment data isolation |
| State | Medium | Cart session + inventory cache + order state machines |

**Overall: Medium (5 of 9 complex dimensions)**

### Scale Projection

```yaml
project:
  name: E-Commerce Checkout
  complexity_score: medium
  complexity_breakdown:
    domain_logic: complex
    data_model: medium
    integrations: medium
    real_time: medium
    team_size: medium
    deploy_cadence: simple
    consistency: complex
    compliance: complex
    statefulness: medium

analysis:
  at_100_users:
    architecture: Monolith + single DB
    infra: 1 app server (4 vCPU, 16 GB), 1 PostgreSQL, 1 Redis (cart sessions), Stripe webhook endpoint
    what_breaks: Nothing — handles comfortably
    bottleneck: None
    response_time: 20–80ms
    cost_estimate: ~$150/mo
    next_shift: Team grows to 4+ engineers → modular monolith boundaries needed

  at_1000_users:
    architecture: Modular monolith + Redis cache + background workers + connection pooler
    infra: 3 app servers behind ALB, PostgreSQL + PgBouncer, Redis cluster (cache + sessions + queue), dedicated worker processes for async jobs
    what_breaks: Repeated product catalog queries hammer DB; inventory hot-shop causes lock contention
    bottleneck: DB read I/O + inventory row-level locks
    response_time: 200–800ms
    cost_estimate: ~$800–1,200/mo
    next_shift: PCI-DSS scope forces payment extraction; inventory contention forces dedicated service

  at_10000_users:
    architecture: Microservices (payment isolated, inventory isolated) + CQRS (read models for product catalog) + Kafka (order events)
    infra: 10+ microservice instances + API gateway, PostgreSQL per service (primary + read replicas), Redis cluster, Kafka cluster, distributed tracing (OpenTelemetry), service mesh (mTLS, retry, circuit breakers)
    what_breaks: Inter-service saga coordination failures; cross-service tracing gaps; partition rebalancing on Kafka during peak
    bottleneck: Saga timeouts, eventual consistency delays between order + inventory + shipping
    response_time: 500ms–3s
    cost_estimate: ~$12,000–20,000/mo
    next_shift: Database write throughput saturation → shard inventory DB; shipping service becomes separate microservice

evolution_path:
  - from: Monolith
    to: Modular monolith + caching + workers
    trigger: Database read I/O at 1,000 users
  - from: Modular monolith
    to: Microservices (payment + inventory) + CQRS + event-driven
    trigger: PCI-DSS compliance scope + inventory write contention at 10,000 users

verdict: >
  Start as a modular monolith. Extract payment into its own service
  early (PCI scope). Extract inventory when write contention appears.
  Use CQRS for product catalog reads. Introduce Kafka for order
  events once 3+ services need to react to the same events.
  Do NOT extract shipping or reviews until they independently
  bottleneck — premature microservices will slow you down more
  than they help.
```

---

## How to Use This Skill

### Workflow

1. **Get the project description** — ask the user or read the codebase to fill in the 9 complexity dimensions
2. **Classify complexity** — rate each dimension as simple / medium / complex; count complex dimensions
3. **Project at each scale** — run the projection tables for 100 / 1,000 / 10,000 users
4. **Write the evolution path** — describe the architecture transition at each breaking point
5. **Output the full report** — use the YAML format above

### Key Rules

- **Start simple and evolve** — most projects should start as a monolith and extract services only when a specific bottleneck forces it. Amazon, Netflix, and Shopify all started as monoliths.
- **A bottleneck at 100 users is rarely the bottleneck at 10,000** — DB connections break at 500 users, repeated reads break at 1,000, writes break at 5,000, coordination breaks at 10,000, and data growth breaks at 50,000+.
- **Microservices do not solve scaling problems — they trade one set of problems for another** — you trade DB contention for network latency, simple deploys for distributed tracing, and ACID for sagas. Only make this trade when the original problem hurts more than the new ones.
- **The simplest architecture that survives the next 12 months is the right one** — do not design for 10,000 users when you have 100. Do design so that getting to 1,000 does not require a rewrite.

### When Not to Use

- Do not use for specific infrastructure recommendations (e.g., "should I use RDS or Aurora?")
- Do not use for UI / frontend architecture decisions
- Do not use when the project is not yet defined enough to fill in the complexity dimensions
