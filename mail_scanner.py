import os
import imaplib
import email
import json
import datetime
from email.utils import parseaddr
from collections import defaultdict

# ─── HARDCODED CREDENTIALS (replace with your real values) ───────────────
ACCOUNTS = [
    {
        "EMAIL_ADDRESS": "peterclark89@gmail.com",
        "EMAIL_PASSWORD": "ugdsogdnqnuykcbw",  # 16-char Gmail app password
        "IMAP_SERVER":    "imap.gmail.com"
    },
    {
        "EMAIL_ADDRESS": "peterclark89@yahoo.com",
        "EMAIL_PASSWORD": "myvjlbkhujfoazqp",  # 16-char Yahoo app password
        "IMAP_SERVER":    "imap.mail.yahoo.com"
    }
]
# ─────────────────────────────────────────────────────────────────────────


FOLDERS  = ["INBOX", "[Gmail]/Spam", "Inbox", "Bulk"]
DAYS_OLD = 30

# Safelist files
WHITELIST_FILE = "whitelist.json"
BLACKLIST_FILE = "blacklist.json"
APPROVED_FILE  = "approved_senders.json"
ONEOFF_FILE    = "oneoff.json"

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        return default

    if isinstance(default, dict) and 'emails' in default:
        if isinstance(data, list):
            return {'emails': data, 'domains': []}
        if isinstance(data, dict):
            return {
                'emails': data.get('emails', []),
                'domains': data.get('domains', [])
            }

    if isinstance(default, list):
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and 'senders' in data and isinstance(data['senders'], list):
            return data['senders']

    return default

def login_imap(acct):
    m = imaplib.IMAP4_SSL(acct["IMAP_SERVER"])
    m.login(acct["EMAIL_ADDRESS"], acct["EMAIL_PASSWORD"])
    return m

def scan_senders(limit=None):
    whitelist = load_json(WHITELIST_FILE, {'emails': [], 'domains': []})
    blacklist = load_json(BLACKLIST_FILE, {'domains': []})
    approved  = load_json(APPROVED_FILE, [])
    oneoff    = load_json(ONEOFF_FILE, [])

    corporate = set()
    unknown   = {}
    skipped   = {
        "whitelist": defaultdict(int),
        "approved": defaultdict(int),
        "oneoff": defaultdict(int)
    }
    subjects_by_sender = defaultdict(list)

    cutoff = (datetime.date.today() - datetime.timedelta(days=DAYS_OLD))\
             .strftime("%d-%b-%Y")

    for acct in ACCOUNTS:
        print(f"\n📡 Connecting to {acct['EMAIL_ADDRESS']}...")
        mail = login_imap(acct)

        for folder in FOLDERS:
            print(f"\n📂 Scanning folder: {folder}")
            typ, _ = mail.select(folder)
            if typ != 'OK':
                print(f"⚠️ Could not open folder: {folder}")
                continue

            status, data = mail.search(None, f'BEFORE {cutoff}')
            if status != 'OK':
                print(f"⚠️ Search failed in folder: {folder}")
                continue
            ids = data[0].split()
            print(f"📨 {len(ids)} messages older than {DAYS_OLD} days")

            if limit:
                ids = ids[:limit]

            if not ids:
                continue

            for eid in ids:
                status, msg_data = mail.fetch(eid, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])')
                if status != 'OK' or not msg_data or not isinstance(msg_data[0], tuple):
                    continue

                msg = email.message_from_bytes(msg_data[0][1])
                sender = parseaddr(msg.get('From', '') or '')[1].lower()
                subject = msg.get('Subject', '').strip()
                domain = sender.split('@')[-1] if '@' in sender else ''

                if not sender:
                    continue

                if subject and len(subjects_by_sender[sender]) < 5:
                    subjects_by_sender[sender].append(subject)

                print(f"🧪 Checking sender: {sender} | Subject: {subject[:60]}")

                if sender in whitelist['emails'] or domain in whitelist['domains']:
                    skipped["whitelist"][sender] += 1
                    continue
                if sender in approved:
                    skipped["approved"][sender] += 1
                    corporate.add(sender)
                    continue
                if sender in oneoff:
                    skipped["oneoff"][sender] += 1
                    corporate.add(sender)
                    continue

                unknown[sender] = unknown.get(sender, 0) + 1

        mail.logout()

    return sorted(corporate), unknown, skipped, subjects_by_sender

if __name__ == "__main__":
    corp, unk, skipped, subjects = scan_senders(limit=None)

    print("\n\n=== ✅ Corporate senders to clean up ===")
    for s in corp:
        print(f" - {s}")

    print(f"\n=== ❓ Unknown senders ({len(unk)}) ===")
    for s, count in unk.items():
        print(f" - {s}: {count} messages")

    print("\n=== 🚫 Skipped senders ===")
    for category, senders in skipped.items():
        print(f"\n{category.upper()} ({len(senders)} senders):")
        for s, count in senders.items():
            print(f" - {s}: {count} messages")

    print("\n=== 📝 Subjects per unknown sender ===")
    for s, subj_list in subjects.items():
        print(f" - {s}:")
        for subj in subj_list:
            print(f"    • {subj}")
