# 🔍 DEBUG LOGGING GUIDE

## **What to Look For in Logs**

I've added comprehensive debug logging. Here's what you'll see:

---

## **PHASE 1: Private Key Decoding (On Backend Startup)**

```
✅ Private key decoded successfully
✅ Private key properly decoded (no literal \n)
🔐 Private key first 100 chars: -----BEGIN RSA PRIVATE KEY-----...
🔐 Private key last 100 chars: ...-----END RSA PRIVATE KEY-----
🔐 Private key length: 1704 chars
🔐 Private key newline count: 25
```

**What this tells us:**
- ✅ If you see "no literal \n" → Key is properly decoded
- ❌ If you see "still has literal \n" → Codecs.decode() failed
- The newline count should be around 25 (for your key)

---

## **PHASE 2: JWT Generation (When registering org)**

```
🔐 === JWT GENERATION DEBUG ===
🔐 App ID: 2072879
🔐 Private key type: <class 'str'>
🔐 Private key length: 1704 chars
🔐 Private key starts with: '-----BEGIN RSA PRIVATE KEY-----\n...'
🔐 Private key ends with: '...\n-----END RSA PRIVATE KEY-----\n'
🔐 Newline count (actual): 25
🔐 Backslash-n count (literal): 0
🔐 JWT Payload: {'iat': 1762059429, 'exp': 1762060029, 'iss': '2072879'}
🔐 Attempting to encode with RS256...
✅ JWT Generated successfully
✅ JWT Token length: 500+ chars
✅ JWT Token header: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9
✅ JWT Token payload: eyJpYXQiOjE3NjIwNTk0MjksImV4cCI6MTc2MjA2MDAyOSwiaXNzIjoiMjA3Mjg3OSJ9
✅ JWT Token signature (first 50): kUO8u2WQ1WcVKMquG25JsNBf8Dxv2qye6_qJ3j0yOQUg...
🔐 === JWT GENERATION COMPLETE ===
```

**What this tells us:**
- ✅ Backslash-n count should be 0 (no literal \n)
- ✅ Actual newline count should be 25
- ✅ JWT should generate without errors
- ✅ Signature should be present

---

## **PHASE 3: GitHub API Call**

```
🔐 === GITHUB API CALL DEBUG ===
🔐 JWT Token generated (length: 500+)
🔐 JWT Token header: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9
🔐 JWT Token payload: eyJpYXQiOjE3NjIwNTk0MjksImV4cCI6MTc2MjA2MDAyOSwiaXNzIjoiMjA3Mjg3OSJ9
🔐 JWT Token signature (first 50): kUO8u2WQ1WcVKMquG25JsNBf8Dxv2qye6_qJ3j0yOQUg...
📡 === API REQUEST ===
📡 URL: https://api.github.com/app/installations
📡 Method: GET
📡 Headers: {'Authorization': 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
📡 === API RESPONSE ===
📡 Status Code: 200
✅ Got 6 app installations
✅ Installations: ['Testing-Org-For-Pustak', 'jaishreeram-testing-alpha', ...]
```

**If it FAILS:**
```
📡 Status Code: 401
❌ Failed to get installations: 401
❌ Error response: {"message": "Bad credentials", "documentation_url": "https://docs.github.com/rest", "status": "401"}
📋 Request headers sent: {'Authorization': 'Bearer eyJhbGci...', ...}
📋 Response headers: {...}
🔐 === API CALL FAILED ===
```

---

## **What Each Log Means**

| Log | Meaning |
|-----|---------|
| `✅ Private key properly decoded (no literal \n)` | Key is correct format ✅ |
| `❌ PROBLEM: Private key still has literal \n` | Key NOT decoded properly ❌ |
| `Backslash-n count (literal): 0` | No literal `\n` in key ✅ |
| `Backslash-n count (literal): > 0` | Still has literal `\n` ❌ |
| `✅ JWT Generated successfully` | JWT creation worked ✅ |
| `❌ JWT Generation failed` | JWT creation failed ❌ |
| `Status Code: 200` | GitHub accepted JWT ✅ |
| `Status Code: 401` | GitHub rejected JWT ❌ |

---

## **How to Capture Logs**

1. **Restart backend:**
   ```bash
   bash start_backend.sh
   ```

2. **Register organization** from UI

3. **Copy ALL logs** from the terminal (especially the sections marked with `===`)

4. **Share with me** - especially:
   - Private key decoding phase
   - JWT generation phase
   - GitHub API response phase

---

## **What We're Debugging**

We're trying to answer:

1. **Is the private key being decoded correctly?**
   - Look for: `Backslash-n count (literal): 0` ✅
   - Or: `PROBLEM: Private key still has literal \n` ❌

2. **Is the JWT being generated?**
   - Look for: `✅ JWT Generated successfully` ✅
   - Or: `❌ JWT Generation failed` ❌

3. **Is GitHub accepting the JWT?**
   - Look for: `Status Code: 200` ✅
   - Or: `Status Code: 401` ❌

---

## **Next Steps**

1. Restart backend with new logging
2. Register org
3. Share the logs
4. We'll know EXACTLY what's wrong!

**The logs will tell us everything!** 🔍
