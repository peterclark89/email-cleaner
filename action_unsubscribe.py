# action_unsubscribe.py

import imaplib
import email
import re
import datetime
import requests
import smtplib
from email.mime.text import MIMEText
from email.header import decode_header
from email.utils import parseaddr

import os
gmail_addr = os.getenv("EMAIL_ADDRESS")
gmail_pass = os.getenv("EMAIL_PASSWORD")
yahoo_addr = os.getenv("YAHOO_EMAIL")
yahoo_pass = os.getenv("YAHOO_PASSWORD")


# ─── CONFIGURATION ────────────────────────────────────────────────────────
+ ACCOUNTS = [
+     {
+         "EMAIL_ADDRESS": gmail_addr,
+         "EMAIL_PASSWORD": gmail_pass,
+         "IMAP_SERVER":    "imap.gmail.com",
+         "SMTP_SERVER":    "smtp.gmail.com",
+         "SMTP_PORT":      465
+     },
+     {
+         "EMAIL_ADDRESS": yahoo_addr,
+         "EMAIL_PASSWORD": yahoo_pass,
+         "IMAP_SERVER":    "imap.mail.yahoo.com",
+         "SMTP_SERVER":    "smtp.mail.yahoo.com",
+         "SMTP_PORT":      465
+     }
+ ]

FOLDERS        = ["INBOX", "[Gmail]/Spam", "Inbox", "Bulk"]
DAYS_OLD       = 30
MAX_PER_FOLDER = None  # set to an int for testing
# ──────────────────────────────────────────────────────────────────────────

def decode_mime_words(s):
    parts = decode_header(s or "")
    return "".join(
        part.decode(enc or "utf-8") if isinstance(part, bytes) else part
        for part, enc in parts
    )

def login_imap(acct):
    m = imaplib.IMAP4_SSL(acct["IMAP_SERVER"])
    m.login(acct["EMAIL_ADDRESS"], acct["EMAIL_PASSWORD"])
    return m

def login_smtp(acct):
    s = smtplib.SMTP_SSL(acct["SMTP_SERVER"], acct["SMTP_PORT"])
    s.login(acct["EMAIL_ADDRESS"], acct["EMAIL_PASSWORD"])
    return s

def send_unsubscribe_email(acct, to_addr, subject):
    to_addr = to_addr.strip()
    if "@" not in to_addr:
        return
    msg = MIMEText("")
    msg["From"]    = acct["EMAIL_ADDRESS"]
    msg["To"]      = to_addr
    msg["Subject"] = subject
    try:
        with login_smtp(acct) as smtp:
            smtp.send_message(msg)
        print(f"[{acct['EMAIL_ADDRESS']}] Sent unsubscribe to {to_addr}")
    except Exception as e:
        print(f"[!] Failed to send unsubscribe to {to_addr}: {e}")

def process_folder(acct, mail, folder):
    typ, data = mail.select(folder)
    if typ != 'OK':
        return
    cutoff = (datetime.date.today() - datetime.timedelta(days=DAYS_OLD))\
             .strftime("%d-%b-%Y")
    status, data = mail.search(None, f'BEFORE {cutoff}')
    if status != 'OK':
        return
    ids = data[0].split()
    if not ids:
        return
    if MAX_PER_FOLDER:
        ids = ids[-MAX_PER_FOLDER:]
    print(f"[{acct['EMAIL_ADDRESS']}] {folder}: {len(ids)} msgs older than {cutoff}")
    for eid in ids:
        _, msg_data = mail.fetch(eid, "(BODY.PEEK[HEADER.FIELDS (FROM LIST-UNSUBSCRIBE SUBJECT)])")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        frm   = decode_mime_words(msg.get("From",""))
        subj  = decode_mime_words(msg.get("Subject",""))
        unsub = msg.get("List-Unsubscribe","")
        print(f"\n  • From: {frm}\n    Subject: {subj}")
        if unsub:
            # HTTP
            for url in re.findall(r'<(http[^>]+)>', unsub):
                try:
                    r = requests.get(url, timeout=10)
                    print(f"    → Visited URL: {url} → {r.status_code}")
                except Exception as e:
                    print(f"    ⚠️ HTTP unsubscribe failed: {e}")
            # mailto
            for mailto in re.findall(r'<mailto:([^>]+)>', unsub):
                addr, _, q = mailto.partition("?")
                sub = "Unsubscribe"
                m = re.search(r"subject=([^&]+)", q)
                if m:
                    sub = m.group(1)
                send_unsubscribe_email(acct, addr, sub)
        # delete
        mail.store(eid, "+FLAGS", "\\Deleted")
    mail.expunge()

def main():
    for acct in ACCOUNTS:
        print(f"\n=== Cleaning: {acct['EMAIL_ADDRESS']} ===")
        mail = login_imap(acct)
        for folder in FOLDERS:
            process_folder(acct, mail, folder)
        mail.logout()

if __name__ == "__main__":
    main()
