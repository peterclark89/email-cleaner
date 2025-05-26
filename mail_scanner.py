# mail_scanner.py

import os
import imaplib
import email
import json
import datetime
from email.utils import parseaddr

# ─── Load credentials from environment ─────────────────────────────────────
gmail_addr = os.getenv("EMAIL_ADDRESS")
gmail_pass = os.getenv("EMAIL_PASSWORD")
yahoo_addr = os.getenv("YAHOO_EMAIL")
yahoo_pass = os.getenv("YAHOO_PASSWORD")
# ──────────────────────────────────────────────────────────────────────────

# ─── CONFIGURATION: one dict per account ──────────────────────────────────
ACCOUNTS = [
    {
        "EMAIL_ADDRESS": gmail_addr,
        "EMAIL_PASSWORD": gmail_pass,
        "IMAP_SERVER":    "imap.gmail.com"
    },
    {
        "EMAIL_ADDRESS": yahoo_addr,
        "EMAIL_PASSWORD": yahoo_pass,
        "IMAP_SERVER":    "imap.mail.yahoo.com"
    }
]
# ──────────────────────────────────────────────────────────────────────────

# Folders to scan
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

    # whitelist.json → dict with emails/domains
    if isinstance(default, dict) and 'emails' in default:
        if isinstance(data, list):
            return {'emails': data, 'domains': []}
        if isinstance(data, dict):
            return {
                'emails': data.get('emails', []),
                'domains': data.get('domains', [])
            }

    # approved_senders.json / oneoff.json → plain list
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
    """
    Scan all ACCOUNTS & FOLDERS for mail older than DAYS_OLD,
    apply safelists, and return (sorted_corporate_list, unknown_dict).
    """
    whitelist = load_json(WHITELIST_FILE, {'emails': [], 'domains': []})
    blacklist = load_json(BLACKLIST_FILE, {'domains': []})
    approved  = load_json(APPROVED_FILE, [])
    oneoff    = load_json(ONEOFF_FILE, [])

    corporate = set()
    unknown   = {}

    cutoff = (datetime.date.today() - datetime.timedelta(days=DAYS_OLD))\
             .strftime("%d-%b-%Y")

    for acct in ACCOUNTS:
        mail = login_imap(acct)
        for folder in FOLDERS:
            typ, _ = mail.select(folder)
            if typ != 'OK':
                continue

            status, data = mail.search(None, f'BEFORE {cutoff}')
            if status != 'OK':
                continue
            ids = data[0].split()
            if not ids:
                continue

            fetch_list = b','.join(ids)
            status, parts = mail.fetch(fetch_list,
                                       '(BODY.PEEK[HEADER.FIELDS (FROM)])')
            if status != 'OK':
                continue

            for part in parts:
                if not isinstance(part, tuple):
                    continue
                msg = email.message_from_bytes(part[1])
                sender = parseaddr(msg.get('From',''))[1].lower()
                domain = sender.split('@')[-1] if '@' in sender else ''

                # Skip whitelist
                if sender in whitelist['emails'] or domain in whitelist['domains']:
                    continue

                # Corporate auto-cleanup
                if domain in blacklist['domains'] or sender in approved or sender in oneoff:
                    corporate.add(sender)
                else:
                    unknown[sender] = unknown.get(sender, 0) + 1

        mail.logout()

    return sorted(corporate), unknown

if __name__ == "__main__":
    corp, unk = scan_senders(limit=None)
    print("Corporate senders to clean up:")
    for s in corp:
        print(" -", s)
    print(f"\nUnknown senders ({len(unk)})")
    for s,count in unk.items():
        print(f" - {s}: {count}")
