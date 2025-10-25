# 🔄 COMPLETE TESTING FLOW DIAGRAMS

## **FLOW 1: WEBHOOK REGISTRATION FLOW**

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER REGISTRATION FLOW                        │
└─────────────────────────────────────────────────────────────────┘

1. USER CLICKS "CONNECT ORGANIZATION"
   │
   ├─ Frontend: ConnectOrganizationModal opens
   │
   ├─ User selects org from dropdown
   │  └─ Fetches from: GET /auth/user/organizations
   │
   ├─ User clicks "Connect Organization"
   │
   ├─ Frontend calls: POST /webhook/register
   │  └─ Body: { "org_id": "beta-org-for-pustak" }
   │
   ├─ Backend receives request
   │  ├─ Extracts user_id from JWT token
   │  ├─ Generates unique webhook_secret
   │  ├─ Stores in org_webhooks table:
   │  │  ├─ user_id: "aca20dc6-..."
   │  │  ├─ org_id: "beta-org-for-pustak"
   │  │  ├─ webhook_secret: "iUy1-fNxjT0EhfXmEDll69kDpHuoPljUUWDxYaS8OY"
   │  │  └─ github_token_id: "token-uuid-123"
   │  │
   │  └─ Returns response:
   │     ├─ status: "registered"
   │     ├─ webhook_url: "https://xxxxx.ngrok.io/webhook"
   │     └─ message: "Organization registered!"
   │
   ├─ Frontend shows success message
   │
   └─ User configures webhook on GitHub with:
      ├─ URL: https://xxxxx.ngrok.io/webhook
      ├─ Secret: iUy1-fNxjT0EhfXmEDll69kDpHuoPljUUWDxYaS8OY
      └─ Events: Push events only

✅ REGISTRATION COMPLETE
```

---

## **FLOW 2: WEBHOOK EVENT PROCESSING FLOW**

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEBHOOK EVENT FLOW                            │
└─────────────────────────────────────────────────────────────────┘

1. USER PUSHES CODE TO GITHUB
   │
   ├─ GitHub detects push event
   │
   ├─ GitHub sends webhook to: POST /webhook
   │  ├─ Headers:
   │  │  ├─ X-Hub-Signature-256: sha256=xxxxx
   │  │  ├─ X-GitHub-Event: push
   │  │  └─ Content-Type: application/json
   │  │
   │  └─ Body:
   │     ├─ repository: { full_name: "beta-org-for-pustak/College-ERP" }
   │     ├─ commits: [...]
   │     └─ ref: "refs/heads/main"
   │
   ├─ Backend receives webhook
   │
   ├─ webhook_multi_org() processes:
   │  ├─ Extracts signature from headers
   │  ├─ Looks up org_webhooks table:
   │  │  └─ Query: WHERE webhook_secret = extracted_secret
   │  │
   │  ├─ Finds webhook record:
   │  │  ├─ user_id: "aca20dc6-..."
   │  │  ├─ org_id: "beta-org-for-pustak"
   │  │  ├─ webhook_secret: "iUy1-fNxjT0EhfXmEDll69kDpHuoPljUUWDxYaS8OY"
   │  │  └─ github_token_id: "token-uuid-123"
   │  │
   │  ├─ Verifies signature with org-specific secret
   │  │  └─ Computes: hmac_sha256(webhook_secret, body)
   │  │
   │  └─ Adds webhook context to payload:
   │     └─ _webhook_context: {
   │        ├─ user_id: "aca20dc6-...",
   │        ├─ org_id: "beta-org-for-pustak",
   │        ├─ github_token_id: "token-uuid-123",
   │        └─ webhook_secret: "iUy1-fNxjT0EhfXmEDll69kDpHuoPljUUWDxYaS8OY"
   │     }
   │
   ├─ process_commit_event() stores event:
   │  └─ Inserts into commit_events:
   │     ├─ repo_id: "beta-org-for-pustak/College-ERP"
   │     ├─ commit_sha: "9dcdaa34..."
   │     ├─ user_id: "aca20dc6-..."
   │     ├─ org_id: "beta-org-for-pustak"
   │     ├─ github_token_id: "token-uuid-123"
   │     ├─ processed: FALSE
   │     └─ created_at: NOW()
   │
   └─ Returns 200 OK immediately

✅ EVENT STORED IN DATABASE
```

