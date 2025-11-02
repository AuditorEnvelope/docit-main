# 📊 DOC-MAINTAINER REPO CREATION - CURRENT STATUS

## **WHAT'S HAPPENING**

When you register an organization:

```
✅ Step 1: Org registered in database
✅ Step 2: Webhook stored
❌ Step 3: Doc-maintainer repo creation FAILS
   └─ Reason: JWT authentication failing (401 Bad credentials)
```

---

## **THE ISSUE**

The `get_app_installations()` method tries to use GitHub App JWT authentication, but it's failing because:

```
❌ Failed to get installations: 401 - Bad credentials
```

This happens because the JWT token generation is not working properly with the GitHub private key.

---

## **CURRENT BEHAVIOR**

### **On Organization Registration:**
1. ✅ Org stored in database
2. ✅ Webhook registered
3. ❌ Doc-maintainer repo NOT created (JWT fails)
4. ⚠️ Falls back to skipping doc-maintainer

### **On Push Event:**
1. ✅ Webhook received
2. ✅ Event stored in commit_events
3. ✅ Event consumer processes it
4. ✅ Docs generated to **source repo** (not doc-maintainer)
5. ❌ No doc-maintainer repo exists

---

## **WHAT NEEDS TO BE FIXED**

The `get_app_installations()` method in `GitHubAppHelper` needs to work properly.

**Current code (FAILING):**
```python
async def get_app_installations(self) -> list:
    jwt_token = self._generate_jwt()  # ❌ JWT generation failing
    # Uses JWT to authenticate with GitHub
```

**Why it's failing:**
- JWT token generation might be incorrect
- GitHub private key might be malformed in .env
- JWT signing algorithm might be wrong

---

## **SOLUTION OPTIONS**

### **Option 1: Fix JWT Authentication** (Recommended)
- Debug why JWT generation is failing
- Verify GITHUB_PRIVATE_KEY format in .env
- Test JWT token generation

### **Option 2: Use User Token Instead**
- Use the user's GitHub token (which works)
- Don't rely on GitHub App JWT
- Simpler but less secure

### **Option 3: Skip Doc-Maintainer for Now**
- Keep current behavior (docs go to source repo)
- Implement doc-maintainer later
- Works but not ideal

---

## **IMMEDIATE WORKAROUND**

For now, **docs ARE being generated** on push events, but they go to the **source repository** instead of doc-maintainer.

This is acceptable because:
- ✅ Docs are still generated
- ✅ Users can see them
- ❌ But not in centralized doc-maintainer repo

---

## **NEXT STEPS**

1. **Check .env file:**
   - Verify `GITHUB_PRIVATE_KEY` is properly formatted
   - Should start with `-----BEGIN RSA PRIVATE KEY-----`
   - Should have `\n` for newlines

2. **Test JWT generation:**
   - Add logging to `_generate_jwt()` method
   - See what token is being generated

3. **Fix the issue:**
   - Either fix JWT generation
   - Or switch to user token approach

---

## **SUMMARY**

| Feature | Status | Works? |
|---------|--------|--------|
| Org Registration | ✅ WORKING | Yes |
| Webhook Handling | ✅ WORKING | Yes |
| Doc Generation | ✅ WORKING | Yes (to source repo) |
| Doc-Maintainer Repo | ❌ FAILING | No (JWT auth issue) |
| Doc-Maintainer Push | ❌ BLOCKED | No (repo doesn't exist) |

**Bottom line:** Docs ARE being generated on push, but to the source repo instead of doc-maintainer.

