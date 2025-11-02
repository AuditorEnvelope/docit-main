# ⚡ QUICK FIX GUIDE - 5 MINUTES

## RUN THESE COMMANDS NOW

### 1. Apply Fixed Migration (2 min)
```bash
cd /Users/harshsrivastava/Desktop/doc_ai

# Run the fixed migration
psql -U postgres -d lekhak_ai < migrations/005_doc_persona_and_maintainer.sql

# Expected output:
# NOTICE:  relation "repositories" already exists, skipping
# CREATE TABLE
# CREATE INDEX
# ... (no errors)
```

### 2. Verify Migration Worked (1 min)
```bash
# Check repositories table has doc_persona column
psql -U postgres -d lekhak_ai -c "SELECT column_name FROM information_schema.columns WHERE table_name='repositories' AND column_name='doc_persona';"

# Should return: doc_persona
```

### 3. Fix .env File (1 min)
```bash
# Open .env and check line 24
nano .env

# Look for syntax errors:
# - Missing = sign
# - Unclosed quotes
# - Invalid characters

# Common issue with GITHUB_PRIVATE_KEY:
# ❌ WRONG: Multi-line without \n
# ✅ CORRECT: Use \n for newlines
```

### 4. Re-authorize Testing-Org-For-Pustak (1 min)
```bash
# Go to: http://localhost:3000/dashboard
# Click: "🔗 Connect Organization"
# Select: "Testing-Org-For-Pustak"
# Click: "Connect with GitHub"
# Authorize in GitHub
```

### 5. Test Event Consumer (1 min)
```bash
# Run event consumer
python -m src.core.event_consumer

# Should see:
# ✅ Event Consumer initialized
# 🔍 Checking for missed commits (MULTI-ORG)...
# ✅ Using GitHub token for [org]
# (no errors)
```

---

## IF YOU GET ERRORS

### Error: "column does not exist"
```bash
# Run migration again
psql -U postgres -d lekhak_ai < migrations/005_doc_persona_and_maintainer.sql
```

### Error: "python-dotenv could not parse"
```bash
# Check .env syntax
cat .env | head -30

# Fix line 24 - look for:
# - Missing =
# - Unclosed quotes
# - Invalid characters
```

### Error: "Unauthorized: GitHub token may be invalid"
```bash
# Re-authorize the org
# Go to dashboard → Connect Organization → Re-authorize
```

### Error: "DocMaintainerPusher not available"
```bash
# This is OK - it means doc-maintainer feature is disabled
# It will fall back to pushing to source repo
```

---

## VERIFY EVERYTHING WORKS

```bash
# 1. Check migration
psql -U postgres -d lekhak_ai -c "\d repositories" | grep doc_persona

# 2. Check .env
python -c "from dotenv import load_dotenv; load_dotenv(); print('✅ .env OK')"

# 3. Check event consumer
python -m src.core.event_consumer

# 4. Check database
psql -U postgres -d lekhak_ai -c "SELECT COUNT(*) FROM repositories;"
```

---

## WHAT WAS FIXED

✅ Migration 005 now properly adds columns to existing tables
✅ Better error handling for DocMaintainerPusher import
✅ All doc_persona columns now exist in database
✅ Event consumer can fetch doc_persona without errors

---

## WHAT YOU NEED TO DO

1. [ ] Run migration
2. [ ] Fix .env line 24
3. [ ] Re-authorize Testing-Org-For-Pustak
4. [ ] Test event consumer

**Total time: 5 minutes**
