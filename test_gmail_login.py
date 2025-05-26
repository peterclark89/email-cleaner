import imaplib

# --- CONFIGURE YOUR CREDENTIALS ---
EMAIL_ADDRESS = "peterclark89@gmail.com"
EMAIL_PASSWORD = "ugds ogdn qnuy kcbw"  # 16-digit app password from Google
IMAP_SERVER = "imap.gmail.com"
# ----------------------------------

def test_login():
    try:
        print("Connecting to Gmail...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        print("✅ Login successful!")

        print("\nAvailable mailboxes:")
        status, mailboxes = mail.list()
        if status == 'OK':
            for box in mailboxes:
                print(box.decode())
        else:
            print("⚠️ Could not list mailboxes.")

        mail.logout()

    except imaplib.IMAP4.error as e:
        print("❌ Login failed:", e)

if __name__ == "__main__":
    test_login()
