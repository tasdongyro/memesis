"""Create the GitHub repository for this project (private by default) and set its topics.

    python tools/create_repo.py            # private
    python tools/create_repo.py --public   # public
"""
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
tok = (ROOT / "Githubtoken.txt").read_text(encoding="utf-8").strip()
H = {"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json"}
SLUG = "eneserdo/memesis"
public = "--public" in sys.argv

r = requests.get(f"https://api.github.com/repos/{SLUG}", headers=H, timeout=20)
if r.status_code == 404:
    r = requests.post("https://api.github.com/user/repos", headers=H, timeout=30, json={
        "name": SLUG.split("/")[1],
        "description": "A programming language for AI agents, written in memes. sus marks what you cannot trust, yolo marks what you cannot undo.",
        "private": not public, "has_wiki": False, "has_projects": False, "auto_init": False})
    print("create:", r.status_code, r.json().get("html_url"))
else:
    print("exists:", r.status_code, r.json().get("html_url"), "private" if r.json().get("private") else "public")
r = requests.put(f"https://api.github.com/repos/{SLUG}/topics", headers=H, timeout=20, json={"names": [
    "ai-agents", "dsl", "programming-language", "memes", "prompt-injection", "taint-tracking", "llm", "python", "interpreter"]})
print("topics:", r.status_code)
