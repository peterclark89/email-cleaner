# action_cleanup.py

import imaplib
import datetime
import requests
import smtplib
from email.mime.text import MIMEText

# ─── CONFIGURATION ────────────────────────────────────────────────────────
ACCOUNTS = [
    {
        "EMAIL_ADDRESS": "peterclark89@gmail.com",
        "EMAIL_PASSWORD": "ugds ogdn qnuy kcbw",
        "IMAP_SERVER":    "imap.gmail.com",
        "SMTP_SERVER":    "smtp.gmail.com",
        "SMTP_PORT":      465
    },
    {
        "EMAIL_ADDRESS": "peterclark89@yahoo.com",
        "EMAIL_PASSWORD": "myvj lbkh ujfo azqp",
        "IMAP_SERVER":    "imap.mail.yahoo.com",
        "SMTP_SERVER":    "smtp.mail.yahoo.com",
        "SMTP_PORT":      465
    }
]

FOLDERS  = ["INBOX", "[Gmail]/Spam", "Inbox", "Bulk"]
DAYS_OLD = 30
# ──────────────────────────────────────────────────────────────────────────

def login_imap(acct):
    m = imaplib.IMAP4_SSL(acct["IMAP_SERVER"])
    m.login(acct["EMAIL_ADDRESS"], acct["EMAIL_PASSWORD"])
    return m

def login_smtp(acct):
    s = smtplib.SMTP_SSL(acct["SMTP_SERVER"], acct["SMTP_PORT"])
    s.login(acct["EMAIL_ADDRESS"], acct["EMAIL_PASSWORD"])
    return s

def unsubscribe_and_delete_sender(target_sender):
    """
    Unsubscribe & delete all mail older than DAYS_OLD from `target_sender`
    across all configured ACCOUNTS.
    """
    cutoff = (datetime.date.today() - datetime.timedelta(days=DAYS_OLD))\
             .strftime("%d-%b-%Y")

    for acct in ACCOUNTS:
        mail = login_imap(acct)
        smtp = login_smtp(acct)

        for folder in FOLDERS:
            typ, data = mail.select(folder)
            if typ != 'OK':
                continue

            status, data = mail.search(None, f'FROM "{target_sender}" BEFORE {cutoff}')
            if status != 'OK':
                continue
            ids = data[0].split()
            if not ids:
                continue

            fetch_list = b','.join(ids)
            status, parts = mail.fetch(fetch_list,
                                       '(BODY.PEEK[HEADER.FIELDS (LIST-UNSUBSCRIBE)])')
            if status != 'OK':
                continue

            for part in parts:
                if not isinstance(part, tuple):
                    continue
                msg = email.message_from_bytes(part[1])
                unsub_hdr = msg.get("List-Unsubscribe", "")
                # handle HTTP unsub
                for token in unsub_hdr.split(','):
                    t = token.strip().strip('<>')
                    if t.lower().startswith("http"):
                        try:
                            requests.get(t, timeout=10)
                        except:
                            pass
                    elif t.lower().startswith("mailto:"):
                        addr, _, query = t[7:].partition("?")
                        subject = "Unsubscribe"
                        if "subject=" in query:
                            subject = query.split("subject=")[1].split("&")[0]
                        m = MIMEText("")
                        m["From"]    = acct["EMAIL_ADDRESS"]
                        m["To"]      = addr
                        m["Subject"] = subject
                        try:
                            smtp.send_message(m)
                        except:
                            pass

            # mark & expunge
            mail.store(fetch_list, '+FLAGS', '\\Deleted')
            mail.expunge()

        smtp.quit()
        mail.logout()
