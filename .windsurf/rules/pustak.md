---
trigger: always_on
---

## PUSTAK AI - WINDSURF RULES

### BEFORE ANY SOLUTION - MANDATORY (ANSWER THESE 4 QUESTIONS)

1. EXISTING DATA CHECK: "Can I solve this by querying what's already in the database?"
2. 5-MINUTE FIX: "If I had 5 minutes, what's the simplest thing I could do?"
3. DUMBEST SOLUTION: "What's the most boring, obvious approach?"
4. BASIC OPERATION: "This is just a [database query | if statement | function call]"

### EXISTING DATA STRUCTURES

- commit_events: All commits (idempotent: ON CONFLICT repo_id+commit_sha)
- repositories: User repos with org_id, user_id, doc_persona
- docbook_repos: Docbook repos per org
- GitHub Apps: Reader (2072879, read-only) + Writer (2229202, write-only)
- Users: With subscription tier (free=1 repo, pro=unlimited)

### RED FLAGS - STOP IMMEDIATELY

❌ "System design" / "Architecture" / "Framework"
❌ "Multiple phases" / "Complex workflows"
❌ "Complex algorithms" / "State machines"
❌ "In-memory solutions when database exists"
❌ "Let me create a new service"

### GREEN FLAGS - DEFAULT TO THESE

✅ "Query existing database"
✅ "Add simple database column/flag"
✅ "Check if already exists (idempotent)"
✅ "Simple timestamp check"
✅ "Basic if/else logic"

### COMMON PATTERNS

Duplicate Prevention: INSERT INTO commit_events ON CONFLICT (repo_id, commit_sha) DO UPDATE
Multi-Org Safety: WHERE org_id = $1 AND user_id = $2
Subscription Limits: if user.tier == "free" and count > 1: raise HTTPException(403)
GitHub Tokens: reader_token = get_reader_token() | writer_token = get_writer_token()

### DECISION TREE

Prevent duplicate X? → Is X a commit? Use ON CONFLICT | Is X a repo? Check table | Is X an action? Check DB
Track Y? → Is Y persistent? Store in DB | Is Y temporary? Store in memory | Related to commit? Add to metadata
Filter/categorize Z? → Already in DB? Query WHERE | New? Add if/else | Complex? You're overthinking
Happening too often? → Same event? Check DB duplicates | Different events? Add frequency check | Bug? Check idempotent

### CODING STANDARDS

1. Always use idempotent operations (ON CONFLICT)
2. Always include org_id AND user_id in queries
3. Always check subscription tier before allowing action
4. Always use correct app token (Reader vs Writer)
5. Always log clearly with ✅ or ❌

### ARCHITECTURE

GitHub Webhook → webhook_multi_org → commit_bus.store_event (idempotent) → event_consumer → smart_processor → docbook_publisher → docbook/staging

### FINAL MINDSET

YOUR DEFAULT: "What's the most boring, obvious way to solve this using what already exists?"
NOT: "How can I build a clever system?" "What new framework?" "How scalable?"
REALITY: Simple > Complex. Boring > Clever. Existing > New.
RULE: If database exists and problem is about persistence/duplicates → USE DATABASE
