import imaplib
import datetime

# ← your Yahoo creds here
acct = {
    "EMAIL_ADDRESS": "peterclark89@yahoo.com",
    "EMAIL_PASSWORD": "myvj lbkh ujfo azqp",
    "IMAP_SERVER": "imap.mail.yahoo.com"
}

def login_imap(acct):
    m = imaplib.IMAP4_SSL(acct["IMAP_SERVER"])
    m.login(acct["EMAIL_ADDRESS"], acct["EMAIL_PASSWORD"])
    return m

def test_list_mailboxes():
    mail = login_imap(acct)
    print("Connected! Now listing all mailboxes:\n")
    typ, boxes = mail.list()
    if typ != 'OK':
        print("❌ Could not list mailboxes:", boxes)
    else:
        for b in boxes:
            print(" ", b.decode())
    mail.logout()

if __name__ == "__main__":
    test_list_mailboxes()
