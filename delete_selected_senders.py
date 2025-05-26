#!/usr/bin/env python3
import imaplib
import json
import os

# ─── CONFIGURATION ─────────────────────────────────────────────
EMAIL_ADDRESS  = os.environ.get("EMAIL_ADDRESS",  "peterclark89@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "ugds ogdn qnuy kcbw")
IMAP_SERVER    = "imap.gmail.com"
# Folders to sweep; must match your IMAP listing exactly
FOLDERS = [
    "INBOX",
    "[Gmail]/All Mail",
    "[Gmail]/Spam",
    "[Gmail]/Trash",
]
# ───────────────────────────────────────────────────────────────

def load_senders():
    """Load approved and one-off senders, filter out blanks."""
    senders = set()
    if os.path.exists("approved_senders.json"):
        senders |= set(json.load(open("approved_senders.json"))["senders"])
    if os.path.exists("oneoff.json"):
        senders |= set(json.load(open("oneoff.json"))["senders"])
    return {s for s in senders if s and "@" in s}

def login_imap():
    m = imaplib.IMAP4_SSL(IMAP_SERVER)
    m.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    return m

def delete_messages_from_sender(mail, sender):
    for folder in FOLDERS:
        # wrap folder in quotes so IMAP handles spaces/slashes
        mb = f'"{folder}"'
        try:
            typ, data = mail.select(mb)
        except imaplib.IMAP4.error:
            # fallback to unquoted if needed
            typ, data = mail.select(folder)
        if typ != 'OK':
            print(f"[!] Couldn't select {folder}: {data}")
            continue

        typ, data = mail.search(None, f'FROM "{sender}"')
        ids = data[0].split()
        if not ids:
            continue

        print(f"→ Deleting {len(ids)} messages from {sender} in {folder}")
        for eid in ids:
            id_str = eid.decode('utf-8')
            mail.store(id_str, '+FLAGS', '\\Deleted')
        mail.expunge()

def main():
    senders = load_senders()
    if not senders:
        print("⚠️  No senders in approved_senders.json or oneoff.json.")
        return

    print(f"Deleting mail for {len(senders)} senders...")
    mail = login_imap()

    for sender in sorted(senders):
        delete_messages_from_sender(mail, sender)

    mail.logout()
    print("✅  Done. All matching messages have been deleted.")

if __name__ == "__main__":
    main()