---

## **FLOW 3: EVENT CONSUMER PROCESSING FLOW**

```
┌─────────────────────────────────────────────────────────────────┐
│                EVENT CONSUMER PROCESSING FLOW                    │
└─────────────────────────────────────────────────────────────────┘

1. EVENT CONSUMER POLLS DATABASE (every 5 seconds)
   │
   ├─ Query: SELECT * FROM commit_events WHERE processed = FALSE
   │
   ├─ Gets event:
   │  ├─ event_id: "ba48c37f-9722-48f5-91f6-81b02126bac3"
   │  ├─ repo_id: "beta-org-for-pustak/College-ERP"
   │  ├─ user_id: "aca20dc6-..."
   │  ├─ org_id: "beta-org-for-pustak"
   │  ├─ github_token_id: "token-uuid-123"
   │  └─ processed: FALSE
   │
   ├─ process_event() extracts context:
   │  ├─ user_id = "aca20dc6-..."
   │  ├─ org_id = "beta-org-for-pustak"
   │  └─ token_id = "token-uuid-123"
   │
   ├─ get_github_token(user_id, token_id):
   │  ├─ Query: SELECT github_token FROM user_github_tokens
   │  │          WHERE user_id = $1 AND token_id = $2
   │  │
   │  ├─ Finds: "ghp_xxxxxxxxxxxxx"
   │  │
   │  └─ Returns decrypted token
   │
   ├─ Falls back to env var if no token found:
   │  └─ github_token = os.getenv("GITHUB_TOKEN")
   │
   ├─ convert_to_webhook_payload():
   │  └─ Converts event to GitHub webhook format
   │
   ├─ handle_push_event(payload, github_token):
   │  ├─ Receives:
   │  │  ├─ payload: webhook format
   │  │  └─ github_token: "ghp_xxxxxxxxxxxxx"
   │  │
   │  ├─ Clones repo:
   │  │  └─ git clone https://x-access-token:ghp_xxxxxxxxxxxxx@github.com/beta-org-for-pustak/College-ERP.git
   │  │
   │  ├─ Generates documentation:
   │  │  ├─ Analyzes changed files
   │  │  ├─ Calls LLM to generate docs
   │  │  └─ Creates /docs folder structure
   │  │
   │  └─ Commits and pushes:
   │     ├─ git add .
   │     ├─ git commit -m "docs: auto-generated documentation"
   │     └─ git push (using same token)
   │
   ├─ Mark event as processed:
   │  └─ UPDATE commit_events SET processed = TRUE WHERE event_id = ...
   │
   └─ Log completion:
      └─ ✅ Event processed successfully

✅ DOCS GENERATED IN GITHUB REPO
```

---

## **FLOW 4: MULTI-ORG SCENARIO FLOW**

