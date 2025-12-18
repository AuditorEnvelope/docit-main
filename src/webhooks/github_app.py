# github_app.py
import time, jwt, os
import requests
from dotenv import load_dotenv
load_dotenv()

APP_ID = os.getenv("GITHUB_APP_ID")
PRIVATE_KEY = os.getenv("GITHUB_PRIVATE_KEY")  # PEM full string, with newlines

def create_jwt():
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": APP_ID
    }
    # PRIVATE_KEY must be a PEM string
    token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
    return token

def get_installation_token(installation_id):
    jwt_token = create_jwt()
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }
    r = requests.post(url, headers=headers)
    r.raise_for_status()
    return r.json()["token"]