#!/usr/bin/env python3
# --- CONFIGURE YOUR CREDENTIALS ---
EMAIL_ADDRESS  = "peterclark89@gmail.com"
EMAIL_PASSWORD = "ugds ogdn qnuy kcbw"
SMTP_HOST      = "smtp.gmail.com"
SMTP_PORT      = 465
# Point this at wherever your webhook_service is running:
WEBHOOK_URL    = "http://127.0.0.1:5000"
# ------------------------------------

import json
from mail_scanner import scan_senders   # returns (corporate_list, unknown_dict)
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def main():
    # 1. Scan your mailbox
    corporate, unknown = scan_senders(limit=None)
    new_unknown = list(unknown.keys())

    if not new_unknown:
        print("No new unknown senders. Exiting.")
        return

    # 2. Build a single “Manage” link
    manage_link = f"{WEBHOOK_URL}/manage"

    # 3. Create a simple HTML email
    html = f"""
    <html>
      <body>
        <p>You have <strong>{len(new_unknown)}</strong> new unknown senders.</p>
        <p>
          <a href="{manage_link}" style="font-size:16px;
                                           padding:10px 20px;
                                           background:#007bff;
                                           color:#fff;
                                           text-decoration:none;
                                           border-radius:4px;">
            Manage &amp; Classify Senders
          </a>
        </p>
      </body>
    </html>
    """

    # 4. Assemble the message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Nightly Unknown-Senders Digest"
    msg['From']    = EMAIL_ADDRESS
    msg['To']      = EMAIL_ADDRESS
    msg.attach(MIMEText(html, 'html'))

    # 5. Send it
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

    print(f"Sent digest with {len(new_unknown)} new senders. Manage at {manage_link}")

if __name__ == '__main__':
    main()
