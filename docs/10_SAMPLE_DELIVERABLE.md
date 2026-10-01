# DocIt AI — Sample Deliverable Package

**Document:** 10  
**Audience:** Prospective customers, RFP respondents  
**Related:** `00_WHITEPAPER.md`

---

## What This Package Contains

When a prospective customer evaluates DocIt AI, we provide a **sample deliverable** that demonstrates the platform's capabilities end-to-end.

### Sample Structure

For a typical Node.js/Express microservice (e.g., `acme/payment-api`), the generated documentation tree looks like:

```
SDK/
├── Authentication/
│   ├── JWT Refresh/
│   │   ├── current.md
│   │   └── v1.0-JWT Refresh.md
│   └── API Key Management/
│       ├── current.md
│       └── v0.8-API Key Management.md
├── Payment Processing/
│   ├── Card Charges/
│   │   ├── current.md
│   │   └── v1.2-Card Charges.md
│   ├── Refunds/
│   │   ├── current.md
│   │   └── v1.0-Refunds.md
│   └── Webhooks/
│       └── current.md (no version file)
├── Error Handling/
│   └── current.md
└── Changelog/
    └── current.md
```

### Sample Output: `SDK/Payment Processing/Card Charges/current.md`

```markdown
# Card Charges

This page describes the card charge API endpoints for the payment service.

## Overview

The `/charges` endpoint enables processing one-time and recurring card payments. All charges are asynchronous and emit webhooks on completion.

## Endpoints

### POST /charges

Create a new card charge.

**Request Body:**
- `amount` (integer, required): Amount in cents
- `currency` (string, required): ISO 4217 currency code (e.g., `usd`)
- `source` (string, required): Tokenized card identifier from the client SDK
- `description` (string, optional): Human-readable description
- `capture` (boolean, optional): Whether to authorize only. Default `true`

**Response:** `201 Created` with charge object.

### GET /charges/{charge_id}

Retrieve a charge by ID.

**Response:** `200 OK` with charge object or `404 Not Found`.

## Error Codes

| Code | Message |
|---|---|
| 400 | Invalid request payload |
| 402 | Card declined |
| 404 | Charge not found |
| 500 | Internal processing error |

## Related Webhooks

- `charge.succeeded` — Emitted when charge completes successfully
- `charge.failed` — Emitted when charge fails
- `charge.captured` — Emitted when an authorized charge is captured

## Implementation Notes

- Charges are processed through Stripe's API (see `External Integrations` section)
- Webhook handlers live in `src/webhooks/charge.webhook.ts`
- Service uses async/await pattern with RabbitMQ for retry logic
```

### Internal Persona Example (Excerpt)

For the `internal` persona, the same API generates a deeper walkthrough:

> **Note:** Internal docs are gated behind SSO and exclude any external references.

```markdown
# Card Charges (Internal View)

## Architecture Context

The charge flow is implemented in `src/services/payment/charge.ts`. The service orchestrates between:
- Stripe SDK (outbound)
- Postgres `charges` table (state persistence)
- Redis cache for rate limiting
- RabbitMQ dead-letter queue for failed retries

## State Transitions

1. `INIT` → API request received
2. `AUTHORIZING` → Stripe `authorization` call
3. `CAPTURED` → Stripe `capture` call (or auto-capture)
4. `COMPLETED` → Webhook `charge.succeeded` received
5. `FAILED` → Webhook `charge.failed` received or timeout after 30s

## Database Schema

`charges` table columns:
- `id` (UUID PK)
- `stripe_id` (TEXT, unique)
- `status` (TEXT, enum: pending/completed/failed)
- `amount_cents` (INT)
- `currency` (TEXT)
- `created_at` (TIMESTAMPTZ)

## Failure Modes

- **Stripe timeout**: Re-queued via AWS SQS with exponential backoff
- **Webhook signature mismatch**: Logged to Sentry with `webhook_validation_failed` tag
- **Duplicate idempotency**: Handled by `stripeChargeId` unique constraint

## Debug Commands

```bash
# View pending authorizations
SELECT * FROM charges WHERE status = 'authorized' AND created_at > NOW() - INTERVAL '1 hour';

# Check Stripe sync status
./scripts/check-stripe-sync.ts --since yesterday
```
```

---

## Demo Request Process

| Step | Action |
|---|---|
| 1 | Connect GitHub repo via OAuth |
| 2 | Install Reader + Writer apps |
| 3 | Push code or trigger manual generation |
| 4 | Receive ping when docs are ready |
| 5 | Review staging PR or direct main merge |

**Time to first doc**: 30–90 seconds (wall clock, from push to PR created).

---

## Evaluation Checklist

| Item | Status |
|---|---|
| Documentation generated from code | ✅ |
| Hierarchical tree structure | ✅ |
| Versioned files (current + historical) | ✅ |
| Internal and Dev personas | ✅ |
| Published to staging branch | ✅ |
| Pending review record created | ✅ |
| No manual configuration required | ✅ |
| Multi-org isolation | ✅ |
| Billing/quotas enforced | ✅ |