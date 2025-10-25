# ⚡ QUICK COMPARISON - Current vs Multi-Org

## **QUESTION 1: Why separate PUSTAK token?**

```
┌─────────────────────────────────────────────────────────────┐
│ GITHUB APP (Installed in each org)                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Lekhak AI App                                              │
│  ├─ Installed in: beta-org-for-pustak                       │
│  │  └─ installation_id = 12345                              │
│  │  └─ Can access: beta-org-for-pustak's repos              │
│  │                                                           │
│  ├─ Installed in: another-org                               │
│  │  └─ installation_id = 67890                              │
│  │  └─ Can access: another-org's repos                      │
│  │                                                           │
│  └─ Installed in: AuditorEnvelope                           │
│     └─ installation_id = 11111                              │
│     └─ Can access: AuditorEnvelope's repos                  │
│                                                             │
│  ⚠️  App tokens are TEMPORARY (1 hour)                      │
│  ⚠️  App tokens are SCOPED to one org                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PERSONAL TOKENS (User's access token)                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PUSTAK's Token (from .env):                                │
│  ├─ Can access: All repos PUSTAK has access to              │
│  ├─ Can access: AuditorEnvelope org ✅                      │
│  ├─ Cannot access: beta-org-for-pustak (unless member) ❌   │
│  ├─ Cannot access: another-org (unless member) ❌           │
│  └─ ❌ NOT SCALABLE for multi-org                           │
│                                                             │
│  Company A User's Token:                                    │
│  ├─ Can access: All repos Company A user has access to      │
│  ├─ Can access: beta-org-for-pustak's private repos ✅      │
│  ├─ Cannot access: another-org ❌                           │
│  └─ ✅ SCALABLE for multi-org                               │
│                                                             │
│  Company B User's Token:                                    │
│  ├─ Can access: All repos Company B user has access to      │
│  ├─ Can access: another-org's private repos ✅              │
│  ├─ Cannot access: beta-org-for-pustak ❌                   │
│  └─ ✅ SCALABLE for multi-org                               │
│                                                             │
│  ✅ Personal tokens are PERSISTENT                          │
│  ✅ Personal tokens can be used for git operations          │
│  ✅ Each user's token has their permissions                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘

WHY WE NEED SEPARATE TOKENS:
├─ PUSTAK's token: Only works for PUSTAK's repos
├─ Company A's token: Only works for Company A's repos
├─ Company B's token: Only works for Company B's repos
└─ ✅ Each org uses their own token = Multi-org support!
```

---

## **QUESTION 2: Server downtime + different org repos?**

```
┌─────────────────────────────────────────────────────────────┐
│ SCENARIO: Server down for 48 hours                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Hour 0: Company A pushes to their repo                     │
│  ├─ Webhook sent to PUSTAK's server                         │
│  ├─ ❌ SERVER DOWN - webhook fails                          │
│  ├─ GitHub retries for 24 hours                             │
│  ├─ At hour 24: GitHub stops retrying                       │
│  └─ ❌ WEBHOOK NEVER ARRIVES (already stopped)              │
│                                                             │
│  Hour 0: Company B pushes to their repo                     │
│  ├─ Webhook sent to PUSTAK's server                         │
│  ├─ ❌ SERVER DOWN - webhook fails                          │
│  ├─ GitHub retries for 24 hours                             │
│  ├─ At hour 24: GitHub stops retrying                       │
│  └─ ❌ WEBHOOK NEVER ARRIVES (already stopped)              │
│                                                             │
│  Hour 48: PUSTAK's server comes back up                     │
│  ├─ EventConsumer.check_missed_commits() runs               │
│  ├─ Queries: "AuditorEnvelope/lekhak_ai" (hardcoded)        │
│  ├─ ❌ Doesn't check Company A's repos                      │
│  ├─ ❌ Doesn't check Company B's repos                      │
│  └─ ❌ COMMITS LOST!                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

AFTER FIX:

┌─────────────────────────────────────────────────────────────┐
│ SCENARIO: Server down for 48 hours (WITH FIX)               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Hour 48: PUSTAK's server comes back up                     │
│  ├─ EventConsumer.check_missed_commits_all_orgs() runs      │
│  │                                                           │
│  ├─ For Company A:                                          │
│  │  ├─ Gets Company A's token                               │
│  │  ├─ Queries: "beta-org-for-pustak/College-ERP"           │
│  │  ├─ GitHub returns: [commit1, commit2, commit3]          │
│  │  └─ ✅ Stores in DB with Company A's context             │
│  │                                                           │
│  ├─ For Company B:                                          │
│  │  ├─ Gets Company B's token                               │
│  │  ├─ Queries: "another-org/Their-Project"                 │
│  │  ├─ GitHub returns: [commit1, commit2]                   │
│  │  └─ ✅ Stores in DB with Company B's context             │
│  │                                                           │
│  ├─ For Company C, D, E, ... (1000 orgs):                   │
│  │  └─ ✅ Same process for each org                         │
│  │                                                           │
│  └─ ✅ ALL MISSED COMMITS RECOVERED!                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

ANSWER: YES, currently broken for multi-org. After fix: WORKS!
```