```
┌─────────────────────────────────────────────────────────────────┐
│                  MULTI-ORG SCENARIO FLOW                         │
└─────────────────────────────────────────────────────────────────┘

SCENARIO: 3 organizations registered, each pushes code

1. ORG 1 (beta-org-for-pustak) PUSHES CODE
   │
   ├─ Webhook received with secret: "iUy1-fNxjT0EhfXmEDll69kDpHuoPljUUWDxYaS8OY"
   ├─ Looked up in org_webhooks → Found!
   ├─ Event stored with: org_id = "beta-org-for-pustak"
   ├─ Event Consumer gets token for this org
   ├─ Docs generated using ORG 1's token
   └─ ✅ Docs pushed to beta-org-for-pustak/repo

2. ORG 2 (another-org) PUSHES CODE
   │
   ├─ Webhook received with secret: "aB2c-dEfGhIjKlMnOpQrStUvWxYzAbCdEfGhIjKlM"
   ├─ Looked up in org_webhooks → Found!
   ├─ Event stored with: org_id = "another-org"
   ├─ Event Consumer gets token for this org
   ├─ Docs generated using ORG 2's token
   └─ ✅ Docs pushed to another-org/repo

3. ORG 3 (testing-org) PUSHES CODE
   │
   ├─ Webhook received with secret: "xYz9-AbCdEfGhIjKlMnOpQrStUvWxYzAbCdEfGhI"
   ├─ Looked up in org_webhooks → Found!
   ├─ Event stored with: org_id = "testing-org"
   ├─ Event Consumer gets token for this org
   ├─ Docs generated using ORG 3's token
   └─ ✅ Docs pushed to testing-org/repo

DATABASE STATE:
├─ org_webhooks: 3 rows (one per org)
├─ user_github_tokens: 3 rows (one per org)
└─ commit_events: 3 rows (one per push)

✅ ALL 3 ORGS PROCESSED INDEPENDENTLY
```

---

## **FLOW 5: MISSED COMMITS DETECTION FLOW**

```
┌─────────────────────────────────────────────────────────────────┐
│              MISSED COMMITS DETECTION FLOW                       │
└─────────────────────────────────────────────────────────────────┘

SCENARIO: Server was down for 30 minutes, commits were missed

1. EVENT CONSUMER STARTS UP
   │
   ├─ check_missed_commits() called
   │
   ├─ check_missed_commits_all_orgs() executes:
   │  │
   │  ├─ Query: SELECT DISTINCT org_id, repo_id, github_token_id, user_id
   │  │          FROM commit_events WHERE org_id IS NOT NULL
   │  │
   │  ├─ Results:
   │  │  ├─ Row 1: org_id="beta-org-for-pustak", repo_id="beta-org-for-pustak/repo1"
   │  │  ├─ Row 2: org_id="another-org", repo_id="another-org/repo2"
   │  │  └─ Row 3: org_id="testing-org", repo_id="testing-org/repo3"
   │  │
   │  └─ For each repo:
   │
   ├─ PROCESS ORG 1:
   │  ├─ Get token: get_github_token("aca20dc6-...", "token-uuid-1")
   │  ├─ Get last processed: get_last_processed_sha_for_repo("beta-org-for-pustak/repo1")
   │  │  └─ Returns: "9dcdaa34..." (last commit we processed)
   │  │
   │  ├─ Query GitHub: find_missed_commits("beta-org-for-pustak/repo1", "9dcdaa34...")
   │  │  └─ Returns: [commit1, commit2, commit3, commit4, commit5]
   │  │
   │  └─ Store missed commits:
   │     ├─ INSERT INTO commit_events (repo_id, org_id, user_id, github_token_id, ...)
   │     ├─ ✅ Stored: 9dcdaa34
   │     ├─ ✅ Stored: 8ecb9923
   │     ├─ ✅ Stored: 7dba8812
   │     ├─ ✅ Stored: 6ca97701
   │     └─ ✅ Stored: 5b986590
   │
   ├─ PROCESS ORG 2:
   │  ├─ Get token: get_github_token("aca20dc6-...", "token-uuid-2")
   │  ├─ Get last processed: get_last_processed_sha_for_repo("another-org/repo2")
   │  ├─ Query GitHub: find_missed_commits("another-org/repo2", ...)
   │  │  └─ Returns: [commit1, commit2, commit3]
   │  │
   │  └─ Store missed commits:
   │     ├─ ✅ Stored: 4a875489
   │     ├─ ✅ Stored: 3b764378
   │     └─ ✅ Stored: 2c653267
   │
   ├─ PROCESS ORG 3:
   │  ├─ Get token: get_github_token("aca20dc6-...", "token-uuid-3")
   │  ├─ Get last processed: get_last_processed_sha_for_repo("testing-org/repo3")
   │  ├─ Query GitHub: find_missed_commits("testing-org/repo3", ...)
   │  │  └─ Returns: [commit1, commit2]
   │  │
   │  └─ Store missed commits:
   │     ├─ ✅ Stored: 1d542156
   │     └─ ✅ Stored: 0c431045
   │
   └─ 🎉 Successfully recovered 10 missed commits across all orgs!

2. EVENT CONSUMER CONTINUES NORMAL PROCESSING
   │
   ├─ Processes all missed commits:
   │  ├─ Event 1 (org 1): ✅ Processed
   │  ├─ Event 2 (org 1): ✅ Processed
   │  ├─ Event 3 (org 2): ✅ Processed
   │  └─ ... (all 10 events)
   │
   └─ ✅ ALL MISSED COMMITS RECOVERED AND PROCESSED

✅ NO COMMITS LOST DURING DOWNTIME
```

