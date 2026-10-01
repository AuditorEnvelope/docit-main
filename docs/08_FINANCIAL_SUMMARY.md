# DocIt AI — Financial Summary

**Document:** 08  
**Audience:** Investors, board, CFO  
**Related:** `00_WHITEPAPER.md`, `05_ROADMAP.md`

---

## Revenue Model

### Subscription Tiers (Monthly / Annual)

| Tier | Monthly Price (annual) | Monthly Price (monthly) | Repos | Indexing Frequency | Overlays | Seats | Target Segment |
|---|---|---|---|---|---|---|---|
| **Free** | $0 | $0 | 1 | Daily | No | 1 | Individual devs, small open source |
| **Team** | $49 | $59 | 10 | Realtime | Yes | 5 | Early-stage startups, indie devs |
| **Enterprise** | Custom | Custom | Unlimited | Realtime | Yes + SSO | Unlimited | Growing SaaS, mid-market, agencies |

> **Note**: Annual pricing offers 2 months free. Custom Enterprise contracts are negotiated per-org and typically range $499–$1,499/mo depending on repo count and SSO scope.

### Usage Quotas

- Each tier includes a monthly quota of `LLM tokens` and `doc generation events`.
- Overages billed at $0.01 / 1K tokens (Gemini flash), $0.02 / 1K tokens (GPT-4).
- Per-endpoint tracking via `usage_events` table; auto-alerts when org reaches 80% of quota.

### Revenue Projection (Year 1)

| Metric | Conservative | Moderate | Aggressive |
|---|---|---|---|
| Orgs acquired | 50 | 200 | 500 |
| Avg. repos / org | 2 | 5 | 10 |
| Total repos | 100 | 1,000 | 5,000 |
| Conversion (Team %) | 15% | 25% | 35% |
| Conversion (Enterprise %) | 2% | 4% | 8% |
| Avg. monthly revenue | $1,176 | $4,704 | $19,600 |
| **Monthly recurring revenue** | **$58,800** | **$941,280** | **$9,800,000** |
| **Annual recurring revenue** | **$705,600** | **$11,295,360** | **$117,600,000** |

*Assumptions: 12-month retention, 95% gross margin (LLM cost is the primary variable), monthly churn < 3%, average contract length 18mo for Enterprise.*

### LLM Cost Per Doc Generation

| Section count | Avg tokens / section | Provider | Cost / generation | Monthly at 10K generations |
|---|---|---|---|---|
| 5 | 400 | Gemini flash | $0.001 | $50 |
| 8 | 500 | Groq | $0.0004 | $32 |
| 6 | 450 | Anthropic Opus | $0.003 | $162 |
| **Total avg** | **~450** | **Mixed** | **~$0.0016** | **$162** |

At 10K monthly doc generations, LLM cost is ~$1.6K / month, or < 5% of MRR at moderate scale.

---

## Unit Economics

| Metric | Value |
|---|---|
| CAC (Customer Acquisition Cost) | ~$500 (assuming $0.50 per lead, 1000 leads to 1 paying customer) |
| LTV / CAC ratio | 3.5x (conservative), 7x (moderate), 14x (aggressive) |
| Gross margin | 94–96% (LLM cost is the only significant variable) |
| Payback period | < 3 months (conservative) |
| Churn rate (monthly) | < 3% (target; industry average for dev tools ~5–7%) |

---

## Funding Allocation (Seed Round)

| Category | % of Round | Dollar Amount |
|---|---|---|
| Engineering | 60% | $X million |
| Infrastructure | 20% | $X million |
| GTM / Sales | 15% | $X million |
| Legal / Admin / Insurance | 5% | $X million |
| **Total** | **100%** | **$X million** |

---

## Exit Scenarios

| Buyer | Rationale |
|---|---|
| GitHub | Doc generation as native feature in the docs site / dev center |
| Atlassian | Integration with Confluence + Jira product doc story |
| Postman / ReadMe | Dev docs + API doc platform expansion |
| Independent | Consolidation of dev-tools SaaS space |