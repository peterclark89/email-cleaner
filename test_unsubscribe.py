import imaplib
import email
import re
import datetime
from email.header import decode_header

# --- CONFIGURE YOUR CREDENTIALS ---
EMAIL_ADDRESS = "peterclark89@gmail.com"
EMAIL_PASSWORD = "ugds ogdn qnuy kcbw"   # your 16-char Gmail app password
IMAP_SERVER = "imap.gmail.com"
FOLDERS = ["INBOX", "[Gmail]/Spam"]    # folders to scan
DAYS_OLD = 30                          # look at emails older than this
# -----------------------------------

def decode_mime_words(s):
    fragments = decode_header(s or "")
    return "".join(
        fragment.decode(enc or "utf-8") if isinstance(fragment, bytes) else fragment
        for fragment, enc in fragments
    )

def preview_unsubscribe():
    # connect & login
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

    # cutoff date for filtering
    cutoff = (datetime.date.today() - datetime.timedelta(days=DAYS_OLD)).strftime("%d-%b-%Y")

    for folder in FOLDERS:
        print(f"\nFolder: {folder}  (emails before {cutoff})")
        mail.select(folder)

        # find old emails
        status, data = mail.search(None, f'BEFORE {cutoff}')
        ids = data[0].split()
        print(f"  ▶️ Found {len(ids)} emails older than {DAYS_OLD} days")

        # preview last 5
        for eid in ids[-5:]:
            status, msg_data = mail.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            subj = decode_mime_words(msg.get("Subject"))
            frm  = decode_mime_words(msg.get("From"))
            unsub_hdr = msg.get("List-Unsubscribe")

            print(f"\n  ✉️  From:    {frm}")
            print(f"     Subject: {subj}")

            if unsub_hdr:
                print(f"     Unsubscribe header: {unsub_hdr}")
                # parse out URL(s)
                urls = re.findall(r'<(http[^>]+)>', unsub_hdr)
                if urls:
                    for url in urls:
                        print(f"       • URL: {url}")
                elif "mailto:" in unsub_hdr:
                    print(f"       • Mailto: {unsub_hdr}")
            else:
                print("     (no List-Unsubscribe header)")

    mail.logout()

if __name__ == "__main__":
    preview_unsubscribe()
