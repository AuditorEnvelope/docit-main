# app.py
import hmac, hashlib, os, json
from fastapi import FastAPI, Header, Request, HTTPException
from smart_processor import handle_push_event
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

def verify_sig(secret, payload_body, signature):
    if not signature:
        return False
    sha_name, sig = signature.split('=')
    mac = hmac.new(secret.encode(), msg=payload_body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), sig)

@app.get("/")
async def root():
    return {
        "service": "DocAI webhook",
        "status": "ok",
        "webhook_path": "/webhook"
    }

@app.post("/webhook")
async def webhook(request: Request, x_hub_signature_256: str = Header(None), x_github_event: str = Header(None)):
    body = await request.body()
    if not verify_sig(WEBHOOK_SECRET, body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid signature")
    payload = json.loads(body)
    # only handle push events
    if x_github_event == "push":
        # offload processing (simple: run sync handler but consider queue in prod)
        handle_push_event(payload)
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)