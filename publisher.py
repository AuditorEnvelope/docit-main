# publisher.py
import os, requests
GITBOOK_KEY = os.getenv("GITBOOK_API_KEY")
GITBOOK_SITE_ID = os.getenv("GITBOOK_SITE_ID")

def publish_to_gitbook(path_on_disk, title, content_md):
    url = f"https://api.gitbook.com/v1/spaces/{GITBOOK_SITE_ID}/pages"
    headers = {"Authorization": f"Bearer {GITBOOK_KEY}", "Content-Type": "application/json"}
    payload = {
        "title": title,
        "content": content_md
    }
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    return r.json()