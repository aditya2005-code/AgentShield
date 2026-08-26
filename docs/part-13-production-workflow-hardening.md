# Part 13 — Production Workflow Hardening: Idempotency, Event Lifecycle & Orchestration Validation

This document outlines the architecture flow, agent routing matrix, event lifecycle states, database-backed idempotency design, concurrency locking, and retry boundaries implemented in the AgentShield system.

---

## 1. System Architecture Flow

The processed event flow now incorporates database-backed idempotency, lifecycle management, and strict routing boundaries:

```
                  Ingress Event Request (event_type, event_id)
                                       ↓
                             Load Event Context (DB)
                                       ↓
                        Check Existing EventWorkflow row
                                       ├── COMPLETED ──→ Return Cached Result
                                       ├── PROCESSING ─→ Return In-Progress Response
                                       └── FAILED / None
                                              ↓
                                        Validate Event
                                              ↓
                                    Acquire processing lock
                                    (Insert status='PROCESSING'
                                  unique constraint enforced)
                                              ↓
                                   Determine Strict Routing
                                              │
                      ┌───────────────────────┼───────────────────────┐
                      ▼                       ▼                       ▼
                 Fraud Agent           Recovery Agent           Growth Agent
              (All Transactions)      (FAILED/BLOCKED tx)       (SUCCESS tx or
                                     or PAYMENT_FAILURE event   growth opportunity)
                      │                       │                       │
                      └───────────────────────┼───────────────────────┘
                                              ↓
                                Sequential Agent Execution
                               (Reuse existing proposals)
                                              ↓
                                 Orchestrated Decision
                                              ↓
                                       Conflict Resolver
                                              ↓
                                    Persist Result (DB)
                                 Transition status to COMPLETED
                                              ↓
                                   Return Structured Result
```

---

## 2. Agent Routing Matrix

Agent selection is evaluated based on the event type norm and current database state:

| Event Type | Transaction Status | Applicable Agents | Description / Rationale |
| :--- | :--- | :--- | :--- |
| `TRANSACTION` | `PENDING` | `['FRAUD']` | Always executes risk check. No recovery or incentives. |
| `TRANSACTION` | `SUCCESS` | `['FRAUD', 'GROWTH']` | Risk check + growth discount/vip upsell campaign. |
| `TRANSACTION` | `FAILED` / `BLOCKED` | `['FRAUD', 'RECOVERY']` | Risk check + payment failure recovery retry strategy. |
| `PAYMENT_FAILURE` | Any (`FAILED` / `BLOCKED` / `SUCCESS`) | `['RECOVERY', 'FRAUD']` | Recovery agent always runs. Fraud runs if context exists. Never run growth. |
| `GROWTH_OPPORTUNITY` | N/A | `['GROWTH']` | Exclusively runs growth incentive campaign context. |

*Routing Inconsistency Found:*
In the previous manual verification script, `tx_vc_402` (which is successful in the seed data) was executed under a `PAYMENT_FAILURE` event, causing it to incorrectly execute the `GrowthAgent` because the selection logic checked `if tx.status == TransactionStatus.SUCCESS` globally across all event types. Under the corrected strict routing logic, `GrowthAgent` is never run for `PAYMENT_FAILURE` events.

---

## 3. Database-Backed Idempotency & Lifecycle States

The lifecycle transitions are tracked in the `event_workflows` database table:

- **`PENDING`**: Initial default state.
- **`PROCESSING`**: Set when processing starts. Concurrency is locked using a PostgreSQL unique constraint on `(event_type, event_id)`. Any simultaneous duplicate request raises an `IntegrityError`, causing the request to immediately return the controlled in-progress state.
- **`COMPLETED`**: Event completed successfully. The final structured response dictionary is serialized as JSONB in the `result` column. Duplicate subsequent requests return this cached result immediately without executing agents again.
- **`FAILED`**: Event failed because all applicable agents failed or threw exceptions. The event is allowed to be safely retried.

---

## 4. Retry Behavior & Record Deduplication

When a `FAILED` event is retried:
1. The `EventWorkflow` state transitions back from `FAILED` to `PROCESSING`.
2. To avoid uncontrolled duplicate records, the orchestration service checks for any existing `AgentProposal` records for the event ID and agent ID.
3. If an existing proposal is found (e.g. from an agent that completed successfully in the previous failed run), it is **reused** directly. The agent is not executed again, preventing duplicate proposals, decisions, and audit log lines.
4. If a proposal does not exist (e.g. from the agent that crashed and caused the event to fail), it is executed for the first time.
5. This creates a clean, resilient resumption boundary without requiring background queues (Celery/Redis/Kafka).

---

## 5. Conflict Resolution Hierarchy

The orchestrator aggregates individual agent proposals and applies the priority hierarchy consistently:
```
REJECT > ESCALATE > MODIFY > APPROVE
```
- If any proposal evaluates to `REJECT` (e.g. Fraud block, invalid action), the final decision is `REJECT`.
- If any proposal evaluates to `ESCALATE` (e.g. human review trigger), the final decision is `ESCALATE`.
- If any proposal evaluates to `MODIFY` (e.g. discount policy cap adjustment), the final decision is `MODIFY`.
- Otherwise, the final decision is `APPROVE`.

If one agent fails during execution but other agents succeed and produce valid proposals, the execution is marked as `DEGRADED`, but the final status transitions to `COMPLETED` since a deterministic decision was successfully reached.

---

## 6. Automated Test Validation Results

A total of **69 tests** passed successfully:
- **5** new test suites in `test_production_hardening.py` representing all 23 focused scenarios (strict routing, database idempotency, lifecycle transitions, concurrency lock, retry logic, conflict resolution, API sanitization, and regression checks).
- **64** existing core tests in `test_agents.py`, `test_agentshield.py`, `test_rag.py`, `test_fraud_inference.py`, `test_fraud_api.py`, `test_fraud_end_to_end.py`, and `test_multi_agent_end_to_end.py`.

---

## 7. Manual Verification Results

- **SUCCESS Transaction (tx_vc_103)**: Executed `['FRAUD', 'GROWTH']`, final decision: `MODIFY`. Status: `COMPLETED`.
- **FAILED Transaction (tx_vc_302)**: Executed `['FRAUD', 'RECOVERY']`, final decision: `ESCALATE`. Status: `COMPLETED`.
- **Duplicate Request**: Returned the identical cached response of Scenario A immediately without executing agents or adding duplicate proposal/decision rows.
- **Agent Failure (tx_vc_401 BLOCKED)**: Executed `['RECOVERY']` (Fraud agent failed due to simulated exception), final decision: `APPROVE`. Status: `DEGRADED`.
- **Deduplication**: Proposal, Decision, and AuditLog tables contain zero duplicate records.
