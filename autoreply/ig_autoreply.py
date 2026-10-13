"""Comment-to-DM auto-replier for @sujithwithai (runs hourly on GitHub Actions in the separate account's repo).

For every reel listed in kits.json: find new comments containing the reel's keyword (e.g. PROMPT), reply publicly
with a rotating short line, and send ONE private reply (Instagram's comment-to-DM) with the promised link.
Never answers the same comment twice (state file keeps only comment IDs). Skips our own comments.

python ig_autoreply.py [--kits kits.json] [--state state.json] [--dry-run]
Credentials: env IG_ACCESS_TOKEN / IG_USER_ID (Actions secrets), else ~/.secrets/reels.env.
"""
import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:  # GitHub Actions runners don't need it
    pass

API = "https://graph.instagram.com/v23.0"
OWN = "sujithwithai"


def creds():
    tok, uid = os.environ.get("IG_ACCESS_TOKEN"), os.environ.get("IG_USER_ID")
    if tok and uid:
        return tok, uid
    env = {}
    for line in (Path.home() / ".secrets" / "reels.env").read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"')
    return env["IG_ACCESS_TOKEN"], env["IG_USER_ID"]


def call(method, path, tok, params=None, payload=None):
    url = f"{API}/{path}"
    data, headers = None, {}
    if method == "GET":
        url += "?" + urllib.parse.urlencode({**(params or {}), "access_token": tok})
    elif payload is not None:
        data = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {tok}"}
    else:
        data = urllib.parse.urlencode({**(params or {}), "access_token": tok}).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()[:300], "status": e.code}


def comments(media_id, tok):
    out, params = [], {"fields": "id,text,username,timestamp", "limit": 50}
    page = call("GET", f"{media_id}/comments", tok, params)
    while True:
        out += page.get("data", [])
        nxt = page.get("paging", {}).get("next")
        if not nxt:
            return out
        with urllib.request.urlopen(nxt, timeout=60) as r:
            page = json.load(r)


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).parent
    ap.add_argument("--kits", default=str(here / "kits.json"))
    ap.add_argument("--state", default=str(here / "state.json"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    tok, uid = creds()
    kits = json.loads(Path(a.kits).read_text(encoding="utf-8"))
    state_p = Path(a.state)
    state = json.loads(state_p.read_text(encoding="utf-8")) if state_p.exists() else {"handled": []}
    handled = set(state["handled"])
    done = 0
    for kit in kits["reels"]:
        word = re.compile(rf"\b{re.escape(kit['keyword'])}\b", re.I)
        for c in comments(kit["media_id"], tok):
            if c["id"] in handled or c.get("username", "").lower() == OWN or not word.search(c.get("text", "")):
                continue
            reply = kit["public_replies"][len(handled) % len(kit["public_replies"])]
            print(f"[{kit['name']}] comment {c['id']}: reply + DM" + (" (dry run)" if a.dry_run else ""))
            if not a.dry_run:
                r1 = call("POST", f"{c['id']}/replies", tok, params={"message": reply})
                r2 = call("POST", f"{uid}/messages", tok, payload={"recipient": {"comment_id": c["id"]},
                                                                   "message": {"text": kit["dm"]}})
                print("   public reply:", "ok" if "id" in r1 else r1, "| DM:", "ok" if "message_id" in r2 or "id" in r2 else r2)
                if "error" in r2 and "error" in r1:
                    continue  # retry next run
            handled.add(c["id"])
            done += 1
    if not a.dry_run:
        state_p.write_text(json.dumps({"handled": sorted(handled)}, indent=0), encoding="utf-8")
    print(f"handled {done} new comment(s)")


if __name__ == "__main__":
    main()
