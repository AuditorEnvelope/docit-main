# 🔴 JWT IS STILL FAILING - HERE'S WHY

## **The Problem**

Your JWT token is being generated but GitHub rejects it with 401 Bad credentials.

The issue is in how we're parsing the escaped newlines.

## **The REAL Solution**

Use Python's `codecs` module which properly handles escaped strings:

**Replace this in `src/utilities/github_app_helper.py` line 20-34:**

```python
def __init__(self):
    self.app_id = os.getenv("GITHUB_APP_ID")
    private_key_raw = os.getenv("GITHUB_PRIVATE_KEY")
    
    # Handle escaped newlines from .env file using codecs
    if private_key_raw:
        # Use codecs to properly decode escaped strings
        import codecs
        self.private_key = codecs.decode(private_key_raw, 'unicode_escape')
    else:
        self.private_key = None
    
    self.app_name = os.getenv("GITHUB_APP_NAME", "lekhak-ai")
    
    if not self.app_id or not self.private_key:
        logger.warning(f"GitHub App credentials not configured: app_id={bool(self.app_id)}, private_key={bool(self.private_key)}")
```

## **Why This Works**

`codecs.decode(string, 'unicode_escape')` properly converts:
- `\n` (literal backslash-n) → actual newline
- `\t` (literal backslash-t) → actual tab
- All other escape sequences

This is the standard Python way to handle escaped strings from .env files.

## **Steps to Fix**

1. Open `src/utilities/github_app_helper.py`
2. Find the `__init__` method (around line 20)
3. Replace lines 20-34 with the code above
4. Save file
5. Restart backend: `bash start_backend.sh`
6. Check logs for JWT success

## **Expected Result**

After fix, you should see:
```
🔐 Private key starts with: -----BEGIN RSA PRIVATE KEY-----
✅ JWT Generated successfully (length: 500+)
✅ Got 6 app installations
✅ Doc-maintainer repo created: Testing-Org-For-Pustak/doc-maintainer
```

## **Why Previous Fix Didn't Work**

The `replace('\\n', '\n')` approach doesn't work because:
- Python string escaping is complex
- `\\n` in a string literal is already a single backslash followed by 'n'
- We need `codecs.decode()` to properly handle the escape sequences

**Use `codecs.decode()` - it's the proper way!** ✅
