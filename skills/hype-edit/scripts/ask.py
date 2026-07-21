#!/usr/bin/env python3
"""ask.py "<text>" — surface a hype-edit clarifying question (or a status heads-up) to
Marcus's phone via the hypebot Telegram bot, so he sees it even when away from the terminal.

SEND-ONLY by design: the hypebot bot runs its own Telegram `getUpdates` poller, so a second
consumer 409-conflicts with it and can't reliably receive replies (and would disrupt the live
bot). So this surfaces the question; Marcus answers in the terminal (AskUserQuestion / next
message). Tell him so in the text. No-ops (exit 0) when the hypebot secrets are absent, so
the skill still works terminal-only.

  ask.py "Q1: full song or a slice? Q2: which fighter? (reply in the terminal)"
Exit: 0 = sent / no-op, 3 = telegram or config error."""
import sys, os, json, urllib.parse, urllib.request

SECRETS = os.path.expanduser("~/.config/hypebot/secrets.env")


def load_secrets():
    d = {}
    try:
        for ln in open(SECRETS):
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            if ln.startswith("export "):
                ln = ln[7:]
            if "=" in ln:
                k, v = ln.split("=", 1)
                d[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return d.get("HYPEBOT_TOKEN"), d.get("HYPEBOT_CHAT_ID")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 3 if len(sys.argv) < 2 else 0
    text = sys.argv[1]
    token, chat = load_secrets()
    if not token or not chat:
        sys.stderr.write("ask.py: no hypebot secrets — skipped (terminal-only)\n")
        return 0
    try:
        data = urllib.parse.urlencode(
            {"chat_id": chat, "text": text, "disable_web_page_preview": "true"}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        r = json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:
        sys.stderr.write(f"ask.py: sendMessage failed: {e}\n")
        return 3
    print("surfaced to Telegram" if r.get("ok") else f"telegram error: {r}")
    return 0 if r.get("ok") else 3


if __name__ == "__main__":
    sys.exit(main())
