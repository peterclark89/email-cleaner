import imaplib
import email
from email.header import decode_header
import datetime

# --- CONFIGURE YOUR CREDENTIALS ---
EMAIL_ADDRESS = "peterclark89@gmail.com"
EMAIL_PASSWORD = "ugds ogdn qnuy kcbw"
IMAP_SERVER = "imap.gmail.com"
FOLDER = "INBOX"  # You can change this to "[Gmail]/Spam"
DAYS_OLD = 30
# ----------------------------------

def decode_mime_words(s):
    decoded_fragments = decode_header(s)
    return ''.join([
        fragment.decode(encoding or 'utf-8') if isinstance(fragment, bytes) else fragment
        for fragment, encoding in decoded_fragments
    ])

def fetch_old_emails():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    mail.select(FOLDER)

    # Calculate cutoff date
    date_cutoff = (datetime.date.today() - datetime.timedelta(days=DAYS_OLD)).strftime("%d-%b-%Y")

    print(f"\n📅 Looking for emails older than {DAYS_OLD} days (before {date_cutoff}) in '{FOLDER}'...\n")

    # Search using IMAP's BEFORE filter
    status, data = mail.search(None, f'BEFORE {date_cutoff}')
    email_ids = data[0].split()

    print(f"📬 Found {len(email_ids)} old emails:\n")

    for eid in email_ids[-5:]:  # show last 5 for preview
        status, msg_data = mail.fetch(eid, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        subject = decode_mime_words(msg.get("Subject", ""))
        sender = decode_mime_words(msg.get("From", ""))
        print(f"✉️  From: {sender}")
        print(f"   Subject: {subject}\n")

    mail.logout()

if __name__ == "__main__":
    fetch_old_emails()
