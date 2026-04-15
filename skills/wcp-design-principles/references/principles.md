# WCP Tech Design Principles

## Purpose

Defines who owns payment state, how it moves, and how other services interact with it. Every design doc and service integration must follow these principles. If a design violates one, it needs a documented exception or a redesign.

> The event system (Section 3) is not yet built. Sections that reference events describe the target architecture. Until then, services use Pay Core's API for current state or the current event stream.

## 1. Single Source of Truth

Core payments canonical table (e.g. `prod-pay-v2-canonical-sc-eu`) is the authoritative record for payment state. If it disagrees with any other data store, canonical wins. Settlement tables, ClickHouse, Redis caches are all derived.

Data not yet in canonical doesn't change the payment's state. A tx hash observed onchain but not yet written to canonical doesn't change a payment's status.

## 2. No Local Payment State

Services consume payment events for their own purposes (analytics, notifications, dashboards). They don't maintain their own copy of payment state for decision-making.

| OK | Not OK |
|---|---|
| Store `payment.succeeded` to compute revenue metrics | Cache payment status to decide whether to send a webhook |
| Store payment ID as a foreign key | Store amount + status + tx_hash as "your view" of the payment |
| Query Pay Core API when you need current state | Build a local state machine that tracks transitions independently |

## 3. Events Over Direct Access

Services learn about payment state changes through the event stream, not by querying Pay Core's database.

```
Pay Core --> Canonical Table --> DDB Stream --> Transformer --> Kinesis --> Consumer
```

Use **events** when: reacting to state changes, building derived data stores, triggering side effects (notifications, webhooks).

Use **Pay Core API** when: you need current state on-demand, you need to request a state transition.

## 4. Idempotent Migrations

Every operation that changes payment state must be safe to replay.

Mechanisms:
- `idempotency_key` on payment creation (client-provided)
- Version checks (optimistic locking) on all canonical table updates
- Settlement records keyed by payment ID (duplicate settlement is a no-op)
- `event_id` for consumer deduplication

## 5. Compensation Over Rollback

On-chain transactions can't be reversed. When a step fails after a prior step succeeded, the path is compensation, not rollback.

| Failed Step | Compensation |
|-------------|--------------|
| Commit fails | Payment dies in intake, no action |
| Broadcast fails | Mark `failed` in canonical |
| Confirmation times out | Monitor chain, reconcile async |
| Settlement batch crashes | Retry next batch (idempotent) |

## 6. Ordered State Transitions

Pay Core enforces that transitions follow the defined lifecycle. Skipping states is not allowed.

```
requires_action --> processing
requires_action --> cancelled
requires_action --> failed
requires_action --> expired
processing --> succeeded
processing --> failed
processing --> expired
```

Commitment (intake -> canonical promotion) happens during `requires_action -> processing`. It is not a separate visible status.

> `processing -> expired` is specific to native ETH payments. Standard ERC-20 payments fail via `processing -> failed`.

Every transition checks current state matches expected state and increments the version (optimistic locking).

## Integration Quick Reference

| I need to... | Do this |
|---|---|
| Know the current payment state | Call Pay Core's internal API |
| React when a payment succeeds | Subscribe to `payment.succeeded` on Kinesis. Deduplicate by `event_id` |
| Trigger a state change | Call Pay Core API with the requested transition |
| Payment data for analytics | Consume event stream into your store. Read-only copy, don't use it for payment decisions |

## Anti-Patterns

| Don't | Why | Instead |
|---|---|---|
| Write directly to canonical table | Bypasses validation and state machine enforcement | Call Pay Core API |
| Monitor chain and maintain your own "payment status" | Race condition with Pay Core. Two services disagree on state | React to Pay Core's events |
| Poll canonical table instead of consuming events | Couples you to DDB schema. Unnecessary load | Use the event stream |

## Ownership

### Payment Creation - Owner: Pay Core
No external service creates payments. Pay Core writes to intake (regional), then promotes to canonical at commitment. Single writer eliminates cross-service reconciliation.

### Payment Status Transitions - Owner: Pay Core
All status transitions are writes to the canonical table with version checks. Other services *request* a transition by calling Pay Core's API. Pay Core validates, applies, and the change propagates via events.

### Fund Movements - Owner: Pay Core
Any on-chain token transfer involving a payment lifecycle is owned by Core.

| Movement | Example | Component |
|----------|---------|-----------|
| Buyer -> MTA | Payment settlement (ERC-3009 via escrow) | Relayer |
| MTA -> Merchant | Batch settlement | Batch Settlement Processor |
| MTA -> Fee Collector | Fee collection during batch settlement | Batch Settlement Processor |
| MRA -> Buyer | Refund execution (future) | TBD |
| Any Pay wallet -> external | Payouts, withdrawals (future) | TBD |

No external service initiates or executes fund movements. Other services *schedule* them. Core executes and handles signing, gas, nonce management, submission, and receipt tracking.

### Product and Merchant Logic - Owner: Product services (MX, BX, PoS, etc.)
Everything that isn't payment state, invariant validation, or onchain execution.

| Area | Examples | Owner |
|------|----------|-------|
| Merchant management | MRA provisioning, funding UX, onboarding flows | MX |
| Refund scheduling | Queue management, auto-retry policy, expiry rules | MX / Refund Service |
| Merchant dashboard | Refund list, payment search, reporting views | MX |
| Buyer experience | Payment UI, wallet selection, confirmation flow | BX |
| PoS integration | Payment initiation, NFC/QR, refund request UI | PoS |
| Notifications (future) | Webhook delivery, merchant alerts, email | Notification Service |

Product services call Core's API to create payments, request transitions, or schedule fund movements. They subscribe to Core's events to update their own views. They don't write to Core's tables or execute onchain.

**Validation split**: Core validates invariants (can't refund more than payment amount, payment must be succeeded). Product services enforce policy (auto-refund eligibility, refund window expiry). Invariants rarely change. Policy changes with the product.
