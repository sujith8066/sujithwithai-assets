"""Comment auto-replier for @sujithwithai (runs hourly on GitHub Actions in the separate account's repo).

For every reel listed in kits.json:
- Keyword comments (e.g. PROMPT): reply publicly with a rotating short line, and send ONE private reply
  (Instagram's comment-to-DM) with the promised link.
- Every other genuine comment (Sujith, 16 Oct 2026: "for them also we can respond, 'Agree with you' like that"):
  one short, warm public reply written by Gemini from the reel's topic and the comment. Gemini may answer SKIP
  (spam, abuse, links, gibberish), and then we stay silent. No facts, numbers, links or promises in these replies.
Never answers the same comment twice (state file keeps only comment IDs). Skips our own comments.

python ig_autoreply.py [--kits kits.json] [--state state.json] [--dry-run]
Credentials: env IG_ACCESS_TOKEN / IG_USER_ID / GEMINI_API_KEY (Actions secrets), else ~/.secrets/reels.env.
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
GEMINI = "https://generativelanguage.googleapis.com/v1beta"
OWN = "sujithwithai"
MAX_CHAT_REPLIES = 15  # per run, so a burst of comments never looks like a spam bot


def creds():
    env = {}
    f = Path.home() / ".secrets" / "reels.env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"')
    get = lambda k: os.environ.get(k) or env.get(k)
    return get("IG_ACCESS_TOKEN"), get("IG_USER_ID"), get("GEMINI_API_KEY")


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


def gemini_model(key):
    """Newest Gemini Flash text model this key can use."""
    with urllib.request.urlopen(f"{GEMINI}/models?key={key}&pageSize=200", timeout=60) as r:
        names = [m["name"].split("/")[-1] for m in json.load(r).get("models", [])
                 if "generateContent" in m.get("supportedGenerationMethods", [])]
    best = None
    for n in names:
        m = re.fullmatch(r"gemini-(\d+(?:\.\d+)?)-flash", n)
        if m and (best is None or float(m.group(1)) > best[0]):
            best = (float(m.group(1)), n)
    return best[1] if best else None


RULES = """You reply to Instagram comments on reels by @sujithwithai (Sujith, an Indian creator making short reels
about what people can do with AI). Write ONE short public reply to the comment below, as Sujith.

Rules:
- At most 15 words. Warm, human, casual. At most one emoji.
- Reply in the commenter's language and script (English, Telugu, Hindi, Hinglish...).
- If they agree, thank them or agree back. If they disagree or give a different number, respect it and ask a short
  follow-up question. If they ask a question, ask what they think or thank them for asking; never promise
  future reels, DMs or help. If they answer the reel's call to action (a vote, a number, a plan), react to it. Never argue.
- NO facts, numbers, statistics, links, prices, promises, product names or claims. Don't repeat the reel's numbers.
- Don't mention being an AI or a bot.
- If the comment is spam, abusive, hateful, sexual, a link, self-promotion, only emojis/tags, or makes no sense,
  answer exactly SKIP.

Reel topic: {topic}
Comment from @{user}: {text}

Reply (or SKIP):"""


def chat_reply(key, model, topic, user, text):
    body = {"contents": [{"parts": [{"text": RULES.format(topic=topic, user=user, text=text)}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}}
    req = urllib.request.Request(f"{GEMINI}/models/{model}:generateContent?key={key}",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            parts = json.load(r)["candidates"][0].get("content", {}).get("parts", [])
        out = " ".join(p["text"] for p in parts if p.get("text") and not p.get("thought")).strip().strip('"')
    except Exception as e:  # noqa: BLE001 - any failure means stay silent this run
        print("   gemini error:", str(e)[:120])
        return None
    if not out or out.upper().startswith("SKIP") or "http" in out.lower() or len(out.split()) > 20:
        return "SKIP"
    return out


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).parent
    ap.add_argument("--kits", default=str(here / "kits.json"))
    ap.add_argument("--state", default=str(here / "state.json"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    tok, uid, gkey = creds()
    kits = json.loads(Path(a.kits).read_text(encoding="utf-8"))
    state_p = Path(a.state)
    state = json.loads(state_p.read_text(encoding="utf-8")) if state_p.exists() else {"handled": []}
    handled = set(state["handled"])
    model = gemini_model(gkey) if gkey else None
    print("chat replies:", f"on ({model})" if model else "off (no Gemini key/model)")
    done = chats = 0
    for kit in kits["reels"]:
        word = re.compile(rf"\b{re.escape(kit['keyword'])}\b", re.I) if kit.get("keyword") else None
        for c in comments(kit["media_id"], tok):
            text = c.get("text", "")
            if c["id"] in handled or c.get("username", "").lower() == OWN or not text.strip():
                continue
            if word and word.search(text):
                reply = kit["public_replies"][len(handled) % len(kit["public_replies"])]
                print(f"[{kit['name']}] keyword comment {c['id']}: reply + DM" + (" (dry run)" if a.dry_run else ""))
                if not a.dry_run:
                    r1 = call("POST", f"{c['id']}/replies", tok, params={"message": reply})
                    r2 = call("POST", f"{uid}/messages", tok, payload={"recipient": {"comment_id": c["id"]},
                                                                       "message": {"text": kit["dm"]}})
                    print("   public reply:", "ok" if "id" in r1 else r1, "| DM:", "ok" if "message_id" in r2 or "id" in r2 else r2)
                    if "error" in r2 and "error" in r1:
                        continue  # retry next run
            else:
                if not model or not kit.get("topic") or chats >= MAX_CHAT_REPLIES:
                    continue
                reply = chat_reply(gkey, model, kit["topic"], c.get("username", "someone"), text)
                if reply is None:
                    continue  # Gemini failed: try again next run
                chats += 1
                print(f"[{kit['name']}] comment {c['id']}: {text[:60]!r} -> {reply!r}" + (" (dry run)" if a.dry_run else ""))
                if reply != "SKIP" and not a.dry_run:
                    r1 = call("POST", f"{c['id']}/replies", tok, params={"message": reply})
                    print("   public reply:", "ok" if "id" in r1 else r1)
                    if "error" in r1:
                        continue
            handled.add(c["id"])
            done += 1
    if not a.dry_run:
        state_p.write_text(json.dumps({"handled": sorted(handled)}, indent=0), encoding="utf-8")
    print(f"handled {done} new comment(s)")


if __name__ == "__main__":
    main()
