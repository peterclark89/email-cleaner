import imaplib
import email
from email.header import decode_header

# --- CONFIGURE YOUR CREDENTIALS ---
EMAIL_ADDRESS = "peterclark89@gmail.com"
EMAIL_PASSWORD = "ugds ogdn qnuy kcbw"
IMAP_SERVER = "imap.gmail.com"
FOLDER = "INBOX"  # Or "[Gmail]/Spam" if you want to test that
MAX_EMAILS = 5
# ----------------------------------

def decode_mime_words(s):
    decoded_fragments = decode_header(s)
    return ''.join([
        fragment.decode(encoding or 'utf-8') if isinstance(fragment, bytes) else fragment
        for fragment, encoding in decoded_fragments
    ])

def fetch_emails():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    mail.select(FOLDER)

    # Search for all emails in folder
    status, data = mail.search(None, 'ALL')
    email_ids = data[0].split()

    print(f"\n📬 Found {len(email_ids)} total emails in '{FOLDER}'. Showing latest {MAX_EMAILS}:\n")

    # Fetch the latest few
    for eid in email_ids[-MAX_EMAILS:]:
        status, msg_data = mail.fetch(eid, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])

        subject = decode_mime_words(msg.get("Subject", ""))
        sender = decode_mime_words(msg.get("From", ""))
        print(f"✉️  From: {sender}")
        print(f"   Subject: {subject}\n")

    mail.logout()

if __name__ == "__main__":
    fetch_emails()