---

## **QUESTION 3: Current flow vs new flow?**

```
┌─────────────────────────────────────────────────────────────┐
│ CURRENT FLOW (SINGLE-ORG, BROKEN FOR MULTI-ORG)             │
├─────────────────────────────────────────────────────────────┤

GitHub Push (Company A)
    ↓
POST /webhook
    ├─ Signature: sha256=abc123...
    ├─ Lookup org_webhooks: ❌ NOT FOUND
    └─ Use env var: GITHUB_WEBHOOK_SECRET ✅
    ↓
process_commit_event()
    ├─ Extract context: ❌ NONE
    ├─ user_id: NULL
    ├─ org_id: NULL
    └─ github_token_id: NULL
    ↓
CommitBusService.store_event()
    ├─ repo_id: "AuditorEnvelope/lekhak_ai"
    ├─ user_id: NULL ❌
    ├─ org_id: NULL ❌
    └─ github_token_id: NULL ❌
    ↓
EventConsumer.process_event()
    ├─ user_id = NULL
    ├─ token_id = NULL
    ├─ if user_id and token_id: FALSE ❌
    └─ github_token = os.getenv("GITHUB_TOKEN") ← PUSTAK's token
    ↓
handle_push_event(payload, PUSTAK's token)
    ├─ Clone: "AuditorEnvelope/lekhak_ai" ✅
    ├─ Generate docs
    └─ Push: "AuditorEnvelope/lekhak_ai" ✅
    ↓
check_missed_commits()
    ├─ Query: "AuditorEnvelope/lekhak_ai" (hardcoded)
    ├─ ❌ Doesn't check Company A's repos
    └─ ❌ Doesn't check Company B's repos

RESULT: ❌ ONLY WORKS FOR PUSTAK'S REPOS

┌─────────────────────────────────────────────────────────────┐
│ NEW FLOW (MULTI-ORG, WORKS FOR ALL ORGS)                    │
├─────────────────────────────────────────────────────────────┤

STEP 1: Webhook Registration (One-time per org)

Company A Admin:
    ├─ POST /webhook/register
    ├─ org_id: "beta-org-for-pustak"
    ├─ github_token: "ghp_xxxxx..."
    ↓
    Generate webhook_secret: "whsec_aaa..."
    ↓
    Store in org_webhooks:
    ├─ user_id: "company-a-uuid"
    ├─ org_id: "beta-org-for-pustak"
    ├─ webhook_secret: "whsec_aaa..."
    └─ github_token_id: "token-uuid-123"
    ↓
    Store in user_github_tokens:
    ├─ token_id: "token-uuid-123"
    ├─ user_id: "company-a-uuid"
    └─ github_token: "ghp_xxxxx..." (encrypted)
    ↓
    Return webhook URL + secret
    ↓
    Company A Admin configures webhook in GitHub ✅

STEP 2: Webhook Receives Event

GitHub Push (Company A)
    ↓
POST /webhook
    ├─ Signature: sha256=whsec_aaa...
    ├─ Lookup org_webhooks: ✅ FOUND!
    ├─ webhook_context = {
    │   "user_id": "company-a-uuid",
    │   "org_id": "beta-org-for-pustak",
    │   "webhook_secret": "whsec_aaa...",
    │   "github_token_id": "token-uuid-123"
    │ }
    └─ webhook_secret = "whsec_aaa..."
    ↓
    Verify signature ✅
    ↓
    Add context to payload:
    └─ payload._webhook_context = webhook_context
    ↓
process_commit_event(payload)
    ├─ Extract context from payload._webhook_context
    ├─ user_id: "company-a-uuid" ✅
    ├─ org_id: "beta-org-for-pustak" ✅
    └─ github_token_id: "token-uuid-123" ✅
    ↓
CommitBusService.store_event()
    ├─ repo_id: "beta-org-for-pustak/College-ERP"
    ├─ user_id: "company-a-uuid" ✅
    ├─ org_id: "beta-org-for-pustak" ✅
    └─ github_token_id: "token-uuid-123" ✅
    ↓
EventConsumer.process_event()
    ├─ user_id = "company-a-uuid"
    ├─ token_id = "token-uuid-123"
    ├─ if user_id and token_id: TRUE ✅
    ├─ github_token = await self.get_github_token(
    │   "company-a-uuid",
    │   "token-uuid-123"
    │ )
    └─ github_token = "ghp_xxxxx..." ← Company A's token ✅
    ↓
handle_push_event(payload, Company A's token)
    ├─ Clone: "beta-org-for-pustak/College-ERP" ✅
    ├─ Generate docs
    └─ Push: "beta-org-for-pustak/College-ERP" ✅
    ↓
check_missed_commits_all_orgs()
    ├─ For each org in database:
    │  ├─ Company A:
    │  │  ├─ Get Company A's token
    │  │  ├─ Query: "beta-org-for-pustak/College-ERP"
    │  │  └─ ✅ Recover missed commits
    │  ├─ Company B:
    │  │  ├─ Get Company B's token
    │  │  ├─ Query: "another-org/Their-Project"
    │  │  └─ ✅ Recover missed commits
    │  └─ ... (1000 orgs)
    └─ ✅ ALL ORGS CHECKED!

RESULT: ✅ WORKS FOR ALL ORGS!
```

