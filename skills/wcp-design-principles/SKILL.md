---
name: wcp-design-principles
description: WalletConnect Pay (WCP) technical design principles and architecture guidelines. Enforces payment state ownership, event-driven integration patterns, and service boundaries. Use when designing new WCP services, reviewing WCP design docs or PRs, integrating with Pay Core, writing code that touches payment state or payment events, or making architectural decisions about WCP payment flows. Also use when checking if a design follows WCP principles or identifying anti-patterns in WCP code.
---

# WCP Design Principles

Architectural guidelines for WalletConnect Pay services. Read [references/principles.md](references/principles.md) for the full principles document.

## Core Rules

1. **Single Source of Truth** - Canonical table is the only authority for payment state. All other stores are derived.
2. **Events as the Integration Layer** - Services learn about state changes through events on Kinesis, not by querying Pay Core's database. Events carry full payment state — use them for display, analytics, and product logic. Event data can be briefly stale; Core validates all mutations at its boundary. Consume fields as Core publishes them, don't derive from raw fields.
3. **Idempotent Operations** - Every state-changing operation must be safe to replay. Use idempotency keys, version checks, event deduplication.
4. **Compensation Over Rollback** - On-chain txs can't be reversed. Failed steps get compensated, not rolled back.
5. **Ordered State Transitions** - `requires_action -> processing -> succeeded/failed/expired`. No skipping states. Optimistic locking on every transition.

## Ownership Boundaries

- **Pay Core owns**: payment creation, status transitions, fund movements (on-chain execution), canonical table writes.
- **Product services own** (MX, BX, PoS): merchant management, refund scheduling/policy, dashboards, buyer experience, notifications.
- **Validation split**: Core enforces invariants (correctness). Product services enforce policy (business rules).

## When Reviewing Designs or Code

Check for these anti-patterns:
- Writing directly to canonical table (bypass validation) -> use Pay Core API
- Maintaining local payment status or deriving fields from raw data -> consume events as Core publishes them
- Polling canonical table (schema coupling) -> use event stream
- Skipping state transitions -> enforce lifecycle order
- Attempting rollback of on-chain operations -> use compensation

## Applying the Principles

When reviewing a design doc, PR, or architecture proposal:

1. Read [references/principles.md](references/principles.md) for the full principles and ownership tables
2. Identify which principles apply to the change
3. Flag any violations with the specific principle number and the recommended alternative
4. For borderline cases, note the violation and suggest documenting a justified exception