---

## **FLOW 6: ERROR HANDLING FLOW**

```
┌─────────────────────────────────────────────────────────────────┐
│                  ERROR HANDLING FLOW                             │
└─────────────────────────────────────────────────────────────────┘

SCENARIO 1: Webhook secret not found
│
├─ Webhook received with unknown secret
├─ webhook_multi_org() queries org_webhooks
├─ No row found
├─ Returns: 401 Unauthorized
└─ ✅ Webhook rejected safely

SCENARIO 2: GitHub token not found
│
├─ Event Consumer tries to get token
├─ Query user_github_tokens returns NULL
├─ Falls back to: os.getenv("GITHUB_TOKEN")
├─ Uses PUSTAK's token (env var)
├─ Logs: "⚠️  Using GITHUB_TOKEN from env (single-org mode)"
└─ ✅ Graceful fallback

SCENARIO 3: Invalid JWT token
│
├─ Webhook registration called with invalid JWT
├─ get_current_user() fails
├─ Returns: 401 Unauthorized
└─ ✅ Request rejected

SCENARIO 4: Database connection error
│
├─ Event Consumer tries to query database
├─ Connection fails
├─ Exception caught
├─ Logs: "⚠️  Error checking missed commits: ..."
├─ Retries on next poll cycle
└─ ✅ Resilient to temporary failures

SCENARIO 5: GitHub API rate limit
│
├─ Query GitHub for missed commits
├─ GitHub returns 429 (rate limit)
├─ Exception caught
├─ Logs: "⚠️  Error checking org/repo: ..."
├─ Continues with next org
└─ ✅ Continues processing other orgs
```

---

## **QUICK VISUAL SUMMARY**

```
┌────────────────────────────────────────────────────────────────┐
│                    SYSTEM ARCHITECTURE                          │
└────────────────────────────────────────────────────────────────┘

                        GitHub
                          │
                    (push events)
                          │
                          ▼
                    /webhook endpoint
                          │
                    webhook_multi_org()
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
    org_webhooks table              commit_events table
    (webhook secrets)               (events to process)
        │                                   │
        │                                   │
        └─────────────────┬─────────────────┘
                          │
                    Event Consumer
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
  get_github_token()            handle_push_event()
  (from DB or env)              (generate docs)
        │                                   │
        └─────────────────┬─────────────────┘
                          │
                          ▼
                    GitHub (push docs)
                          │
                          ▼
                    ✅ Docs in repo!

┌────────────────────────────────────────────────────────────────┐
│                    DATA FLOW SUMMARY                            │
└────────────────────────────────────────────────────────────────┘

User Registration:
  User → API → org_webhooks table → user_github_tokens table

Event Processing:
  GitHub → webhook → org_webhooks lookup → commit_events store
           → Event Consumer → get_github_token → smart_processor
           → GitHub (docs push)

Missed Commits:
  Event Consumer startup → Query all orgs → get_github_token
  → GitHub API → commit_events store → Event Consumer processes
```