---

## **SIDE-BY-SIDE COMPARISON**

| Step | Current | New |
|------|---------|-----|
| **1. Registration** | ❌ None | ✅ Per org |
| **2. Webhook Verification** | env var | org's secret |
| **3. Event Storage** | No context | ✅ user_id, org_id, token_id |
| **4. Token Lookup** | Hardcoded | ✅ Per-org from DB |
| **5. Doc Generation** | PUSTAK's token | ✅ Org's token |
| **6. Missed Commits** | 1 repo | ✅ 100,000 repos |
| **7. Multi-org Support** | ❌ No | ✅ Yes |

---

## **IMPLEMENTATION CHECKLIST**

```
Phase 1: Database
  ☐ Create org_webhooks table
  ☐ Create user_github_tokens table
  ☐ Add columns to commit_events: user_id, org_id, github_token_id

Phase 2: Webhook Registration
  ☐ Add POST /webhook/register endpoint
  ☐ Generate webhook_secret
  ☐ Store org context
  ☐ Return webhook URL

Phase 3: Multi-Org Webhook Handler
  ☐ Update POST /webhook to look up org from signature
  ☐ Add context to payload
  ☐ Store with org context

Phase 4: Event Consumer Integration
  ☐ Add get_github_token() method
  ☐ Replace process_event() method
  ☐ Pass token to smart_processor

Phase 5: Smart Processor Update
  ☐ Accept github_token parameter
  ☐ Use for clone and push

Phase 6: Missed Commits Detection
  ☐ Loop through all orgs
  ☐ Get each org's token
  ☐ Query GitHub for each org
  ☐ Store with org context

Phase 7: Testing
  ☐ Test with Company A
  ☐ Test with Company B
  ☐ Test missed commits
  ☐ Test token rotation
```
